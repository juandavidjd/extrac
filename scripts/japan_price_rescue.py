#!/usr/bin/env python3
"""
ODI JAPAN Price Rescue - Mode Price-First
Rescate específico para productos sin precio de JAPAN.
- Micro-batching de 20 productos
- Skip Stage 3 (Enrichment)
- External Intel directo
- Actualización inmediata al JSON
"""

import os
import sys
import json
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('japan_rescue')

# Paths
DATA_PATH = '/opt/odi/data/orden_maestra_v6/'
JAPAN_JSON = os.path.join(DATA_PATH, 'JAPAN_products.json')

# Config
BATCH_SIZE = 20
GLOBAL_TIMEOUT = 1200  # 20 minutos
MAX_API_CALLS_PER_BATCH = 15

# Load environment
def load_env():
    env_path = '/opt/odi/.env'
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip().strip("'").strip('"')

load_env()

# Import External Intel after loading env
sys.path.insert(0, '/opt/odi')
try:
    from core.external_intel import ExternalIntel
    INTEL_AVAILABLE = True
except ImportError:
    logger.warning('External Intel not available - using fallback')
    INTEL_AVAILABLE = False

def load_japan_products():
    with open(JAPAN_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_japan_products(products):
    with open(JAPAN_JSON, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def get_zero_price_products(products):
    zero_price = []
    for i, p in enumerate(products):
        price = p.get('price') or 0
        try:
            price = float(price)
        except:
            price = 0
        if price <= 0:
            zero_price.append((i, p))
    return zero_price

def rescue_batch(batch, intel, all_products):
    rescued = 0
    failed = 0

    for idx, product in batch:
        sku = product.get('sku', '')
        title = product.get('title', '')

        if not title:
            failed += 1
            continue

        try:
            result = intel.rescue_price(
                product_name=title,
                store='JAPAN',
                csv_prices=None,
                sku=sku,
                has_image_match=False
            )

            if result and result.price > 0:
                all_products[idx]['price'] = result.price
                all_products[idx]['price_source'] = 'external_intel:' + result.source
                all_products[idx]['price_rescued_at'] = datetime.utcnow().isoformat()
                rescued += 1
                logger.info('  OK %s: $%s (%s)', sku, format(result.price, ','), result.source)
            else:
                failed += 1
                logger.warning('  FAIL %s: Sin precio - %s...', sku, title[:40])

        except Exception as e:
            failed += 1
            logger.error('  ERROR %s: %s', sku, str(e)[:50])

        time.sleep(0.5)

    return rescued, failed

def main():
    start_time = time.time()

    print('=' * 60)
    print('ODI JAPAN PRICE RESCUE - Mode Price-First')
    print('Fecha:', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))
    print('Timeout:', GLOBAL_TIMEOUT, 's | Batch:', BATCH_SIZE)
    print('=' * 60)
    print()

    logger.info('Cargando productos JAPAN...')
    products = load_japan_products()
    total = len(products)

    zero_price = get_zero_price_products(products)
    logger.info('Total productos: %d', total)
    logger.info('Productos sin precio: %d', len(zero_price))
    print()

    if not zero_price:
        logger.info('No hay productos sin precio. Saliendo.')
        return

    if not INTEL_AVAILABLE:
        logger.error('External Intel no disponible. Saliendo.')
        return

    intel = ExternalIntel()

    total_rescued = 0
    total_failed = 0
    batch_num = 0

    for i in range(0, len(zero_price), BATCH_SIZE):
        batch_num += 1
        batch = zero_price[i:i + BATCH_SIZE]

        elapsed = time.time() - start_time
        if elapsed > GLOBAL_TIMEOUT:
            logger.warning('Timeout alcanzado (%ds). Guardando progreso...', GLOBAL_TIMEOUT)
            break

        remaining = GLOBAL_TIMEOUT - elapsed
        logger.info('--- Batch %d (%d productos) | Tiempo restante: %ds ---', batch_num, len(batch), int(remaining))

        rescued, failed = rescue_batch(batch, intel, products)
        total_rescued += rescued
        total_failed += failed

        if rescued > 0:
            save_japan_products(products)
            logger.info('Batch %d: %d rescatados, %d fallidos | Guardado OK', batch_num, rescued, failed)
        else:
            logger.info('Batch %d: %d rescatados, %d fallidos', batch_num, rescued, failed)

        print()

        stats = intel.get_stats()
        logger.info('API Stats: saved=%d, made=%d, retries=%d', stats['api_calls_saved'], stats['api_calls_made'], stats['backoff_retries'])

        if stats['backoff_retries'] > 20:
            logger.warning('Demasiados rate limits. Pausando 60s...')
            time.sleep(60)

        print()

    save_japan_products(products)

    elapsed = time.time() - start_time
    print()
    print('=' * 60)
    print('RESUMEN FINAL')
    print('=' * 60)
    print('Tiempo total:', int(elapsed), 's')
    print('Productos procesados:', total_rescued + total_failed)
    print('Precios rescatados:', total_rescued)
    print('Sin precio encontrado:', total_failed)
    print('Pendientes:', len(zero_price) - (total_rescued + total_failed))
    print()

    products_final = load_japan_products()
    zero_final = len([p for p in products_final if not p.get('price') or float(p.get('price', 0)) <= 0])
    print('Estado final JAPAN:', len(products_final) - zero_final, 'con precio,', zero_final, 'sin precio')
    print()

if __name__ == '__main__':
    main()
