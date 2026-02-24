#!/usr/bin/env python3
"""Rescue prices for DRAFT products using External Intel"""
import sys
sys.path.insert(0, '/opt/odi')

import requests
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

try:
    from core.external_intel import ExternalIntel
except ImportError:
    logger.error("Cannot import ExternalIntel")
    sys.exit(1)

def rescue_draft_prices(store_name, limit=50):
    logger.info(f'\n=== {store_name.upper()} ===')

    # Load Shopify config
    with open(f'/opt/odi/data/brands/{store_name}.json') as f:
        config = json.load(f)

    shopify = config.get('shopify', {})
    shop = shopify.get('shop_name', shopify.get('shop', ''))
    token = shopify.get('access_token', shopify.get('token', ''))

    if not shop.endswith('.myshopify.com'):
        shop = f'{shop}.myshopify.com'

    headers = {'X-Shopify-Access-Token': token, 'Content-Type': 'application/json'}
    base = f'https://{shop}/admin/api/2024-01'

    # Get DRAFT products
    url = f'{base}/products.json?limit=250&status=draft&fields=id,title,variants'
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        logger.error(f'  Error: {r.status_code}')
        return 0

    products = r.json().get('products', [])
    logger.info(f'  {len(products)} productos en DRAFT')

    if not products:
        return 0

    # Init External Intel
    intel = ExternalIntel()

    rescued = 0
    failed = 0

    for i, p in enumerate(products[:limit]):
        title = p['title']

        # Clean title for search
        search_title = title.replace('Empaque ', '').replace('Conector Mofle ', '')[:60]

        # Search for price
        try:
            result = intel.rescue_price(search_title, store_name.upper())

            if result and result.price > 0:
                # Update price in Shopify
                variant_id = p['variants'][0]['id']
                update_url = f'{base}/variants/{variant_id}.json'
                payload = {'variant': {'price': str(result.price)}}

                resp = requests.put(update_url, headers=headers, json=payload)
                time.sleep(0.3)

                if resp.status_code == 200:
                    # Change to ACTIVE
                    prod_url = f'{base}/products/{p["id"]}.json'
                    status_payload = {'product': {'status': 'active'}}
                    requests.put(prod_url, headers=headers, json=status_payload)
                    time.sleep(0.3)

                    rescued += 1
                    if rescued <= 5:
                        logger.info(f'  OK {title[:35]} -> ${result.price} ({result.source})')
            else:
                failed += 1
        except Exception as e:
            logger.error(f'  Error: {e}')
            failed += 1

        if (i + 1) % 10 == 0:
            logger.info(f'  Progreso: {i+1}/{min(len(products), limit)}')

    logger.info(f'  RESCUED: {rescued} | FAILED: {failed}')
    return rescued

if __name__ == '__main__':
    store = sys.argv[1] if len(sys.argv) > 1 else 'japan'
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    rescue_draft_prices(store, limit)
