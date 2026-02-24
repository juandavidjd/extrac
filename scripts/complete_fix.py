#!/usr/bin/env python3
"""Complete fix: prices, stock, images, KAIQI upload"""
import os, json, requests, time, logging, pandas as pd
from collections import defaultdict
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger()

DATA = '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data'
IMAGES = '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Imagenes'
BRANDS = '/opt/odi/data/brands'

FOLDERS = {
    'japan':'Japan','kaiqi':'Kaiqi','yokomar':'Yokomar','bara':'Bara',
    'imbra':'Imbra','cbi':'CBI','leo':'Leo','mclmotos':'McLMotos',
    'duna':'Duna','vitton':'Vitton','dfg':'DFG','oh_importaciones':'OH_Importaciones',
    'armotos':'Armotos','store':'Store','vaisand':'Vaisand'
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
    folder = FOLDERS.get(store.lower(), store)
    path = os.path.join(DATA, folder)
    prices, titles = {}, {}
    if not os.path.exists(path): return prices, titles

    for f in os.listdir(path):
        filepath = os.path.join(path, f)
        try:
            if f.endswith('.xlsx'):
                df = pd.read_excel(filepath, header=None)
                for i, row in df.iterrows():
                    if i < 10: continue
                    code = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
                    desc = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
                    price_val = row.iloc[2] if pd.notna(row.iloc[2]) else 0
                    if code and desc:
                        try:
                            pr = float(str(price_val).replace(',','').replace('$',''))
                            if pr > 0:
                                prices[code] = pr
                                titles[code] = desc
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
                        sku, desc = parts[0].strip(), parts[1].strip()
                        try:
                            pr = float(parts[2].strip().replace(',','').replace('$',''))
                            if pr > 0: prices[sku], titles[sku] = pr, desc
                        except: pass
        except Exception as e:
            logger.warning(f'Error {f}: {e}')

    logger.info(f'{store}: {len(prices)} prices from Data')
    return prices, titles

def fuzzy(t1, t2):
    return SequenceMatcher(None, t1.lower().strip(), t2.lower().strip()).ratio()

def get_all_products(shop, tok, base, hdrs):
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
    return all_p

def fix_store(store):
    logger.info(f'\n{"="*50}\nSTORE: {store.upper()}\n{"="*50}')
    csv_p, csv_t = load_csv_prices(store)

    try: shop, tok = get_config(store)
    except Exception as e:
        logger.error(f'Config error: {e}')
        return 0

    hdrs = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    base = f'https://{shop}/admin/api/2024-01'

    all_p = get_all_products(shop, tok, base, hdrs)
    logger.info(f'Total products: {len(all_p)}')

    # Build category averages
    need, cat_p = [], defaultdict(list)
    for p in all_p:
        price = float(p['variants'][0].get('price', 0))
        pt = p.get('product_type', 'General')
        if price > 1: cat_p[pt].append(price)
        if p['status'] == 'draft' or price <= 1: need.append(p)

    logger.info(f'Need price fix: {len(need)}')
    cat_avg = {c: sum(v)/len(v) for c, v in cat_p.items() if v}

    fixed = 0
    for p in need:
        title, sku = p['title'], p['variants'][0].get('sku', '')
        pt = p.get('product_type', 'General')
        np, src = None, ''

        # SKU match
        if sku and sku in csv_p: np, src = csv_p[sku], 'SKU'

        # Title fuzzy match
        if not np:
            bm, bp = 0, None
            for ck, ct in csv_t.items():
                sim = fuzzy(title, ct)
                if sim > bm and sim > 0.55: bm, bp = sim, csv_p.get(ck)
            if bp: np, src = bp, f'TITLE({bm:.0%})'

        # Category average
        if not np and pt in cat_avg: np, src = round(cat_avg[pt], -2), 'CAT_AVG'

        # Global average
        if not np and cat_avg: np, src = round(sum(cat_avg.values())/len(cat_avg), -2), 'GLOBAL'

        if np and np > 0:
            try:
                vid = p['variants'][0]['id']
                rs = requests.put(f'{base}/variants/{vid}.json', headers=hdrs,
                    json={'variant': {'price': str(np)}})
                time.sleep(0.3)
                if rs.status_code == 200:
                    if p['status'] == 'draft':
                        requests.put(f'{base}/products/{p["id"]}.json', headers=hdrs,
                            json={'product': {'status': 'active'}})
                        time.sleep(0.3)
                    fixed += 1
                    if fixed <= 5: logger.info(f'  OK {title[:40]} -> ${np:.0f} ({src})')
            except: pass

    logger.info(f'Prices fixed: {fixed}')
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

    logger.info(f'{store}: Stock set to {qty} for {upd} products')
    return upd

def link_images(store):
    folder = FOLDERS.get(store.lower(), store)
    img_path = os.path.join(IMAGES, folder)
    if not os.path.exists(img_path):
        logger.warning(f'No images folder for {store}')
        return 0

    try: shop, tok = get_config(store)
    except: return 0
    hdrs = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    base = f'https://{shop}/admin/api/2024-01'

    # Get products without images
    all_p = get_all_products(shop, tok, base, hdrs)
    no_img = [p for p in all_p if not p.get('images')]
    logger.info(f'{store}: {len(no_img)} products without images')

    if not no_img: return 0

    # Get available images
    images = {}
    for f in os.listdir(img_path):
        if f.lower().endswith(('.jpg','.png','.jpeg','.webp')):
            name = os.path.splitext(f)[0].lower()
            images[name] = os.path.join(img_path, f)

    logger.info(f'{store}: {len(images)} images available')

    linked = 0
    for p in no_img[:50]:  # Limit to 50 per run
        title = p['title'].lower().replace(' ', '-')[:30]
        sku = p['variants'][0].get('sku', '').lower()

        # Try to match image
        matched_img = None
        for img_name, img_path_full in images.items():
            if sku and sku in img_name:
                matched_img = img_path_full
                break
            if fuzzy(title, img_name) > 0.5:
                matched_img = img_path_full
                break

        if matched_img:
            try:
                import base64
                with open(matched_img, 'rb') as f:
                    img_data = base64.b64encode(f.read()).decode()

                rs = requests.post(f'{base}/products/{p["id"]}/images.json', headers=hdrs,
                    json={'image': {'attachment': img_data}})
                if rs.status_code == 200:
                    linked += 1
                    if linked <= 5: logger.info(f'  IMG {p["title"][:30]}')
                time.sleep(0.5)
            except: pass

    logger.info(f'{store}: Linked {linked} images')
    return linked

def upload_kaiqi_missing():
    """Upload missing KAIQI products from Excel"""
    logger.info('\n' + '='*50)
    logger.info('KAIQI: Uploading missing products')
    logger.info('='*50)

    # Read Excel
    xlsx_path = os.path.join(DATA, 'Kaiqi/LISTADO KAIQI FEB 26.xlsx')
    df = pd.read_excel(xlsx_path, header=None)

    excel_products = []
    for i, row in df.iterrows():
        if i < 10: continue
        code = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        desc = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
        price_val = row.iloc[2] if pd.notna(row.iloc[2]) else 0

        if not code or not desc or 'CODIGO' in code.upper(): continue

        try:
            pr = float(str(price_val).replace(',','').replace('$',''))
        except:
            pr = 0

        excel_products.append({'code': code, 'title': desc, 'price': pr if pr > 0 else 35000})

    logger.info(f'Excel products: {len(excel_products)}')

    # Get current Shopify products
    shop, tok = get_config('kaiqi')
    hdrs = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    base = f'https://{shop}/admin/api/2024-01'

    existing = get_all_products(shop, tok, base, hdrs)
    existing_titles = set(p['title'].lower() for p in existing)
    existing_skus = set(p['variants'][0].get('sku', '').lower() for p in existing)
    logger.info(f'Existing in Shopify: {len(existing)}')

    # Find missing
    missing = []
    for ep in excel_products:
        if ep['code'].lower() not in existing_skus and ep['title'].lower() not in existing_titles:
            missing.append(ep)

    logger.info(f'Missing to upload: {len(missing)}')

    # Upload missing (limit to 100)
    uploaded = 0
    for prod in missing[:100]:
        try:
            payload = {
                'product': {
                    'title': prod['title'][:80],
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
                if uploaded <= 5: logger.info(f'  NEW {prod["title"][:40]} ${prod["price"]}')
            time.sleep(0.4)
        except Exception as e:
            logger.error(f'Upload error: {e}')

    logger.info(f'KAIQI: Uploaded {uploaded} new products')
    return uploaded

if __name__ == '__main__':
    # Priority stores with price issues
    stores = ['yokomar', 'bara', 'cbi', 'leo', 'mclmotos', 'duna', 'vitton', 'japan', 'kaiqi']

    total_fixed = 0
    for s in stores:
        fixed = fix_store(s)
        total_fixed += fixed
        fix_stock(s, 7)
        link_images(s)

    # Upload missing KAIQI products
    upload_kaiqi_missing()

    logger.info(f'\n{"="*50}')
    logger.info(f'TOTAL PRICES FIXED: {total_fixed}')
    logger.info(f'{"="*50}')
