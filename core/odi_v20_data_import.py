#!/usr/bin/env python3
"""
ODI V20 Data Import Module
Imports missing products from Data/ files to PostgreSQL.
Integrated in /opt/odi/core/ - NO loose scripts.
"""
import json
import logging
import os
import re
import psycopg2
from typing import Dict, List, Optional, Any, Set
import pandas as pd

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

# Paths
DATA_DIR = '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/'
IMAGES_DIR = '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Imagenes/'

# Folder to store code mapping
FOLDER_MAP = {
    'Armotos': 'ARMOTOS', 'Bara': 'BARA', 'CBI': 'CBI', 'Cbi': 'CBI',
    'DFG': 'DFG', 'Duna': 'DUNA', 'Imbra': 'IMBRA', 'Japan': 'JAPAN',
    'Kaiqi': 'KAIQI', 'Leo': 'LEO', 'MclMotos': 'MCLMOTOS',
    'OH Importaciones': 'OH_IMPORTACIONES', 'Store': 'STORE',
    'Vaisand': 'VAISAND', 'Vitton': 'VITTON', 'Yokomar': 'YOKOMAR'
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def read_csv_safe(filepath: str) -> pd.DataFrame:
    """Read CSV with encoding fallback."""
    for enc in ['utf-8-sig', 'latin-1', 'cp1252']:
        for sep in [',', ';', '\t']:
            try:
                df = pd.read_csv(filepath, encoding=enc, sep=sep)
                if len(df.columns) > 1:
                    return df
            except:
                continue
    raise ValueError(f'Could not read CSV: {filepath}')


def read_excel_safe(filepath: str) -> pd.DataFrame:
    """Read Excel with header auto-detection."""
    df_raw = pd.read_excel(filepath, header=None, nrows=20)
    header_row = 0

    for i in range(min(15, len(df_raw))):
        row_str = ' '.join([str(x) for x in df_raw.iloc[i].tolist() if pd.notna(x)]).upper()
        if 'CODIGO' in row_str or 'REFERENCIA' in row_str or 'SKU' in row_str:
            header_row = i
            break

    return pd.read_excel(filepath, header=header_row)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to standard format, handling duplicates."""
    col_map = {}
    seen = set()

    for col in df.columns:
        col_upper = str(col).upper().strip()

        # Determine standard name
        if 'CODIGO' in col_upper or col_upper == 'REF' or col_upper == 'REFERENCIA':
            new_name = 'CODIGO'
        elif 'DESCRIPCION' in col_upper or 'PRODUCTO' in col_upper or 'NOMBRE' in col_upper:
            new_name = 'DESCRIPCION'
        elif 'PRECIO' in col_upper and 'SIN' in col_upper:
            new_name = 'PRECIO_SIN_IVA'
        elif 'PRECIO' in col_upper and 'IVA' in col_upper:
            new_name = 'PRECIO_CON_IVA'
        elif col_upper in ['PRECIO', 'P.VENTA', 'PVP', 'VALOR']:
            new_name = 'PRECIO'
        else:
            new_name = col

        # Handle duplicates - only keep first occurrence
        if new_name in seen:
            col_map[col] = f'{new_name}_{len(seen)}'
        else:
            col_map[col] = new_name
            seen.add(new_name)

    return df.rename(columns=col_map)


def get_existing_codes(cur, empresa_id: int) -> Set[str]:
    """Get all existing product codes for a company."""
    cur.execute(
        "SELECT codigo_proveedor FROM productos WHERE empresa_id = %s",
        (empresa_id,)
    )
    return {row[0].upper().strip() for row in cur.fetchall()}


def find_image_for_code(store: str, code: str) -> Optional[str]:
    """Find image file for a product code."""
    store_img_dir = os.path.join(IMAGES_DIR, store)

    if not os.path.exists(store_img_dir):
        # Try alternate names
        for folder in os.listdir(IMAGES_DIR):
            if folder.upper() == store.upper():
                store_img_dir = os.path.join(IMAGES_DIR, folder)
                break

    if not os.path.exists(store_img_dir):
        return None

    code_upper = code.upper().strip()

    for f in os.listdir(store_img_dir):
        f_upper = f.upper()
        # Match by code in filename
        if code_upper in f_upper:
            return os.path.join(store_img_dir, f)
        # Match by code at start
        if f_upper.startswith(code_upper):
            return os.path.join(store_img_dir, f)

    return None


def clean_title(title: str) -> str:
    """Clean and normalize title."""
    if not title or pd.isna(title):
        return ''

    title = str(title).strip()

    # Remove garbage characters
    title = ''.join(c for c in title if ord(c) >= 32 or c in '\n\t')

    return title[:300]  # Max length


def extract_price(row: pd.Series) -> Optional[float]:
    """Extract price from row, trying multiple columns."""
    for col in ['PRECIO_SIN_IVA', 'PRECIO', 'PRECIO_CON_IVA']:
        if col in row.index:
            val = row[col]
            if pd.notna(val):
                try:
                    # Handle numeric values directly
                    if isinstance(val, (int, float)):
                        return float(val)

                    val_str = str(val).strip()
                    # Remove currency symbols
                    val_str = val_str.replace('$', '').replace(' ', '')

                    # Handle thousands separator (.) vs decimal (,) - Colombian format
                    # If has both . and ,: . is thousands, , is decimal
                    if '.' in val_str and ',' in val_str:
                        val_str = val_str.replace('.', '').replace(',', '.')
                    # If only comma: might be decimal
                    elif ',' in val_str and '.' not in val_str:
                        val_str = val_str.replace(',', '.')
                    # If only dots and more than one: thousands separator
                    elif val_str.count('.') > 1:
                        val_str = val_str.replace('.', '')
                    # Single dot with 3+ digits after: thousands
                    elif '.' in val_str:
                        parts = val_str.split('.')
                        if len(parts) == 2 and len(parts[1]) >= 3:
                            val_str = val_str.replace('.', '')

                    if val_str:
                        return float(val_str)
                except:
                    pass
    return None


def import_from_data_files(store: str, dry_run: bool = False) -> Dict[str, Any]:
    """Import missing products from Data/ files for a store."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Get empresa_id
    cur.execute("SELECT id FROM empresas WHERE codigo = %s", (store.upper(),))
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        return {'error': f'Empresa {store} not found'}

    empresa_id = result[0]

    # Get existing codes
    existing_codes = get_existing_codes(cur, empresa_id)
    logger.info(f'{store}: {len(existing_codes)} existing products')

    # Find data folder
    data_folder = None
    for folder, code in FOLDER_MAP.items():
        if code == store.upper():
            folder_path = os.path.join(DATA_DIR, folder)
            if os.path.exists(folder_path):
                data_folder = folder_path
                break

    if not data_folder:
        # Try direct match
        for folder in os.listdir(DATA_DIR):
            if folder.upper() == store.upper():
                data_folder = os.path.join(DATA_DIR, folder)
                break

    if not data_folder or not os.path.exists(data_folder):
        cur.close()
        conn.close()
        return {'error': f'Data folder not found for {store}'}

    # Read all data files
    all_products = []

    for f in os.listdir(data_folder):
        fpath = os.path.join(data_folder, f)

        try:
            if f.lower().endswith('.csv'):
                df = read_csv_safe(fpath)
            elif f.lower().endswith(('.xlsx', '.xls')):
                df = read_excel_safe(fpath)
            else:
                continue

            df = normalize_column_names(df)

            if 'CODIGO' not in df.columns:
                logger.warning(f'{store}: No CODIGO column in {f}')
                continue

            for _, row in df.iterrows():
                code = row.get('CODIGO')

                # Handle case where code might be a Series (duplicate columns)
                if isinstance(code, pd.Series):
                    code = code.iloc[0]

                if pd.isna(code) or str(code).strip() == '':
                    continue

                code = str(code).strip().upper()

                # Skip if already exists
                if code in existing_codes:
                    continue

                desc = row.get('DESCRIPCION', '')
                if isinstance(desc, pd.Series):
                    desc = desc.iloc[0]

                price = extract_price(row)

                all_products.append({
                    'codigo': code,
                    'titulo': clean_title(desc) or code,
                    'precio': price,
                    'source_file': f
                })

                existing_codes.add(code)  # Prevent duplicates within files

        except Exception as e:
            logger.error(f'{store}: Error reading {f}: {e}')

    logger.info(f'{store}: Found {len(all_products)} new products to import')

    if dry_run:
        cur.close()
        conn.close()
        return {
            'store': store,
            'new_products': len(all_products),
            'dry_run': True,
            'sample': all_products[:5]
        }

    # Import products
    inserted = 0
    with_price = 0
    with_image = 0

    for p in all_products:
        try:
            # Find image
            img_path = find_image_for_code(store, p['codigo'])

            # Insert product
            cur.execute("""
                INSERT INTO productos (
                    empresa_id, codigo_proveedor, titulo_raw, precio_sin_iva, status
                ) VALUES (%s, %s, %s, %s, 'draft')
                ON CONFLICT (empresa_id, codigo_proveedor) DO NOTHING
                RETURNING id
            """, (empresa_id, p['codigo'], p['titulo'], p['precio']))

            result = cur.fetchone()
            if result:
                prod_id = result[0]
                inserted += 1

                if p['precio']:
                    with_price += 1

                # Insert image if found
                if img_path:
                    cur.execute("""
                        INSERT INTO producto_imagenes (
                            producto_id, url_origen, tipo, es_principal, orden
                        ) VALUES (%s, %s, 'real', true, 1)
                        ON CONFLICT DO NOTHING
                    """, (prod_id, img_path))
                    with_image += 1

        except Exception as e:
            logger.error(f'{store}: Error inserting {p["codigo"]}: {e}')

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f'{store}: Inserted {inserted}, with price {with_price}, with image {with_image}')

    return {
        'store': store,
        'found': len(all_products),
        'inserted': inserted,
        'with_price': with_price,
        'with_image': with_image
    }


