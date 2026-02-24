#!/usr/bin/env python3
"""V18 Image Diagnosis - Step 1.0"""
import os
import json
import glob
import requests
import time

# Load brand configs
brands_dir = '/opt/odi/data/brands'
productos_dir = '/opt/odi/data/orden_maestra_v6'
image_banks = [
    '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data',
    '/opt/odi/data'
]

results = []

# Get all stores from JSONs
json_files = sorted(glob.glob(f'{productos_dir}/*.json'))

for json_file in json_files:
    store = os.path.basename(json_file).replace('.json', '').upper()
    
    # Count products
    with open(json_file, 'r') as f:
        products = json.load(f)
    total = len(products)
    
    # Count products with images (from JSON)
    con_imagen = sum(1 for p in products if p.get('images') or p.get('image_src'))
    sin_imagen = total - con_imagen
    
    # Count images in bank
    imagenes_banco = 0
    for bank in image_banks:
        # Check various possible paths
        paths_to_check = [
            f'{bank}/{store}',
            f'{bank}/{store}/images',
            f'{bank}/{store.lower()}',
            f'{bank}/{store.lower()}/images',
            f'{bank}/{store}/smart_film_images',
        ]
        for path in paths_to_check:
            if os.path.exists(path):
                for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
                    imagenes_banco += len(glob.glob(f'{path}/{ext}'))
                    imagenes_banco += len(glob.glob(f'{path}/**/{ext}', recursive=True))
    
    # Remove duplicates from recursive count
    imagenes_banco = imagenes_banco // 2 if imagenes_banco > total * 2 else imagenes_banco
    
    gap = sin_imagen - imagenes_banco if imagenes_banco < sin_imagen else 0
    
    results.append({
        'tienda': store,
        'productos': total,
        'con_imagen': con_imagen,
        'sin_imagen': sin_imagen,
        'imagenes_banco': imagenes_banco,
        'gap': gap
    })

# Print table
print('| Tienda | Productos | Con Imagen | Sin Imagen | Imágenes Banco | Gap |')
print('|--------|-----------|------------|------------|----------------|-----|')
totals = {'productos': 0, 'con_imagen': 0, 'sin_imagen': 0, 'imagenes_banco': 0, 'gap': 0}
for r in results:
    print(f"| {r['tienda']:14} | {r['productos']:>9} | {r['con_imagen']:>10} | {r['sin_imagen']:>10} | {r['imagenes_banco']:>14} | {r['gap']:>3} |")
    for k in totals:
        totals[k] += r[k]
print('|----------------|-----------|------------|------------|----------------|-----|')
print(f"| TOTAL          | {totals['productos']:>9} | {totals['con_imagen']:>10} | {totals['sin_imagen']:>10} | {totals['imagenes_banco']:>14} | {totals['gap']:>3} |")
