#!/usr/bin/env python3
"""
V22 Store Processor - Procesa tiendas desde CSV crudo
"""
import csv
import json
import sys
import requests
import time
import re
import os
from datetime import datetime
import psycopg2

sys.path.insert(0, "/opt/odi")
from core.ficha_360_template import build_ficha_360

def normalize_title(title):
    if not title:
        return title
    title = title.strip()
    title = re.sub(r"\s+", " ", title)
    if title.isupper():
        lowercase_words = {"de", "del", "la", "el", "los", "las", "para", "con", "sin", "en", "y", "o", "a", "al", "por"}
        words = title.lower().split()
        result = []
        for i, word in enumerate(words):
            if i == 0:
                result.append(word.capitalize())
            elif word in lowercase_words:
                result.append(word.lower())
            else:
                result.append(word.capitalize())
        title = " ".join(result)
    if len(title) > 60:
        title = title[:57].rsplit(" ", 1)[0] + "..."
    return title

def extract_compatibility(title):
    title_lower = title.lower()
    brands = {
        "pulsar": "Pulsar", "discover": "Discover", "boxer": "Boxer",
        "fz": "FZ", "ybr": "YBR", "xtz": "XTZ", "akt": "AKT",
        "tvs": "TVS", "cb": "CB", "bajaj": "Bajaj", "yamaha": "Yamaha",
        "honda": "Honda", "suzuki": "Suzuki", "kawasaki": "Kawasaki"
    }
    matches = []
    for key, val in brands.items():
        if key in title_lower:
            cc_match = re.search(rf"{key}\s*(\d{{2,3}})", title_lower)
            if cc_match:
                matches.append(f"{val} {cc_match.group(1)}")
            else:
                matches.append(val)
    return ", ".join(list(dict.fromkeys(matches))[:4]) if matches else ""

def process_csv(csv_path, empresa):
    products = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        sample = f.read(2048)
        f.seek(0)
        delimiter = ";" if ";" in sample else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            sku = row.get("sku", row.get("SKU", row.get("codigo", ""))).strip()
            titulo = row.get("titulo", row.get("title", row.get("TITULO", ""))).strip()
            precio = row.get("precio", row.get("price", row.get("PRECIO", ""))).strip()
            categoria = row.get("categoria", row.get("category", "")).strip()
            imagen = row.get("imagenes", row.get("image", row.get("imagen", ""))).strip()
            vendor = row.get("vendor", row.get("marca", empresa)).strip()
            
            if not sku or sku in ("None", "null", ""):
                continue
            titulo_normalizado = normalize_title(titulo)
            if not titulo_normalizado:
                continue
            try:
                precio_clean = re.sub(r"[^\d.]", "", str(precio))
                precio_float = float(precio_clean) if precio_clean else 0
            except:
                precio_float = 0
            status = "active" if precio_float > 0 else "draft"
            compatibilidad = extract_compatibility(titulo)
            if not vendor or vendor.upper() == "STORE":
                vendor = empresa
            body_html = build_ficha_360(
                title=titulo_normalizado,
                sku=sku,
                compatibilidad=compatibilidad,
                empresa=empresa,
                extra_info={"categoria": categoria}
            )
            handle_base = re.sub(r"[^a-z0-9]+", "-", titulo_normalizado.lower()).strip("-")
            handle = f"{handle_base}-{empresa.lower()}"[:100]
            products.append({
                "sku": sku,
                "title": titulo_normalizado,
                "handle": handle,
                "body_html": body_html,
                "vendor": vendor,
                "product_type": categoria or "Repuestos",
                "status": status,
                "price": precio_float if precio_float > 0 else 0,
                "inventory_quantity": 10,
                "image_url": imagen if imagen.startswith("http") else None
            })
    return products

def upload_to_shopify(products, shop, token):
    url = f"https://{shop}/admin/api/2024-01/products.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    uploaded = 0
    errors = 0
    for i, p in enumerate(products):
        product_data = {
            "product": {
                "title": p["title"],
                "handle": p["handle"],
                "body_html": p["body_html"],
                "vendor": p["vendor"],
                "product_type": p["product_type"],
                "status": p["status"],
                "variants": [{
                    "sku": p["sku"],
                    "price": str(p["price"]) if p["price"] > 0 else "0",
                    "inventory_management": "shopify",
                    "inventory_quantity": p["inventory_quantity"]
                }]
            }
        }
        if p.get("image_url"):
            product_data["product"]["images"] = [{"src": p["image_url"]}]
        try:
            response = requests.post(url, headers=headers, json=product_data, timeout=30)
            if response.status_code == 201:
                uploaded += 1
            else:
                errors += 1
                if errors < 5:
                    print(f"  Error {p[sku]}: {response.status_code}")
        except Exception as e:
            errors += 1
        time.sleep(0.3)
        if (i + 1) % 100 == 0:
            print(f"  Progreso: {i + 1}/{len(products)} (ok: {uploaded}, err: {errors})")
    return uploaded, errors

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 v22_process_store.py EMPRESA")
        sys.exit(1)
    empresa = sys.argv[1].upper()
    print(f"\n=== V22 PROCESSOR: {empresa} ===")
    print(f"Inicio: {datetime.now().strftime('%H:%M:%S')}")
    data_dir = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data"
    folder_map = {
        "IMBRA": "Imbra", "BARA": "Bara", "DFG": "DFG", "YOKOMAR": "Yokomar",
        "ARMOTOS": "Armotos", "CBI": "CBI", "DUNA": "Duna", "JAPAN": "JAPAN MOTOS",
        "KAIQI": "Kaiqi", "LEO": "Leo", "MCLMOTOS": "MCL Motos",
        "OH_IMPORTACIONES": "OH Importaciones", "STORE": "Store",
        "VAISAND": "Vaisand", "VITTON": "Vitton"
    }
    folder = folder_map.get(empresa, empresa)
    csv_path = f"{data_dir}/{folder}/Base_Datos_{folder}.csv"
    if not os.path.exists(csv_path):
        csv_path = f"{data_dir}/{folder}/Lista_Precios_{folder}.csv"
        if not os.path.exists(csv_path):
            print(f"ERROR: No CSV for {empresa}")
            sys.exit(1)
    print(f"CSV: {csv_path}")
    conn = psycopg2.connect(host="172.18.0.8", port=5432, database="odi",
                            user="odi_user", password="odi_secure_password")
    cur = conn.cursor()
    cur.execute("SELECT shopify_shop_url, shopify_api_password FROM empresas WHERE UPPER(codigo) = %s", (empresa,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        print(f"ERROR: No Shopify config for {empresa}")
        sys.exit(1)
    shop, token = row
    print(f"Shopify: {shop}")
    print("\n[1/2] Procesando CSV...")
    products = process_csv(csv_path, empresa)
    print(f"  Productos: {len(products)}")
    print(f"  Con precio: {sum(1 for p in products if p["price"] > 0)}")
    print(f"  Sin precio: {sum(1 for p in products if p["price"] == 0)}")
    print("\n[2/2] Subiendo a Shopify...")
    uploaded, errors = upload_to_shopify(products, shop, token)
    print(f"\n=== RESULTADO ===")
    print(f"Subidos: {uploaded} | Errores: {errors}")
    print(f"Fin: {datetime.now().strftime('%H:%M:%S')}")
    return uploaded

if __name__ == "__main__":
    main()
