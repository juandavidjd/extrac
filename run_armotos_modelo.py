#!/usr/bin/env python3
"""ARMOTOS TIENDA MODELO - Pipeline Completo con KB Chunks"""
import os, sys, json, time, base64, random
from pathlib import Path
from io import BytesIO

sys.stdout.reconfigure(line_buffering=True)

from dotenv import load_dotenv
load_dotenv('/opt/odi/.env')

import google.generativeai as genai
from PIL import Image
import fitz
import requests
import chromadb

PDF_PATH = '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Armotos/CATALOGO NOVIEMBRE V01-2025 NF.pdf'
OUTPUT_DIR = Path('/opt/odi/data/ARMOTOS')
STORE = 'ARMOTOS'
BATCH_SIZE = 10
SLEEP_BETWEEN_BATCHES = 3
MAX_RETRIES = 2

genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

SHOP = os.environ.get('ARMOTOS_SHOP')
TOKEN = os.environ.get('ARMOTOS_TOKEN')
SHOPIFY_URL = f'https://{SHOP}/admin/api/2025-01'

(OUTPUT_DIR / 'images').mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / 'json').mkdir(parents=True, exist_ok=True)

all_products = []
all_kb_chunks = []
seen_skus = set()
stats = {'pages': 0, 'products': 0, 'with_image': 0, 'skipped_dup': 0}

EXTRACTION_PROMPT = """Analiza esta pagina de catalogo de motos y extrae TODOS los productos visibles.

Para CADA producto encontrado, devuelve JSON:
{
  "products": [
    {
      "sku": "Codigo/referencia (ej: ARM-001). NO uses precio ni numero de pagina",
      "title": "Nombre completo del producto",
      "description": "Descripcion tecnica si existe",
      "price": precio numerico en COP (sin puntos),
      "category": "Categoria (Filtros, Frenos, Suspension, Electrico, Motor, Transmision, Carroceria)",
      "compatible_models": ["Lista de motos compatibles"],
      "specifications": {"spec1": "valor1"},
      "has_photo": true/false,
      "photo_bbox": [x1, y1, x2, y2] si has_photo=true (0-1)
    }
  ]
}

SOLO fotos REALES (textura, sombras). NO celdas de tabla ni bloques de color.
Devuelve JSON valido."""

def validate_image(img_bytes):
    if len(img_bytes) < 10240: return False, 'small'
    try:
        img = Image.open(BytesIO(img_bytes))
        w, h = img.size
        if w < 100 or h < 100: return False, 'lowres'
        if max(w/h, h/w) > 5: return False, 'aspect'
        img_small = img.resize((50, 50)).convert('RGB')
        pixels = list(img_small.getdata())
        counts = {}
        for p in pixels: counts[p] = counts.get(p, 0) + 1
        if max(counts.values()) / len(pixels) > 0.8: return False, 'solid'
        return True, 'ok'
    except: return False, 'error'

def generate_ficha_360(p):
    title = p.get('title', 'Producto')
    desc = p.get('description', '')
    specs = p.get('specifications', {})
    compat = p.get('compatible_models', [])
    cat = p.get('category', 'General')
    price = p.get('price', 0)
    sku = p.get('sku', '')

    specs_html = '<ul>' + ''.join([f'<li><b>{k}:</b> {v}</li>' for k,v in specs.items()]) + '</ul>' if specs else '<p>Consultar especificaciones.</p>'
    compat_text = ', '.join(compat) if compat else 'Multiples modelos'

    return f"""<div class="ficha-360">
<h3>Descripcion</h3>
<p>{desc if desc else title}</p>
<h3>Especificaciones</h3>
{specs_html}
<h3>Compatibilidad</h3>
<p>{compat_text}</p>
<h3>Categoria</h3>
<p>{cat}</p>
<h3>Garantia</h3>
<p>Producto garantizado por ARMOTOS. Ref: {sku}</p>
<h3>Envio</h3>
<p>Envio a toda Colombia.</p>
</div>"""

def create_kb_chunk(p):
    sku = p.get('sku', '')
    title = p.get('title', '')
    cat = p.get('category', 'General')
    price = p.get('price', 0)
    compat = ', '.join(p.get('compatible_models', [])) or 'multiples modelos'
    specs = '. '.join([f'{k}: {v}' for k,v in p.get('specifications', {}).items()])
    text = f"Producto: {title}. Categoria: {cat}. Compatibilidad: {compat}. {specs}. Precio: ${price:,.0f} COP. Referencia: {sku}. Proveedor: ARMOTOS."
    return {'id': f'kb_{STORE}_{sku}', 'text': text, 'metadata': {'type': 'kb_chunk', 'store': STORE, 'sku': sku, 'category': cat, 'price': int(price) if price else 0, 'title': title}}

