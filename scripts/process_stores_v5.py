#!/usr/bin/env python3
"""
ORDEN MAESTRA v5 - Pipeline con Fuzzy Image Matching + Vision Fix
15 tiendas Shopify - Solo JSON output (sin upload)
"""

import os
import re
import csv
import json
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

BASE_PATH = '/mnt/volume_sfo3_01/profesion/ecosistema_odi'
VISION_PATH = '/opt/odi/data/pending_upload'
OUTPUT_PATH = '/opt/odi/data/orden_maestra_v5'

# Orden de procesamiento (mejor data primero para KB learning)
STORES_ORDER = [
    'DFG', 'OH_IMPORTACIONES', 'BARA', 'DUNA', 'IMBRA', 'YOKOMAR',
    'JAPAN', 'ARMOTOS', 'MCLMOTOS', 'CBI', 'KAIQI', 'LEO',
    'VITTON', 'STORE', 'VAISAND'
]

# Tiendas con Vision AI (usar JSONs pre-extraidos)
VISION_STORES = ['ARMOTOS', 'MCLMOTOS', 'CBI', 'VITTON']

# Placeholders genericos por sistema
GENERIC_IMAGES = {
    'MOTOR': 'https://cdn.shopify.com/s/files/1/0placeholder/motor.jpg',
    'TRANSMISION': 'https://cdn.shopify.com/s/files/1/0placeholder/transmision.jpg',
    'SUSPENSION': 'https://cdn.shopify.com/s/files/1/0placeholder/suspension.jpg',
    'FRENOS': 'https://cdn.shopify.com/s/files/1/0placeholder/frenos.jpg',
    'ELECTRICO': 'https://cdn.shopify.com/s/files/1/0placeholder/electrico.jpg',
    'CARROCERIA': 'https://cdn.shopify.com/s/files/1/0placeholder/carroceria.jpg',
    'default': 'https://cdn.shopify.com/s/files/1/0placeholder/moto.jpg'
}

def normalize_for_match(text):
    if not text:
        return ''
    text = str(text).lower()
    replacements = {'á':'a','é':'e','í':'i','ó':'o','ú':'u','ñ':'n','ü':'u'}
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return ' '.join(text.split())

def extract_keywords(text):
    normalized = normalize_for_match(text)
    words = normalized.split()
    stopwords = {'para', 'con', 'sin', 'los', 'las', 'del', 'por', 'que', 'una', 'uno', 'moto', 'motocicleta'}
    return [w for w in words if len(w) >= 3 and w not in stopwords]

def similarity_score(text1, text2):
    norm1 = normalize_for_match(text1)
    norm2 = normalize_for_match(text2)
    if not norm1 or not norm2:
        return 0
    seq_score = SequenceMatcher(None, norm1, norm2).ratio()
    kw1 = set(extract_keywords(text1))
    kw2 = set(extract_keywords(text2))
    if kw1 and kw2:
        common = kw1 & kw2
        kw_score = len(common) / max(len(kw1), len(kw2))
    else:
        kw_score = 0
    return (seq_score * 0.4) + (kw_score * 0.6)

def fuzzy_match_image(title, image_bank, threshold=0.35):
    best_match = None
    best_score = 0
    for img_name, img_path in image_bank.items():
        base_name = os.path.splitext(img_name)[0]
        img_text = base_name.replace('-', ' ').replace('_', ' ')
        score = similarity_score(title, img_text)
        if score > best_score:
            best_score = score
            best_match = img_path
    if best_score >= threshold:
        return best_match, best_score
    return None, 0

def parse_price_cop(price_str):
    if not price_str:
        return 0
    price_str = str(price_str).strip()
    price_str = price_str.replace('$', '').replace(' ', '').replace(',', '')
    # Detectar formato miles: 135.000 -> 135000
    if re.match(r'^\d{1,3}(\.\d{3})+$', price_str):
        price_str = price_str.replace('.', '')
    try:
        return float(price_str)
    except:
        return 0

