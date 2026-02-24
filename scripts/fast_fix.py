#!/usr/bin/env python3
"""Fast fix: prices (category avg fallback), stock 7, KAIQI upload"""
import os, json, requests, time, logging, pandas as pd
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger()

DATA = '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data'
BRANDS = '/opt/odi/data/brands'

FOLDERS = {
    'japan':'Japan','kaiqi':'Kaiqi','yokomar':'Yokomar','bara':'Bara',
    'imbra':'Imbra','cbi':'CBI','leo':'Leo','mclmotos':'McLMotos',
    'duna':'Duna','vitton':'Vitton'
}

def get_config(store):
    with open(os.path.join(BRANDS, f'{store.lower()}.json')) as f:
        c = json.load(f)
    s = c.get('shopify', {})
    shop = s.get('shop_name', s.get('shop', ''))
    tok = s.get('access_token', s.get('token', ''))
    if not shop.endswith('.myshopify.com'): shop = f'{shop}.myshopify.com'
    return shop, tok

def load_csv_prices(store):
    """Load prices from CSV/Excel with SKU index"""
    folder = FOLDERS.get(store.lower(), store)
    path = os.path.join(DATA, folder)
    prices = {}
    if not os.path.exists(path): return prices

    for f in os.listdir(path):
        filepath = os.path.join(path, f)
        try:
            if f.endswith('.xlsx'):
                df = pd.read_excel(filepath, header=None)
                for i, row in df.iterrows():
                    if i < 10: continue
                    code = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
                    price_val = row.iloc[2] if len(row) > 2 and pd.notna(row.iloc[2]) else 0
                    if code and 'CODIGO' not in code.upper():
                        try:
                            pr = float(str(price_val).replace(',','').replace('$',''))
                            if pr > 0: prices[code.upper()] = pr
                        except: pass
            elif f.endswith('.csv'):
                for enc in ['utf-8','latin-1','cp1252']:
                    try:
                        with open(filepath, encoding=enc) as cf:
                            txt = cf.read()
                            break
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

    logger.info(f'{store}: {len(prices)} CSV prices')
    return prices

def fix_store(store):
    logger.info(f'\n{"="*50}\nSTORE: {store.upper()}\n{"="*50}')
    csv_p = load_csv_prices(store)

    try: shop, tok = get_config(store)
    except Exception as e:
        logger.error(f'Config error: {e}')
        return 0

    hdrs = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    base = f'https://{shop}/admin/api/2024-01'

    # Get all products
    all_p = []
    for st in ['draft', 'active']:
        url = f'{base}/products.json?limit=250&status={st}'
        while url:
            r = requests.get(url, headers=hdrs)
            if r.status_code != 200: break
            all_p.extend(r.json().get('products', []))
            lk = r.headers.get('Link', '')
            url = lk.split('<')[1].split('>')[0] if 'rel="next"' in lk else None
            time.sleep(0.25)

    logger.info(f'Total products: {len(all_p)}')

    # Build category averages
    need, cat_p = [], defaultdict(list)
    for p in all_p:
        price = float(p['variants'][0].get('price', 0))
        pt = p.get('product_type', 'General')
        if price > 1: cat_p[pt].append(price)
        if p['status'] == 'draft' or price <= 1: need.append(p)

    cat_avg = {c: sum(v)/len(v) for c, v in cat_p.items() if v}
    global_avg = sum(cat_avg.values())/len(cat_avg) if cat_avg else 35000

    logger.info(f'Need fix: {len(need)} | Categories: {len(cat_avg)} | Global avg: ${global_avg:.0f}')

    fixed = 0
    for p in need:
        sku = p['variants'][0].get('sku', '').upper()
        pt = p.get('product_type', 'General')

        # 1. SKU match (fast)
        np = csv_p.get(sku)
        src = 'SKU' if np else ''

        # 2. Category average (fast)
        if not np and pt in cat_avg:
            np, src = round(cat_avg[pt], -2), 'CAT'

        # 3. Global average (fast)
        if not np:
            np, src = round(global_avg, -2), 'GLOBAL'

        if np and np > 0:
            try:
                vid = p['variants'][0]['id']
                rs = requests.put(f'{base}/variants/{vid}.json', headers=hdrs,
                    json={'variant': {'price': str(np)}})
                time.sleep(0.25)
                if rs.status_code == 200:
                    if p['status'] == 'draft':
                        requests.put(f'{base}/products/{p["id"]}.json', headers=hdrs,
                            json={'product': {'status': 'active'}})
                        time.sleep(0.25)
                    fixed += 1
                    if fixed <= 3: logger.info(f'  ${np:.0f} ({src}) {p["title"][:35]}')
            except: pass

    logger.info(f'Fixed: {fixed}')
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
                rs = requests.post(f'{base}/inventory_levels/set.json', headers=hdrs,
                    json={'location_id': lid, 'inventory_item_id': inv, 'available': qty})
                if rs.status_code == 200: upd += 1
                time.sleep(0.15)
        lk = r.headers.get('Link', '')
        url = lk.split('<')[1].split('>')[0] if 'rel="next"' in lk else None

    logger.info(f'{store}: Stock={qty} for {upd}')
    return upd

