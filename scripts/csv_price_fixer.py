#!/usr/bin/env python3
import os, json, requests, time, logging
from collections import defaultdict
from difflib import SequenceMatcher
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()
DATA = '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data'
BRANDS = '/opt/odi/data/brands'
FOLDERS = {'japan':'Japan','kaiqi':'Kaiqi','yokomar':'Yokomar','bara':'Bara','imbra':'Imbra','cbi':'CBI','leo':'Leo','mclmotos':'McLMotos','duna':'Duna','vitton':'Vitton'}

def load_csv(store):
    folder = FOLDERS.get(store.lower(), store)
    path = os.path.join(DATA, folder)
    prices, titles = {}, {}
    if not os.path.exists(path): return prices, titles
    for f in os.listdir(path):
        if not f.endswith('.csv'): continue
        try:
            for enc in ['utf-8','latin-1','cp1252']:
                try:
                    with open(os.path.join(path,f), encoding=enc) as cf:
                        txt = cf.read()
                        break
                except: continue
            for line in txt.strip().split('\n')[1:]:
                parts = line.split(';')
                if len(parts) >= 3:
                    sku, desc = parts[0].strip(), parts[1].strip()
                    try:
                        pr = float(parts[2].strip().replace(',','').replace('$',''))
                        if pr > 0: prices[sku], titles[sku] = pr, desc
                    except: pass
        except: pass
    logger.info(f'{store}: {len(prices)} CSV prices')
    return prices, titles

def get_config(store):
    with open(os.path.join(BRANDS, f'{store.lower()}.json')) as f:
        c = json.load(f)
    s = c.get('shopify', {})
    shop = s.get('shop_name', s.get('shop', ''))
    tok = s.get('access_token', s.get('token', ''))
    if not shop.endswith('.myshopify.com'): shop = f'{shop}.myshopify.com'
    return shop, tok

def fuzzy(t1, t2):
    return SequenceMatcher(None, t1.lower().strip(), t2.lower().strip()).ratio()

def fix_store(store):
    logger.info(f'\n==== {store.upper()} ====')
    csv_p, csv_t = load_csv(store)
    try: shop, tok = get_config(store)
    except Exception as e:
        logger.error(f'Config error: {e}')
        return 0
    hdrs = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    base = f'https://{shop}/admin/api/2024-01'
    all_p = []
    for st in ['draft', 'active']:
        url = f'{base}/products.json?limit=250&status={st}'
        while url:
            r = requests.get(url, headers=hdrs)
            if r.status_code != 200: break
            all_p.extend(r.json().get('products', []))
            lk = r.headers.get('Link', '')
            url = lk.split('<')[1].split('>')[0] if 'rel="next"' in lk else None
            time.sleep(0.3)
    logger.info(f'Total: {len(all_p)}')
    need, cat_p = [], defaultdict(list)
    for p in all_p:
        price = float(p['variants'][0].get('price', 0))
        pt = p.get('product_type', 'General')
        if price > 1: cat_p[pt].append(price)
        if p['status'] == 'draft' or price <= 1: need.append(p)
    logger.info(f'Need fix: {len(need)}')
    cat_avg = {c: sum(v)/len(v) for c, v in cat_p.items() if v}
    fixed, failed = 0, 0
    for p in need:
        title, sku = p['title'], p['variants'][0].get('sku', '')
        pt = p.get('product_type', 'General')
        np, src = None, ''
        if sku and sku in csv_p: np, src = csv_p[sku], 'SKU'
        if not np:
            bm, bp = 0, None
            for ck, ct in csv_t.items():
                sim = fuzzy(title, ct)
                if sim > bm and sim > 0.6: bm, bp = sim, csv_p.get(ck)
            if bp: np, src = bp, f'TITLE({bm:.0%})'
        if not np and pt in cat_avg: np, src = round(cat_avg[pt], -2), 'CAT_AVG'
        if not np and cat_avg: np, src = round(sum(cat_avg.values())/len(cat_avg), -2), 'GLOBAL'
        if np and np > 0:
            try:
                vid = p['variants'][0]['id']
                rs = requests.put(f'{base}/variants/{vid}.json', headers=hdrs, json={'variant': {'price': str(np)}})
                time.sleep(0.3)
                if rs.status_code == 200:
                    if p['status'] == 'draft':
                        requests.put(f'{base}/products/{p["id"]}.json', headers=hdrs, json={'product': {'status': 'active'}})
                        time.sleep(0.3)
                    fixed += 1
                    if fixed <= 5: logger.info(f'  OK {title[:35]} -> ${np:.0f} ({src})')
                else: failed += 1
            except Exception as e:
                logger.error(f'  Error: {e}')
                failed += 1
        else: failed += 1
    logger.info(f'RESULT: Fixed={fixed}, Failed={failed}')
    return fixed

def fix_stock(store, qty=7):
    try: shop, tok = get_config(store)
    except: return 0
    hdrs = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    base = f'https://{shop}/admin/api/2024-01'
    r = requests.get(f'{base}/locations.json', headers=hdrs)
    if r.status_code != 200: return 0
    locs = r.json().get('locations', [])
    if not locs: return 0
    lid = locs[0]['id']
    url = f'{base}/products.json?limit=250&status=active'
    upd = 0
    while url:
        r = requests.get(url, headers=hdrs)
        if r.status_code != 200: break
        for p in r.json().get('products', []):
            inv = p['variants'][0].get('inventory_item_id')
            if inv:
                rs = requests.post(f'{base}/inventory_levels/set.json', headers=hdrs, json={'location_id': lid, 'inventory_item_id': inv, 'available': qty})
                if rs.status_code == 200: upd += 1
                time.sleep(0.2)
        lk = r.headers.get('Link', '')
        url = lk.split('<')[1].split('>')[0] if 'rel="next"' in lk else None
    logger.info(f'{store}: Stock updated {upd}')
    return upd

if __name__ == '__main__':
    stores = ['japan', 'kaiqi', 'yokomar', 'bara', 'cbi', 'leo', 'mclmotos', 'duna', 'vitton']
    total = 0
    for s in stores:
        total += fix_store(s)
        fix_stock(s, 7)
    logger.info(f'\nTOTAL FIXED: {total}')
