#!/usr/bin/env python3
"""Pipeline v2 - Correcciones completas para 15 tiendas"""
import json
import csv
import re
import random
from pathlib import Path
import chromadb

BASE_DIR = Path('/mnt/volume_sfo3_01/profesion/ecosistema_odi')
PENDING_DIR = Path('/opt/odi/data/pending_upload')

STORES_ORDER = [
    'DFG', 'BARA', 'IMBRA', 'DUNA', 'YOKOMAR', 'JAPAN', 'OH_IMPORTACIONES',
    'ARMOTOS', 'MCLMOTOS', 'CBI', 'VITTON',
    'KAIQI', 'LEO', 'STORE', 'VAISAND'
]

# Tiendas con datos Vision en pending_upload
VISION_STORES = ['ARMOTOS', 'MCLMOTOS', 'CBI', 'VITTON']

PIEZAS = {
    'aceite': 'Lubricantes', 'lubricante': 'Lubricantes', 'grasa': 'Lubricantes',
    'cadena': 'Cadena de Transmision', 'arbol': 'Arbol de Levas',
    'balancin': 'Balancin', 'biela': 'Biela', 'bomba': 'Bomba',
    'bujia': 'Bujia', 'cable': 'Cable', 'carburador': 'Carburador',
    'cilindro': 'Cilindro', 'clutch': 'Clutch', 'piston': 'Piston',
    'empaque': 'Empaque', 'filtro': 'Filtro', 'llanta': 'Llanta',
    'manigueta': 'Manigueta', 'retrovisor': 'Retrovisor', 'rodamiento': 'Rodamiento',
    'balinera': 'Rodamiento', 'switch': 'Switch', 'tensor': 'Tensor',
    'valvula': 'Valvula', 'amortiguador': 'Amortiguador', 'freno': 'Freno',
    'disco': 'Disco de Freno', 'pastilla': 'Pastillas de Freno',
    'faro': 'Faro', 'direccional': 'Direccional', 'espejo': 'Espejo',
    'manubrio': 'Manubrio', 'pedal': 'Pedal', 'palanca': 'Palanca',
    'sprocket': 'Sprocket', 'piñon': 'Piñon', 'corona': 'Corona',
    'kit': 'Kit', 'juego': 'Kit', 'arandela': 'Arandela', 'tornillo': 'Tornilleria',
    'tuerca': 'Tornilleria', 'resorte': 'Resorte', 'muelle': 'Resorte',
    'guaya': 'Guaya', 'manguera': 'Manguera', 'abrazadera': 'Abrazadera',
    'bobina': 'Bobina', 'regulador': 'Regulador', 'cdi': 'CDI',
    'estator': 'Estator', 'rotor': 'Rotor', 'arranque': 'Motor de Arranque',
    'relay': 'Relay', 'fusible': 'Fusible', 'bateria': 'Bateria',
    'stop': 'Luces', 'bombillo': 'Luces', 'luz': 'Luces'
}

SISTEMAS = {
    'motor': 'Motor', 'transmision': 'Transmision', 'freno': 'Frenos',
    'suspension': 'Suspension', 'electrico': 'Electrico', 'bobina': 'Electrico',
    'cdi': 'Electrico', 'bateria': 'Electrico', 'faro': 'Electrico',
    'luz': 'Electrico', 'carroceria': 'Carroceria', 'escape': 'Escape',
    'direccion': 'Direccion', 'lubricante': 'Lubricantes', 'aceite': 'Lubricantes'
}

GENERIC_IMAGES = {
    'Motor': 'https://via.placeholder.com/400x400/1a1a2e/ffffff?text=Motor',
    'Transmision': 'https://via.placeholder.com/400x400/16213e/ffffff?text=Transmision',
    'Frenos': 'https://via.placeholder.com/400x400/0f3460/ffffff?text=Frenos',
    'Electrico': 'https://via.placeholder.com/400x400/e94560/ffffff?text=Electrico',
    'Lubricantes': 'https://via.placeholder.com/400x400/f39c12/ffffff?text=Lubricantes',
    'default': 'https://via.placeholder.com/400x400/1a1a2e/ffffff?text=Repuesto+Moto'
}


def parse_price_cop(price_str):
    """Parsea precio COP: '$ 135.000' -> 135000"""
    if not price_str:
        return 0
    price_str = str(price_str).strip()
    # Remover $ y espacios
    price_str = price_str.replace('$', '').replace(' ', '')
    # Si tiene formato X.XXX (miles con punto), quitar puntos
    if re.match(r'^\d{1,3}(\.\d{3})+$', price_str):
        price_str = price_str.replace('.', '')
    # Si tiene formato X,XXX quitar comas
    price_str = price_str.replace(',', '')
    try:
        return float(price_str)
    except:
        return 0


