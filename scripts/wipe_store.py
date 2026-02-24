#!/usr/bin/env python3
import os, sys, time, requests
from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")

store = sys.argv[1] if len(sys.argv) > 1 else "ARMOTOS"
shop = os.getenv(store+"_SHOP") or os.getenv("SHOPIFY_"+store+"_SHOP")
token = os.getenv(store+"_TOKEN") or os.getenv("SHOPIFY_"+store+"_TOKEN")
headers = {"X-Shopify-Access-Token": token}
base = "https://" + shop + "/admin/api/2024-01"

print(f"WIPE {store}", flush=True)
deleted = 0

while True:
    # Get count first
    r = requests.get(base + "/products/count.json", headers=headers, timeout=30)
    count = r.json().get("count", 0)
    if count == 0:
        break
    
    # Get products
    r = requests.get(base + "/products.json?limit=250&fields=id", headers=headers, timeout=30)
    products = r.json().get("products", [])
    if not products:
        time.sleep(2)
        continue
    
    # Delete batch
    for p in products[:50]:
        try:
            requests.delete(base + "/products/" + str(p["id"]) + ".json", headers=headers, timeout=30)
            deleted += 1
        except:
            pass
        time.sleep(0.1)
    
    print(f"{store}: {deleted} eliminados, {count-50} restantes", flush=True)
    time.sleep(1)

print(f"WIPE {store} COMPLETO: {deleted} eliminados", flush=True)