def normalize_sku(sku):
    if not sku:
        return ''
    sku = str(sku).strip().upper()
    if '/' in sku:
        parts = sku.split('/')
        parts = [p.lstrip('0') or '0' for p in parts]
        sku = '-'.join(parts)
    return sku

def classify_product(title):
    title_upper = title.upper() if title else ''

    systems = {
        'MOTOR': ['ACEITE', 'FILTRO', 'PISTON', 'CILINDRO', 'BIELA', 'CIGUENAL', 'VALVULA', 'ARBOL', 'EJE'],
        'TRANSMISION': ['CADENA', 'PIÑON', 'CORONA', 'KIT', 'CLUTCH', 'EMBRAGUE'],
        'SUSPENSION': ['AMORTIGUADOR', 'TIJERA', 'DIRECCION', 'RODAMIENTO', 'BALINERA'],
        'FRENOS': ['PASTILLA', 'DISCO', 'ZAPATA', 'BOMBA FRENO', 'PALANCA'],
        'ELECTRICO': ['BOBINA', 'CDI', 'REGULADOR', 'FARO', 'BOMBILLO', 'BATERIA', 'SWITCH'],
        'CARROCERIA': ['PLASTICO', 'GUARDABARRO', 'TANQUE', 'ASIENTO', 'ESPEJO', 'MANUBRIO']
    }

    for system, keywords in systems.items():
        for kw in keywords:
            if kw in title_upper:
                return system, 'REPUESTOS'

    if 'LLANTA' in title_upper or 'NEUMATICO' in title_upper:
        return 'LLANTAS', 'LLANTAS'
    if 'CASCO' in title_upper or 'GUANTE' in title_upper:
        return 'ACCESORIOS', 'ACCESORIOS'

    return 'GENERAL', 'REPUESTOS'

def load_image_bank(store_path, store_name):
    images = {}
    img_dir = os.path.join(store_path, 'imagenes')

    if os.path.exists(img_dir):
        for root, dirs, files in os.walk(img_dir):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                    full_path = os.path.join(root, f)
                    key = f.upper()
                    images[key] = full_path

    return images

def load_csv_with_urls(store_path):
    urls = {}

    for subdir in ['catalogo', 'precios']:
        dir_path = os.path.join(store_path, subdir)
        if not os.path.exists(dir_path):
            continue

        for f in os.listdir(dir_path):
            if f.lower().endswith('.csv'):
                csv_path = os.path.join(dir_path, f)
                try:
                    for enc in ['utf-8', 'latin-1', 'cp1252']:
                        try:
                            with open(csv_path, 'r', encoding=enc) as file:
                                sample = file.read(2048)
                                delimiter = ';' if ';' in sample else ','
                                file.seek(0)
                                reader = csv.DictReader(file, delimiter=delimiter)
                                for row in reader:
                                    row = {k.strip().replace('\ufeff', ''): v for k, v in row.items() if k}

                                    sku = row.get('SKU') or row.get('CODIGO') or row.get('sku') or row.get('codigo') or ''
                                    sku = normalize_sku(sku)

                                    img_url = (row.get('Imagen_URL_Origen') or row.get('Imagen_Externa') or
                                              row.get('imagen') or row.get('URL_IMAGEN') or
                                              row.get('image_url') or row.get('URL') or row.get('url') or '')

                                    if sku and img_url and img_url.startswith('http'):
                                        urls[sku] = img_url
                            break
                        except UnicodeDecodeError:
                            continue
                except Exception as e:
                    pass

    return urls

