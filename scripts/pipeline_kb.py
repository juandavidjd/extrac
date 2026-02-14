#!/usr/bin/env python3
"""Pipeline con Knowledge Base - Enriquecimiento via ChromaDB"""
import os
import json
import csv
import re
import chromadb
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')

BASE_DIR = Path('/mnt/volume_sfo3_01/profesion/ecosistema_odi')
CHROMA_HOST = 'localhost'
CHROMA_PORT = 8000
COLLECTION = 'odi_ind_motos'

PIEZAS = {
    'cadena': 'Cadena de Transmision',
    'arbol': 'Arbol de Levas',
    'balancin': 'Balancin',
    'biela': 'Biela',
    'bomba': 'Bomba de Aceite',
    'bujia': 'Bujia',
    'cable': 'Cable',
    'carburador': 'Carburador',
    'cilindro': 'Cilindro',
    'clutch': 'Clutch',
    'embolo': 'Piston',
    'empaque': 'Empaque',
    'filtro': 'Filtro',
    'llanta': 'Llanta',
    'manigueta': 'Manigueta',
    'piston': 'Piston',
    'retrovisor': 'Retrovisor',
    'rodamiento': 'Rodamiento',
    'switch': 'Switch',
    'tensor': 'Tensor',
    'valvula': 'Valvula'
}

SISTEMAS = {
    'motor': 'Motor',
    'transmision': 'Transmision',
    'freno': 'Frenos',
    'suspension': 'Suspension',
    'electrico': 'Electrico',
    'carroceria': 'Carroceria',
    'escape': 'Escape'
}

def normalize_sku(sku):
    """Normaliza SKU: 2/03/1985 -> 2-3-85, elimina ceros a la izquierda"""
    if not sku:
        return ''
    # Reemplazar / por -
    sku = sku.replace('/', '-')
    # Separar por guiones y quitar ceros a la izquierda de cada parte
    parts = sku.split('-')
    normalized_parts = []
    for p in parts:
        # Si es un numero, quitar ceros a la izquierda
        if p.isdigit():
            normalized_parts.append(str(int(p)))
        else:
            normalized_parts.append(p)
    return '-'.join(normalized_parts)


