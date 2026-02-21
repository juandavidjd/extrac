#!/usr/bin/env python3
"""
ODI V19 Shopify Sync Module
Generates V19 fichas for draft products and uploads to Shopify.
Integrated in /opt/odi/core/ - NO loose scripts.
"""
import json
import logging
import os
import re
import time
import psycopg2
from typing import Dict, List, Optional, Any
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DB_CONFIG = {
    'host': '172.18.0.8',
    'port': 5432,
    'database': 'odi',
    'user': 'odi_user',
    'password': 'odi_secure_password'
}

BRANDS_DIR = '/opt/odi/data/brands'


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_shopify_config(store: str) -> Optional[Dict]:
    """Get Shopify configuration for a store."""
    config_names = [
        f'{store.lower()}.json',
        f'{store.lower().replace("_", "")}.json',
        'oh_importaciones.json' if store == 'OH_IMPORTACIONES' else None
    ]

    for name in config_names:
        if name:
            path = os.path.join(BRANDS_DIR, name)
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
    return None


def normalize_title(title: str) -> str:
    """Normalize title: proper Title Case for ALL CAPS titles."""
    if not title:
        return title

    upper_count = sum(1 for c in title if c.isupper())
    total_alpha = sum(1 for c in title if c.isalpha())

    if total_alpha > 0 and upper_count / total_alpha > 0.7:
        lowercase_words = {'de', 'del', 'la', 'el', 'los', 'las', 'para', 'con', 'sin', 'en', 'y', 'o', 'a', 'al', 'por'}
        words = title.lower().split()
        result = []

        for i, word in enumerate(words):
            if i == 0:
                result.append(word.capitalize())
            elif word in lowercase_words:
                result.append(word.lower())
            else:
                result.append(word.capitalize())

        return ' '.join(result)

    return title


def extract_compatibility(title: str) -> str:
    """Extract motorcycle compatibility from title."""
    title_lower = title.lower()
    matches = []

    brands = {
        'pulsar': 'Pulsar', 'discover': 'Discover', 'boxer': 'Boxer',
        'platino': 'Platino', 'fz': 'FZ', 'ybr': 'YBR', 'xtz': 'XTZ',
        'libero': 'Libero', 'crypton': 'Crypton', 'apache': 'Apache',
        'gixxer': 'Gixxer', 'cb': 'CB', 'cbf': 'CBF', 'nxr': 'NXR',
        'cg': 'CG', 'titan': 'Titan', 'bws': 'BWS', 'nmax': 'NMax',
        'akt': 'AKT', 'tvs': 'TVS', 'bajaj': 'Bajaj', 'yamaha': 'Yamaha',
        'honda': 'Honda', 'suzuki': 'Suzuki', 'kawasaki': 'Kawasaki',
    }

    for key, val in brands.items():
        if key in title_lower:
            cc_match = re.search(rf'{key}\s*(\d{{2,3}})', title_lower)
            if cc_match:
                matches.append(f'{val} {cc_match.group(1)}')
            else:
                matches.append(val)

    # Standalone cilindrada
    cc_patterns = re.findall(r'(\d{3})\s*(cc|ns|rs)?', title_lower)
    for cc, suffix in cc_patterns:
        if cc in ['100', '110', '125', '135', '150', '160', '180', '200', '220', '250', '300', '350', '400']:
            if suffix:
                matches.append(f'{cc}{suffix.upper()}')

    if matches:
        return ', '.join(list(dict.fromkeys(matches))[:4])

    return 'Motos compatibles'