def create_product_doc(p):
    sku = p.get('sku', '')
    title = p.get('title', '')
    price = p.get('price', 0)
    text = f"{title} SKU:{sku} ${price:,.0f} ARMOTOS"
    return {'id': f'prod_{STORE}_{sku}', 'text': text, 'metadata': {'type': 'product', 'store': STORE, 'sku': sku, 'price': int(price) if price else 0, 'title': title}}

def extract_page(doc, page_num):
    global stats
    page = doc[page_num]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img_bytes = pix.tobytes('png')
    img = Image.open(BytesIO(img_bytes))

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = model.generate_content([EXTRACTION_PROMPT, img])
            text = response.text.strip()
            # Clean markdown
            if '```' in text:
                parts = text.split('```')
                if len(parts) >= 2:
                    text = parts[1]
                    if text.startswith('json'):
                        text = text[4:]
            text = text.strip()
            data = json.loads(text)
            products = data.get('products', [])

            page_products = []
            for p in products:
                sku = p.get('sku', '')
                if not sku or sku in seen_skus:
                    if sku in seen_skus: stats['skipped_dup'] += 1
                    continue
                seen_skus.add(sku)

                if p.get('has_photo') and p.get('photo_bbox'):
                    bbox = p['photo_bbox']
                    try:
                        pw, ph = pix.width, pix.height
                        x1, y1 = int(bbox[0]*pw), int(bbox[1]*ph)
                        x2, y2 = int(bbox[2]*pw), int(bbox[3]*ph)
                        crop = Image.open(BytesIO(img_bytes)).crop((x1, y1, x2, y2))
                        crop_io = BytesIO()
                        crop.save(crop_io, 'PNG')
                        crop_bytes = crop_io.getvalue()
                        valid, _ = validate_image(crop_bytes)
                        if valid:
                            safe_sku = sku.replace("/","_").replace("\\","_").replace(" ","_")
                            img_path = OUTPUT_DIR / 'images' / f'{safe_sku}.png'
                            with open(img_path, 'wb') as f: f.write(crop_bytes)
                            p['image_path'] = str(img_path)
                            stats['with_image'] += 1
                    except Exception as e:
                        pass

                p['body_html'] = generate_ficha_360(p)
                all_products.append(p)
                all_kb_chunks.append(create_kb_chunk(p))
                page_products.append(p)
                stats['products'] += 1
            return page_products
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(2)
            else:
                print(f'  ERROR p{page_num}: {e}')
                return []
    return []

def audit_products(products, count=10):
    sample = random.sample(products, min(count, len(products)))
    print(f'\n{"="*60}')
    print(f'AUDITORIA PRE-UPLOAD: {len(sample)} productos')
    print('='*60)
    for i, p in enumerate(sample, 1):
        print(f'\n[{i}] SKU: {p.get("sku")} | Precio: ${p.get("price",0):,.0f}')
        print(f'    {p.get("title","")[:60]}')
        print(f'    Cat: {p.get("category")} | Img: {"SI" if p.get("image_path") else "NO"}')
        compat = p.get('compatible_models', [])
        if compat:
            print(f'    Compat: {", ".join(compat[:3])}')
    print('='*60)
    return sample

def upload_to_shopify(products):
    print(f'\nSubiendo {len(products)} a Shopify...')
    headers = {'X-Shopify-Access-Token': TOKEN, 'Content-Type': 'application/json'}
    uploaded, errors = 0, 0
    for i, p in enumerate(products):
        try:
            data = {
                'product': {
                    'title': p.get('title'),
                    'body_html': p.get('body_html',''),
                    'vendor': STORE,
                    'product_type': p.get('category','General'),
                    'variants': [{
                        'price': str(p.get('price',0)),
                        'sku': p.get('sku',''),
                        'inventory_management': 'shopify',
                        'inventory_quantity': 10
                    }]
                }
            }
            if p.get('image_path') and os.path.exists(p['image_path']):
                with open(p['image_path'], 'rb') as f:
                    data['product']['images'] = [{'attachment': base64.b64encode(f.read()).decode()}]
            resp = requests.post(f'{SHOPIFY_URL}/products.json', headers=headers, json=data)
            if resp.status_code == 201:
                uploaded += 1
            else:
                errors += 1
                if errors <= 5:
                    print(f'  Error {p.get("sku")}: {resp.status_code} - {resp.text[:100]}')
            if uploaded % 100 == 0:
                print(f'  Subidos: {uploaded}/{len(products)}')
            if i % 2 == 0:
                time.sleep(0.5)
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f'  Exception {p.get("sku")}: {e}')
    print(f'Shopify: {uploaded} OK, {errors} errores')
    return uploaded, errors