class KBPipeline:
    def __init__(self):
        self.client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        try:
            self.collection = self.client.get_or_create_collection(COLLECTION)
        except Exception as e:
            print(f'Error ChromaDB: {e}')
            self.collection = None

    def query_kb(self, title, n_results=3):
        """Consulta ChromaDB para encontrar productos similares"""
        if not self.collection:
            return []
        try:
            results = self.collection.query(
                query_texts=[title],
                n_results=n_results
            )
            matches = []
            if results and results.get('metadatas'):
                for i, meta in enumerate(results['metadatas'][0]):
                    if results.get('distances') and results['distances'][0][i] < 0.8:
                        matches.append({
                            'id': results['ids'][0][i] if results.get('ids') else '',
                            'distance': results['distances'][0][i],
                            **meta
                        })
            return matches
        except Exception as e:
            print(f'KB query error: {e}')
            return []

    def enrich_from_kb(self, product, kb_matches):
        """Enriquece producto con datos de KB"""
        if not kb_matches:
            product['kb_enriched'] = False
            return product

        best_match = kb_matches[0]
        enriched_fields = []

        if not product.get('system'):
            kb_system = best_match.get('sistema_moto') or best_match.get('system', '')
            if kb_system:
                product['system'] = kb_system
                enriched_fields.append('system')

        if not product.get('category'):
            kb_cat = best_match.get('categoria') or best_match.get('category', '')
            if kb_cat:
                product['category'] = kb_cat
                enriched_fields.append('category')

        if not product.get('compatible_models'):
            kb_models = best_match.get('modelos') or best_match.get('compatible_models', '')
            if kb_models:
                product['compatible_models'] = kb_models
                enriched_fields.append('compatible_models')

        if product.get('price', 0) == 0:
            kb_price = best_match.get('price')
            if kb_price and str(kb_price) != '0':
                try:
                    product['price_reference'] = float(kb_price)
                    product['price_source'] = best_match.get('vendor', 'kb')
                    enriched_fields.append('price_reference')
                except:
                    pass

        product['kb_enriched'] = len(enriched_fields) > 0
        product['kb_fields'] = enriched_fields
        product['kb_source'] = best_match.get('vendor', 'unknown')
        product['kb_distance'] = best_match.get('distance', 1.0)

        return product

    def save_to_kb(self, products, store_name):
        """Guarda productos procesados en ChromaDB"""
        if not self.collection:
            return 0

        saved = 0
        for p in products:
            try:
                doc_text = f"{p.get('title', '')} {p.get('category', '')} {p.get('system', '')} {p.get('compatible_models', '')}"
                doc_id = f"{store_name}_{p.get('sku', p.get('handle', str(saved)))}"

                self.collection.upsert(
                    documents=[doc_text],
                    ids=[doc_id],
                    metadatas=[{
                        'sku': str(p.get('sku', '')),
                        'price': str(p.get('price', 0)),
                        'vendor': store_name,
                        'sistema_moto': p.get('system', ''),
                        'categoria': p.get('category', ''),
                        'modelos': p.get('compatible_models', ''),
                        'titulo_normalizado': p.get('title', '')
                    }]
                )
                saved += 1
            except Exception as e:
                pass
        return saved

    def detect_pieza(self, title):
        """Detecta tipo de pieza en el titulo"""
        title_lower = title.lower()
        for key, val in PIEZAS.items():
            if key in title_lower:
                return val
        return ''

    def detect_sistema(self, title):
        """Detecta sistema de la moto"""
        title_lower = title.lower()
        for key, val in SISTEMAS.items():
            if key in title_lower:
                return val
        return ''

    def detect_modelo(self, title):
        """Extrae modelo/CC de moto"""
        patterns = [
            r'(AKT|BAJAJ|HERO|HONDA|YAMAHA|SUZUKI|TVS|PULSAR|DISCOVER|BWS|FZ|XTZ|NKD|TITAN|CG|CB|CBF|XL|XR)\s*(\d+)?',
            r'(\d{2,3})\s*CC',
        ]
        for pat in patterns:
            m = re.search(pat, title, re.IGNORECASE)
            if m:
                return m.group(0).strip()
        return ''

    def normalize_title(self, raw_title):
        """Normaliza titulo con estructura profesional"""
        pieza = self.detect_pieza(raw_title)
        modelo = self.detect_modelo(raw_title)
        sistema = self.detect_sistema(raw_title)

        clean = re.sub(r'[_\-]+', ' ', raw_title)
        clean = re.sub(r'\s+', ' ', clean).strip()
        clean = clean.title()

        if pieza and modelo:
            return f"{pieza} {modelo} - Repuesto {sistema or 'Moto'}"
        elif pieza:
            return f"{pieza} - Repuesto Moto"

        return clean

    def load_store_data(self, store_name):
        """Carga datos de una tienda desde estructura ecosistema_odi"""
        store_dir = BASE_DIR / store_name
        if not store_dir.exists():
            print(f'No existe: {store_dir}')
            return []

        products = []
        prices = {}
        images = {}

        # Cargar precios de ambas carpetas (precios/ y catalogo/)
        for price_dir in [store_dir / 'precios', store_dir / 'catalogo']:
            if price_dir.exists():
                for f in price_dir.iterdir():
                    if f.suffix == '.csv':
                        try:
                            with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                                # Detectar delimitador
                                first_line = fp.readline()
                                fp.seek(0)
                                delimiter = ';' if ';' in first_line else ','
                                reader = csv.DictReader(fp, delimiter=delimiter)
                                for row in reader:
                                    # Limpiar keys (eliminar espacios)
                                    row = {k.strip(): v for k, v in row.items()}
                                    sku = row.get('CODIGO') or row.get('codigo') or row.get('SKU') or row.get('sku') or ''
                                    price = row.get('PRECIO') or row.get('precio') or row.get('PRICE') or row.get('price') or '0'
                                    if sku:
                                        try:
                                            # Guardar con SKU original y normalizado
                                            sku_clean = sku.strip()
                                            sku_norm = normalize_sku(sku_clean)
                                            # Manejar formato europeo: 23.400 -> 23400
                                            price_str = str(price).strip()
                                            if re.match(r'^\d{1,3}\.\d{3}$', price_str):
                                                price_str = price_str.replace('.', '')
                                            price_val = float(re.sub(r'[^\d.]', '', price_str))
                                            prices[sku_clean] = price_val
                                            prices[sku_norm] = price_val
                                        except:
                                            pass
                        except Exception as e:
                            print(f'Error precios {f}: {e}')

        img_dir = store_dir / 'imagenes'
        if img_dir.exists():
            for f in img_dir.iterdir():
                if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                    key = f.stem.upper()
                    images[key] = str(f)

        catalogo_dir = store_dir / 'catalogo'
        if catalogo_dir.exists():
            for f in catalogo_dir.iterdir():
                if 'Base_Datos' in f.name and f.suffix == '.csv':
                    try:
                        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                            # Detectar delimitador
                            first_line = fp.readline()
                            fp.seek(0)
                            delimiter = ';' if ';' in first_line else ','
                            reader = csv.DictReader(fp, delimiter=delimiter)
                            for row in reader:
                                # Limpiar keys (eliminar espacios)
                                row = {k.strip(): v for k, v in row.items()}
                                sku = row.get('CODIGO') or row.get('codigo') or row.get('SKU') or row.get('sku') or row.get('Handle') or ''
                                title_raw = row.get('DESCRIPCION') or row.get('descripcion') or row.get('Title') or row.get('TITULO') or sku
                                csv_price = row.get('PRECIO') or row.get('precio') or '0'

                                if not sku:
                                    continue

                                sku = sku.strip()
                                sku_norm = normalize_sku(sku)
                                # Precio desde el propio CSV o desde archivo de precios
                                price = prices.get(sku, 0) or prices.get(sku_norm, 0)
                                if price == 0 and csv_price:
                                    try:
                                        # Manejar formato europeo: 23.400 -> 23400
                                        price_str = str(csv_price).strip()
                                        # Si tiene formato X.XXX (miles con punto), quitamos el punto
                                        if re.match(r'^\d{1,3}\.\d{3}$', price_str):
                                            price_str = price_str.replace('.', '')
                                        price = float(re.sub(r'[^\d.]', '', price_str))
                                    except:
                                        pass

                                img = images.get(sku.upper(), '')
                                if not img:
                                    for k, v in images.items():
                                        if sku.upper() in k or k in sku.upper():
                                            img = v
                                            break

                                products.append({
                                    'sku': sku,
                                    'handle': sku.lower().replace(' ', '-'),
                                    'title_raw': title_raw,
                                    'title': self.normalize_title(title_raw),
                                    'price': price,
                                    'image': img,
                                    'system': self.detect_sistema(title_raw),
                                    'category': self.detect_pieza(title_raw),
                                    'compatible_models': self.detect_modelo(title_raw),
                                    'vendor': store_name
                                })
                    except Exception as e:
                        print(f'Error catalogo {f}: {e}')

        return products

    def process_store(self, store_name, save_to_kb_flag=True):
        """Procesa tienda completa con KB"""
        print(f'\n{"="*60}')
        print(f'PROCESANDO: {store_name}')
        print(f'{"="*60}')

        products = self.load_store_data(store_name)
        print(f'Productos cargados: {len(products)}')

        if not products:
            return []

        enriched_count = 0
        for i, p in enumerate(products):
            kb_matches = self.query_kb(p['title_raw'])
            products[i] = self.enrich_from_kb(p, kb_matches)
            if products[i].get('kb_enriched'):
                enriched_count += 1

        print(f'Enriquecidos con KB: {enriched_count}/{len(products)} ({100*enriched_count//len(products) if products else 0}%)')

        if save_to_kb_flag:
            saved = self.save_to_kb(products, store_name)
            print(f'Guardados en KB: {saved}')

        output_dir = BASE_DIR / store_name / 'output'
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f'{store_name}_kb_enriched.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print(f'Output: {output_file}')

        with_price = sum(1 for p in products if p.get('price', 0) > 0)
        with_image = sum(1 for p in products if p.get('image'))
        print(f'Con precio: {with_price}/{len(products)}')
        print(f'Con imagen: {with_image}/{len(products)}')

        return products


def main():
    import sys
    stores = sys.argv[1:] if len(sys.argv) > 1 else ['BARA']

    pipeline = KBPipeline()

    for store in stores:
        products = pipeline.process_store(store)

        enriched = [p for p in products if p.get('kb_enriched')]
        print(f'\n--- 5 PRODUCTOS ENRIQUECIDOS ({store}) ---')
        for p in enriched[:5]:
            print(f'\nSKU: {p.get("sku")}')
            print(f'  Titulo: {p.get("title")}')
            print(f'  Precio: ${p.get("price", 0):,.0f}')
            print(f'  Sistema: {p.get("system", "-")}')
            print(f'  Categoria: {p.get("category", "-")}')
            print(f'  KB Source: {p.get("kb_source", "-")}')
            print(f'  KB Fields: {p.get("kb_fields", [])}')
            print(f'  KB Distance: {p.get("kb_distance", "-")}')

if __name__ == '__main__':
    main()
