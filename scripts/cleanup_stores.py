#!/usr/bin/env python3
"""
Limpieza de tiendas: OH_IMPORTACIONES, ARMOTOS, VITTON
"""
import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")
API_VERSION = "2024-01"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def shopify_request(shop, token, method, endpoint, data=None):
    url = f"https://{shop}/admin/api/{API_VERSION}/{endpoint}"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    
    for attempt in range(5):
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                r = requests.post(url, headers=headers, json=data, timeout=60)
            elif method == "DELETE":
                r = requests.delete(url, headers=headers, timeout=30)
            
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", 2))
                time.sleep(wait)
                continue
            return r
        except:
            time.sleep(2 ** attempt)
    return None

def wipe_store(shop, token, store_name):
    log(f"  Wiping {store_name}...")
    deleted = 0
    while True:
        r = shopify_request(shop, token, "GET", "products.json?limit=250&fields=id")
        if not r or r.status_code != 200:
            break
        products = r.json().get("products", [])
        if not products:
            break
        for p in products:
            pid = p["id"]
            dr = shopify_request(shop, token, "DELETE", f"products/{pid}.json")
            if dr and dr.status_code in [200, 204]:
                deleted += 1
            time.sleep(0.25)
        log(f"    Deleted batch... total: {deleted}")
    return deleted

def upload_products(shop, token, store_name, products):
    log(f"  Uploading {len(products)} products...")
    uploaded = errors = 0
    
    for i, p in enumerate(products):
        price = p.get("price", 0) or 0
        images = []
        img = p.get("image", "")
        if img and isinstance(img, str) and img.startswith("http") and "placeholder" not in img:
            images = [{"src": img}]
        
        data = {
            "product": {
                "title": str(p.get("title", "Sin titulo"))[:255],
                "body_html": p.get("description", "") or "",
                "vendor": store_name,
                "product_type": p.get("category", "Repuestos"),
                "tags": [store_name, p.get("system", "GENERAL")],
                "status": "draft",
                "variants": [{
                    "sku": str(p.get("sku", ""))[:255],
                    "price": str(price),
                    "inventory_management": "shopify",
                    "inventory_quantity": 10
                }]
            }
        }
        if images:
            data["product"]["images"] = images
        
        r = shopify_request(shop, token, "POST", "products.json", data)
        if r and r.status_code == 201:
            uploaded += 1
        else:
            errors += 1
        
        if (i + 1) % 200 == 0:
            log(f"    Progress: {i+1}/{len(products)} ({uploaded} ok)")
        time.sleep(0.3)
    
    return uploaded, errors

def get_count(shop, token):
    r = shopify_request(shop, token, "GET", "products/count.json")
    return r.json().get("count", 0) if r else 0

# Store configs
STORES = [
    {
        "name": "OH_IMPORTACIONES",
        "json_path": "/opt/odi/data/orden_maestra_v6/OH_IMPORTACIONES_products.json",
        "expected": 1414
    },
    {
        "name": "ARMOTOS",
        "json_path": "/opt/odi/data/pdf_extracted/ARMOTOS/ARMOTOS_extracted.json",
        "expected": 1953
    },
    {
        "name": "VITTON",
        "json_path": "/opt/odi/data/pdf_extracted/VITTON/VITTON_extracted.json",
        "expected": 160
    }
]

log("=" * 60)
log("LIMPIEZA DE TIENDAS - OH_IMPORTACIONES, ARMOTOS, VITTON")
log("=" * 60)

results = []

for store_config in STORES:
    store_name = store_config["name"]
    json_path = store_config["json_path"]
    expected = store_config["expected"]
    
    log(f"\n[{store_name}]")
    log("-" * 40)
    
    shop = os.getenv(f"{store_name}_SHOP")
    token = os.getenv(f"{store_name}_TOKEN")
    
    if not shop or not token:
        log("  ERROR: No credentials")
        continue
    
    # Current count
    current = get_count(shop, token)
    log(f"  Current: {current} productos")
    
    # Load JSON
    with open(json_path, "r") as f:
        products = json.load(f)
    log(f"  JSON: {len(products)} productos (expected: {expected})")
    
    # Wipe
    deleted = wipe_store(shop, token, store_name)
    log(f"  Deleted: {deleted}")
    
    # Upload
    uploaded, errors = upload_products(shop, token, store_name, products)
    
    # Final count
    final = get_count(shop, token)
    log(f"  FINAL: {final} productos")
    
    results.append({
        "store": store_name,
        "before": current,
        "deleted": deleted,
        "uploaded": uploaded,
        "errors": errors,
        "final": final,
        "expected": expected
    })

log("\n" + "=" * 60)
log("RESUMEN")
log("=" * 60)
for r in results:
    status = "OK" if r["final"] == r["expected"] else "CHECK"
    log(f"{r[store]}: {r[before]} -> {r[final]} (expected: {r[expected]}) [{status}]")
