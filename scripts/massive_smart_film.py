#!/usr/bin/env python3
"""Generate smart film images for all ARMOTOS products with hotspots"""
import sys
sys.path.insert(0, '/opt/odi')

from core.odi_image_highlighter import ImageHighlighter
import json
import os

PAGES_DIR = '/opt/odi/data/ARMOTOS/hotspot_pages'
HOTSPOTS_FILE = '/opt/odi/data/ARMOTOS/hotspot_map_sample.json'
OUTPUT_DIR = '/opt/odi/data/ARMOTOS/smart_film_images'

os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(HOTSPOTS_FILE) as f:
    hotspots = json.load(f)

highlighter = ImageHighlighter(overlay_color='black', alpha=180)

total = 0
success = 0
failed = 0

print('=== GENERACIÓN MASIVA PELÍCULA INTELIGENTE ===')
print(f'Modo: Negro α180 | Salida: {OUTPUT_DIR}')
print()

for page_key, page_data in hotspots.get('hotspots', {}).items():
    page_num = int(page_key.replace('page_', ''))
    products = page_data.get('products', [])
    
    for product in products:
        bbox = product.get('bbox', {})
        sku = str(product.get('codigo', product.get('sku', 'unknown')))
        
        if not bbox:
            continue
        
        total += 1
        input_path = f'{PAGES_DIR}/page_{page_num}.png'
        output_path = f'{OUTPUT_DIR}/page_{page_num:03d}_sku_{sku}.png'
        
        if highlighter.highlight_product_row(input_path, bbox, output_path, full_width=True):
            success += 1
        else:
            failed += 1
        
        if total % 100 == 0:
            print(f'  Procesados: {total} ({success} ok, {failed} fail)')

print()
print(f'=== COMPLETADO ===')
print(f'Total: {total}')
print(f'Éxito: {success}')
print(f'Fallidos: {failed}')
print(f'Imágenes en: {OUTPUT_DIR}')
