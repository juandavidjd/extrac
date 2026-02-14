#!/usr/bin/env python3
"""Procesar 15 tiendas - ORDEN MAESTRA con KB Learning"""
import json
import csv
import re
import random
from pathlib import Path
import chromadb

BASE_DIR = Path('/mnt/volume_sfo3_01/profesion/ecosistema_odi')

STORES_ORDER = [
    'DFG', 'BARA', 'IMBRA',
    'DUNA', 'YOKOMAR', 'JAPAN', 'OH_IMPORTACIONES',
    'ARMOTOS', 'MCLMOTOS', 'CBI', 'VITTON',
    'KAIQI', 'LEO', 'STORE', 'VAISAND'
]

PIEZAS = {
    'cadena': 'Cadena de Transmision', 'arbol': 'Arbol de Levas',
    'balancin': 'Balancin', 'biela': 'Biela', 'bomba': 'Bomba de Aceite',
    'bujia': 'Bujia', 'cable': 'Cable', 'carburador': 'Carburador',
    'cilindro': 'Cilindro', 'clutch': 'Clutch', 'embolo': 'Piston',
    'empaque': 'Empaque', 'filtro': 'Filtro', 'llanta': 'Llanta',
    'manigueta': 'Manigueta', 'piston': 'Piston', 'retrovisor': 'Retrovisor',
    'rodamiento': 'Rodamiento', 'switch': 'Switch', 'tensor': 'Tensor',
    'valvula': 'Valvula', 'amortiguador': 'Amortiguador', 'freno': 'Freno',
    'disco': 'Disco de Freno', 'pastilla': 'Pastillas de Freno',
    'faro': 'Faro', 'direccional': 'Direccional', 'espejo': 'Espejo',
    'manubrio': 'Manubrio', 'pedal': 'Pedal', 'palanca': 'Palanca'
}

SISTEMAS = {
    'motor': 'Motor', 'transmision': 'Transmision', 'freno': 'Frenos',
    'suspension': 'Suspension', 'electrico': 'Sistema Electrico',
    'carroceria': 'Carroceria', 'escape': 'Escape', 'direccion': 'Direccion'
}

GENERIC_IMAGES = {
    'Motor': 'https://via.placeholder.com/400x400/1a1a2e/ffffff?text=Motor',
    'Transmision': 'https://via.placeholder.com/400x400/16213e/ffffff?text=Transmision',
    'Frenos': 'https://via.placeholder.com/400x400/0f3460/ffffff?text=Frenos',
    'Suspension': 'https://via.placeholder.com/400x400/533483/ffffff?text=Suspension',
    'Sistema Electrico': 'https://via.placeholder.com/400x400/e94560/ffffff?text=Electrico',
    'default': 'https://via.placeholder.com/400x400/1a1a2e/ffffff?text=Repuesto+Moto'
}

BENEFITS = [
    'Fabricado con materiales de alta resistencia',
    'Diseñado para máximo rendimiento',
    'Compatibilidad garantizada con modelos originales',
    'Durabilidad superior en condiciones extremas',
    'Instalación sencilla y rápida',
    'Mejora el desempeño de tu moto',
    'Producto con garantía de calidad',
    'Especificaciones OEM para ajuste perfecto'
]

def normalize_sku(sku):
    if not sku:
        return ''
    sku = sku.replace('/', '-')
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
        r'(AKT|BAJAJ|HERO|HONDA|YAMAHA|SUZUKI|TVS|PULSAR|DISCOVER|BWS|FZ|XTZ|NKD|TITAN|CG|CB|CBF|XL|XR|KYMCO|AGILITY|CRYPTON|RX|DT|BOXER|PLATINO)\s*(\d{2,3})?',
        r'(\d{2,3})\s*(CC|cc)',
    ]
    for pat in patterns:
        m = re.search(pat, title, re.IGNORECASE)
        if m:
            return m.group(0).strip().upper()
    return ''

