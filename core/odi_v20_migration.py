#!/usr/bin/env python3
"""
ODI V20 Database Migration Module
Integrates taxonomy population and product migration.
No loose scripts - everything in /opt/odi/core/
"""
import json
import logging
import psycopg2
from typing import Dict, List, Optional, Any
import requests
import time

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

# Taxonomy hierarchy: Sistema -> SubSistema -> Tipo
TAXONOMY_HIERARCHY = {
    'MOTOR': {
        'COMBUSTION': ['piston', 'piston ring', 'piston rings', 'cylinder', 'cylinder head', 'cylinder sleeve liner', 'valve', 'camshaft', 'crankshaft', 'connecting rod', 'connecting rod kit', 'rocker arm'],
        'SELLADO': ['gasket', 'gasket kit', 'complete gasket kit', 'oil seal'],
        'ENCENDIDO': ['spark plug', 'CDI unit', 'ignition coil', 'carbon brush'],
        'CARBURACION': ['carburetor', 'air filter', 'throttle cable'],
        'LUBRICACION': ['oil filter', 'pump'],
    },
    'TRANSMISION': {
        'EMBRAGUE': ['clutch', 'clutch cable', 'clutch bell', 'clutch bell housing'],
        'ARRASTRE': ['motorcycle chain', 'sprocket', 'rear sprocket', 'timing chain'],
        'CAJA': ['gearbox housing'],
    },
    'FRENOS': {
        'DISCO': ['brake disc', 'brake caliper', 'brake pad', 'brake pads'],
        'TAMBOR': ['brake', 'brake cable'],
    },
    'SUSPENSION': {
        'AMORTIGUACION': ['shock absorber', 'spring'],
        'DIRECCION': ['steering bearing race', 'handlebar'],
        'EJES': ['axle shaft', 'front axle', 'rear axle'],
    },
    'ELECTRICO': {
        'ILUMINACION': ['headlight', 'tail light', 'turn signal', 'light bulb', 'LED bulb'],
        'GENERACION': ['stator', 'voltage regulator'],
        'CABLEADO': ['wiring harness', 'handlebar switch assembly'],
    },
    'CARROCERIA': {
        'PLASTICOS': ['fender', 'fairing', 'side cover', 'cover cap'],
        'TANQUE': ['fuel tank'],
        'ASIENTO': ['seat'],
    },
    'CONTROLES': {
        'MANUBRIO': ['handlebar grip', 'lever', 'handlebar lever', 'mirror'],
        'GUAYAS': ['control cable', 'speedometer cable'],
        'PEDALES': ['footpeg', 'footpeg rubber'],
    },
    'RODAMIENTOS': {
        'GENERAL': ['bearing', 'rubber bushing'],
    },
    'SOPORTE': {
        'PATAS': ['side stand', 'center stand'],
    },
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def populate_taxonomy():
    """Populate categorias table from TAXONOMY_HIERARCHY."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Get SRM rama_id
    cur.execute("SELECT id FROM ramas WHERE codigo = 'SRM'")
    rama_id = cur.fetchone()[0]

    categories_inserted = 0

    for sistema, subsistemas in TAXONOMY_HIERARCHY.items():
        # Insert Level 1: Sistema
        cur.execute("""
            INSERT INTO categorias (rama_id, nivel, codigo, nombre, parent_id)
            VALUES (%s, 1, %s, %s, NULL)
            ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre
            RETURNING id
        """, (rama_id, f'SRM_{sistema}', sistema))
        sistema_id = cur.fetchone()[0]
        categories_inserted += 1

        for subsistema, tipos in subsistemas.items():
            # Insert Level 2: SubSistema
            cur.execute("""
                INSERT INTO categorias (rama_id, nivel, codigo, nombre, parent_id)
                VALUES (%s, 2, %s, %s, %s)
                ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre
                RETURNING id
            """, (rama_id, f'SRM_{sistema}_{subsistema}', subsistema, sistema_id))
            subsistema_id = cur.fetchone()[0]
            categories_inserted += 1

            for tipo in tipos:
                # Insert Level 3: Tipo
                tipo_code = tipo.replace(' ', '_').upper()
                cur.execute("""
                    INSERT INTO categorias (rama_id, nivel, codigo, nombre, nombre_en, parent_id)
                    VALUES (%s, 3, %s, %s, %s, %s)
                    ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre
                    RETURNING id
                """, (rama_id, f'SRM_{sistema}_{subsistema}_{tipo_code}', tipo.title(), tipo, subsistema_id))
                categories_inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f'Taxonomy populated: {categories_inserted} categories inserted')
    return categories_inserted


def get_empresa_id(cur, codigo: str) -> Optional[int]:
    """Get empresa ID by codigo."""
    cur.execute("SELECT id FROM empresas WHERE codigo = %s", (codigo.upper(),))
    result = cur.fetchone()
    return result[0] if result else None


def fetch_shopify_products(store: str, config_path: str = '/opt/odi/data/brands') -> List[Dict]:
    """Fetch all products from a Shopify store."""
    try:
        with open(f'{config_path}/{store.lower()}.json') as f:
            cfg = json.load(f)
    except FileNotFoundError:
        logger.error(f'{store}: Config not found')
        return []

    shop = cfg['shopify']['shop']
    token = cfg['shopify']['token']

    products = []
    url = f'https://{shop}/admin/api/2024-01/products.json?limit=250'
    headers = {'X-Shopify-Access-Token': token}

    while url:
        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            time.sleep(0.5)

            for p in r.json().get('products', []):
                variant = p['variants'][0] if p.get('variants') else {}
                products.append({
                    'shopify_product_id': p['id'],
                    'shopify_variant_id': variant.get('id'),
                    'title': p.get('title', ''),
                    'sku': variant.get('sku', ''),
                    'price': variant.get('price'),
                    'body_html': p.get('body_html', ''),
                    'product_type': p.get('product_type', ''),
                    'status': p.get('status', 'active'),
                    'images': [img.get('src') for img in p.get('images', [])],
                })

            link = r.headers.get('Link', '')
            url = None
            if 'rel="next"' in link:
                for part in link.split(','):
                    if 'rel="next"' in part:
                        url = part.split('<')[1].split('>')[0]
                        break
        except Exception as e:
            logger.error(f'{store}: Fetch error - {e}')
            break

    return products


def migrate_store_products(store: str) -> Dict[str, int]:
    """Migrate products from Shopify to PostgreSQL for a single store."""
    conn = get_db_connection()
    cur = conn.cursor()

    empresa_id = get_empresa_id(cur, store)
    if not empresa_id:
        # Try alternate naming
        alt_codes = {'OH_IMPORT': 'OH_IMPORTACIONES'}
        alt_code = alt_codes.get(store, store)
        empresa_id = get_empresa_id(cur, alt_code)

    if not empresa_id:
        logger.error(f'{store}: Empresa not found in database')
        cur.close()
        conn.close()
        return {'error': 'Empresa not found'}

    products = fetch_shopify_products(store)
    if not products:
        cur.close()
        conn.close()
        return {'fetched': 0, 'inserted': 0}

    inserted = 0
    updated = 0

    for p in products:
        sku = p['sku'] or f"SHOP_{p['shopify_product_id']}"

        cur.execute("""
            SELECT id FROM productos
            WHERE empresa_id = %s AND codigo_proveedor = %s
        """, (empresa_id, sku))
        existing = cur.fetchone()

        price = None
        if p['price']:
            try:
                price = float(p['price'])
            except:
                pass

        status = 'active' if p['status'] == 'active' else 'draft'

        if existing:
            cur.execute("""
                UPDATE productos SET
                    titulo_raw = %s,
                    precio_sin_iva = %s,
                    status = %s,
                    shopify_product_id = %s,
                    shopify_variant_id = %s,
                    shopify_synced_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (p['title'], price, status, p['shopify_product_id'], p['shopify_variant_id'], existing[0]))
            updated += 1
            prod_id = existing[0]
        else:
            cur.execute("""
                INSERT INTO productos (
                    empresa_id, codigo_proveedor, titulo_raw, precio_sin_iva, status,
                    shopify_product_id, shopify_variant_id, shopify_synced_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id
            """, (empresa_id, sku, p['title'], price, status, p['shopify_product_id'], p['shopify_variant_id']))
            prod_id = cur.fetchone()[0]
            inserted += 1

        if p['body_html']:
            cur.execute("""
                INSERT INTO fichas_360 (producto_id, body_html, enrichment_source)
                VALUES (%s, %s, 'manual')
                ON CONFLICT (producto_id) DO UPDATE SET body_html = EXCLUDED.body_html
            """, (prod_id, p['body_html']))

        for i, img_url in enumerate(p['images']):
            cur.execute("""
                INSERT INTO producto_imagenes (producto_id, url_origen, url_shopify, tipo, es_principal, orden)
                VALUES (%s, %s, %s, 'real', %s, %s)
                ON CONFLICT DO NOTHING
            """, (prod_id, img_url, img_url, i == 0, i + 1))

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f'{store}: Fetched {len(products)}, Inserted {inserted}, Updated {updated}')
    return {'fetched': len(products), 'inserted': inserted, 'updated': updated}