def normalize_sku(sku):
    if not sku:
        return ''
    sku = str(sku).replace('/', '-')
    parts = sku.split('-')
    normalized = []
    for p in parts:
        if p.isdigit():
            normalized.append(str(int(p)))
        else:
            normalized.append(p)
    return '-'.join(normalized)


def detect_pieza(title):
    title_lower = title.lower()
    for key, val in PIEZAS.items():
        if key in title_lower:
            return val
    return ''


def detect_sistema(title):
    title_lower = title.lower()
    for key, val in SISTEMAS.items():
        if key in title_lower:
            return val
    return ''


def detect_modelo(title):
    patterns = [
        r'(AKT|BAJAJ|HERO|HONDA|YAMAHA|SUZUKI|TVS|PULSAR|DISCOVER|BWS|FZ|XTZ|NKD|TITAN|CG|CB|CBF|XL|XR|KYMCO|AGILITY|CRYPTON|RX|DT|BOXER|PLATINO|APACHE|GIXXER|FAZER|MT|R15|NS|AS|DUKE|RC|KTM|VESPA|LIBERTY|ZIP|FLY|BEVERLY)\s*(\d{2,3})?',
        r'(\d{2,3})\s*(CC|cc)',
    ]
    for pat in patterns:
        m = re.search(pat, title, re.IGNORECASE)
        if m:
            return m.group(0).strip().upper()
    return ''


def enrich_title(raw_title, category='', system='', model=''):
    """Genera titulo enriquecido"""
    clean = re.sub(r'[_\-]+', ' ', raw_title)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = clean.title()

    # Si ya tiene estructura, retornar limpio
    if len(clean) > 50:
        return clean

    suffix_parts = []
    if model:
        suffix_parts.append(model)
    if system and system not in clean:
        suffix_parts.append(f"Repuesto {system}")
    elif category and category not in clean:
        suffix_parts.append(f"Repuesto Moto")

    if suffix_parts:
        return f"{clean} - {' '.join(suffix_parts)}"
    return clean


def generate_body_html(product, brand_colors=None):
    """Genera ficha HTML profesional"""
    pieza = product.get('category', 'Repuesto')
    sistema = product.get('system', 'Moto')
    modelo = product.get('compatible_models', '')
    title = product.get('title', '')

    primary = brand_colors.get('primary', '#1a1a2e') if brand_colors else '#1a1a2e'
    accent = brand_colors.get('accent', '#e94560') if brand_colors else '#e94560'

    benefits = random.sample([
        'Fabricado con materiales de alta resistencia',
        'Diseñado para máximo rendimiento',
        'Compatibilidad garantizada',
        'Durabilidad superior',
        'Instalación sencilla',
        'Producto con garantía de calidad'
    ], 3)

    benefits_html = ''.join([f'<li>{b}</li>' for b in benefits])

    descriptions = [
        f"Repuesto de alta calidad. {pieza or 'Este componente'} ofrece rendimiento óptimo y durabilidad.",
        f"{pieza or 'Componente'} fabricado con estándares superiores para tu moto.",
        f"Mantén tu moto al máximo con este {pieza.lower() if pieza else 'repuesto'} de calidad premium."
    ]

    return f'''<div style="font-family: Arial, sans-serif; color: #333;">
  <div style="background: linear-gradient(135deg, {primary}, #16213e); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
    <h2 style="margin: 0;">{title}</h2>
    <p style="margin: 10px 0 0 0; opacity: 0.9;">SKU: {product.get('sku', 'N/A')}</p>
  </div>
  <div style="margin-bottom: 20px;">
    <h3 style="color: {primary}; border-bottom: 2px solid {accent}; padding-bottom: 8px;">Descripcion</h3>
    <p>{random.choice(descriptions)}</p>
  </div>
  <div style="margin-bottom: 20px;">
    <h3 style="color: {primary}; border-bottom: 2px solid {accent}; padding-bottom: 8px;">Especificaciones</h3>
    <table style="width: 100%; border-collapse: collapse;">
      <tr style="background: #f5f5f5;"><td style="padding: 10px; border: 1px solid #ddd;"><strong>Tipo</strong></td><td style="padding: 10px; border: 1px solid #ddd;">{pieza or 'Repuesto'}</td></tr>
      <tr><td style="padding: 10px; border: 1px solid #ddd;"><strong>Sistema</strong></td><td style="padding: 10px; border: 1px solid #ddd;">{sistema or 'General'}</td></tr>
      <tr style="background: #f5f5f5;"><td style="padding: 10px; border: 1px solid #ddd;"><strong>Compatibilidad</strong></td><td style="padding: 10px; border: 1px solid #ddd;">{modelo or 'Consultar'}</td></tr>
    </table>
  </div>
  <div style="margin-bottom: 20px;">
    <h3 style="color: {primary}; border-bottom: 2px solid {accent}; padding-bottom: 8px;">Beneficios</h3>
    <ul style="list-style: none; padding: 0;">{benefits_html}</ul>
  </div>
</div>'''


