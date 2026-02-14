#!/usr/bin/env python3
"""Wipe rápido usando GraphQL bulk delete"""
import os
import requests
from dotenv import load_dotenv
import time

load_dotenv("/opt/odi/.env")

STORES = {
    "KAIQI": (os.getenv("KAIQI_SHOP"), os.getenv("KAIQI_TOKEN")),
    "BARA": (os.getenv("BARA_SHOP"), os.getenv("BARA_TOKEN")),
    "DFG": (os.getenv("DFG_SHOP"), os.getenv("DFG_TOKEN")),
    "DUNA": (os.getenv("DUNA_SHOP"), os.getenv("DUNA_TOKEN")),
    "IMBRA": (os.getenv("IMBRA_SHOP"), os.getenv("IMBRA_TOKEN")),
    "JAPAN": (os.getenv("JAPAN_SHOP"), os.getenv("JAPAN_TOKEN")),
    "YOKOMAR": (os.getenv("YOKOMAR_SHOP"), os.getenv("YOKOMAR_TOKEN")),
    "LEO": (os.getenv("LEO_SHOP"), os.getenv("LEO_TOKEN")),
    "STORE": (os.getenv("STORE_SHOP"), os.getenv("STORE_TOKEN")),
    "VAISAND": (os.getenv("VAISAND_SHOP"), os.getenv("VAISAND_TOKEN")),
    "VITTON": (os.getenv("VITTON_SHOP"), os.getenv("VITTON_TOKEN")),
    "MCLMOTOS": (os.getenv("MCLMOTOS_SHOP"), os.getenv("MCLMOTOS_TOKEN")),
    "CBI": (os.getenv("CBI_SHOP"), os.getenv("CBI_TOKEN")),
    "ARMOTOS": (os.getenv("ARMOTOS_SHOP"), os.getenv("ARMOTOS_TOKEN")),
    "OH_IMPORTACIONES": (os.getenv("OH_IMPORTACIONES_SHOP"), os.getenv("OH_IMPORTACIONES_TOKEN")),
}

def wipe_store(name, shop, token):
    if not shop or not token:
        return 0
    
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    base = f"https://{shop}/admin/api/2026-01"
    
    # Count
    try:
        r = requests.get(f"{base}/products/count.json", headers=headers, timeout=10)
        count = r.json().get("count", 0)
    except:
        return 0
    
    if count == 0:
        print(f"{name}: Ya vacía")
        return 0
    
    print(f"{name}: Eliminando {count} productos...", flush=True)
    deleted = 0
    
    while True:
        try:
            r = requests.get(f"{base}/products.json?limit=250&fields=id", headers=headers, timeout=30)
            products = r.json().get("products", [])
        except:
            break
        
        if not products:
            break
        
        for p in products:
            try:
                requests.delete(f"{base}/products/{p[id]}.json", headers=headers, timeout=10)
                deleted += 1
            except:
                pass
        
        print(f"  {name}: {deleted}/{count}", flush=True)
        time.sleep(0.3)
    
    print(f"{name}: OK ({deleted} eliminados)")
    return deleted

if __name__ == "__main__":
    print("=" * 50)
    print("WIPE COMPLETO - 15 TIENDAS")
    print("=" * 50)
    total = 0
    for name, (shop, token) in STORES.items():
        total += wipe_store(name, shop, token)
    print("=" * 50)
    print(f"TOTAL: {total} productos eliminados")