def extract_product_type(title: str) -> str:
    """Extract product type from title."""
    title_lower = title.lower()

    type_keywords = {
        'filtro aceite': 'oil filter', 'filtro aire': 'air filter', 'filtro': 'filter',
        'bujia': 'spark plug', 'bujías': 'spark plug',
        'pastilla': 'brake pad', 'pastillas': 'brake pads',
        'disco': 'brake disc', 'freno': 'brake',
        'cadena': 'motorcycle chain', 'piñon': 'sprocket', 'corona': 'rear sprocket',
        'empaque': 'gasket', 'kit empaque': 'gasket kit',
        'reten': 'oil seal', 'retenedor': 'oil seal',
        'rodamiento': 'bearing', 'balinera': 'bearing',
        'piston': 'piston', 'anillo': 'piston ring',
        'valvula': 'valve', 'arbol de levas': 'camshaft', 'cigueñal': 'crankshaft',
        'biela': 'connecting rod', 'cilindro': 'cylinder', 'culata': 'cylinder head',
        'embrague': 'clutch', 'clutch': 'clutch',
        'amortiguador': 'shock absorber', 'suspension': 'shock absorber',
        'bobina': 'ignition coil', 'cdi': 'CDI unit', 'regulador': 'voltage regulator',
        'faro': 'headlight', 'stop': 'tail light', 'direccional': 'turn signal',
        'bombillo': 'light bulb', 'led': 'LED bulb',
        'guaya': 'control cable', 'cable': 'control cable',
        'espejo': 'mirror', 'manigueta': 'handlebar lever', 'palanca': 'lever',
        'estribo': 'footpeg', 'pata': 'side stand',
        'tanque': 'fuel tank', 'sillin': 'seat', 'guardabarro': 'fender',
        'aceite': 'oil', 'lubricante': 'oil',
    }

    for keyword, ptype in type_keywords.items():
        if keyword in title_lower:
            return ptype

    return 'motorcycle part'


def get_category_template(product_type: str) -> Dict[str, str]:
    """Get material and spec template for product type."""
    templates = {
        'oil filter': {'material': 'Papel filtro de alta eficiencia', 'spec': 'Filtro con válvula anti-retorno'},
        'air filter': {'material': 'Espuma/papel filtro multicapa', 'spec': 'Filtro de alto flujo'},
        'spark plug': {'material': 'Electrodo de níquel/iridio', 'spec': 'Bujía resistente a altas temperaturas'},
        'brake pad': {'material': 'Compuesto semimetálico', 'spec': 'Pastillas con alto coeficiente de fricción'},
        'brake pads': {'material': 'Compuesto semimetálico', 'spec': 'Pastillas con alto coeficiente de fricción'},
        'brake disc': {'material': 'Acero inoxidable', 'spec': 'Disco de freno ventilado'},
        'brake': {'material': 'Compuesto semimetálico', 'spec': 'Sistema de frenado de alta eficiencia'},
        'motorcycle chain': {'material': 'Acero aleado con tratamiento térmico', 'spec': 'Cadena con O-rings sellados'},
        'sprocket': {'material': 'Acero templado', 'spec': 'Dientes de perfil optimizado'},
        'rear sprocket': {'material': 'Acero templado', 'spec': 'Corona con dientes de perfil optimizado'},
        'gasket': {'material': 'Material compuesto multicapa', 'spec': 'Empaque de alta resistencia térmica'},
        'gasket kit': {'material': 'Materiales compuestos', 'spec': 'Kit completo de empaques'},
        'oil seal': {'material': 'Caucho nitrílico', 'spec': 'Retenedor con labio de sello'},
        'bearing': {'material': 'Acero al cromo', 'spec': 'Rodamiento sellado de alta precisión'},
        'piston': {'material': 'Aluminio forjado', 'spec': 'Pistón con recubrimiento antifricción'},
        'piston ring': {'material': 'Acero de alta resistencia', 'spec': 'Anillo con acabado cromado'},
        'valve': {'material': 'Acero inoxidable', 'spec': 'Válvula con asiento rectificado'},
        'camshaft': {'material': 'Acero templado', 'spec': 'Árbol de levas con perfil optimizado'},
        'crankshaft': {'material': 'Acero forjado', 'spec': 'Cigüeñal balanceado'},
        'connecting rod': {'material': 'Acero forjado', 'spec': 'Biela de alta resistencia'},
        'cylinder': {'material': 'Aluminio con camisa de hierro', 'spec': 'Cilindro con acabado de precisión'},
        'cylinder head': {'material': 'Aluminio fundido', 'spec': 'Culata con canales de refrigeración'},
        'clutch': {'material': 'Fibra de fricción reforzada', 'spec': 'Discos con ranuras de ventilación'},
        'shock absorber': {'material': 'Acero con recubrimiento anticorrosivo', 'spec': 'Amortiguador con ajuste de precarga'},
        'ignition coil': {'material': 'Bobinado de cobre', 'spec': 'Bobina de encendido de alto voltaje'},
        'CDI unit': {'material': 'Circuito electrónico encapsulado', 'spec': 'CDI con curva de encendido optimizada'},
        'voltage regulator': {'material': 'Componentes electrónicos', 'spec': 'Regulador rectificador de voltaje'},
        'headlight': {'material': 'Plástico y vidrio', 'spec': 'Faro con reflector parabólico'},
        'tail light': {'material': 'Plástico y LEDs', 'spec': 'Stop con iluminación LED'},
        'turn signal': {'material': 'Plástico y bombillo', 'spec': 'Direccional con luz ámbar'},
        'light bulb': {'material': 'Vidrio resistente a vibraciones', 'spec': 'Bombillo de alta luminosidad'},
        'LED bulb': {'material': 'LEDs de alta eficiencia', 'spec': 'Bombillo LED de bajo consumo'},
        'control cable': {'material': 'Cable de acero trenzado con funda', 'spec': 'Guaya con terminales de fábrica'},
        'mirror': {'material': 'Plástico y vidrio', 'spec': 'Espejo con amplio campo de visión'},
        'handlebar lever': {'material': 'Aluminio fundido', 'spec': 'Manigueta con ajuste de distancia'},
        'lever': {'material': 'Aluminio fundido', 'spec': 'Palanca con ajuste de distancia'},
        'footpeg': {'material': 'Aluminio o acero', 'spec': 'Estribo antideslizante'},
        'side stand': {'material': 'Acero', 'spec': 'Pata lateral con resorte'},
        'fuel tank': {'material': 'Metal con recubrimiento interno', 'spec': 'Tanque con protección anticorrosión'},
        'seat': {'material': 'Espuma y vinilo', 'spec': 'Sillín ergonómico con base reforzada'},
        'fender': {'material': 'Plástico ABS', 'spec': 'Guardabarro resistente a impactos'},
    }

    return templates.get(product_type, {'material': 'Materiales de alta calidad', 'spec': 'Repuesto con especificaciones OEM'})


