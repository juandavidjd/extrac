#!/usr/bin/env python3
"""
Upload PDF Stores (ARMOTOS, VITTON) a Shopify como DRAFT
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')

API_VERSION = '2024-01'

STORES = {
    'ARMOTOS': {
        'shop_var': 'ARMOTOS_SHOP',
        'token_var': 'ARMOTOS_TOKEN',
        'json_path': '/opt/odi/data/pdf_extracted/ARMOTOS/ARMOTOS_extracted.json'
    },
    'VITTON': {
        'shop_var': 'VITTON_SHOP',
        'token_var': 'VITTON_TOKEN',
        'json_path': '/opt/odi/data/pdf_extracted/VITTON/VITTON_extracted.json'
    }
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def shopify_request(shop, token, method, endpoint, data=None):
    url = f'https://{shop}/admin/api/{API_VERSION}/{endpoint}'
    headers = {'X-Shopify-Access-Token': token, 'Content-Type': 'application/json'}

    for attempt in range(5):
        try:
            if method == 'GET':
                r = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                r = requests.post(url, headers=headers, json=data, timeout=60)
            elif method == 'DELETE':
                r = requests.delete(url, headers=headers, timeout=30)

            if r.status_code == 429:
                wait = float(r.headers.get('Retry-After', 2))
                time.sleep(wait)
                continue
            return r
        except Exception as e:
            time.sleep(2 ** attempt)
    return None

def wipe_store(shop, token, store_name):
    log(f"  Wiping {store_name}...")
    deleted = 0
    while True:
        r = shopify_request(shop, token, 'GET', 'products.json?limit=250&fields=id')
        if not r or r.status_code != 200:
            break
        products = r.json().get('products', [])
        if not products:
            break
        for p in products:
            dr = shopify_request(shop, token, 'DELETE', f'products/{p["id"]}.json')
            if dr and dr.status_code in [200, 204]:
                deleted += 1
            time.sleep(0.25)
    log(f"    Deleted {deleted}")
    return deleted

def upload_products(shop, token, store_name, products):
    log(f"  Uploading {len(products)} products (DRAFT)...")
    uploaded = errors = 0

    for i, p in enumerate(products):
        price = p.get('price') or 0

        # Handle local images - convert path to hosted URL would need separate hosting
        # For now, skip local images
        images = []
        img = p.get('image', '')
        if img and img.startswith('http'):
            images = [{'src': img}]

        data = {
            'product': {
                'title': str(p.get('title', 'Sin titulo'))[:255],
                'body_html': p.get('description', ''),
                'vendor': store_name,
                'product_type': p.get('category', 'Repuestos'),
                'tags': [store_name, p.get('category', 'GENERAL')],
                'status': 'draft',
                'variants': [{
                    'sku': str(p.get('sku', ''))[:255],
                    'price': str(price),
                    'inventory_management': 'shopify',
                    'inventory_quantity': 10
                }]
            }
        }

        if images:
            data['product']['images'] = images

        r = shopify_request(shop, token, 'POST', 'products.json', data)
        if r and r.status_code == 201:
            uploaded += 1
        else:
            errors += 1

        if (i + 1) % 50 == 0:
            log(f"    Progress: {i+1}/{len(products)}")

        time.sleep(0.3)

    log(f"    Done: {uploaded} ok, {errors} errors")
    return uploaded, errors

def main():
    log("="*60)
    log("UPLOAD PDF STORES (ARMOTOS, VITTON)")
    log("="*60)

    results = []

    for store_name, config in STORES.items():
        log(f"\n[{store_name}]")
        log("-"*40)

        shop = os.getenv(config['shop_var'])
        token = os.getenv(config['token_var'])

        if not shop or not token:
            log("  ERROR: No credentials")
            continue

        json_path = config['json_path']
        if not os.path.exists(json_path):
            log(f"  ERROR: JSON not found: {json_path}")
            continue

        with open(json_path, 'r') as f:
            products = json.load(f)

        log(f"  Loaded {len(products)} products")

        # Wipe
        wipe_store(shop, token, store_name)

        # Upload
        uploaded, errors = upload_products(shop, token, store_name, products)

        results.append({
            'store': store_name,
            'total': len(products),
            'uploaded': uploaded,
            'errors': errors
        })

    # Summary
    log("\n" + "="*60)
    log("RESUMEN")
    log("="*60)
    for r in results:
        log(f"{r['store']}: {r['uploaded']}/{r['total']} (errors: {r['errors']})")

    total = sum(r['uploaded'] for r in results)
    log(f"\nTOTAL SUBIDOS: {total} productos (DRAFT)")

if __name__ == '__main__':
    main()
