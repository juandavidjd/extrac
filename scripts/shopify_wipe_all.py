#!/usr/bin/env python3
"""
Shopify Wipe All Products - Batch delete con rate limiting
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')

STORES = ['VAISAND','STORE','LEO','KAIQI','VITTON','CBI','MCLMOTOS','BARA','JAPAN','YOKOMAR','IMBRA','DUNA','OH_IMPORTACIONES','ARMOTOS','DFG']
BATCH_SIZE = 50
SLEEP_BETWEEN = 1.0

def get_credentials(store):
    shop = os.getenv(f'{store}_SHOP') or os.getenv(f'SHOPIFY_{store}_SHOP')
    token = os.getenv(f'{store}_TOKEN') or os.getenv(f'SHOPIFY_{store}_TOKEN')
    return shop, token

def get_product_ids(shop, token, limit=250):
    url = f'https://{shop}/admin/api/2024-01/products.json?limit={limit}&fields=id'
    r = requests.get(url, headers={'X-Shopify-Access-Token': token}, timeout=30)
    if r.status_code == 200:
        return [p['id'] for p in r.json().get('products', [])]
    return []

def delete_product(shop, token, product_id):
    url = f'https://{shop}/admin/api/2024-01/products/{product_id}.json'
    r = requests.delete(url, headers={'X-Shopify-Access-Token': token}, timeout=30)
    return r.status_code in [200, 204]

def wipe_store(store):
    shop, token = get_credentials(store)
    if not shop or not token:
        print(f'[{store}] SIN CREDENCIALES')
        return 0
    
    total_deleted = 0
    while True:
        ids = get_product_ids(shop, token)
        if not ids:
            break
        
        for pid in ids[:BATCH_SIZE]:
            if delete_product(shop, token, pid):
                total_deleted += 1
            time.sleep(0.1)  # Rate limit
        
        print(f'[{store}] Eliminados: {total_deleted}')
        time.sleep(SLEEP_BETWEEN)
    
    print(f'[{store}] COMPLETADO - {total_deleted} productos eliminados')
    return total_deleted

if __name__ == '__main__':
    print('='*60)
    print('SHOPIFY WIPE ALL - 15 TIENDAS')
    print('='*60)
    
    grand_total = 0
    for store in STORES:
        deleted = wipe_store(store)
        grand_total += deleted
    
    print('='*60)
    print(f'WIPE COMPLETADO - {grand_total} productos eliminados')
    print('='*60)
