#!/usr/bin/env python3
import os
import json
import base64
import httpx
from dotenv import load_dotenv
import time

load_dotenv('/opt/odi/.env')

SHOP = os.getenv('ARMOTOS_SHOP')
TOKEN = os.getenv('ARMOTOS_TOKEN')
API_VERSION = '2025-01'
BASE_URL = f'https://{SHOP}/admin/api/{API_VERSION}'
HEADERS = {'X-Shopify-Access-Token': TOKEN, 'Content-Type': 'application/json'}
IMAGES_DIR = '/opt/odi/data/ARMOTOS/smart_film_images'

print('=== UPLOAD PELICULAS A SHOPIFY ===')

images = [f for f in os.listdir(IMAGES_DIR) if f.endswith('.png')]
print(f'Imagenes: {len(images)}')

# Build SKU mapping
print('Mapeando SKUs...')
sku_to_product = {}
url = f'{BASE_URL}/products.json'
params = {'limit': 250, 'fields': 'id,variants'}

while True:
    resp = httpx.get(url, headers=HEADERS, params=params, timeout=60)
    products = resp.json().get('products', [])
    if not products:
        break
    for p in products:
        for v in p.get('variants', []):
            sku = v.get('sku', '')
            if sku:
                norm = str(int(sku)) if sku.isdigit() else sku
                sku_to_product[norm] = p['id']
    link = resp.headers.get('Link', '')
    if 'rel=next' not in link:
        break
    import re
    m = re.search(r'<([^>]+)>; rel=next', link)
    if m:
        url = m.group(1)
        params = {}
    else:
        break

print(f'SKUs: {len(sku_to_product)}')

uploaded = skipped = failed = 0

for i, fn in enumerate(images):
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
        r = httpx.post(f'{BASE_URL}/products/{pid}/images.json',
            headers=HEADERS, json={'image': {'attachment': data, 'position': 2, 'alt': f'Catalogo {sku}'}},
            timeout=60)
        if r.status_code in [200, 201]:
            uploaded += 1
        else:
            failed += 1
    except:
        failed += 1
    
    if (i+1) % 100 == 0:
        print(f'  {i+1}/{len(images)} | ok:{uploaded} skip:{skipped} fail:{failed}')
    if (i+1) % 40 == 0:
        time.sleep(1)

print(f'\n=== DONE ===')
print(f'Uploaded: {uploaded}')
print(f'Skipped: {skipped}')
print(f'Failed: {failed}')