def index_chromadb(products, kb_chunks):
    print(f'\nIndexando en ChromaDB...')
    client = chromadb.HttpClient('localhost', 8000)
    col = client.get_or_create_collection('odi_ind_motos')

    # Delete existing ARMOTOS docs first
    try:
        existing = col.get(where={'store': 'ARMOTOS'}, include=[])
        if existing['ids']:
            print(f'  Eliminando {len(existing["ids"])} docs ARMOTOS existentes...')
            col.delete(ids=existing['ids'])
    except:
        pass

    prod_ids = [f'prod_{STORE}_{p.get("sku")}' for p in products]
    prod_texts = [f'{p.get("title")} SKU:{p.get("sku")} ${p.get("price",0):,.0f} ARMOTOS' for p in products]
    prod_metas = [{'type':'product','store':STORE,'sku':p.get('sku',''),'price':int(p.get('price',0)) if p.get('price') else 0,'title':p.get('title',''),'category':p.get('category','General')} for p in products]

    kb_ids = [k['id'] for k in kb_chunks]
    kb_texts = [k['text'] for k in kb_chunks]
    kb_metas = [k['metadata'] for k in kb_chunks]

    # Batch upsert
    for i in range(0, len(prod_ids), 100):
        col.upsert(ids=prod_ids[i:i+100], documents=prod_texts[i:i+100], metadatas=prod_metas[i:i+100])
    for i in range(0, len(kb_ids), 100):
        col.upsert(ids=kb_ids[i:i+100], documents=kb_texts[i:i+100], metadatas=kb_metas[i:i+100])

    print(f'ChromaDB: {len(prod_ids)} products + {len(kb_ids)} kb_chunks = {len(prod_ids)+len(kb_ids)} total')
    return len(prod_ids) + len(kb_ids)

def main():
    print('='*60)
    print('ARMOTOS TIENDA MODELO - Pipeline Completo')
    print('='*60)
    print(f'PDF: {PDF_PATH}')
    print(f'Output: {OUTPUT_DIR}')

    doc = fitz.open(PDF_PATH)
    total = len(doc)
    print(f'Paginas totales: {total}')

    start_time = time.time()

    for batch in range(0, total, BATCH_SIZE):
        end = min(batch + BATCH_SIZE, total)
        batch_num = batch // BATCH_SIZE + 1
        print(f'\nBatch {batch_num}: paginas {batch+1}-{end}')

        for page_num in range(batch, end):
            extract_page(doc, page_num)
            stats['pages'] += 1

        print(f'  Acumulado: {stats["products"]} productos, {stats["with_image"]} con imagen')

        # Progress report every 50 pages
        if stats['pages'] % 50 == 0:
            elapsed = time.time() - start_time
            rate = stats['pages'] / elapsed * 60
            print(f'\n>>> PROGRESO: {stats["pages"]}/{total} paginas ({rate:.0f} pags/min)')
            print(f'    Productos: {stats["products"]} | Imagenes: {stats["with_image"]} | Dups: {stats["skipped_dup"]}')

        if end < total:
            time.sleep(SLEEP_BETWEEN_BATCHES)

    doc.close()
    elapsed = time.time() - start_time

    print(f'\n{"="*60}')
    print('EXTRACCION COMPLETA')
    print(f'  Tiempo: {elapsed:.0f}s ({elapsed/60:.1f} min)')
    print(f'  Paginas: {stats["pages"]}')
    print(f'  Productos: {stats["products"]}')
    print(f'  Con imagen: {stats["with_image"]}')
    print(f'  Duplicados saltados: {stats["skipped_dup"]}')
    print('='*60)

    # Save JSONs
    with open(OUTPUT_DIR / 'json' / 'products.json', 'w') as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    print(f'\nJSON: {OUTPUT_DIR}/json/products.json')

    with open(OUTPUT_DIR / 'json' / 'kb_chunks.json', 'w') as f:
        json.dump(all_kb_chunks, f, indent=2, ensure_ascii=False)
    print(f'KB: {OUTPUT_DIR}/json/kb_chunks.json')

    # Audit
    if all_products:
        audit_products(all_products, 10)

        print('\n' + '='*60)
        print('FASE 2: UPLOAD A SHOPIFY + CHROMADB')
        print('='*60)

        # Upload to Shopify
        uploaded, errors = upload_to_shopify(all_products)

        # Index to ChromaDB
        indexed = index_chromadb(all_products, all_kb_chunks)

        print('\n' + '='*60)
        print('ARMOTOS TIENDA MODELO - COMPLETADO')
        print('='*60)
        print(f'  Shopify: {uploaded} productos')
        print(f'  ChromaDB: {indexed} documentos')
        print(f'  Imagenes: {stats["with_image"]}')
        print('='*60)

if __name__ == '__main__':
    main()
