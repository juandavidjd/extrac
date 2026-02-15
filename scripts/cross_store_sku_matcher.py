#!/usr/bin/env python3
"""
Cross-Store SKU Image Matching
Busca SKUs exactos entre tiendas para clonar imagenes.
"""
import os
import sys
import json
import csv
import requests
import base64
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

DATA_DIR = Path("/opt/odi/data")
REPORTS_DIR = DATA_DIR / "reports"
IMAGE_KB = DATA_DIR / "image_kb/image_hashes.json"

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
    if not sku:
        return ""
    return str(sku).strip().upper().replace(" ", "")

def get_credentials(store):
    if store not in STORES:
        return None, None
    shop_env, token_env = STORES[store]
    return os.getenv(shop_env), os.getenv(token_env)

def get_all_products(store_name):
    """Obtiene todos los productos de una tienda con SKU e imagenes"""
    shop, token = get_credentials(store_name)
    if not shop or not token:
        return []

    products = []
    url = f"https://{shop}/admin/api/2024-01/products.json"
    params = {"limit": 250, "fields": "id,title,variants,images"}

    while url:
        try:
            resp = requests.get(url, headers={"X-Shopify-Access-Token": token}, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for p in data.get("products", []):
                sku = ""
                if p.get("variants"):
                    sku = p["variants"][0].get("sku", "")

                has_image = len(p.get("images", [])) > 0
                image_url = p["images"][0]["src"] if has_image else None

                products.append({
                    "id": p["id"],
                    "title": p["title"],
                    "sku": sku,
                    "sku_normalized": normalize_sku(sku),
                    "has_image": has_image,
                    "image_url": image_url,
                    "store": store_name
                })

            params = {}
            link = resp.headers.get("Link", "")
            if "next" in link:
                for part in link.split(","):
                    if "next" in part:
                        url = part.split(";")[0].strip().strip("<>")
                        break
            else:
                url = None
        except Exception as e:
            print(f"    Error {store_name}: {e}")
            break

    return products

def load_image_kb():
    """Carga el KB de imagenes local"""
    if not IMAGE_KB.exists():
        return {}

    with open(IMAGE_KB) as f:
        kb = json.load(f)

    # Index por SKU normalizado
    sku_index = {}
    for entry in kb["entries"]:
        sku = normalize_sku(entry.get("sku", ""))
        if sku:
            sku_index[sku] = {
                "image_path": entry["image_path"],
                "store": entry["store"],
                "title": entry.get("title", ""),
                "source": "local_kb"
            }

    return sku_index

def main():
    print("=" * 70)
    print("CROSS-STORE SKU IMAGE MATCHING")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Paso 1: Cargar Image KB local
    print("[1/4] Cargando Image KB local...")
    kb_index = load_image_kb()
    print(f"      {len(kb_index)} SKUs en KB local")

    # Paso 2: Obtener todos los productos de todas las tiendas
    print("\n[2/4] Obteniendo productos de todas las tiendas...")
    all_products = []
    products_with_image = []  # Para crear indice de imagenes disponibles
    products_without_image = []

    for store_name in STORES.keys():
        print(f"      {store_name}...", end=" ", flush=True)
        products = get_all_products(store_name)

        with_img = sum(1 for p in products if p["has_image"])
        without_img = sum(1 for p in products if not p["has_image"])
        print(f"{len(products)} productos ({with_img} con img, {without_img} sin img)")

        for p in products:
            if p["has_image"]:
                products_with_image.append(p)
            else:
                products_without_image.append(p)

        all_products.extend(products)

    print(f"\n      Total: {len(all_products)} productos")
    print(f"      Con imagen: {len(products_with_image)}")
    print(f"      Sin imagen: {len(products_without_image)}")

    # Paso 3: Crear indice de imagenes disponibles (Shopify + KB local)
    print("\n[3/4] Creando indice de imagenes disponibles...")

    # Indice de Shopify (SKU -> imagen de otra tienda)
    shopify_sku_index = {}
    for p in products_with_image:
        sku = p["sku_normalized"]
        if sku and sku not in shopify_sku_index:
            shopify_sku_index[sku] = {
                "image_url": p["image_url"],
                "store": p["store"],
                "title": p["title"],
                "source": "shopify"
            }

    print(f"      {len(shopify_sku_index)} SKUs con imagen en Shopify")
    print(f"      {len(kb_index)} SKUs en KB local")

    # Combinar indices (prioridad: KB local > Shopify)
    combined_index = {**shopify_sku_index, **kb_index}
    print(f"      {len(combined_index)} SKUs unicos con imagen disponible")

    # Paso 4: Buscar matches
    print("\n[4/4] Buscando matches para productos sin imagen...")

    matches = []
    no_match = []

    for p in products_without_image:
        sku = p["sku_normalized"]

        if sku and sku in combined_index:
            source_info = combined_index[sku]

            # No matchear consigo mismo (misma tienda)
            if source_info["store"] != p["store"]:
                matches.append({
                    "target_store": p["store"],
                    "target_product_id": p["id"],
                    "target_title": p["title"],
                    "target_sku": p["sku"],
                    "source_store": source_info["store"],
                    "source_title": source_info["title"],
                    "source_type": source_info["source"],
                    "image_url": source_info.get("image_url"),
                    "image_path": source_info.get("image_path")
                })
            else:
                no_match.append(p)
        else:
            no_match.append(p)

    # Guardar resultados
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(REPORTS_DIR / "cross_store_matches.json", "w") as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)

    # Generar CSV de potencial por tienda
    by_target_store = defaultdict(list)
    for m in matches:
        by_target_store[m["target_store"]].append(m)

    csv_path = REPORTS_DIR / "potencial_por_tienda.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Tienda", "Sin_Imagen", "Matches_Cross_Store", "Potencial_%", "Fuentes"])

        for store in STORES.keys():
            sin_img = sum(1 for p in products_without_image if p["store"] == store)
            matches_count = len(by_target_store.get(store, []))
            pct = (matches_count / sin_img * 100) if sin_img > 0 else 0

            # Fuentes de imagenes
            sources = defaultdict(int)
            for m in by_target_store.get(store, []):
                sources[m["source_store"]] += 1
            sources_str = ", ".join([f"{k}:{v}" for k, v in sorted(sources.items(), key=lambda x: -x[1])[:3]])

            writer.writerow([store, sin_img, matches_count, f"{pct:.1f}", sources_str])

    # Reporte
    print()
    print("=" * 70)
    print("REPORTE FINAL")
    print("=" * 70)
    print(f"Productos sin imagen:          {len(products_without_image)}")
    print(f"Matches cross-store:           {len(matches)}")
    print(f"Sin match:                     {len(no_match)}")
    print(f"Potencial de cobertura:        {len(matches) / len(products_without_image) * 100:.1f}%")
    print()

    print("Por tienda destino:")
    print(f"{'Tienda':20} {'SinImg':>8} {'Match':>8} {'%':>8}")
    print("-" * 50)

    for store in sorted(STORES.keys()):
        sin_img = sum(1 for p in products_without_image if p["store"] == store)
        match_count = len(by_target_store.get(store, []))
        pct = (match_count / sin_img * 100) if sin_img > 0 else 0
        if sin_img > 0:
            print(f"{store:20} {sin_img:>8} {match_count:>8} {pct:>7.1f}%")

    print()
    print("Por fuente de imagen:")
    by_source = defaultdict(int)
    by_source_type = defaultdict(int)
    for m in matches:
        by_source[m["source_store"]] += 1
        by_source_type[m["source_type"]] += 1

    print(f"  Shopify: {by_source_type.get('shopify', 0)}")
    print(f"  KB Local: {by_source_type.get('local_kb', 0)}")
    print()
    print("Top fuentes:")
    for store, count in sorted(by_source.items(), key=lambda x: -x[1])[:5]:
        print(f"  {store}: {count}")

    print()
    print("Archivos generados:")
    print(f"  {REPORTS_DIR / 'cross_store_matches.json'}")
    print(f"  {csv_path}")
    print("=" * 70)

if __name__ == "__main__":
    main()
