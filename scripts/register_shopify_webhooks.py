#!/usr/bin/env python3
"""Register orders/paid webhooks for all 15 Shopify stores."""
import requests
import os
import json
import time
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

STORES = {
    "BARA": "4jqcki-jq.myshopify.com",
    "YOKOMAR": "u1zmhk-ts.myshopify.com",
    "KAIQI": "u03tqc-0e.myshopify.com",
    "DFG": "0se1jt-q1.myshopify.com",
    "DUNA": "ygsfhq-fs.myshopify.com",
    "IMBRA": "0i1mdf-gi.myshopify.com",
    "JAPAN": "7cy1zd-qz.myshopify.com",
    "LEO": "h1hywg-pq.myshopify.com",
    "STORE": "0b6umv-11.myshopify.com",
    "VAISAND": "z4fpdj-mz.myshopify.com",
    "ARMOTOS": "znxx5p-10.myshopify.com",
    "VITTON": "hxjebc-it.myshopify.com",
    "MCLMOTOS": "v023qz-8x.myshopify.com",
    "CBI": "yrf6hp-f6.myshopify.com",
    "OH_IMPORTACIONES": "6fbakq-sj.myshopify.com",
}

WEBHOOK_ADDRESS = "https://odi.larocamotorepuestos.com/v1/webhook/shopify-order-paid"

def get_token(store_name):
    for key in [
        f"SHOPIFY_{store_name}_TOKEN",
        f"{store_name}_TOKEN",
        f"SHOPIFY_ACCESS_TOKEN_{store_name}",
    ]:
        token = os.getenv(key)
        if token:
            return token
    return None

def list_webhooks(domain, token):
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    r = requests.get(f"https://{domain}/admin/api/2024-10/webhooks.json", headers=headers, timeout=15)
    if r.status_code == 200:
        return r.json().get("webhooks", [])
    return []

def register_webhook(store_name, domain):
    token = get_token(store_name)
    if not token:
        print(f"  SKIP {store_name}: no token found")
        return False

    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}

    # Check if webhook already exists
    existing = list_webhooks(domain, token)
    for wh in existing:
        if wh.get("topic") == "orders/paid" and WEBHOOK_ADDRESS in wh.get("address", ""):
            print(f"  OK {store_name}: webhook already exists (id={wh['id']})")
            return True

    # Register new webhook
    payload = {
        "webhook": {
            "topic": "orders/paid",
            "address": WEBHOOK_ADDRESS,
            "format": "json"
        }
    }
    r = requests.post(
        f"https://{domain}/admin/api/2024-10/webhooks.json",
        headers=headers, json=payload, timeout=15
    )

    if r.status_code == 201:
        wh_id = r.json().get("webhook", {}).get("id", "?")
        print(f"  OK {store_name}: webhook created (id={wh_id})")
        return True
    else:
        print(f"  FAIL {store_name}: {r.status_code} — {r.text[:200]}")
        return False

def main():
    print("=== Registering Shopify orders/paid webhooks ===")
    print(f"Address: {WEBHOOK_ADDRESS}\n")

    results = {}
    for store_name, domain in STORES.items():
        ok = register_webhook(store_name, domain)
        results[store_name] = ok
        time.sleep(0.5)

    print(f"\n{'='*50}")
    ok_count = sum(1 for v in results.values() if v)
    print(f"RESULTS: {ok_count}/{len(results)} stores registered")
    for name, ok in results.items():
        print(f"  {'OK' if ok else 'FAIL'} {name}")

    # Save report
    os.makedirs("/opt/odi/logs", exist_ok=True)
    with open("/opt/odi/logs/webhook_registration.json", "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "address": WEBHOOK_ADDRESS,
            "results": results,
        }, f, indent=2)

if __name__ == "__main__":
    main()
