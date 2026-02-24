#!/usr/bin/env python3
"""V18 Full Image Diagnosis - Check Shopify + Image Banks"""
import os
import json
import glob
import requests
import time

brands_dir = '/opt/odi/data/brands'
image_banks = [
    '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data',
    '/opt/odi/data',
    '/mnt/volume_sfo3_01/profesion/ecosistema_odi'
]

results = []

# Load all brand configs
brand_files = glob.glob(f'{brands_dir}/*.json')
stores = {}
for bf in brand_files:
    with open(bf) as f:
        data = json.load(f)
        name = data.get('name', '').upper()
        if name and data.get('shopify'):
            stores[name] = data['shopify']

# Also add stores we know exist
known_stores = ['ARMOTOS', 'BARA', 'CBI', 'DFG', 'DUNA', 'IMBRA', 'JAPAN', 
                'KAIQI', 'LEO', 'MCLMOTOS', 'OH_IMPORTACIONES', 'STORE', 
                'VAISAND', 'VITTON', 'YOKOMAR']

def count_shopify_products(shop, token):
    """Count products with/without images via Shopify API"""
    url = f'https://{shop}/admin/api/2024-01/products/count.json'
    headers = {'X-Shopify-Access-Token': token}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        total = r.json().get('count', 0)
        
        # Get sample to check images
        url2 = f'https://{shop}/admin/api/2024-01/products.json?limit=250&fields=id,images'
        con_img = 0
        sin_img = 0
        page = 1
        
        while True:
            r = requests.get(url2, headers=headers, timeout=30)
            time.sleep(0.6)  # Rate limit
            data = r.json()
            products = data.get('products', [])
            if not products:
                break
            
            for p in products:
                if p.get('images') and len(p.get('images', [])) > 0:
                    con_img += 1
                else:
                    sin_img += 1
            
            # Get next page
            link = r.headers.get('Link', '')
            if 'rel="next"' in link:
                # Extract next URL
                parts = link.split(',')
                for part in parts:
                    if 'rel="next"' in part:
                        url2 = part.split('<')[1].split('>')[0]
                        break
            else:
                break
            page += 1
            if page > 50:  # Safety limit
                break
        
        return total, con_img, sin_img
    except Exception as e:
        return 0, 0, 0

def count_image_bank(store_name):
    """Count images in bank for a store"""
    count = 0
    checked_paths = set()
    
    search_patterns = [
        f'*/{store_name}',
        f'*/{store_name.lower()}',
        f'*/{store_name}/images',
        f'*/{store_name.lower()}/images',
        f'{store_name}',
        f'{store_name.lower()}',
        f'{store_name}/smart_film_images',
        f'{store_name}/images',
    ]
    
    for bank in image_banks:
        if not os.path.exists(bank):
            continue
        
        # Direct path check
        for pattern in search_patterns:
            full_pattern = f'{bank}/{pattern}'
            matches = glob.glob(full_pattern)
            for match in matches:
                if os.path.isdir(match) and match not in checked_paths:
                    checked_paths.add(match)
                    for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.JPG', '*.PNG']:
                        count += len(glob.glob(f'{match}/{ext}'))
                        count += len(glob.glob(f'{match}/**/{ext}', recursive=True))
    
    return count // 2 if count > 10000 else count  # Dedupe recursive

print('V18 IMAGE DIAGNOSIS - STEP 1.0')
print('=' * 80)
print()

# First, list what's in the image banks
print('Checking image banks...')
for bank in image_banks:
    if os.path.exists(bank):
        print(f'  {bank}: EXISTS')
        try:
            dirs = os.listdir(bank)[:10]
            print(f'    Subdirs: {dirs}')
        except:
            pass
    else:
        print(f'  {bank}: NOT FOUND')
print()

# Check ARMOTOS smart_film specifically
armotos_smart = '/opt/odi/data/ARMOTOS/smart_film_images'
if os.path.exists(armotos_smart):
    count = len(glob.glob(f'{armotos_smart}/*.png'))
    print(f'ARMOTOS smart_film_images: {count} PNGs')
else:
    print(f'ARMOTOS smart_film_images: NOT FOUND')
print()

print('| Tienda           | Shopify | Con Img | Sin Img | Banco Imgs | Gap    |')
print('|------------------|---------|---------|---------|------------|--------|')

totals = {'total': 0, 'con': 0, 'sin': 0, 'banco': 0, 'gap': 0}

for store in sorted(known_stores):
    shop_info = stores.get(store, {})
    shop = shop_info.get('shop', '')
    token = shop_info.get('token', '')
    
    if shop and token:
        total, con_img, sin_img = count_shopify_products(shop, token)
    else:
        total, con_img, sin_img = 0, 0, 0
    
    banco = count_image_bank(store)
    gap = max(0, sin_img - banco)
    
    print(f'| {store:16} | {total:>7} | {con_img:>7} | {sin_img:>7} | {banco:>10} | {gap:>6} |')
    
    totals['total'] += total
    totals['con'] += con_img
    totals['sin'] += sin_img
    totals['banco'] += banco
    totals['gap'] += gap
    
    results.append({
        'tienda': store,
        'productos': total,
        'con_imagen': con_img,
        'sin_imagen': sin_img,
        'imagenes_banco': banco,
        'gap': gap
    })

print('|------------------|---------|---------|---------|------------|--------|')
print(f"| TOTAL            | {totals['total']:>7} | {totals['con']:>7} | {totals['sin']:>7} | {totals['banco']:>10} | {totals['gap']:>6} |")

# Save results
with open('/opt/odi/data/v18_diagnosis.json', 'w') as f:
    json.dump(results, f, indent=2)
print()
print('Results saved to /opt/odi/data/v18_diagnosis.json')