def load_prices(store_path):
    prices = {}

    for subdir in ['precios', 'catalogo']:
        dir_path = os.path.join(store_path, subdir)
        if not os.path.exists(dir_path):
            continue

        for f in os.listdir(dir_path):
            if f.lower().endswith('.csv'):
                csv_path = os.path.join(dir_path, f)
                try:
                    for enc in ['utf-8', 'latin-1', 'cp1252']:
                        try:
                            with open(csv_path, 'r', encoding=enc) as file:
                                sample = file.read(2048)
                                delimiter = ';' if ';' in sample else ','
                                file.seek(0)
                                reader = csv.DictReader(file, delimiter=delimiter)
                                for row in reader:
                                    row = {k.strip().replace('\ufeff', ''): v for k, v in row.items() if k}

                                    sku = row.get('SKU') or row.get('CODIGO') or row.get('sku') or row.get('codigo') or ''
                                    sku = normalize_sku(sku)

                                    price_str = (row.get('PRECIO') or row.get('precio') or
                                                row.get('PRICE') or row.get('price') or '')
                                    price = parse_price_cop(price_str)

                                    if sku and price > 0:
                                        prices[sku] = price
                            break
                        except UnicodeDecodeError:
                            continue
                except:
                    pass

    return prices

def process_csv_store(store_name, store_path):
    products = []
    image_bank = load_image_bank(store_path, store_name)
    image_urls = load_csv_with_urls(store_path)
    prices_db = load_prices(store_path)

    # Buscar CSV principal
    main_csv = None
    for subdir in ['catalogo', 'precios', '.']:
        dir_path = os.path.join(store_path, subdir) if subdir != '.' else store_path
        if not os.path.exists(dir_path):
            continue
        for f in os.listdir(dir_path):
            if f.lower().endswith('.csv') and ('base' in f.lower() or 'catalogo' in f.lower() or 'producto' in f.lower()):
                main_csv = os.path.join(dir_path, f)
                break
        if main_csv:
            break

    if not main_csv:
        for subdir in ['catalogo', 'precios', '.']:
            dir_path = os.path.join(store_path, subdir) if subdir != '.' else store_path
            if not os.path.exists(dir_path):
                continue
            for f in os.listdir(dir_path):
                if f.lower().endswith('.csv'):
                    main_csv = os.path.join(dir_path, f)
                    break
            if main_csv:
                break

    if not main_csv:
        return products, {'images': len(image_bank), 'urls': len(image_urls)}

    # Leer CSV
    for enc in ['utf-8', 'latin-1', 'cp1252']:
        try:
            with open(main_csv, 'r', encoding=enc) as file:
                sample = file.read(2048)
                delimiter = ';' if ';' in sample else ','
                file.seek(0)
                reader = csv.DictReader(file, delimiter=delimiter)

                for row in reader:
                    row = {k.strip().replace('\ufeff', ''): v for k, v in row.items() if k}

                    sku = row.get('SKU') or row.get('CODIGO') or row.get('sku') or row.get('codigo') or ''
                    sku = normalize_sku(sku)

                    title = (row.get('DESCRIPCION') or row.get('TITULO') or row.get('Title') or
                            row.get('titulo') or row.get('descripcion') or row.get('NOMBRE') or '')
                    title = str(title).strip()

                    if not title:
                        continue

                    price_str = (row.get('PRECIO') or row.get('precio') or
                                row.get('PRICE') or row.get('price') or '')
                    price = parse_price_cop(price_str)
                    if price == 0 and sku:
                        price = prices_db.get(sku, 0)

                    system, category = classify_product(title)

                    # Imagen: 1) URL del CSV, 2) Fuzzy match en banco, 3) Placeholder
                    img = ''
                    img_source = 'none'

                    if sku and sku in image_urls:
                        img = image_urls[sku]
                        img_source = 'csv_url'

                    if not img:
                        url_field = (row.get('Imagen_URL_Origen') or row.get('Imagen_Externa') or
                                    row.get('imagen') or row.get('URL_IMAGEN') or row.get('image_url') or '')
                        if url_field and url_field.startswith('http'):
                            img = url_field
                            img_source = 'csv_url'

                    if not img and image_bank:
                        matched_img, score = fuzzy_match_image(title, image_bank)
                        if matched_img:
                            img = matched_img
                            img_source = f'fuzzy_{score:.2f}'

                    if not img:
                        img = GENERIC_IMAGES.get(system, GENERIC_IMAGES['default'])
                        img_source = 'placeholder'

                    products.append({
                        'sku': sku or f'{store_name}-{len(products)+1}',
                        'title': title,
                        'price': price,
                        'system': system,
                        'category': category,
                        'image': img,
                        'image_source': img_source,
                        'vendor': store_name
                    })
            break
        except UnicodeDecodeError:
            continue

    return products, {'images': len(image_bank), 'urls': len(image_urls)}

