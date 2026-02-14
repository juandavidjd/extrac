#!/usr/bin/env python3
import os, sys, json, time
import requests
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')

def upload_store(empresa_key):
    shop = os.getenv(f'{empresa_key}_SHOP')
    token = os.getenv(f'{empresa_key}_TOKEN')
    
    if not shop or not token:
        print(f'{empresa_key}: No configurado')
        return 0
    
    products_file = f'/opt/odi/data/processed/{empresa_key}/products_ready.json'
    if not os.path.exists(products_file):
        print(f'{empresa_key}: No hay productos procesados')
        return 0
    
    with open(products_file) as f:
        products = json.load(f)
    
    print(f'{empresa_key}: Subiendo {len(products)} productos a {shop}')
    
    headers = {'X-Shopify-Access-Token': token, 'Content-Type': 'application/json'}
    base_url = f'https://{shop}/admin/api/2026-01/products.json'
    
    uploaded = 0
    errors = 0
    
    for i, p in enumerate(products, 1):
        payload = {
            'product': {
                'title': p.get('title', 'Sin titulo'),
                'body_html': p.get('body_html', ''),
                'vendor': p.get('vendor', empresa_key),
                'product_type': p.get('category', 'Repuesto'),
                'tags': p.get('tags', ''),
                'status': 'active',
                'variants': [{
                    'sku': p.get('sku', ''),
                    'price': str(p.get('price', 0)),
                    'inventory_management': 'shopify',
                    'inventory_quantity': p.get('quantity', 0)
                }]
            }
        }
        
        try:
            r = requests.post(base_url, headers=headers, json=payload, timeout=30)
            if r.status_code == 201:
                uploaded += 1
            else:
                errors += 1
        except:
            errors += 1
        
        if i % 50 == 0:
            print(f'  {i}/{len(products)} ({uploaded} OK, {errors} err)')
        
        time.sleep(0.5)
    
    print(f'{empresa_key}: COMPLETADO - {uploaded}/{len(products)} subidos')
    return uploaded

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 upload_to_shopify.py EMPRESA_KEY')
        sys.exit(1)
    upload_store(sys.argv[1])
