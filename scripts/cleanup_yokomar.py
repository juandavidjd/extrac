#!/usr/bin/env python3
"""
YOKOMAR Emergency Cleanup - 33,000 -> 1,000 productos
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

shop = os.getenv("YOKOMAR_SHOP")
token = os.getenv("YOKOMAR_TOKEN")

log("=" * 60)
log("YOKOMAR EMERGENCY CLEANUP")
log("33,000 -> 1,000 productos")
log("=" * 60)

# Wipe ALL
log("Wiping YOKOMAR (this will take a while)...")
deleted = 0
batch = 0
while True:
    r = shopify_request(shop, token, "GET", "products.json?limit=250&fields=id")
    if not r or r.status_code != 200:
        break
    products = r.json().get("products", [])
    if not products:
        break
    batch += 1
    for p in products:
        pid = p["id"]
        dr = shopify_request(shop, token, "DELETE", f"products/{pid}.json")
        if dr and dr.status_code in [200, 204]:
            deleted += 1
        time.sleep(0.2)
    log(f"  Batch {batch}: {deleted} deleted total")

log(f"Wipe complete: {deleted} deleted")

# Load JSON
with open("/opt/odi/data/orden_maestra_v6/YOKOMAR_products.json", "r") as f:
    products = json.load(f)
log(f"Uploading {len(products)} products...")

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
            "vendor": "YOKOMAR",
            "product_type": p.get("category", "Repuestos"),
            "tags": ["YOKOMAR", p.get("system", "GENERAL")],
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
    
    if (i + 1) % 100 == 0:
        log(f"  Progress: {i+1}/{len(products)} ({uploaded} ok)")
    time.sleep(0.3)

# Final
r = shopify_request(shop, token, "GET", "products/count.json")
final = r.json().get("count", 0) if r else 0

log("=" * 60)
log(f"YOKOMAR CLEANUP COMPLETE")
log(f"Final: {final} productos (expected: 1000)")
log("=" * 60)