def load_prices(store_dir):
    """Carga todos los precios de CSVs"""
    prices = {}

    for search_dir in [store_dir / 'precios', store_dir / 'catalogo']:
        if not search_dir.exists():
            continue
        for f in search_dir.iterdir():
            if f.suffix.lower() == '.csv':
                try:
                    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                        first_line = fp.readline()
                        fp.seek(0)
                        delimiter = ';' if ';' in first_line else ','
                        reader = csv.DictReader(fp, delimiter=delimiter)
                        for row in reader:
                            row = {k.strip().replace('\ufeff', ''): v for k, v in row.items()}
                            sku = row.get('CODIGO') or row.get('codigo') or row.get('SKU') or row.get('sku') or ''
                            price_raw = row.get('PRECIO') or row.get('precio') or row.get('price') or ''
                            if sku and price_raw:
                                sku_clean = sku.strip()
                                sku_norm = normalize_sku(sku_clean)
                                price = parse_price_cop(price_raw)
                                if price > 0:
                                    prices[sku_clean] = price
                                    prices[sku_norm] = price
                except Exception as e:
                    print(f'    Error precios {f.name}: {e}')
    return prices


def load_images(store_dir):
    """Carga imagenes locales por SKU"""
    images = {}
    img_dir = store_dir / 'imagenes'
    if img_dir.exists():
        for f in img_dir.iterdir():
            if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                key = f.stem.upper()
                images[key] = str(f)
                # También guardar sin extensión y variantes
                key_clean = re.sub(r'[^A-Z0-9]', '', key)
                images[key_clean] = str(f)
    return images


def find_image(sku, images, category='', system=''):
    """Busca imagen por SKU con fuzzy matching"""
    sku_upper = sku.upper()
    sku_clean = re.sub(r'[^A-Z0-9]', '', sku_upper)

    # Match exacto
    if sku_upper in images:
        return images[sku_upper]
    if sku_clean in images:
        return images[sku_clean]

    # Match parcial
    for key, path in images.items():
        if sku_upper in key or key in sku_upper:
            return path
        if len(sku_clean) > 4 and sku_clean in key:
            return path

    # Imagen genérica por sistema
    return GENERIC_IMAGES.get(system, GENERIC_IMAGES.get(category, GENERIC_IMAGES['default']))


def load_vision_products(store_name):
    """Carga productos de Vision AI (pending_upload)"""
    json_path = PENDING_DIR / store_name / 'products_ready.json'
    if not json_path.exists():
        return []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        products = []
        for p in data:
            sku = p.get('sku_odi') or p.get('sku') or p.get('codigo') or ''
            title = p.get('nombre') or p.get('title') or p.get('descripcion') or ''
            price = parse_price_cop(p.get('precio') or p.get('price') or 0)
            category = p.get('categoria') or p.get('category') or detect_pieza(title)

            if not title:
                continue

            products.append({
                'sku': sku,
                'title_raw': title,
                'price': price,
                'category': category,
                'system': detect_sistema(title),
                'compatible_models': detect_modelo(title),
                'image': '',
                'vendor': store_name
            })
        return products
    except Exception as e:
        print(f'    Error Vision {store_name}: {e}')
        return []