def enrich_title(raw_title, kb_data=None):
    """Genera titulo enriquecido y profesional"""
    pieza = detect_pieza(raw_title)
    modelo = detect_modelo(raw_title)
    sistema = detect_sistema(raw_title)

    # Si KB tiene datos adicionales, usarlos
    if kb_data:
        if not modelo and kb_data.get('modelos'):
            modelo = kb_data['modelos']
        if not sistema and kb_data.get('sistema_moto'):
            sistema = kb_data['sistema_moto']
        if not pieza and kb_data.get('categoria'):
            pieza = kb_data['categoria']

    # Construir titulo rico
    if pieza and modelo:
        suffix = f"- Repuesto {sistema}" if sistema else "- Repuesto Moto Original"
        return f"{pieza} {modelo} {suffix}"
    elif pieza:
        suffix = f"- Repuesto {sistema}" if sistema else "- Repuesto Moto"
        return f"{pieza} {suffix}"
    else:
        # Limpiar y capitalizar
        clean = re.sub(r'[_\-]+', ' ', raw_title)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean.title()

def generate_body_html(product, brand_colors=None):
    """Genera ficha HTML profesional con variacion"""
    pieza = product.get('category', 'Repuesto')
    sistema = product.get('system', 'Moto')
    modelo = product.get('compatible_models', '')
    title = product.get('title', '')

    # Colores por defecto (industrial)
    primary = brand_colors.get('primary', '#1a1a2e') if brand_colors else '#1a1a2e'
    secondary = brand_colors.get('secondary', '#16213e') if brand_colors else '#16213e'
    accent = brand_colors.get('accent', '#e94560') if brand_colors else '#e94560'

    # Seleccionar beneficios aleatorios para variacion
    selected_benefits = random.sample(BENEFITS, min(4, len(BENEFITS)))
    benefits_html = ''.join([f'<li>{b}</li>' for b in selected_benefits])

    # Variaciones de descripcion
    descriptions = [
        f"Repuesto de alta calidad para tu moto. {pieza or 'Este componente'} diseñado para ofrecer rendimiento óptimo y durabilidad excepcional.",
        f"{pieza or 'Componente'} fabricado con estándares de calidad superiores. Ideal para mantener tu moto en perfectas condiciones.",
        f"Mantén tu moto funcionando al máximo con este {pieza.lower() if pieza else 'repuesto'} de calidad premium. Diseño que garantiza compatibilidad perfecta.",
        f"Repuesto original compatible. {pieza or 'Este producto'} ofrece el ajuste perfecto y rendimiento que tu moto necesita."
    ]
    description = random.choice(descriptions)

    html = f'''<div style="font-family: Arial, sans-serif; color: #333;">
  <div style="background: linear-gradient(135deg, {primary}, {secondary}); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
    <h2 style="margin: 0;">{title}</h2>
    <p style="margin: 10px 0 0 0; opacity: 0.9;">SKU: {product.get('sku', 'N/A')}</p>
  </div>

  <div style="margin-bottom: 20px;">
    <h3 style="color: {primary}; border-bottom: 2px solid {accent}; padding-bottom: 8px;">Descripcion</h3>
    <p>{description}</p>
  </div>

  <div style="margin-bottom: 20px;">
    <h3 style="color: {primary}; border-bottom: 2px solid {accent}; padding-bottom: 8px;">Especificaciones</h3>
    <table style="width: 100%; border-collapse: collapse;">
      <tr style="background: #f5f5f5;"><td style="padding: 10px; border: 1px solid #ddd;"><strong>Tipo</strong></td><td style="padding: 10px; border: 1px solid #ddd;">{pieza or 'Repuesto'}</td></tr>
      <tr><td style="padding: 10px; border: 1px solid #ddd;"><strong>Sistema</strong></td><td style="padding: 10px; border: 1px solid #ddd;">{sistema or 'General'}</td></tr>
      <tr style="background: #f5f5f5;"><td style="padding: 10px; border: 1px solid #ddd;"><strong>Compatibilidad</strong></td><td style="padding: 10px; border: 1px solid #ddd;">{modelo or 'Universal / Consultar'}</td></tr>
      <tr><td style="padding: 10px; border: 1px solid #ddd;"><strong>Marca</strong></td><td style="padding: 10px; border: 1px solid #ddd;">{product.get('vendor', 'N/A')}</td></tr>
    </table>
  </div>

  <div style="margin-bottom: 20px;">
    <h3 style="color: {primary}; border-bottom: 2px solid {accent}; padding-bottom: 8px;">Beneficios</h3>
    <ul style="list-style: none; padding: 0;">
      {benefits_html}
    </ul>
  </div>

  <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid {accent};">
    <p style="margin: 0;"><strong>Garantia de Calidad:</strong> Todos nuestros productos cuentan con garantia. Envios a todo el pais.</p>
  </div>
</div>'''
    return html