def process_vision_store(store_name):
    products = []
    json_path = os.path.join(VISION_PATH, store_name, 'products_ready.json')

    if not os.path.exists(json_path):
        return products, {}

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        title = item.get('title') or item.get('name') or ''
        if not title:
            continue

        # Handle nested variants structure
        variants = item.get('variants', [])
        first_variant = variants[0] if variants else {}

        sku = (first_variant.get('sku') or item.get('sku') or
               item.get('codigo') or f'{store_name}-{len(products)+1}')

        # Price from variants or direct
        price_raw = first_variant.get('price') or item.get('price') or item.get('precio') or 0
        price = parse_price_cop(price_raw)

        system, category = classify_product(title)

        # Image from images array or direct
        images_arr = item.get('images', [])
        img = ''
        if images_arr:
            first_img = images_arr[0]
            img = first_img.get('src') or first_img.get('url') or ''
        if not img:
            img = item.get('image') or item.get('imagen') or ''

        img_source = 'vision' if img else 'placeholder'
        if not img:
            img = GENERIC_IMAGES.get(system, GENERIC_IMAGES['default'])

        products.append({
            'sku': sku,
            'title': title,
            'price': price,
            'system': system,
            'category': category,
            'image': img,
            'image_source': img_source,
            'vendor': store_name
        })

    return products, {'vision_products': len(data)}

def main():
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    results = []
    total_products = 0

    print('='*60)
    print('ORDEN MAESTRA v5 - FUZZY + VISION FIX')
    print('='*60)
    print()

    for store_name in STORES_ORDER:
        store_path = os.path.join(BASE_PATH, store_name)

        print(f'[{store_name}]')

        if store_name in VISION_STORES:
            products, meta = process_vision_store(store_name)
            print(f'  Fuente: Vision AI JSON')
        else:
            products, meta = process_csv_store(store_name, store_path)
            print(f'  Fuente: CSV')
            print(f'  Banco imagenes: {meta.get("images", 0)}, URLs CSV: {meta.get("urls", 0)}')

        if not products:
            print(f'  Sin productos')
            results.append({'store': store_name, 'products': 0, 'price_pct': 0, 'image_pct': 0})
            continue

        with_price = sum(1 for p in products if p['price'] > 0)
        with_real_img = sum(1 for p in products if p['image_source'] != 'placeholder')

        price_pct = round(with_price / len(products) * 100)
        image_pct = round(with_real_img / len(products) * 100)

        print(f'  Productos: {len(products)}')
        print(f'  Precio: {price_pct}% ({with_price}/{len(products)})')
        print(f'  Imagen: {image_pct}% ({with_real_img}/{len(products)})')

        output_file = os.path.join(OUTPUT_PATH, f'{store_name}_products.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print(f'  -> {output_file}')

        results.append({
            'store': store_name,
            'products': len(products),
            'price_pct': price_pct,
            'image_pct': image_pct,
            'with_price': with_price,
            'with_image': with_real_img
        })

        total_products += len(products)
        print()

    print('='*60)
    print('RESUMEN FINAL')
    print('='*60)
    print()
    print(f'| {"Tienda":<18} | {"Productos":>10} | {"Precio":>7} | {"Imagen":>7} |')
    print(f'|{"-"*20}|{"-"*12}|{"-"*9}|{"-"*9}|')

    for r in results:
        print(f'| {r["store"]:<18} | {r["products"]:>10} | {r["price_pct"]:>6}% | {r["image_pct"]:>6}% |')

    print(f'|{"-"*20}|{"-"*12}|{"-"*9}|{"-"*9}|')
    print(f'| {"TOTAL":<18} | {total_products:>10} |         |         |')
    print()
    print(f'JSONs guardados en: {OUTPUT_PATH}')

if __name__ == '__main__':
    main()
