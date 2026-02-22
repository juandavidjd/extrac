#!/usr/bin/env python3
"""V22.3 CSV Processor - Con configuracion por tienda"""

import os
import sys
import csv
import json
import logging
import time

sys.path.insert(0, '/opt/odi/core')
from odi_compatibility_parser import CompatibilityParser
from odi_source_quality_gate import SourceQualityGate

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('v22.3')

DATA_DIR = '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data'

# Configuracion especifica por tienda
CSV_STORES = {
    'DFG': {
        'csv': f'{DATA_DIR}/DFG/Base_Datos_DFG.csv',
        'delimiter': ';',
        'fields': {'sku': 'CODIGO', 'title': 'DESCRIPCION', 'price': 'PRECIO'},
    },
    'DUNA': {
        'csv': f'{DATA_DIR}/Duna/Base_Datos_Duna.csv',
        'delimiter': ';',
        'fields': {'sku': 'CODIGO', 'title': 'DESCRIPCION'},
    },
    'JAPAN': {
        'csv': f'{DATA_DIR}/Japan/LISTA_PRECIOS_RESCATADOS_FEB2026.csv',
        'delimiter': ';',
        'fields': {'sku': 'SKU', 'title': 'DESCRIPCION', 'price': 'PRECIO'},
    },
    'LEO': {
        'csv': f'{DATA_DIR}/Leo/LISTA_PRECIOS_RESCATADOS_FEB2026.csv',
        'delimiter': ';',
        'fields': {'sku': 'SKU', 'title': 'DESCRIPCION', 'price': 'PRECIO'},
    },
    'STORE': {
        'csv': f'{DATA_DIR}/Store/Base_Datos_Store.csv',
        'delimiter': ';',
        'fields': {'title': 'DESCRIPCION'},
    },
    'VAISAND': {
        'csv': f'{DATA_DIR}/Vaisand/Base_Datos_Vaisand.csv',
        'delimiter': ';',
        'fields': {'title': 'DESCRIPCION', 'image_url': 'URL_Origen'},
    },
    'OH_IMPORTACIONES': {
        'csv': f'{DATA_DIR}/OH Importaciones/Base_Datos_OH_Importaciones.csv',
        'delimiter': ',',
        'fields': {'sku': 'SKU', 'title': 'TITULO', 'price': 'PRECIO'},
    },
}


class V22Processor:
    def __init__(self):
        self.parser = CompatibilityParser()
        self.gate = SourceQualityGate()

    def load_csv(self, csv_path, delimiter=';'):
        products = []
        encodings = ['utf-8', 'latin-1', 'cp1252']
        for enc in encodings:
            try:
                with open(csv_path, 'r', encoding=enc) as f:
                    reader = csv.DictReader(f, delimiter=delimiter)
                    for row in reader:
                        products.append(dict(row))
                logger.info(f'CSV cargado ({enc}): {len(products)} productos')
                break
            except UnicodeDecodeError:
                continue
        return products

    def normalize_product(self, raw, field_map):
        product = {}
        for target, source in field_map.items():
            if source in raw and raw[source]:
                val = str(raw[source]).strip()
                val = val.replace('\ufeff', '')
                if val and val.lower() not in ['nan', 'none', 'null', '']:
                    product[target] = val
        if 'price' in product:
            price_str = product['price'].replace('$', '').replace('.', '').replace(',', '').strip()
            try:
                product['price'] = float(price_str)
            except ValueError:
                product['price'] = 0
        product['raw_data'] = raw
        return product

    def enrich_product(self, product):
        title = product.get('title', '')
        compatibles = self.parser.parse(title, product.get('raw_data', {}))
        if compatibles:
            product['compatibilidad'] = self.parser.format_for_shopify(compatibles)
            product['tags'] = self.parser.format_for_tags(compatibles)
        else:
            product['compatibilidad'] = ''
            product['tags'] = []
        if title and title == title.upper() and len(title) > 5:
            product['title'] = title.title()
        return product

    def process_store(self, store_code):
        store = store_code.upper()
        if store not in CSV_STORES:
            return {'error': 'store_not_found', 'available': list(CSV_STORES.keys())}

        config = CSV_STORES[store]
        csv_path = config['csv']
        delimiter = config.get('delimiter', ';')
        field_map = config.get('fields', {})

        if not os.path.exists(csv_path):
            return {'error': 'csv_not_found', 'path': csv_path}

        sep = '=' * 60
        logger.info(f'\n{sep}\nPROCESANDO: {store}\n{sep}')
        raw_products = self.load_csv(csv_path, delimiter)

        if not raw_products:
            return {'error': 'csv_empty'}

        logger.info('Paso 1: Normalizando...')
        products = [self.normalize_product(p, field_map) for p in raw_products]
        products = [p for p in products if p.get('title')]

        logger.info('Paso 2: Quality Gate...')
        quality = self.gate.evaluate(products, store)
        logger.info(f"  Grado: {quality['grade']} | {quality['recommendation']}")

        logger.info('Paso 3: Enriqueciendo compatibilidad...')
        enriched = [self.enrich_product(p) for p in products]
        compat_count = sum(1 for p in enriched if p.get('compatibilidad'))
        compat_pct = round(100*compat_count/len(enriched), 1) if enriched else 0
        logger.info(f'  Compatibilidad: {compat_count}/{len(enriched)} ({compat_pct}%)')

        with_compat = [p for p in enriched if p.get('compatibilidad')][:3]
        for p in with_compat:
            logger.info(f"    {p.get('sku', '?')}: {p['compatibilidad']}")

        result = {
            'store': store,
            'total': len(enriched),
            'quality_grade': quality['grade'],
            'compat_count': compat_count,
            'compat_pct': compat_pct,
            'metrics': quality.get('metrics', {}),
            'sample': [{'sku': p.get('sku'), 'title': p.get('title'), 'price': p.get('price'),
                        'compat': p.get('compatibilidad')} for p in enriched[:5]],
        }

        logger.info(f"\n{sep}\nRESULTADO {store}: {result['total']} productos, Grado {result['quality_grade']}, Compat {result['compat_pct']}%\n{sep}")
        return result

def main():
    if len(sys.argv) < 2:
        print('Uso: python3 v22_3_csv_processor.py <TIENDA|ALL>')
        print(f'Tiendas: {list(CSV_STORES.keys())}')
        sys.exit(1)

    target = sys.argv[1].upper()
    processor = V22Processor()

    if target == 'ALL':
        results = {}
        for store in CSV_STORES:
            results[store] = processor.process_store(store)

        print('\n' + '='*60)
        print('RESUMEN V22.3 - TODAS LAS TIENDAS CSV')
        print('='*60)
        for store, r in results.items():
            if 'error' in r:
                print(f"  {store}: ERROR - {r['error']}")
            else:
                print(f"  {store}: {r['total']:,} productos | Grado {r['quality_grade']} | Compat {r['compat_pct']}%")
    else:
        result = processor.process_store(target)
        print(json.dumps(result, indent=2, default=str))

if __name__ == '__main__':
    main()