def load_brand_colors(store_name):
    """Carga colores de brand.json si existe"""
    brand_file = BASE_DIR / store_name / 'perfil' / 'brand.json'
    if brand_file.exists():
        try:
            with open(brand_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {'primary': '#1a1a2e', 'secondary': '#16213e', 'accent': '#e94560'}

def load_store_data(store_name):
    """Carga datos SIN consulta KB (KB se consulta en batch despues)"""
    store_dir = BASE_DIR / store_name
    if not store_dir.exists():
        return []

    products = []
    prices = {}
    images = {}
    seen_skus = set()  # Para evitar duplicados

    # Cargar precios
    for search_dir in [store_dir / 'precios', store_dir / 'catalogo']:
        if search_dir.exists():
            for f in search_dir.iterdir():
                if f.suffix == '.csv':
                    try:
                        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                            first_line = fp.readline()
                            fp.seek(0)
                            delimiter = ';' if ';' in first_line else ','
                            reader = csv.DictReader(fp, delimiter=delimiter)
                            for row in reader:
                                row = {k.strip(): v for k, v in row.items()}
                                sku = row.get('CODIGO') or row.get('codigo') or row.get('SKU') or row.get('sku') or row.get('Handle') or ''
                                price_raw = row.get('PRECIO') or row.get('precio') or row.get('PRICE') or row.get('Variant Price') or '0'
                                if sku:
                                    sku_clean = sku.strip()
                                    sku_norm = normalize_sku(sku_clean)
                                    price_str = str(price_raw).strip()
                                    if re.match(r'^\d{1,3}\.\d{3}$', price_str):
                                        price_str = price_str.replace('.', '')
                                    try:
                                        price_val = float(re.sub(r'[^\d.]', '', price_str))
                                        prices[sku_clean] = price_val
                                        prices[sku_norm] = price_val
                                    except:
                                        pass
                    except:
                        pass

    # Cargar imagenes locales
    img_dir = store_dir / 'imagenes'
    if img_dir.exists():
        for f in img_dir.iterdir():
            if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                key = f.stem.upper()
                images[key] = str(f)

    # Cargar colores de marca
    brand_colors = load_brand_colors(store_name)

    # Cargar catalogo
    catalogo_dir = store_dir / 'catalogo'
    if catalogo_dir.exists():
        for f in catalogo_dir.iterdir():
            if f.suffix == '.csv' and ('base_datos' in f.name.lower() or f.name.lower().startswith(store_name.lower()) or '_vision' in f.name.lower()):
                try:
                    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                        first_line = fp.readline()
                        fp.seek(0)
                        delimiter = ';' if ';' in first_line else ','
                        reader = csv.DictReader(fp, delimiter=delimiter)

                        for i, row in enumerate(reader):
                            # Limpiar keys (BOM, espacios)
                            row = {k.strip().replace('\ufeff', ''): v for k, v in row.items()}
                            sku = row.get('sku_odi') or row.get('CODIGO') or row.get('codigo') or row.get('SKU') or row.get('sku') or row.get('Handle') or row.get('handle') or f'{store_name}-{i+1}'
                            title_raw = row.get('nombre') or row.get('DESCRIPCION') or row.get('descripcion') or row.get('Title') or row.get('TITULO') or row.get('titulo') or row.get('title') or ''
                            csv_price = row.get('PRECIO') or row.get('precio') or row.get('price') or row.get('Variant Price') or '0'
                            img_url = row.get('URL_Origen') or row.get('Image Src') or row.get('imagenes') or row.get('Imagen_URL_Origen') or ''
                            # Vision CSV puede tener categoria directa
                            vision_category = row.get('categoria') or ''

                            if not title_raw:
                                continue

                            sku = str(sku).strip()
                            if not sku or sku in seen_skus:
                                continue
                            seen_skus.add(sku)
                            sku_norm = normalize_sku(sku)

                            # PRECIO: propio > csv > (KB se aplica despues)
                            price = prices.get(sku, 0) or prices.get(sku_norm, 0)
                            price_source = 'propio' if price > 0 else None

                            if price == 0 and csv_price:
                                price_str = str(csv_price).strip()
                                if re.match(r'^\d{1,3}\.\d{3}$', price_str):
                                    price_str = price_str.replace('.', '')
                                try:
                                    price = float(re.sub(r'[^\d.]', '', price_str))
                                    price_source = 'csv'
                                except:
                                    pass

                            # Detectar metadatos (usar Vision si disponible)
                            category = vision_category if vision_category else detect_pieza(title_raw)
                            system = detect_sistema(title_raw)
                            models = detect_modelo(title_raw)

                            # IMAGEN: local > URL > generica
                            img = images.get(sku.upper(), '') or img_url
                            if not img:
                                for k, v in images.items():
                                    if sku.upper() in k or k in sku.upper():
                                        img = v
                                        break
                            if not img:
                                img = GENERIC_IMAGES.get(system, GENERIC_IMAGES.get(category, GENERIC_IMAGES['default']))

                            products.append({
                                'sku': sku,
                                'handle': re.sub(r'[^a-z0-9-]', '-', sku.lower()),
                                'title_raw': title_raw,
                                'price': price,
                                'price_source': price_source,
                                'image': img,
                                'system': system,
                                'category': category,
                                'compatible_models': models,
                                'vendor': store_name,
                                'brand_colors': brand_colors,
                                'kb_enriched': False,
                                'kb_fields': []
                            })

                except Exception as e:
                    print(f'  Error {f.name}: {e}')

    return products


def enrich_with_kb_batch(products, collection):
    """Enriquece productos con KB en batches eficientes"""
    if not products:
        return 0

    enriched_count = 0
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
                        kb_data = metas[0]
                        kb_fields = []

                        # Precio de KB si no tiene
                        if p['price'] == 0 and kb_data.get('price'):
                            try:
                                kb_price = float(kb_data['price'])
                                if kb_price > 0:
                                    p['price'] = kb_price
                                    p['price_source'] = f"KB_{kb_data.get('vendor', 'ref')}"
                                    kb_fields.append('price')
                            except:
                                pass

                        # Categoria
                        if not p.get('category') and kb_data.get('categoria'):
                            p['category'] = kb_data['categoria']
                            kb_fields.append('category')

                        # Sistema
                        if not p.get('system') and kb_data.get('sistema_moto'):
                            p['system'] = kb_data['sistema_moto']
                            kb_fields.append('system')

                        # Modelos
                        if not p.get('compatible_models') and kb_data.get('modelos'):
                            p['compatible_models'] = kb_data['modelos']
                            kb_fields.append('models')

                        if kb_fields:
                            p['kb_enriched'] = True
                            p['kb_fields'] = kb_fields
                            p['kb_source'] = kb_data.get('vendor', 'unknown')
                            enriched_count += 1
        except Exception as e:
            pass

    return enriched_count


def finalize_products(products):
    """Genera titulos enriquecidos y body_html"""
    for p in products:
        # Titulo enriquecido
        kb_data = {'categoria': p.get('category'), 'sistema_moto': p.get('system'), 'modelos': p.get('compatible_models')} if p.get('kb_enriched') else None
        p['title'] = enrich_title(p['title_raw'], kb_data)

        # Body HTML
        p['body_html'] = generate_body_html(p, p.get('brand_colors'))

        # Limpiar campos temporales
        if 'brand_colors' in p:
            del p['brand_colors']

def save_to_kb(products, store_name, collection):
    """Guarda productos procesados en KB (sin duplicados)"""
    docs, ids, metas = [], [], []
    seen_ids = set()

    for p in products:
        doc_id = f"{store_name}_{p.get('sku', '')}"
        # Evitar duplicados
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)

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
            print(f'  Error KB batch {i}: {e}')

    return len(docs)

