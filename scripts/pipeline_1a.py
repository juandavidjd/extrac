#!/usr/bin/env python3
import os, sys, json, re
import pandas as pd
from pathlib import Path

sys.path.insert(0, '/opt/odi/core')
try:
    from odi_semantic_normalizer import SemanticNormalizer
    normalizer = SemanticNormalizer()
except:
    normalizer = None

DATA_BASE = Path('/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data')
IDENTITY_BASE = Path('/opt/odi/data/identidad')
OUTPUT_BASE = Path('/opt/odi/data/test_quality')

STORE_FOLDERS = {
    'KAIQI': 'Kaiqi', 'BARA': 'Bara', 'DFG': 'Dfg', 'YOKOMAR': 'Yokomar',
    'JAPAN': 'Japan', 'IMBRA': 'Imbra', 'DUNA': 'Duna', 'LEO': 'Leo',
    'STORE': 'Store', 'VAISAND': 'Vaisand', 'OH_IMPORTACIONES': 'OH Importaciones',
    'VITTON': 'Vitton', 'ARMOTOS': 'Armotos', 'MCLMOTOS': 'Mclmotos', 'CBI': 'Cbi',
}

def load_csv(path):
    for sep in [';', ',']:
        for enc in ['utf-8', 'latin-1']:
            try:
                df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str, on_bad_lines='skip')
                if len(df.columns) > 1:
                    return df
            except:
                pass
    return None

def load_excel(path):
    try:
        return pd.read_excel(path, dtype=str)
    except:
        return None

def clean_price(val):
    if pd.isna(val) or val is None:
        return 0.0
    s = str(val).strip().replace('$', '').replace(' ', '')
    s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except:
        return 0.0

def run_pipeline(store_key):
    folder = STORE_FOLDERS.get(store_key, store_key)
    data_path = DATA_BASE / folder
    out_path = OUTPUT_BASE / store_key
    out_path.mkdir(parents=True, exist_ok=True)
    
    print('='*60)
    print(f'PIPELINE 1A - {store_key}')
    print('='*60)
    
    # Find files
    csvs = list(data_path.glob('*.csv'))
    excels = list(data_path.glob('*.xlsx'))
    
    base_csv = price_csv = catalog_csv = None
    price_excel = None
    
    for f in csvs:
        nl = f.name.lower()
        if 'base' in nl and 'datos' in nl:
            base_csv = f
        elif 'precio' in nl or 'lista' in nl:
            price_csv = f
        elif 'catalogo' in nl and 'imagen' in nl:
            catalog_csv = f
    
    if not base_csv and csvs:
        base_csv = csvs[0]
    
    for f in excels:
        nl = f.name.lower()
        if 'precio' in nl or 'lista' in nl:
            price_excel = f
    
    print(f'Base CSV: {base_csv.name if base_csv else NO}')
    print(f'Price CSV: {price_csv.name if price_csv else NO}')
    print(f'Price Excel: {price_excel.name if price_excel else NO}')
    print(f'Catalog CSV: {catalog_csv.name if catalog_csv else NO}')
    
    # Load prices
    prices = {}
    if price_csv:
        df = load_csv(price_csv)
        if df is not None:
            for c in df.columns:
                if 'precio' in c.lower():
                    col_p = c
                    col_c = None
                    for cc in df.columns:
                        if 'codigo' in cc.lower():
                            col_c = cc
                    if col_p:
                        for _, row in df.iterrows():
                            code = str(row.get(col_c, '')).strip().upper() if col_c else ''
                            price = clean_price(row.get(col_p))
                            if code and price > 0:
                                prices[code] = price
                    break
            print(f'Precios CSV: {len(prices)}')
    
    if price_excel:
        df = load_excel(price_excel)
        if df is not None:
            col_p = col_c = None
            for c in df.columns:
                cl = str(c).lower()
                if 'precio' in cl or 'publico' in cl:
                    col_p = c
                if 'codigo' in cl or 'ref' in cl:
                    col_c = c
            if col_p:
                for _, row in df.iterrows():
                    code = str(row.get(col_c, '')).strip().upper() if col_c else ''
                    price = clean_price(row.get(col_p))
                    if code and price > 0:
                        prices[code] = price
            print(f'Precios Excel: {len(prices)} (total)')
    
    # Load base data
    df = load_csv(base_csv)
    if df is None:
        print('ERROR: No CSV base')
        return
    
    print(f'Filas base: {len(df)}')
    
    # Find columns
    col_desc = col_code = col_price_base = None
    for c in df.columns:
        cl = c.lower().replace('﻿', '')
        if 'desc' in cl or 'nombre' in cl:
            col_desc = c
        if 'codigo' in cl or 'sku' in cl:
            col_code = c
        if 'precio' in cl:
            col_price_base = c
    if not col_desc:
        col_desc = df.columns[0]
    
    # Extract products
    products = []
    matched = 0
    zero = 0
    
    for idx, row in df.iterrows():
        desc = str(row.get(col_desc, '')).strip()
        if not desc or desc == 'nan':
            continue
        
        code = str(row.get(col_code, '')).strip().upper() if col_code else ''
        sku = f'{store_key[:3]}-{code or idx}'
        
        # Get price
        price = 0.0
        if code and code in prices:
            price = prices[code]
            matched += 1
        elif col_price_base:
            price = clean_price(row.get(col_price_base))
        
        if price == 0:
            zero += 1
        
        # Normalize title
        title = normalizer.normalize(desc) if normalizer else desc.title()
        
        products.append({
            'sku': sku,
            'title': title,
            'title_raw': desc,
            'price': price,
            'quantity': 0,
            'tags': f'Moto, Repuesto, {store_key}',
            'vendor': store_key,
        })
    
    print(f'Productos: {len(products)}')
    print(f'Precios matched: {matched}')
    print(f'Precios en /usr/bin/bash: {zero}')
    
    # Save
    out_file = out_path / 'products_ready.json'
    with open(out_file, 'w') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print(f'Guardado: {out_file}')
    
    # Show examples
    print()
    print('=== 5 EJEMPLOS ===')
    for p in products[:5]:
        print(f'RAW: {p[title_raw]}')
        print(f'NEW: {p[title]}')
        print(f'PRICE: ')
        print()

if __name__ == '__main__':
    store = sys.argv[1].upper() if len(sys.argv) > 1 else 'KAIQI'
    run_pipeline(store)
