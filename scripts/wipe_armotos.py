#!/usr/bin/env python3
import os, time, requests
from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")
shop = os.getenv("ARMOTOS_SHOP") or os.getenv("SHOPIFY_ARMOTOS_SHOP")
token = os.getenv("ARMOTOS_TOKEN") or os.getenv("SHOPIFY_ARMOTOS_TOKEN")
headers = {"X-Shopify-Access-Token": token}
deleted = 0
while True:
    r = requests.get(f"https://{shop}/admin/api/2024-01/products.json?limit=250&fields=id", headers=headers, timeout=30)
    ids = [p["id"] for p in r.json().get("products", [])] if r.ok else []
    if not ids: break
    for pid in ids[:50]:
        requests.delete(f"https://{shop}/admin/api/2024-01/products/{pid}.json", headers=headers, timeout=30)
        deleted += 1
        time.sleep(0.1)
    print(f"Eliminados: {deleted}", flush=True)
    time.sleep(1)
print(f"WIPE COMPLETO: {deleted}")