def load_csv_products(store_name, prices, images):
    """Carga productos de CSV"""
    store_dir = BASE_DIR / store_name
    products = []
    seen_skus = set()

    catalogo_dir = store_dir / 'catalogo'
    if not catalogo_dir.exists():
        return []

    for f in catalogo_dir.iterdir():
        fname_lower = f.name.lower()
        if f.suffix.lower() != '.csv':
            continue
        if not ('base_datos' in fname_lower or fname_lower.startswith(store_name.lower()) or store_name.lower() in fname_lower):
            continue
        if 'imagen' in fname_lower or 'catalogo_imagen' in fname_lower:
            continue

        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                first_line = fp.readline()
                fp.seek(0)
                delimiter = ';' if ';' in first_line else ','
                reader = csv.DictReader(fp, delimiter=delimiter)

                for i, row in enumerate(reader):
                    row = {k.strip().replace('\ufeff', ''): v for k, v in row.items()}

                    sku = (row.get('sku_odi') or row.get('CODIGO') or row.get('codigo') or
                           row.get('SKU') or row.get('sku') or row.get('Handle') or f'{store_name}-{i+1}')
                    title = (row.get('nombre') or row.get('DESCRIPCION') or row.get('descripcion') or
                             row.get('TITULO') or row.get('Title') or row.get('titulo') or '')
                    csv_price = row.get('PRECIO') or row.get('precio') or row.get('price') or ''
                    # Imagen: nombre de archivo o URL
                    img_file = row.get('Imagen_Externa') or row.get('imagen_externa') or ''
                    img_url = row.get('imagenes') or row.get('Imagen_URL_Origen') or row.get('URL_Origen') or row.get('Image Src') or ''
                    vision_cat = row.get('categoria') or ''

                    if not title:
                        continue

                    sku = str(sku).strip()
                    if not sku or sku in seen_skus:
                        continue
                    seen_skus.add(sku)

                    # Precio: CSV propio > archivo precios
                    price = parse_price_cop(csv_price)
                    if price == 0:
                        price = prices.get(sku, 0) or prices.get(normalize_sku(sku), 0)

                    # Categoría y sistema
                    category = vision_cat or detect_pieza(title)
                    system = detect_sistema(title)
                    models = detect_modelo(title)

                    # Imagen: 1) archivo referenciado, 2) match por SKU, 3) URL, 4) placeholder
                    img = ''
                    if img_file:
                        # Buscar por nombre de archivo referenciado
                        img_key = img_file.upper().replace('.JPG', '').replace('.PNG', '').replace('.JPEG', '')
                        img_key_clean = re.sub(r'[^A-Z0-9]', '', img_key)
                        if img_key in images:
                            img = images[img_key]
                        elif img_key_clean in images:
                            img = images[img_key_clean]
                    if not img:
                        img = find_image(sku, images, category, system)
                    if not img or 'placeholder' in img:
                        if img_url:
                            img = img_url
                    if not img:
                        img = GENERIC_IMAGES.get(system, GENERIC_IMAGES.get(category, GENERIC_IMAGES['default']))

                    products.append({
                        'sku': sku,
                        'title_raw': title,
                        'price': price,
                        'category': category,
                        'system': system,
                        'compatible_models': models,
                        'image': img,
                        'vendor': store_name
                    })
        except Exception as e:
            print(f'    Error CSV {f.name}: {e}')

    return products


def enrich_with_kb(products, collection):
    """Enriquece con ChromaDB en batch"""
    if not products:
        return 0

    enriched = 0
    batch_size = 100

    for i in range(0, len(products), batch_size):
        batch = products[i:i+batch_size]
        titles = [p['title_raw'] for p in batch]

        try:
            results = collection.query(query_texts=titles, n_results=1)

            for j, p in enumerate(batch):
                if results and results.get('metadatas') and len(results['metadatas']) > j:
                    metas = results['metadatas'][j]
                    dists = results['distances'][j] if results.get('distances') else [1.0]

                    if metas and dists[0] < 0.5:
                        kb = metas[0]
                        fields = []

                        if p['price'] == 0 and kb.get('price'):
                            try:
                                kb_price = float(kb['price'])
                                if kb_price > 0:
                                    p['price'] = kb_price
                                    p['price_source'] = f"KB_{kb.get('vendor', '')}"
                                    fields.append('price')
                            except:
                                pass

                        if not p.get('category') and kb.get('categoria'):
                            p['category'] = kb['categoria']
                            fields.append('category')

                        if not p.get('system') and kb.get('sistema_moto'):
                            p['system'] = kb['sistema_moto']
                            fields.append('system')

                        if fields:
                            p['kb_enriched'] = True
                            p['kb_fields'] = fields
                            enriched += 1
        except:
            pass

    return enriched


