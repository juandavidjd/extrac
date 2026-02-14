#!/usr/bin/env python3
"""
FASE 1: Upload ORDEN MAESTRA v6 a 15 tiendas Shopify
- Wipe productos existentes
- Subir JSONs de /opt/odi/data/orden_maestra_v6/
- Precio $0 para tiendas sin precio
- Sin imagenes donde no existan
"""

import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')

JSON_PATH = '/opt/odi/data/orden_maestra_v6'

# Mapeo tienda -> env vars
STORES = {
    'DFG': ('DFG_SHOP', 'DFG_TOKEN'),
    'OH_IMPORTACIONES': ('OH_IMPORTACIONES_SHOP', 'OH_IMPORTACIONES_TOKEN'),
    'BARA': ('BARA_SHOP', 'BARA_TOKEN'),
    'DUNA': ('DUNA_SHOP', 'DUNA_TOKEN'),
    'IMBRA': ('IMBRA_SHOP', 'IMBRA_TOKEN'),
    'YOKOMAR': ('YOKOMAR_SHOP', 'YOKOMAR_TOKEN'),
    'JAPAN': ('JAPAN_SHOP', 'JAPAN_TOKEN'),
    'ARMOTOS': ('ARMOTOS_SHOP', 'ARMOTOS_TOKEN'),
    'MCLMOTOS': ('MCLMOTOS_SHOP', 'MCLMOTOS_TOKEN'),
    'CBI': ('CBI_SHOP', 'CBI_TOKEN'),
    'KAIQI': ('KAIQI_SHOP', 'KAIQI_TOKEN'),
    'LEO': ('LEO_SHOP', 'LEO_TOKEN'),
    'VITTON': ('VITTON_SHOP', 'VITTON_TOKEN'),
    'STORE': ('STORE_SHOP', 'STORE_TOKEN'),
    'VAISAND': ('VAISAND_SHOP', 'VAISAND_TOKEN'),
}

API_VERSION = '2024-01'

def get_credentials(store_name):
    shop_var, token_var = STORES[store_name]
    shop = os.getenv(shop_var)
    token = os.getenv(token_var)
    return shop, token

def shopify_request(shop, token, method, endpoint, data=None):
    url = f'https://{shop}/admin/api/{API_VERSION}/{endpoint}'
    headers = {
        'X-Shopify-Access-Token': token,
        'Content-Type': 'application/json'
    }

    for attempt in range(3):
        try:
            if method == 'GET':
                r = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                r = requests.post(url, headers=headers, json=data, timeout=60)
            elif method == 'DELETE':
                r = requests.delete(url, headers=headers, timeout=30)

            # Rate limiting
            if r.status_code == 429:
                retry_after = float(r.headers.get('Retry-After', 2))
                time.sleep(retry_after)
                continue

            return r
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                raise e
    return None

def wipe_store(shop, token, store_name):
    """Elimina todos los productos de una tienda"""
    print(f'  Wiping {store_name}...')

    deleted = 0
    while True:
        # Get batch of products
        r = shopify_request(shop, token, 'GET', 'products.json?limit=250&fields=id')
        if not r or r.status_code != 200:
            print(f'    Error getting products: {r.status_code if r else "no response"}')
            break

        products = r.json().get('products', [])
        if not products:
            break

        for p in products:
            dr = shopify_request(shop, token, 'DELETE', f'products/{p["id"]}.json')
            if dr and dr.status_code in [200, 204]:
                deleted += 1
            time.sleep(0.25)  # Rate limit

    print(f'    Deleted {deleted} products')
    return deleted

def upload_products(shop, token, store_name, products):
    """Sube productos a Shopify"""
    print(f'  Uploading {len(products)} products to {store_name}...')

    uploaded = 0
    errors = 0

    for i, p in enumerate(products):
        # Build Shopify product
        price = p.get('price', 0)
        if price <= 0:
            price = 0

        # Image handling
        images = []
        img = p.get('image', '')
        if img and img.startswith('http') and 'placeholder' not in img:
            images = [{'src': img}]

        product_data = {
            'product': {
                'title': p.get('title', 'Sin titulo'),
                'body_html': p.get('description', ''),
                'vendor': store_name,
                'product_type': p.get('category', 'Repuestos'),
                'tags': [store_name, p.get('system', 'GENERAL')],
                'status': 'active',
                'variants': [{
                    'sku': p.get('sku', ''),
                    'price': str(price),
                    'inventory_management': 'shopify',
                    'inventory_quantity': 10
                }]
            }
        }

        if images:
            product_data['product']['images'] = images

        r = shopify_request(shop, token, 'POST', 'products.json', product_data)

        if r and r.status_code == 201:
            uploaded += 1
        else:
            errors += 1
            if errors <= 3:
                print(f'    Error {i}: {r.status_code if r else "no response"} - {p.get("title", "")[:30]}')

        # Progress
        if (i + 1) % 100 == 0:
            print(f'    Progress: {i+1}/{len(products)} ({uploaded} ok, {errors} err)')

        time.sleep(0.3)  # Rate limit

    print(f'    Completed: {uploaded} uploaded, {errors} errors')
    return uploaded, errors

def main():
    print('='*70)
    print('FASE 1: UPLOAD ORDEN MAESTRA v6 A SHOPIFY')
    print('='*70)
    print()

    results = []

    for store_name in STORES.keys():
        print(f'\n[{store_name}]')
        print('-' * 40)

        # Get credentials
        shop, token = get_credentials(store_name)
        if not shop or not token:
            print(f'  ERROR: No credentials for {store_name}')
            results.append({'store': store_name, 'status': 'NO_CREDENTIALS'})
            continue

        # Load JSON
        json_file = os.path.join(JSON_PATH, f'{store_name}_products.json')
        if not os.path.exists(json_file):
            print(f'  ERROR: JSON not found: {json_file}')
            results.append({'store': store_name, 'status': 'NO_JSON'})
            continue

        with open(json_file, 'r', encoding='utf-8') as f:
            products = json.load(f)

        print(f'  Loaded {len(products)} products from JSON')

        # Wipe existing
        wipe_store(shop, token, store_name)

        # Upload new
        uploaded, errors = upload_products(shop, token, store_name, products)

        results.append({
            'store': store_name,
            'json_count': len(products),
            'uploaded': uploaded,
            'errors': errors
        })

    # Summary
    print('\n' + '='*70)
    print('RESUMEN FINAL')
    print('='*70)
    print()
    print(f'| {"Tienda":<18} | {"JSON":>8} | {"Subidos":>8} | {"Errores":>8} |')
    print(f'|{"-"*20}|{"-"*10}|{"-"*10}|{"-"*10}|')

    total_json = 0
    total_uploaded = 0
    total_errors = 0

    for r in results:
        if 'uploaded' in r:
            print(f'| {r["store"]:<18} | {r["json_count"]:>8} | {r["uploaded"]:>8} | {r["errors"]:>8} |')
            total_json += r['json_count']
            total_uploaded += r['uploaded']
            total_errors += r['errors']
        else:
            print(f'| {r["store"]:<18} | {r["status"]:<28} |')

    print(f'|{"-"*20}|{"-"*10}|{"-"*10}|{"-"*10}|')
    print(f'| {"TOTAL":<18} | {total_json:>8} | {total_uploaded:>8} | {total_errors:>8} |')
    print()

if __name__ == '__main__':
    main()
