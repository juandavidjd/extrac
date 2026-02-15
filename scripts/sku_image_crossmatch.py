#!/usr/bin/env python3
"""
Fase 2: Cruce Deterministico SKU vs Image KB
READ-ONLY - Solo genera reportes, no sube nada.
"""
import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

DATA_DIR = Path("/opt/odi/data")
IMAGE_KB = DATA_DIR / "image_kb/image_hashes.json"
REPORTS_DIR = DATA_DIR / "reports"

STORES = {
    "DFG": ("DFG_SHOP", "DFG_TOKEN"),
    "ARMOTOS": ("ARMOTOS_SHOP", "ARMOTOS_TOKEN"),
    "OH_IMPORTACIONES": ("OH_IMPORTACIONES_SHOP", "OH_IMPORTACIONES_TOKEN"),
    "DUNA": ("DUNA_SHOP", "DUNA_TOKEN"),
    "IMBRA": ("IMBRA_SHOP", "IMBRA_TOKEN"),
    "YOKOMAR": ("YOKOMAR_SHOP", "YOKOMAR_TOKEN"),
    "JAPAN": ("JAPAN_SHOP", "JAPAN_TOKEN"),
    "BARA": ("BARA_SHOP", "BARA_TOKEN"),
    "MCLMOTOS": ("MCLMOTOS_SHOP", "MCLMOTOS_TOKEN"),
    "CBI": ("CBI_SHOP", "CBI_TOKEN"),
    "VITTON": ("VITTON_SHOP", "VITTON_TOKEN"),
    "KAIQI": ("KAIQI_SHOP", "KAIQI_TOKEN"),
    "LEO": ("LEO_SHOP", "LEO_TOKEN"),
    "STORE": ("STORE_SHOP", "STORE_TOKEN"),
    "VAISAND": ("VAISAND_SHOP", "VAISAND_TOKEN"),
}

def normalize_sku(sku):
    """Normaliza SKU: strip, uppercase, sin espacios extras"""
    if not sku:
        return ""
    return str(sku).strip().upper().replace(" ", "")

def load_image_kb():
    """Carga el KB de imagenes y crea indice por SKU normalizado"""
    if not IMAGE_KB.exists():
        print(f"ERROR: {IMAGE_KB} no existe. Ejecuta build_image_kb.py primero.")
        sys.exit(1)

    with open(IMAGE_KB) as f:
        kb = json.load(f)

    # Crear indice SKU -> imagen
    sku_index = {}
    for entry in kb["entries"]:
        sku = normalize_sku(entry.get("sku", ""))
        if sku:
            if sku not in sku_index:
                sku_index[sku] = []
            sku_index[sku].append({
                "store": entry["store"],
                "image_path": entry["image_path"],
                "title": entry.get("title", ""),
                "phash": entry["hashes"]["phash"]
            })

    return sku_index, kb["stats"]["total"]

def get_products_without_image(store_name, shop_env, token_env):
    """Obtiene productos sin imagen de una tienda Shopify"""
    shop = os.getenv(shop_env)
    token = os.getenv(token_env)

    if not shop or not token:
        return []

    products_no_img = []
    url = f"https://{shop}/admin/api/2024-01/products.json"
    params = {"limit": 250, "fields": "id,title,variants,images"}

    while url:
        try:
            resp = requests.get(url, headers={"X-Shopify-Access-Token": token}, params=params)
            resp.raise_for_status()
            data = resp.json()

            for p in data.get("products", []):
                if not p.get("images"):
                    sku = ""
                    if p.get("variants"):
                        sku = p["variants"][0].get("sku", "")
                    products_no_img.append({
                        "id": p["id"],
                        "title": p["title"],
                        "sku": sku,
                        "sku_normalized": normalize_sku(sku)
                    })

            # Paginacion
            params = {}
            link_header = resp.headers.get("Link", "")
            next_url = None
            if "next" in link_header:
                for part in link_header.split(","):
                    if "next" in part:
                        next_url = part.split(";")[0].strip().strip("<>")
                        break
            url = next_url

        except Exception as e:
            print(f"  Error {store_name}: {e}")
            break

    return products_no_img