def save_to_kb(products, store_name, collection):
    """Guarda en ChromaDB"""
    docs, ids, metas = [], [], []
    seen = set()

    for p in products:
        doc_id = f"{store_name}_{p.get('sku', '')}"
        if doc_id in seen:
            continue
        seen.add(doc_id)

        doc = f"{p.get('title', '')} {p.get('category', '')} {p.get('system', '')} {p.get('compatible_models', '')}"
        meta = {
            'sku': str(p.get('sku', '')),
            'price': str(p.get('price', 0)),
            'vendor': store_name,
            'sistema_moto': p.get('system', ''),
            'categoria': p.get('category', ''),
            'modelos': p.get('compatible_models', ''),
            'titulo_normalizado': p.get('title', '')
        }
        docs.append(doc)
        ids.append(doc_id)
        metas.append(meta)

    batch_size = 100
    for i in range(0, len(docs), batch_size):
        try:
            collection.upsert(
                documents=docs[i:i+batch_size],
                ids=ids[i:i+batch_size],
                metadatas=metas[i:i+batch_size]
            )
        except Exception as e:
            print(f'    Error KB batch: {e}')

    return len(docs)


def process_store(store_name, collection):
    """Procesa una tienda completa"""
    import sys
    print(f'\n[{store_name}]')
    sys.stdout.flush()

    store_dir = BASE_DIR / store_name

    # Cargar precios e imágenes
    prices = load_prices(store_dir)
    images = load_images(store_dir)
    print(f'  Precios: {len(prices)}, Imagenes: {len(images)}')
    sys.stdout.flush()

    # Cargar productos
    if store_name in VISION_STORES:
        products = load_vision_products(store_name)
        print(f'  Fuente: Vision AI')
    else:
        products = load_csv_products(store_name, prices, images)
        print(f'  Fuente: CSV')

    print(f'  Productos: {len(products)}')
    sys.stdout.flush()

    if not products:
        return {'store': store_name, 'products': 0, 'price': 0, 'image': 0, 'enriched': 0}

    # Asignar imágenes a Vision products
    for p in products:
        if not p.get('image') or p['image'].startswith('http://via.'):
            p['image'] = find_image(p['sku'], images, p.get('category', ''), p.get('system', ''))

    # Enriquecer con KB
    enriched = enrich_with_kb(products, collection)
    print(f'  KB Enriched: {enriched}')
    sys.stdout.flush()

    # Finalizar productos
    for p in products:
        p['title'] = enrich_title(p['title_raw'], p.get('category', ''), p.get('system', ''), p.get('compatible_models', ''))
        p['handle'] = re.sub(r'[^a-z0-9-]', '-', p['sku'].lower())
        p['body_html'] = generate_body_html(p)

    # Guardar en KB
    saved = save_to_kb(products, store_name, collection)
    print(f'  Guardados KB: {saved}')
    sys.stdout.flush()

    # Guardar JSON
    output_dir = store_dir / 'output'
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / f'{store_name}_processed.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    # Stats
    with_price = sum(1 for p in products if p.get('price', 0) > 0)
    with_image = sum(1 for p in products if p.get('image') and not 'placeholder' in p['image'])

    pct_price = 100 * with_price // len(products) if products else 0
    pct_image = 100 * with_image // len(products) if products else 0

    print(f'  Precio: {with_price}/{len(products)} ({pct_price}%)')
    print(f'  Imagen Real: {with_image}/{len(products)} ({pct_image}%)')
    sys.stdout.flush()

    return {
        'store': store_name,
        'products': len(products),
        'price': with_price,
        'price_pct': pct_price,
        'image': with_image,
        'image_pct': pct_image,
        'enriched': enriched
    }


def main():
    import sys
    print('='*60)
    print('PIPELINE v2 - CORRECCIONES COMPLETAS')
    print('='*60)
    sys.stdout.flush()

    client = chromadb.HttpClient(host='localhost', port=8000)
    collection = client.get_or_create_collection('odi_ind_motos')

    results = []

    for store in STORES_ORDER:
        r = process_store(store, collection)
        results.append(r)

    # Resumen
    print('\n' + '='*60)
    print('RESUMEN FINAL')
    print('='*60)
    print(f'\n{"Tienda":<20} {"Productos":>10} {"Precio":>10} {"Imagen":>10} {"KB":>8}')
    print('-'*58)

    total_prod = total_price = total_img = total_kb = 0
    for r in results:
        pct_p = r.get('price_pct', 0)
        pct_i = r.get('image_pct', 0)
        print(f"{r['store']:<20} {r['products']:>10} {pct_p:>9}% {pct_i:>9}% {r.get('enriched',0):>8}")
        total_prod += r['products']
        total_price += r.get('price', 0)
        total_img += r.get('image', 0)
        total_kb += r.get('enriched', 0)

    print('-'*58)
    print(f"{'TOTAL':<20} {total_prod:>10} {total_price:>10} {total_img:>10} {total_kb:>8}")
    print(f'\nChromaDB: {collection.count()}')
    sys.stdout.flush()


if __name__ == '__main__':
    main()