def import_all_gaps(dry_run: bool = False) -> Dict[str, Any]:
    """Import missing products for all stores with gaps."""
    stores_with_gap = ['DFG', 'YOKOMAR', 'BARA', 'KAIQI', 'DUNA', 'OH_IMPORTACIONES']

    results = {}
    total_inserted = 0

    for store in stores_with_gap:
        logger.info(f'Processing {store}...')
        result = import_from_data_files(store, dry_run)
        results[store] = result

        if 'inserted' in result:
            total_inserted += result['inserted']

    return {
        'stores': results,
        'total_inserted': total_inserted,
        'dry_run': dry_run
    }


def verify_product(store: str, codigo: str) -> Dict[str, Any]:
    """Verify a specific product exists and show details."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT p.id, p.codigo_proveedor, p.titulo_raw, p.precio_sin_iva,
               p.shopify_product_id, p.status, e.codigo as empresa
        FROM productos p
        JOIN empresas e ON p.empresa_id = e.id
        WHERE e.codigo = %s AND UPPER(p.codigo_proveedor) = %s
    """, (store.upper(), codigo.upper()))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if row:
        return {
            'found': True,
            'id': row[0],
            'codigo': row[1],
            'titulo': row[2],
            'precio': float(row[3]) if row[3] else None,
            'shopify_id': row[4],
            'status': row[5],
            'empresa': row[6]
        }

    return {'found': False, 'codigo': codigo, 'store': store}


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage:')
        print('  python3 odi_v20_data_import.py import STORE       # Import one store')
        print('  python3 odi_v20_data_import.py import-all         # Import all gaps')
        print('  python3 odi_v20_data_import.py dry-run STORE      # Preview import')
        print('  python3 odi_v20_data_import.py verify STORE CODE  # Verify product')
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'import' and len(sys.argv) > 2:
        store = sys.argv[2].upper()
        result = import_from_data_files(store)
        print(json.dumps(result, indent=2))

    elif cmd == 'import-all':
        result = import_all_gaps()
        print(json.dumps(result, indent=2, default=str))

    elif cmd == 'dry-run' and len(sys.argv) > 2:
        store = sys.argv[2].upper()
        result = import_from_data_files(store, dry_run=True)
        print(json.dumps(result, indent=2))

    elif cmd == 'verify' and len(sys.argv) > 3:
        store = sys.argv[2].upper()
        code = sys.argv[3].upper()
        result = verify_product(store, code)
        print(json.dumps(result, indent=2))

    else:
        print(f'Unknown command: {cmd}')
        sys.exit(1)