def migrate_all_stores() -> Dict[str, Any]:
    """Migrate all 15 SRM stores to PostgreSQL."""
    STORES = [
        'ARMOTOS', 'BARA', 'CBI', 'DFG', 'DUNA', 'IMBRA', 'JAPAN',
        'KAIQI', 'LEO', 'MCLMOTOS', 'OH_IMPORT', 'STORE', 'VAISAND', 'VITTON', 'YOKOMAR'
    ]

    results = {}
    total_fetched = 0
    total_inserted = 0
    total_updated = 0

    for store in STORES:
        logger.info(f'Migrating {store}...')
        result = migrate_store_products(store)
        results[store] = result

        if 'fetched' in result:
            total_fetched += result['fetched']
            total_inserted += result.get('inserted', 0)
            total_updated += result.get('updated', 0)

    return {
        'stores': results,
        'total_fetched': total_fetched,
        'total_inserted': total_inserted,
        'total_updated': total_updated
    }


def verify_migration() -> List[Dict]:
    """Verify migration results."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM v_resumen_empresas")
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [dict(zip(columns, row)) for row in rows]


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage: python3 odi_v20_migration.py [taxonomy|migrate|verify|all]')
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'taxonomy':
        count = populate_taxonomy()
        print(f'Taxonomy populated: {count} categories')

    elif cmd == 'migrate':
        if len(sys.argv) > 2:
            store = sys.argv[2].upper()
            result = migrate_store_products(store)
            print(json.dumps(result, indent=2))
        else:
            result = migrate_all_stores()
            print(json.dumps(result, indent=2))

    elif cmd == 'verify':
        result = verify_migration()
        for r in result:
            print(f"{r['empresa']}: {r['total_productos']} productos, {r['activos']} activos, {r['con_precio']} con precio")

    elif cmd == 'all':
        print('Step 1: Populating taxonomy...')
        count = populate_taxonomy()
        print(f'  {count} categories created')

        print('\nStep 2: Migrating all stores...')
        result = migrate_all_stores()
        print(f"  Total fetched: {result['total_fetched']}")
        print(f"  Total inserted: {result['total_inserted']}")
        print(f"  Total updated: {result['total_updated']}")

        print('\nStep 3: Verification...')
        verify = verify_migration()
        for v in verify:
            if v['total_productos'] > 0:
                print(f"  {v['empresa']}: {v['total_productos']} productos")

    else:
        print(f'Unknown command: {cmd}')
        sys.exit(1)


# === ENCODING SAFETY FUNCTIONS ===

def read_csv_safe(filepath: str):
    """Read CSV with encoding fallback: utf-8-sig -> latin-1 -> cp1252."""
    import pandas as pd

    for encoding in ['utf-8-sig', 'latin-1', 'cp1252']:
        for sep in [',', ';', '\t']:
            try:
                df = pd.read_csv(filepath, encoding=encoding, sep=sep)
                if len(df.columns) > 1:
                    return df
            except:
                continue

    raise ValueError(f'Could not read CSV: {filepath}')


def read_excel_safe(filepath: str, header_row: int = 0):
    """Read Excel with proper header detection."""
    import pandas as pd

    df_raw = pd.read_excel(filepath, header=None, nrows=20)

    for i in range(min(15, len(df_raw))):
        row_str = ' '.join([str(x) for x in df_raw.iloc[i].tolist() if pd.notna(x)]).upper()
        if 'CODIGO' in row_str or 'REFERENCIA' in row_str or 'SKU' in row_str:
            header_row = i
            break

    return pd.read_excel(filepath, header=header_row)


def clean_title(title: str) -> str:
    """Clean title: remove garbage characters, fix double-encoded UTF-8."""
    if not title:
        return title

    # Common double-encoding fixes (UTF-8 interpreted as Latin-1)
    replacements = {
        '\xc3\xa9': 'e', '\xc3\xa1': 'a', '\xc3\xad': 'i', '\xc3\xb3': 'o', '\xc3\xba': 'u',
        '\xc3\xb1': 'n', '\xc3\x81': 'A', '\xc3\x89': 'E', '\xc3\x8d': 'I', '\xc3\x93': 'O',
        '\xc3\x9a': 'U', '\xc3\x91': 'N', '\xc2': '', '\x84': '', '\x85': '',
    }

    for bad, good in replacements.items():
        title = title.replace(bad, good)

    # Remove control characters (keep printable + newline/tab)
    title = ''.join(c for c in title if ord(c) >= 32 or c in '\n\t')

    return title.strip()


def build_shopify_sku_map(store: str) -> Dict[str, int]:
    """Build map of codigo_proveedor -> shopify_product_id for a store."""
    products = fetch_shopify_products(store)

    sku_map = {}
    for p in products:
        sku = p['sku'] or f"SHOP_{p['shopify_product_id']}"
        sku_map[sku] = p['shopify_product_id']

    return sku_map
