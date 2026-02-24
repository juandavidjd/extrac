#!/usr/bin/env python3
"""V15 - Actualizar body_html con Template Ficha 360° Estándar"""
import os, sys, json, requests, time
from dotenv import load_dotenv
load_dotenv('/opt/odi/.env')

sys.path.insert(0, '/opt/odi')
from core.ficha_360_template import build_ficha_360

def get_products_graphql(shop, token):
    """Get all products via GraphQL"""
    products = []
    query_base = '''
    {
      products(first: 250%s) {
        edges {
          node {
            id
            title
            variants(first: 1) {
              edges {
                node {
                  sku
                }
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    '''
    
    url = f'https://{shop}/admin/api/2025-01/graphql.json'
    headers = {'X-Shopify-Access-Token': token, 'Content-Type': 'application/json'}
    cursor = None
    
    while True:
        if cursor:
            query = query_base % f', after: "{cursor}"'
        else:
            query = query_base % ''
        
        resp = requests.post(url, json={'query': query}, headers=headers, timeout=30)
        if resp.status_code == 429:
            time.sleep(5)
            continue
        if resp.status_code != 200:
            print(f'Error GraphQL: {resp.status_code}')
            break
        
        data = resp.json()
        edges = data.get('data', {}).get('products', {}).get('edges', [])
        for edge in edges:
            node = edge['node']
            sku = ''
            variants = node.get('variants', {}).get('edges', [])
            if variants:
                sku = variants[0]['node'].get('sku', '')
            products.append({
                'id': node['id'].split('/')[-1],
                'title': node['title'],
                'sku': sku
            })
        
        page_info = data.get('data', {}).get('products', {}).get('pageInfo', {})
        if not page_info.get('hasNextPage'):
            break
        cursor = page_info.get('endCursor')
        time.sleep(0.3)
    
    return products

def update_product(session, shop, token, product_id, body_html):
    """Update product body_html via REST API"""
    url = f'https://{shop}/admin/api/2025-01/products/{product_id}.json'
    headers = {'X-Shopify-Access-Token': token, 'Content-Type': 'application/json'}
    data = {'product': {'id': int(product_id), 'body_html': body_html}}
    
    for attempt in range(3):
        try:
            resp = session.put(url, json=data, headers=headers, timeout=30)
            if resp.status_code == 200:
                return True
            elif resp.status_code == 429:
                time.sleep(3)
            else:
                return False
        except:
            time.sleep(2)
    return False

def extract_compat_from_title(title):
    """Extract compatibility from product title"""
    title_up = title.upper()
    motos = [
        'AKT DYNAMIC', 'AKT EVO', 'AKT NKD', 'AKT TTR', 'AKT CR', 'AKT',
        'BAJAJ PULSAR', 'BAJAJ BOXER', 'BAJAJ DISCOVER', 'BAJAJ',
        'HONDA CB', 'HONDA XR', 'HONDA CRF', 'HONDA',
        'YAMAHA FZ', 'YAMAHA YBR', 'YAMAHA XTZ', 'YAMAHA BWS', 'YAMAHA',
        'SUZUKI GN', 'SUZUKI GIXXER', 'SUZUKI AX', 'SUZUKI',
        'PULSAR NS', 'PULSAR',
        'TVS APACHE', 'TVS',
        'KTM DUKE', 'KTM',
        'BOXER', 'DISCOVER',
    ]
    
    for moto in motos:
        if moto in title_up:
            # Try to get more specific match
            idx = title_up.find(moto)
            # Get rest of string and extract model
            rest = title[idx:idx+30]
            parts = rest.split()
            if len(parts) >= 2:
                return ' '.join(parts[:2])
            return moto.title()
    
    return 'Universal'

def main():
    if len(sys.argv) < 2:
        print('Uso: python3 v15_ficha360_update.py ARMOTOS|VITTON')
        sys.exit(1)
    
    empresa = sys.argv[1].upper()
    
    shop = os.environ.get(f'{empresa}_SHOP')
    token = os.environ.get(f'{empresa}_TOKEN')
    
    if not shop or not token:
        print(f'Error: No config for {empresa}')
        sys.exit(1)
    
    print(f'V15 - Ficha 360° Update: {empresa}')
    print('=' * 60)
    print(f'Shop: {shop}')
    
    # Load Vision AI compat map if ARMOTOS
    compat_map = {}
    if empresa == 'ARMOTOS':
        try:
            vision_data = json.load(open('/opt/odi/data/ARMOTOS/vision_compat_results.json'))
            for page_data in vision_data:
                for p in page_data.get('products', []):
                    sku = p.get('sku', '').strip()
                    compat = p.get('compat', '')
                    if sku and compat:
                        compat_map[sku] = compat
            print(f'Vision AI compat: {len(compat_map)}')
        except:
            print('No Vision AI compat data')
    
    # Get products
    print('Obteniendo productos via GraphQL...')
    products = get_products_graphql(shop, token)
    print(f'Productos: {len(products)}')
    
    # Update each product
    session = requests.Session()
    ok = 0
    err = 0
    start = time.time()
    total = len(products)
    
    for i, p in enumerate(products):
        pid = p['id']
        title = p['title']
        sku = p['sku']
        
        # Get compatibility
        if sku in compat_map:
            compat = compat_map[sku]
        else:
            compat = extract_compat_from_title(title)
        
        # Build Ficha 360°
        html = build_ficha_360(title, sku, compat, empresa)
        
        # Update
        if update_product(session, shop, token, pid, html):
            ok += 1
        else:
            err += 1
        
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start
            print(f'Progreso: {i+1}/{total} ({ok} ok, {err} err) - {int(elapsed)}s', flush=True)
        
        time.sleep(0.5)
    
    elapsed = time.time() - start
    print('=' * 60)
    print(f'RESULTADO: {ok} ok, {err} err de {total}')
    print(f'Tiempo: {int(elapsed)}s')
    
    # Stats
    with_vision = sum(1 for p in products if p['sku'] in compat_map)
    print(f'Con Vision AI: {with_vision}')
    print(f'Con extracción título: {total - with_vision}')

if __name__ == '__main__':
    main()
