#!/usr/bin/env python3
"""
ARMOTOS EXTRACCION UNIFICADA - Producto + Imagen nacen juntos
15 Feb 2026
"""
import sys
sys.path.insert(0, '/opt/odi/odi_production/extractors')

import os
import json
import time
import base64
import requests
import logging
import warnings
warnings.filterwarnings('ignore')
from dotenv import load_dotenv
from pdf2image import convert_from_path
from unified_extractor import UnifiedExtractor

load_dotenv('/opt/odi/.env')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('armotos')

PDF = '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Armotos/CATALOGO NOVIEMBRE V01-2025 NF.pdf'
OUT = '/opt/odi/data/ARMOTOS'
STORE = 'ARMOTOS'

shop = os.getenv('ARMOTOS_SHOP')
token = os.getenv('ARMOTOS_TOKEN')
headers = {'X-Shopify-Access-Token': token, 'Content-Type': 'application/json'}

def upload_to_shopify(product):
    """Sube producto a Shopify con imagen y ficha 360"""
    title = product.get('normalized_title') or product.get('name', 'Producto')
    price = product.get('price', 0)
    if isinstance(price, str):
        price = float(price.replace(',', '').replace('$', '')) if price else 0
    
    shopify_product = {
        'product': {
            'title': title,
            'body_html': product.get('body_html', ''),
            'vendor': STORE,
            'product_type': product.get('category', 'Repuesto'),
            'tags': ','.join(product.get('compatible_models', [])),
            'variants': [{
                'price': str(price) if price > 0 else '0',
                'sku': product.get('sku', ''),
                'inventory_management': None
            }]
        }
    }
    
    # Add image if exists
    img_path = product.get('image_path')
    if img_path and os.path.exists(img_path):
        with open(img_path, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
        shopify_product['product']['images'] = [{'attachment': img_b64}]
    
    try:
        r = requests.post(
            f'https://{shop}/admin/api/2025-07/products.json',
            headers=headers,
            json=shopify_product,
            timeout=30
        )
        if r.status_code == 201:
            return True
        else:
            return False
    except:
        return False

def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(f'{OUT}/images', exist_ok=True)
    os.makedirs(f'{OUT}/json', exist_ok=True)
    
    log.info('=' * 60)
    log.info('ARMOTOS EXTRACCION UNIFICADA')
    log.info('=' * 60)
    
    extractor = UnifiedExtractor()
    
    # Get total pages
    from PyPDF2 import PdfReader
    reader = PdfReader(PDF)
    total_pages = len(reader.pages)
    log.info(f'PDF tiene {total_pages} paginas')
    
    all_products = []
    uploaded = 0
    errors = 0
    
    # Process in batches
    BATCH_SIZE = 10
    
    for batch_start in range(1, total_pages + 1, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE - 1, total_pages)
        log.info(f'Batch: paginas {batch_start}-{batch_end}')
        
        for page_num in range(batch_start, batch_end + 1):
            try:
                pages = convert_from_path(PDF, dpi=200, first_page=page_num, last_page=page_num)
                temp_path = f'{OUT}/temp_page.png'
                pages[0].save(temp_path)
                
                products = extractor.extract_page_unified(temp_path, STORE, page_num, OUT)
                
                for prod in products:
                    all_products.append(prod)
                    if upload_to_shopify(prod):
                        uploaded += 1
                    else:
                        errors += 1
                    
                    if uploaded % 50 == 0:
                        log.info(f'  Uploaded: {uploaded}, Errors: {errors}')
                
            except Exception as e:
                log.error(f'  Page {page_num} error: {e}')
        
        time.sleep(1)  # Rate limit between batches
    
    # Save all products to JSON
    with open(f'{OUT}/json/products_unified.json', 'w') as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    
    log.info('=' * 60)
    log.info('RESULTADO FINAL')
    log.info('=' * 60)
    total = len(all_products)
    with_img = len([p for p in all_products if p.get('image_path')])
    with_price = len([p for p in all_products if p.get('price', 0) > 0])
    log.info(f'Total productos extraidos: {total}')
    log.info(f'Con imagen: {with_img} ({with_img/max(total,1)*100:.0f}%)')
    log.info(f'Con precio: {with_price} ({with_price/max(total,1)*100:.0f}%)')
    log.info(f'Uploaded a Shopify: {uploaded}')
    log.info(f'Errores: {errors}')
    log.info('=' * 60)

if __name__ == '__main__':
    main()