def build_ficha_360(title: str, sku: str, compatibility: str, empresa: str, template: Dict) -> str:
    """Build V19 ficha 360 HTML."""
    material = template.get('material', 'Materiales de alta calidad')
    spec = template.get('spec', 'Repuesto con especificaciones OEM')

    html = f'''<div class="ficha-360">
<h3>🔧 {title}</h3>

<div class="compatibilidad">
<strong>✅ Compatible con:</strong> {compatibility}
</div>

<div class="caracteristicas">
<h4>📋 Características</h4>
<ul>
<li><strong>Material:</strong> {material}</li>
<li><strong>Especificaciones:</strong> {spec}</li>
<li><strong>Código:</strong> {sku}</li>
</ul>
</div>

<div class="beneficios">
<h4>⭐ Beneficios</h4>
<ul>
<li>✓ Ajuste perfecto garantizado</li>
<li>✓ Durabilidad superior</li>
<li>✓ Rendimiento óptimo</li>
</ul>
</div>

<div class="garantia">
<strong>🛡️ Garantía:</strong> Respaldado por {empresa}
</div>
</div>'''

    return html


def build_shopify_sku_map(config: Dict) -> Dict[str, int]:
    """Build map of SKU -> Shopify product ID for a store."""
    shop = config['shopify']['shop']
    token = config['shopify']['token']

    sku_map = {}
    url = f'https://{shop}/admin/api/2024-01/products.json?limit=250&fields=id,variants'
    headers = {'X-Shopify-Access-Token': token}

    while url:
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            time.sleep(0.3)

            for p in r.json().get('products', []):
                for v in p.get('variants', []):
                    sku = v.get('sku', '')
                    if sku:
                        sku_map[sku.upper()] = p['id']

            link = r.headers.get('Link', '')
            url = None
            if 'rel="next"' in link:
                for part in link.split(','):
                    if 'rel="next"' in part:
                        url = part.split('<')[1].split('>')[0]
                        break
        except Exception as e:
            logger.error(f"Error building SKU map: {e}")
            break

    return sku_map


def update_shopify_product(config: Dict, shopify_id: int, product: Dict) -> bool:
    """Update an existing product in Shopify."""
    shop = config['shopify']['shop']
    token = config['shopify']['token']

    url = f'https://{shop}/admin/api/2024-01/products/{shopify_id}.json'
    headers = {
        'X-Shopify-Access-Token': token,
        'Content-Type': 'application/json'
    }

    product_data = {
        'product': {
            'id': shopify_id,
            'body_html': product['body_html'],
        }
    }

    # Update price if provided and > 0
    if product.get('price') and float(product.get('price', 0)) > 0:
        product_data['product']['variants'] = [{
            'price': str(product['price'])
        }]

    try:
        response = requests.put(url, headers=headers, json=product_data, timeout=30)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Shopify update error: {e}")
        return False