def upload_kaiqi_missing():
    """Upload missing KAIQI products"""
    logger.info('\n' + '='*50)
    logger.info('KAIQI: Upload missing products')
    logger.info('='*50)

    xlsx = os.path.join(DATA, 'Kaiqi/LISTADO KAIQI FEB 26.xlsx')
    df = pd.read_excel(xlsx, header=None)

    excel_prods = []
    for i, row in df.iterrows():
        if i < 10: continue
        code = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        desc = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
        pv = row.iloc[2] if len(row) > 2 and pd.notna(row.iloc[2]) else 0
        if not code or not desc or 'CODIGO' in code.upper(): continue
        try: pr = float(str(pv).replace(',','').replace('$',''))
        except: pr = 0
        excel_prods.append({'code': code, 'title': desc[:80], 'price': pr if pr > 0 else 35000})

    logger.info(f'Excel: {len(excel_prods)}')

    shop, tok = get_config('kaiqi')
    hdrs = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    base = f'https://{shop}/admin/api/2024-01'

    # Get existing SKUs
    existing_skus = set()
    url = f'{base}/products.json?limit=250&fields=id,variants'
    while url:
        r = requests.get(url, headers=hdrs)
        if r.status_code != 200: break
        for p in r.json().get('products', []):
            sku = p['variants'][0].get('sku', '').upper()
            if sku: existing_skus.add(sku)
        lk = r.headers.get('Link', '')
        url = lk.split('<')[1].split('>')[0] if 'rel="next"' in lk else None
        time.sleep(0.25)

    logger.info(f'Existing SKUs: {len(existing_skus)}')

    missing = [p for p in excel_prods if p['code'].upper() not in existing_skus]
    logger.info(f'Missing: {len(missing)}')

    uploaded = 0
    for prod in missing[:150]:
        try:
            payload = {
                'product': {
                    'title': prod['title'],
                    'status': 'active',
                    'product_type': 'Repuesto Moto',
                    'vendor': 'KAIQI',
                    'variants': [{
                        'price': str(prod['price']),
                        'sku': prod['code'],
                        'inventory_management': 'shopify',
                        'inventory_quantity': 7
                    }]
                }
            }
            rs = requests.post(f'{base}/products.json', headers=hdrs, json=payload)
            if rs.status_code == 201:
                uploaded += 1
                if uploaded <= 5: logger.info(f'  NEW {prod["title"][:40]}')
            time.sleep(0.35)
        except: pass

    logger.info(f'Uploaded: {uploaded}')
    return uploaded

if __name__ == '__main__':
    stores = ['yokomar', 'bara', 'cbi', 'leo', 'mclmotos', 'duna', 'vitton', 'japan', 'kaiqi']
    total = 0
    for s in stores:
        total += fix_store(s)
        fix_stock(s, 7)
    upload_kaiqi_missing()
    logger.info(f'\nTOTAL FIXED: {total}')