def main():
    print('='*70)
    print('ORDEN MAESTRA: PROCESANDO 15 TIENDAS')
    print('='*70)
    import sys
    sys.stdout.flush()

    client = chromadb.HttpClient(host='localhost', port=8000)
    collection = client.get_or_create_collection('odi_ind_motos')

    results = []

    for i, store in enumerate(STORES_ORDER, 1):
        print(f'\n[{i}/15] {store}')
        print('-' * 40)
        sys.stdout.flush()

        # 1. Cargar datos (sin KB)
        products = load_store_data(store)

        if not products:
            print(f'  Sin productos')
            results.append({'store': store, 'products': 0, 'price': 0, 'image': 0, 'enriched': 0, 'saved': 0})
            sys.stdout.flush()
            continue

        print(f'  Cargados: {len(products)}')
        sys.stdout.flush()

        # 2. Enriquecer con KB en batch
        enriched = enrich_with_kb_batch(products, collection)
        print(f'  Enriquecidos KB: {enriched}')
        sys.stdout.flush()

        # 3. Finalizar (titulos y body_html)
        finalize_products(products)

        # 4. Guardar en KB
        saved = save_to_kb(products, store, collection)
        print(f'  Guardados KB: {saved}')
        sys.stdout.flush()

        # 5. Guardar JSON
        output_dir = BASE_DIR / store / 'output'
        output_dir.mkdir(exist_ok=True)
        with open(output_dir / f'{store}_processed.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        # Stats
        with_price = sum(1 for p in products if p.get('price', 0) > 0)
        with_image = sum(1 for p in products if p.get('image'))
        pct_price = 100 * with_price // len(products) if products else 0
        pct_image = 100 * with_image // len(products) if products else 0
        pct_enrich = 100 * enriched // len(products) if products else 0

        print(f'  Con precio: {with_price} ({pct_price}%)')
        print(f'  Con imagen: {with_image} ({pct_image}%)')
        sys.stdout.flush()

        results.append({
            'store': store, 'products': len(products),
            'price': with_price, 'price_pct': pct_price,
            'image': with_image, 'image_pct': pct_image,
            'enriched': enriched, 'enriched_pct': pct_enrich,
            'saved': saved
        })

    # Resumen
    print('\n' + '='*70)
    print('RESUMEN FINAL - 15 TIENDAS')
    print('='*70)
    print(f'\n{"Tienda":<20} {"Productos":>10} {"Precio":>10} {"Imagen":>10} {"KB Enrich":>12} {"Guardados":>10}')
    print('-'*72)

    total_prod = total_price = total_img = total_enrich = total_saved = 0
    for r in results:
        print(f"{r['store']:<20} {r['products']:>10} {r.get('price_pct',0):>9}% {r.get('image_pct',0):>9}% {r.get('enriched_pct',0):>11}% {r['saved']:>10}")
        total_prod += r['products']
        total_price += r.get('price', 0)
        total_img += r.get('image', 0)
        total_enrich += r.get('enriched', 0)
        total_saved += r.get('saved', 0)

    print('-'*72)
    print(f"{'TOTAL':<20} {total_prod:>10} {total_price:>10} {total_img:>10} {total_enrich:>12} {total_saved:>10}")
    print(f'\nProductos en ChromaDB: {collection.count()}')

if __name__ == '__main__':
    main()