def create_shopify_product(config: Dict, product: Dict) -> Optional[int]:
    """Create a product in Shopify and return the product ID."""
    shop = config['shopify']['shop']
    token = config['shopify']['token']

    # Validate required fields
    if not product.get('title') or len(product['title'].strip()) < 3:
        logger.warning(f"Skipping product with invalid title: {product.get('sku')}")
        return None

    price = float(product.get('price', 0))
    if price <= 0:
        price = 1  # Minimum price to avoid Shopify errors

    url = f'https://{shop}/admin/api/2024-01/products.json'
    headers = {
        'X-Shopify-Access-Token': token,
        'Content-Type': 'application/json'
    }

    product_data = {
        'product': {
            'title': product['title'][:255],  # Max length
            'body_html': product['body_html'],
            'vendor': product.get('vendor', ''),
            'product_type': product.get('product_type', ''),
            'status': 'active',
            'variants': [{
                'sku': product['sku'],
                'price': str(price),
                'inventory_management': 'shopify',
                'inventory_quantity': product.get('inventory_quantity', product.get('stock', 10))  # V22 fix: use source qty or default 10
            }]
        }
    }

    # Add image if available and valid URL
    if product.get('image_url') and product['image_url'].startswith('http'):
        product_data['product']['images'] = [{'src': product['image_url']}]

    try:
        response = requests.post(url, headers=headers, json=product_data, timeout=30)
        response.raise_for_status()

        result = response.json()
        return result['product']['id']

    except Exception as e:
        logger.error(f"Shopify create error for {product.get('sku')}: {e}")
        return None


