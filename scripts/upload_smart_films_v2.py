#!/usr/bin/env python3
import os
import json
import base64
import httpx
from dotenv import load_dotenv
import time
import re

load_dotenv('/opt/odi/.env')

SHOP = os.getenv('ARMOTOS_SHOP')
TOKEN = os.getenv('ARMOTOS_TOKEN')
API_VERSION = '2025-01'
BASE_URL = f'https://{SHOP}/admin/api/{API_VERSION}'
HEADERS = {'X-Shopify-Access-Token': TOKEN, 'Content-Type': 'application/json'}
IMAGES_DIR = '/opt/odi/data/ARMOTOS/smart_film_images'

print('=== UPLOAD PELICULAS A SHOPIFY v2 ===')

images = [f for f in os.listdir(IMAGES_DIR) if f.endswith('.png')]
print(f'Imagenes: {len(images)}')

# Build SKU mapping with proper pagination
print('Mapeando SKUs (todas las paginas)...')
sku_to_product = {}

# Use since_id pagination
since_id = 0
page = 0
while True:
    page += 1
    url = f'{BASE_URL}/products.json?limit=250&since_id={since_id}&fields=id,variants'
    resp = httpx.get(url, headers=HEADERS, timeout=60)
    products = resp.json().get('products', [])
    
    if not products:
        break
    
    for p in products:
        since_id = max(since_id, p['id'])
        for v in p.get('variants', []):
            sku = v.get('sku', '')
            if sku:
                # Normalize: remove leading zeros
                norm = str(int(sku)) if sku.isdigit() else sku
                sku_to_product[norm] = p['id']
    
    if page % 10 == 0:
        print(f'  Pagina {page}: {len(sku_to_product)} SKUs')

print(f'Total SKUs mapeados: {len(sku_to_product)}')

# Upload images
uploaded = skipped = failed = 0

for i, fn in enumerate(images):
    # Extract SKU
    parts = fn.replace('.png', '').split('_')
    sku = None
    for j, p in enumerate(parts):
        if p == 'sku' and j+1 < len(parts):
            sku = parts[j+1]
            break
    
    if not sku or sku not in sku_to_product:
        skipped += 1
        continue
    
    pid = sku_to_product[sku]
    path = os.path.join(IMAGES_DIR, fn)
    
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    
    try:
        r = httpx.post(
            f'{BASE_URL}/products/{pid}/images.json',
            headers=HEADERS,
            json={'image': {'attachment': data, 'position': 2, 'alt': f'Vista catalogo {sku}'}},
            timeout=90
        )
        if r.status_code in [200, 201]:
            uploaded += 1
        else:
            failed += 1
            if failed <= 3:
                print(f'  Error {r.status_code} for {sku}')
    except Exception as e:
        failed += 1
    
    if (i+1) % 50 == 0:
        print(f'  {i+1}/{len(images)} | ok:{uploaded} skip:{skipped} fail:{failed}')
    
    # Rate limit: 2 requests per second
    time.sleep(0.5)

print(f'\n=== COMPLETADO ===')
print(f'Subidos: {uploaded}')
print(f'Saltados: {skipped}')
print(f'Fallidos: {failed}')
