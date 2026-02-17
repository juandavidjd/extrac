#!/usr/bin/env python3
import os
import base64
import httpx
from dotenv import load_dotenv
import time

load_dotenv('/opt/odi/.env')

SHOP = os.getenv('ARMOTOS_SHOP')
TOKEN = os.getenv('ARMOTOS_TOKEN')
API = '2025-01'
BASE = f'https://{SHOP}/admin/api/{API}'
HEADERS = {'X-Shopify-Access-Token': TOKEN, 'Content-Type': 'application/json'}
IMAGES_DIR = '/opt/odi/data/ARMOTOS/smart_film_images'

print('=== UPLOAD FINAL ===')

# Build comprehensive SKU mapping
print('Mapeando SKUs...')
sku_to_pid = {}

since_id = 0
while True:
    r = httpx.get(f'{BASE}/products.json?limit=250&since_id={since_id}&fields=id,variants',
                  headers=HEADERS, timeout=60)
    products = r.json().get('products', [])
    if not products:
        break
    for p in products:
        since_id = max(since_id, p['id'])
        for v in p.get('variants', []):
            sku = v.get('sku', '')
            if sku:
                # Store both original and normalized versions
                sku_to_pid[sku] = p['id']
                # Also store without leading zeros
                if sku.isdigit():
                    sku_to_pid[str(int(sku))] = p['id']
                    # And with 5-digit padding
                    sku_to_pid[sku.zfill(5)] = p['id']

print(f'SKU mappings: {len(sku_to_pid)}')

# Upload
images = [f for f in os.listdir(IMAGES_DIR) if f.endswith('.png')]
print(f'Images: {len(images)}')

uploaded = skipped = failed = 0

for i, fn in enumerate(images):
    # Extract SKU
    parts = fn.replace('.png', '').split('_')
    sku = None
    for j, p in enumerate(parts):
        if p == 'sku' and j+1 < len(parts):
            sku = parts[j+1]
            break
    
    if not sku:
        skipped += 1
        continue
    
    # Try to find product ID
    pid = sku_to_pid.get(sku)
    if not pid and sku.isdigit():
        pid = sku_to_pid.get(str(int(sku)))
    if not pid and sku.isdigit():
        pid = sku_to_pid.get(sku.zfill(5))
    
    if not pid:
        skipped += 1
        continue
    
    path = os.path.join(IMAGES_DIR, fn)
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    
    try:
        r = httpx.post(f'{BASE}/products/{pid}/images.json',
            headers=HEADERS,
            json={'image': {'attachment': data, 'position': 2, 'alt': f'Catalogo {sku}'}},
            timeout=90)
        if r.status_code in [200, 201]:
            uploaded += 1
        else:
            failed += 1
    except:
        failed += 1
    
    if (i+1) % 100 == 0:
        print(f'  {i+1}/{len(images)} | ok:{uploaded} skip:{skipped} fail:{failed}')
    time.sleep(0.5)

print(f'\n=== DONE ===')
print(f'Uploaded: {uploaded}')
print(f'Skipped: {skipped}')
print(f'Failed: {failed}')