def process_draft_products(store: str, limit: int = 100, dry_run: bool = False) -> Dict[str, Any]:
    """Process draft products for a store: generate fichas and sync to Shopify."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Get Shopify config
    config = get_shopify_config(store)
    if not config:
        cur.close()
        conn.close()
        return {'error': f'Shopify config not found for {store}'}

    # Build SKU map from Shopify to prevent duplicates
    logger.info(f'{store}: Building Shopify SKU map...')
    shopify_sku_map = build_shopify_sku_map(config)
    logger.info(f'{store}: Found {len(shopify_sku_map)} existing products in Shopify')

    # Get draft products (without shopify_product_id)
    cur.execute("""
        SELECT p.id, p.codigo_proveedor, p.titulo_raw, p.precio_sin_iva,
               e.codigo as empresa, pi.url_origen as image_url
        FROM productos p
        JOIN empresas e ON p.empresa_id = e.id
        LEFT JOIN producto_imagenes pi ON pi.producto_id = p.id AND pi.es_principal = true
        WHERE e.codigo = %s AND p.shopify_product_id IS NULL
        LIMIT %s
    """, (store.upper(), limit))

    products = cur.fetchall()
    logger.info(f'{store}: Found {len(products)} products without Shopify ID')

    if dry_run:
        # Count how many would be created vs updated
        to_create = sum(1 for p in products if p[1].upper() not in shopify_sku_map)
        to_update = sum(1 for p in products if p[1].upper() in shopify_sku_map)

        cur.close()
        conn.close()
        return {
            'store': store,
            'products_found': len(products),
            'to_create': to_create,
            'to_update': to_update,
            'existing_in_shopify': len(shopify_sku_map),
            'dry_run': True,
            'sample': [{'sku': p[1], 'title': p[2][:50]} for p in products[:5]]
        }

    created = 0
    updated = 0
    errors = 0

    for prod in products:
        prod_id, sku, titulo_raw, precio, empresa, image_url = prod

        try:
            # Normalize title
            title = normalize_title(titulo_raw)

            # Extract info
            compatibility = extract_compatibility(titulo_raw)
            product_type = extract_product_type(titulo_raw)
            template = get_category_template(product_type)

            # Build ficha
            body_html = build_ficha_360(title, sku, compatibility, empresa, template)

            shopify_data = {
                'title': title,
                'body_html': body_html,
                'sku': sku,
                'price': float(precio) if precio else 0,
                'vendor': empresa,
                'product_type': product_type,
                'image_url': image_url
            }

            # Check if SKU exists in Shopify
            existing_shopify_id = shopify_sku_map.get(sku.upper())

            if existing_shopify_id:
                # UPDATE existing product
                if update_shopify_product(config, existing_shopify_id, shopify_data):
                    cur.execute("""
                        UPDATE productos
                        SET shopify_product_id = %s,
                            titulo_normalizado = %s,
                            status = 'active',
                            shopify_synced_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (existing_shopify_id, title, prod_id))

                    cur.execute("""
                        INSERT INTO fichas_360 (producto_id, body_html, enrichment_source)
                        VALUES (%s, %s, 'category_template')
                        ON CONFLICT (producto_id) DO UPDATE SET body_html = EXCLUDED.body_html
                    """, (prod_id, body_html))

                    updated += 1
                    logger.info(f'{store}: Updated {sku} (Shopify ID {existing_shopify_id})')
                else:
                    errors += 1
            else:
                # CREATE new product
                new_shopify_id = create_shopify_product(config, shopify_data)

                if new_shopify_id:
                    cur.execute("""
                        UPDATE productos
                        SET shopify_product_id = %s,
                            titulo_normalizado = %s,
                            status = 'active',
                            shopify_synced_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (new_shopify_id, title, prod_id))

                    cur.execute("""
                        INSERT INTO fichas_360 (producto_id, body_html, enrichment_source)
                        VALUES (%s, %s, 'category_template')
                        ON CONFLICT (producto_id) DO UPDATE SET body_html = EXCLUDED.body_html
                    """, (prod_id, body_html))

                    created += 1
                    shopify_sku_map[sku.upper()] = new_shopify_id  # Add to map
                    logger.info(f'{store}: Created {sku} -> Shopify ID {new_shopify_id}')
                else:
                    errors += 1

            # Rate limiting
            time.sleep(0.5)

        except Exception as e:
            logger.error(f'{store}: Error processing {sku}: {e}')
            errors += 1

        # Commit every 10 products
        if (created + updated) % 10 == 0:
            conn.commit()

    conn.commit()
    cur.close()
    conn.close()

    return {
        'store': store,
        'processed': len(products),
        'created': created,
        'updated': updated,
        'errors': errors
    }


def sync_all_draft_stores(limit_per_store: int = 500) -> Dict[str, Any]:
    """Sync all stores with draft products."""
    stores = ['OH_IMPORTACIONES', 'YOKOMAR', 'KAIQI', 'BARA']

    results = {}
    total_uploaded = 0

    for store in stores:
        logger.info(f'Processing {store}...')
        result = process_draft_products(store, limit=limit_per_store)
        results[store] = result

        if 'uploaded' in result:
            total_uploaded += result['uploaded']

        # Pause between stores
        time.sleep(2)

    return {
        'stores': results,
        'total_uploaded': total_uploaded
    }


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage:')
        print('  python3 odi_v19_shopify_sync.py sync STORE [limit]  # Sync one store')
        print('  python3 odi_v19_shopify_sync.py sync-all [limit]    # Sync all draft stores')
        print('  python3 odi_v19_shopify_sync.py dry-run STORE       # Preview')
        print('  python3 odi_v19_shopify_sync.py count               # Count drafts')
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'sync' and len(sys.argv) > 2:
        store = sys.argv[2].upper()
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        result = process_draft_products(store, limit=limit)
        print(json.dumps(result, indent=2))

    elif cmd == 'sync-all':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 500
        result = sync_all_draft_stores(limit_per_store=limit)
        print(json.dumps(result, indent=2, default=str))

    elif cmd == 'dry-run' and len(sys.argv) > 2:
        store = sys.argv[2].upper()
        result = process_draft_products(store, dry_run=True)
        print(json.dumps(result, indent=2))

    elif cmd == 'count':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT e.codigo, COUNT(*) as drafts
            FROM productos p
            JOIN empresas e ON p.empresa_id = e.id
            WHERE p.shopify_product_id IS NULL AND p.status = 'draft'
            GROUP BY e.codigo
            ORDER BY drafts DESC
        """)
        for row in cur.fetchall():
            print(f'{row[0]}: {row[1]} drafts')
        cur.close()
        conn.close()

    else:
        print(f'Unknown command: {cmd}')
        sys.exit(1)