def main():
    print("=" * 70)
    print("FASE 2: CRUCE DETERMINISTICO SKU vs IMAGE KB")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("Modo: READ-ONLY (no sube imagenes)")
    print()

    # Cargar KB
    print("[1/3] Cargando Image KB...")
    sku_index, total_kb = load_image_kb()
    print(f"      {total_kb} imagenes en KB")
    print(f"      {len(sku_index)} SKUs unicos indexados")

    # Obtener productos sin imagen de todas las tiendas
    print("\n[2/3] Obteniendo productos sin imagen de Shopify...")
    all_products_no_img = []

    for store_name, (shop_env, token_env) in STORES.items():
        products = get_products_without_image(store_name, shop_env, token_env)
        for p in products:
            p["store"] = store_name
        all_products_no_img.extend(products)
        if products:
            print(f"      {store_name}: {len(products)} sin imagen")

    print(f"      TOTAL: {len(all_products_no_img)} productos sin imagen")

    # Cruce SKU exacto
    print("\n[3/3] Ejecutando cruce SKU exacto...")
    exact_matches = []
    unmatched = []

    for p in all_products_no_img:
        sku_norm = p["sku_normalized"]
        if sku_norm and sku_norm in sku_index:
            matches = sku_index[sku_norm]
            exact_matches.append({
                "product_id": p["id"],
                "store": p["store"],
                "title": p["title"],
                "sku": p["sku"],
                "matches": matches
            })
        else:
            unmatched.append({
                "product_id": p["id"],
                "store": p["store"],
                "title": p["title"],
                "sku": p["sku"]
            })

    # Guardar reportes
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(REPORTS_DIR / "sku_exact_matches.json", "w") as f:
        json.dump(exact_matches, f, indent=2, ensure_ascii=False)

    with open(REPORTS_DIR / "sku_unmatched.json", "w") as f:
        json.dump(unmatched, f, indent=2, ensure_ascii=False)

    # Reporte
    total_no_img = len(all_products_no_img)
    total_matched = len(exact_matches)
    coverage = (total_matched / total_no_img * 100) if total_no_img > 0 else 0

    print()
    print("=" * 70)
    print("REPORTE FINAL")
    print("=" * 70)
    print(f"Total productos sin imagen:    {total_no_img}")
    print(f"Matches exactos por SKU:       {total_matched}")
    print(f"Sin match:                     {len(unmatched)}")
    print(f"Cobertura inmediata:           {coverage:.1f}%")
    print()
    print("Archivos generados:")
    print(f"  {REPORTS_DIR / 'sku_exact_matches.json'}")
    print(f"  {REPORTS_DIR / 'sku_unmatched.json'}")
    print("=" * 70)

    # Desglose por tienda
    print("\nDesglose por tienda:")
    by_store_matched = {}
    by_store_unmatched = {}
    for m in exact_matches:
        s = m["store"]
        by_store_matched[s] = by_store_matched.get(s, 0) + 1
    for u in unmatched:
        s = u["store"]
        by_store_unmatched[s] = by_store_unmatched.get(s, 0) + 1

    all_stores = set(by_store_matched.keys()) | set(by_store_unmatched.keys())
    print(f"{'Tienda':20} {'Match':>8} {'NoMatch':>8} {'Pct':>8}")
    print("-" * 50)
    for store in sorted(all_stores):
        m = by_store_matched.get(store, 0)
        u = by_store_unmatched.get(store, 0)
        t = m + u
        pct = (m / t * 100) if t > 0 else 0
        print(f"{store:20} {m:>8} {u:>8} {pct:>7.1f}%")

if __name__ == "__main__":
    main()
