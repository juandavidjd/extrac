#!/usr/bin/env python3
"""
Upload Secuencial - 14 Tiendas Restantes
Orden por tamaño (mayor a menor), PDF stores al final
REGLA: Productos quedan en DRAFT hasta autorización
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')

JSON_PATH = '/opt/odi/data/orden_maestra_v6'
PDF_JSON_PATH = '/opt/odi/data/pdf_extracted'
API_VERSION = '2024-01'

# Orden de upload (por tamaño, PDF al final)
STORES_ORDER = [
    # CSV stores primero (ya tienen JSON en orden_maestra_v6)
    ('OH_IMPORTACIONES', 1414, 'csv'),
    ('DUNA', 1200, 'csv'),
    ('IMBRA', 1131, 'csv'),
    ('YOKOMAR', 1000, 'csv'),
    ('JAPAN', 734, 'csv'),
    ('BARA', 698, 'csv'),
    ('KAIQI', 138, 'csv'),
    ('LEO', 120, 'csv'),
    ('STORE', 66, 'csv'),
    ('VAISAND', 50, 'csv'),
    # PDF stores al final (requieren extracción completa)
    ('ARMOTOS', 377, 'pdf'),
    ('MCLMOTOS', 349, 'pdf'),
    ('CBI', 227, 'pdf'),
    ('VITTON', 160, 'pdf'),
]

# Mapeo tienda -> env vars
STORE_CREDENTIALS = {
    'OH_IMPORTACIONES': ('OH_IMPORTACIONES_SHOP', 'OH_IMPORTACIONES_TOKEN'),
    'DUNA': ('DUNA_SHOP', 'DUNA_TOKEN'),
    'IMBRA': ('IMBRA_SHOP', 'IMBRA_TOKEN'),
    'YOKOMAR': ('YOKOMAR_SHOP', 'YOKOMAR_TOKEN'),
    'JAPAN': ('JAPAN_SHOP', 'JAPAN_TOKEN'),
    'BARA': ('BARA_SHOP', 'BARA_TOKEN'),
    'KAIQI': ('KAIQI_SHOP', 'KAIQI_TOKEN'),
    'LEO': ('LEO_SHOP', 'LEO_TOKEN'),
    'STORE': ('STORE_SHOP', 'STORE_TOKEN'),
    'VAISAND': ('VAISAND_SHOP', 'VAISAND_TOKEN'),
    'ARMOTOS': ('ARMOTOS_SHOP', 'ARMOTOS_TOKEN'),
    'MCLMOTOS': ('MCLMOTOS_SHOP', 'MCLMOTOS_TOKEN'),
    'CBI': ('CBI_SHOP', 'CBI_TOKEN'),
    'VITTON': ('VITTON_SHOP', 'VITTON_TOKEN'),
}


def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}", flush=True)


def get_credentials(store_name):
    shop_var, token_var = STORE_CREDENTIALS[store_name]
    return os.getenv(shop_var), os.getenv(token_var)


def shopify_request(shop, token, method, endpoint, data=None):
    url = f'https://{shop}/admin/api/{API_VERSION}/{endpoint}'
    headers = {
        'X-Shopify-Access-Token': token,
        'Content-Type': 'application/json'
    }

    for attempt in range(5):
        try:
            if method == 'GET':
                r = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                r = requests.post(url, headers=headers, json=data, timeout=60)
            elif method == 'DELETE':
                r = requests.delete(url, headers=headers, timeout=30)

            if r.status_code == 429:
                retry_after = float(r.headers.get('Retry-After', 2))
                log(f"    Rate limit, waiting {retry_after}s")
                time.sleep(retry_after)
                continue

            return r
        except Exception as e:
            if attempt < 4:
                time.sleep(2 ** attempt)
            else:
                log(f"    Request failed: {e}")
                return None
    return None


def wipe_store(shop, token, store_name):
    """Elimina todos los productos"""
    log(f"  Wiping {store_name}...")
    deleted = 0

    while True:
        r = shopify_request(shop, token, 'GET', 'products.json?limit=250&fields=id')
        if not r or r.status_code != 200:
            break

        products = r.json().get('products', [])
        if not products:
            break

        for p in products:
            dr = shopify_request(shop, token, 'DELETE', f'products/{p["id"]}.json')
            if dr and dr.status_code in [200, 204]:
                deleted += 1
            time.sleep(0.25)

    log(f"    Deleted {deleted} products")
    return deleted


def upload_products(shop, token, store_name, products):
    """Sube productos en status DRAFT"""
    log(f"  Uploading {len(products)} products (DRAFT mode)...")

    uploaded = 0
    errors = 0

    for i, p in enumerate(products):
        price = p.get('price', 0)
        if price is None or price <= 0:
            price = 0

        # Image handling
        images = []
        img = p.get('image', '')
        if img and isinstance(img, str):
            if img.startswith('http') and 'placeholder' not in img:
                images = [{'src': img}]
            elif img.startswith('/opt/odi/'):
                # Local file - skip for now (would need hosting)
                pass

        product_data = {
            'product': {
                'title': p.get('title', 'Sin titulo')[:255],
                'body_html': p.get('description', '') or p.get('body_html', ''),
                'vendor': store_name,
                'product_type': p.get('category', 'Repuestos'),
                'tags': [store_name, p.get('system', 'GENERAL')],
                'status': 'draft',  # IMPORTANTE: DRAFT hasta autorización
                'variants': [{
                    'sku': str(p.get('sku', ''))[:255],
                    'price': str(price),
                    'inventory_management': 'shopify',
                    'inventory_quantity': 10
                }]
            }
        }

        if images:
            product_data['product']['images'] = images

        r = shopify_request(shop, token, 'POST', 'products.json', product_data)

        if r and r.status_code == 201:
            uploaded += 1
        else:
            errors += 1
            if errors <= 3:
                status = r.status_code if r else 'no response'
                log(f"    Error {i}: {status} - {p.get('title', '')[:30]}")

        if (i + 1) % 100 == 0:
            log(f"    Progress: {i+1}/{len(products)} ({uploaded} ok, {errors} err)")

        time.sleep(0.3)

    log(f"    Completed: {uploaded} uploaded, {errors} errors")
    return uploaded, errors


def get_json_path(store_name, source_type):
    """Obtiene path del JSON según tipo de tienda"""
    if source_type == 'csv':
        return os.path.join(JSON_PATH, f'{store_name}_products.json')
    else:  # pdf
        return os.path.join(PDF_JSON_PATH, store_name, f'{store_name}_extracted.json')


def check_pdf_ready(store_name):
    """Verifica si la extracción PDF está completa"""
    json_path = get_json_path(store_name, 'pdf')
    if not os.path.exists(json_path):
        return False, "JSON not found"

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        if len(data) < 10:
            return False, f"Only {len(data)} products (extraction incomplete?)"
        return True, f"{len(data)} products ready"
    except Exception as e:
        return False, str(e)


def main():
    log("="*70)
    log("UPLOAD SECUENCIAL - 14 TIENDAS RESTANTES")
    log("="*70)
    log("NOTA: Productos suben en status DRAFT")
    log("      Activación requiere autorización manual")
    log("")

    results = []

    for store_name, expected_count, source_type in STORES_ORDER:
        log(f"\n[{store_name}] ({expected_count} esperados, fuente: {source_type})")
        log("-" * 50)

        # Get credentials
        shop, token = get_credentials(store_name)
        if not shop or not token:
            log(f"  ERROR: No credentials")
            results.append({'store': store_name, 'status': 'NO_CREDENTIALS'})
            continue

        # Check if PDF extraction is ready
        if source_type == 'pdf':
            ready, msg = check_pdf_ready(store_name)
            if not ready:
                log(f"  SKIPPED: PDF extraction not ready - {msg}")
                results.append({'store': store_name, 'status': f'PDF_NOT_READY: {msg}'})
                continue

        # Load JSON
        json_path = get_json_path(store_name, source_type)
        if not os.path.exists(json_path):
            log(f"  ERROR: JSON not found: {json_path}")
            results.append({'store': store_name, 'status': 'NO_JSON'})
            continue

        with open(json_path, 'r', encoding='utf-8') as f:
            products = json.load(f)

        log(f"  Loaded {len(products)} products")

        # Wipe existing
        wipe_store(shop, token, store_name)

        # Upload new (DRAFT mode)
        uploaded, errors = upload_products(shop, token, store_name, products)

        results.append({
            'store': store_name,
            'source': source_type,
            'json_count': len(products),
            'uploaded': uploaded,
            'errors': errors,
            'status': 'DRAFT'
        })

    # Summary
    log("\n" + "="*70)
    log("RESUMEN FINAL")
    log("="*70)
    log("")
    log(f"| {'Tienda':<18} | {'Fuente':<6} | {'JSON':>8} | {'Subidos':>8} | {'Status':<12} |")
    log(f"|{'-'*20}|{'-'*8}|{'-'*10}|{'-'*10}|{'-'*14}|")

    total_uploaded = 0

    for r in results:
        if 'uploaded' in r:
            log(f"| {r['store']:<18} | {r['source']:<6} | {r['json_count']:>8} | {r['uploaded']:>8} | {r['status']:<12} |")
            total_uploaded += r['uploaded']
        else:
            log(f"| {r['store']:<18} | {'---':<6} | {'---':>8} | {'---':>8} | {r['status']:<12} |")

    log(f"|{'-'*20}|{'-'*8}|{'-'*10}|{'-'*10}|{'-'*14}|")
    log(f"| {'TOTAL':<18} | {'':6} | {'':>8} | {total_uploaded:>8} | {'DRAFT':<12} |")
    log("")
    log("IMPORTANTE: Todos los productos están en DRAFT")
    log("           Ejecutar activación solo con autorización")


if __name__ == '__main__':
    main()
