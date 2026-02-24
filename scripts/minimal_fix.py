#!/usr/bin/env python3
"""Minimal fix - one store at a time, no fuzzy matching"""
import os, json, requests, time, logging, sys
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger()

DATA = '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data'
BRANDS = '/opt/odi/data/brands'
FOLDERS = {'japan':'Japan','kaiqi':'Kaiqi','yokomar':'Yokomar','bara':'Bara',
    'imbra':'Imbra','cbi':'CBI','leo':'Leo','mclmotos':'McLMotos','duna':'Duna','vitton':'Vitton'}

def get_cfg(store):
    with open(f'{BRANDS}/{store.lower()}.json') as f:
        c = json.load(f)
    s = c.get('shopify', {})
    shop = s.get('shop_name', s.get('shop', ''))
    tok = s.get('access_token', s.get('token', ''))
    if not shop.endswith('.myshopify.com'): shop = f'{shop}.myshopify.com'
    return shop, tok

def load_prices(store):
    folder = FOLDERS.get(store.lower(), store)
    path = f'{DATA}/{folder}'
    prices = {}
    if not os.path.exists(path): return prices
    for f in os.listdir(path):
        if not f.endswith('.csv'): continue
        try:
            for enc in ['utf-8','latin-1','cp1252']:
                try:
                    with open(f'{path}/{f}', encoding=enc) as cf:
                        txt = cf.read(); break
                except: continue
            for line in txt.strip().split('\n')[1:]:
                parts = line.split(';')
                if len(parts) >= 3:
                    sku = parts[0].strip().upper()
                    try:
                        pr = float(parts[2].strip().replace(',','').replace('$',''))
                        if pr > 0: prices[sku] = pr
                    except: pass
        except: pass
    return prices

def fix_one(store):
    log.info(f'\n=== {store.upper()} ===')
    prices = load_prices(store)
    log.info(f'CSV: {len(prices)} prices')

    try: shop, tok = get_cfg(store)
    except Exception as e:
        log.error(f'Config error: {e}'); return 0

    hdrs = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    base = f'https://{shop}/admin/api/2024-01'

    # Get product count
    r = requests.get(f'{base}/products/count.json', headers=hdrs, timeout=30)
    if r.status_code != 200:
        log.error(f'API error: {r.status_code}'); return 0
    total = r.json().get('count', 0)
    log.info(f'Total: {total}')

    # Process in batches
    fixed, cat_prices = 0, defaultdict(list)
    url = f'{base}/products.json?limit=250&status=draft'

    while url:
        try:
            r = requests.get(url, headers=hdrs, timeout=60)
            if r.status_code != 200: break
            prods = r.json().get('products', [])

            for p in prods:
                sku = p['variants'][0].get('sku', '').upper()
                pt = p.get('product_type', 'General')

                # Get price from CSV or use 35000
                np = prices.get(sku, 35000)

                try:
                    vid = p['variants'][0]['id']
                    rs = requests.put(f'{base}/variants/{vid}.json', headers=hdrs,
                        json={'variant': {'price': str(np)}}, timeout=30)
                    if rs.status_code == 200:
                        # Activate
                        requests.put(f'{base}/products/{p["id"]}.json', headers=hdrs,
                            json={'product': {'status': 'active'}}, timeout=30)
                        fixed += 1
                        if fixed <= 3: log.info(f'  ${np:.0f} {p["title"][:40]}')
                    time.sleep(0.3)
                except: pass

            lk = r.headers.get('Link', '')
            url = lk.split('<')[1].split('>')[0] if 'rel="next"' in lk else None
            time.sleep(0.3)
        except Exception as e:
            log.error(f'Error: {e}'); break

    log.info(f'Fixed: {fixed} DRAFT products')

    # Fix $1 prices in active
    url = f'{base}/products.json?limit=250&status=active'
    fixed2 = 0
    while url:
        try:
            r = requests.get(url, headers=hdrs, timeout=60)
            if r.status_code != 200: break
            prods = r.json().get('products', [])

            for p in prods:
                price = float(p['variants'][0].get('price', 0))
                if price > 1: continue

                sku = p['variants'][0].get('sku', '').upper()
                np = prices.get(sku, 35000)

                try:
                    vid = p['variants'][0]['id']
                    rs = requests.put(f'{base}/variants/{vid}.json', headers=hdrs,
                        json={'variant': {'price': str(np)}}, timeout=30)
                    if rs.status_code == 200:
                        fixed2 += 1
                        if fixed2 <= 3: log.info(f'  $1->$${np:.0f} {p["title"][:35]}')
                    time.sleep(0.3)
                except: pass

            lk = r.headers.get('Link', '')
            url = lk.split('<')[1].split('>')[0] if 'rel="next"' in lk else None
            time.sleep(0.3)
        except: break

    log.info(f'Fixed: {fixed2} $1 prices')
    return fixed + fixed2

def fix_stock(store):
    try: shop, tok = get_cfg(store)
    except: return 0
    hdrs = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    base = f'https://{shop}/admin/api/2024-01'

    r = requests.get(f'{base}/locations.json', headers=hdrs, timeout=30)
    if r.status_code != 200: return 0
    locs = r.json().get('locations', [])
    if not locs: return 0
    lid = locs[0]['id']

    url = f'{base}/products.json?limit=250&status=active&fields=id,variants'
    upd = 0
    while url:
        try:
            r = requests.get(url, headers=hdrs, timeout=60)
            if r.status_code != 200: break
            for p in r.json().get('products', []):
                inv = p['variants'][0].get('inventory_item_id')
                if inv:
                    rs = requests.post(f'{base}/inventory_levels/set.json', headers=hdrs,
                        json={'location_id': lid, 'inventory_item_id': inv, 'available': 7}, timeout=30)
                    if rs.status_code == 200: upd += 1
                    time.sleep(0.15)
            lk = r.headers.get('Link', '')
            url = lk.split('<')[1].split('>')[0] if 'rel="next"' in lk else None
        except: break
    log.info(f'Stock: {upd}')
    return upd

if __name__ == '__main__':
    stores = sys.argv[1:] if len(sys.argv) > 1 else ['yokomar','bara','cbi','leo','mclmotos','duna','vitton','japan','kaiqi']
    total = 0
    for s in stores:
        total += fix_one(s)
        fix_stock(s)
    log.info(f'\nTOTAL: {total}')
