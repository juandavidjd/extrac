#!/usr/bin/env python3
import os
import re
import httpx
from dotenv import load_dotenv
import time

load_dotenv('/opt/odi/.env')

SHOP = os.getenv('ARMOTOS_SHOP')
TOKEN = os.getenv('ARMOTOS_TOKEN')
API = '2025-01'
BASE = f'https://{SHOP}/admin/api/{API}'
HEADERS = {'X-Shopify-Access-Token': TOKEN, 'Content-Type': 'application/json'}

print('=== TAREA 2: NORMALIZAR TODOS LOS TITULOS ===')

REMOVE = [
    r'\s*-\s*Armotos\s*$',
    r'\s*-\s*ARMOTOS\s*$', 
    r'\s*Armotos\s*$',
    r'\s*ARMOTOS\s*$',
    r'\s*-\s*$',
]

def normalize(title):
    r = title.strip()
    for p in REMOVE:
        r = re.sub(p, '', r, flags=re.IGNORECASE)
    r = r.strip()
    if len(r) > 60:
        r = r[:57] + '...'
    return r

# Get all products
print('Cargando productos...')
to_update = []
since_id = 0

while True:
    r = httpx.get(f'{BASE}/products.json?limit=250&since_id={since_id}&fields=id,title,variants',
                  headers=HEADERS, timeout=60)
    products = r.json().get('products', [])
    if not products:
        break
    for p in products:
        since_id = max(since_id, p['id'])
        orig = p.get('title', '')
        norm = normalize(orig)
        if norm != orig:
            sku = p['variants'][0].get('sku', '') if p.get('variants') else ''
            to_update.append({'id': p['id'], 'sku': sku, 'orig': orig, 'norm': norm})

print(f'Titulos a actualizar: {len(to_update)}')

if to_update:
    print('\nMuestra:')
    for t in to_update[:3]:
        print(f'  {t["orig"][:50]}')
        print(f'  -> {t["norm"]}')
    
    print(f'\nActualizando...')
    ok = fail = 0
    for i, t in enumerate(to_update):
        try:
            r = httpx.put(f'{BASE}/products/{t["id"]}.json',
                headers=HEADERS,
                json={'product': {'id': t['id'], 'title': t['norm']}},
                timeout=30)
            if r.status_code == 200:
                ok += 1
            else:
                fail += 1
        except:
            fail += 1
        if (i+1) % 50 == 0:
            print(f'  {i+1}/{len(to_update)} | ok:{ok} fail:{fail}')
        time.sleep(0.3)
    
    print(f'\n=== DONE ===')
    print(f'OK: {ok}')
    print(f'Fail: {fail}')
else:
    print('No hay titulos que actualizar.')
