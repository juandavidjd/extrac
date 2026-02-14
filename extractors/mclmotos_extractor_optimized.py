#!/usr/bin/env python3
"""
MCLMOTOS PDF Extractor - Optimizado para PDF 313MB
- Batch de 5 páginas
- Retry con backoff exponencial
- Rate limit handling
"""

import os
import sys
import json
import base64
import re
import time
import hashlib
from pathlib import Path
from io import BytesIO
from datetime import datetime
from typing import List, Dict

import fitz  # PyMuPDF
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')

# Config
PDF_PATH = '/mnt/volume_sfo3_01/profesion/ecosistema_odi/MCLMOTOS/catalogo/REPUESTOS CATÁLOGO 2025 ACTUALIZADO  16 DE DICIEMBRE.pdf'
OUTPUT_PATH = '/opt/odi/data/pdf_extracted/MCLMOTOS'
IMAGES_PATH = '/opt/odi/data/pdf_images/MCLMOTOS'
STORE_NAME = 'MCLMOTOS'

# Optimized settings
BATCH_SIZE = 5  # Pages per batch checkpoint
MAX_RETRIES = 5
BASE_DELAY = 2  # seconds

os.makedirs(OUTPUT_PATH, exist_ok=True)
os.makedirs(IMAGES_PATH, exist_ok=True)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

EXTRACTION_PROMPT = """Analiza esta pagina de catalogo de repuestos de motocicleta.

EXTRAE TODOS los productos visibles en formato JSON:

{
  "products": [
    {
      "sku": "codigo del producto (si visible)",
      "title": "nombre LIMPIO y profesional del producto",
      "description": "descripcion tecnica breve",
      "price": precio como numero (sin $ ni puntos de miles, ej: 15000),
      "category": "categoria (MOTOR, TRANSMISION, FRENOS, ELECTRICO, SUSPENSION, CARROCERIA, ACCESORIOS)",
      "brand_fit": "marcas/modelos compatibles si se mencionan",
      "position": "posicion aproximada en la pagina"
    }
  ],
  "page_category": "categoria general de la pagina"
}

REGLAS:
- Titulo LIMPIO: sin codigos mezclados, profesional para e-commerce
- Precio: solo el numero. Si dice "$15.000" -> 15000
- Si no hay precio visible, usar null
- Extraer TODOS los productos visibles

Responde SOLO con el JSON."""


def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}", flush=True)


def extract_images_from_page(page, page_num):
    """Extrae imagenes de una pagina"""
    images = []
    try:
        img_list = page.get_images()
        for img_idx, img_info in enumerate(img_list):
            try:
                xref = img_info[0]
                base_image = page.parent.extract_image(xref)
                if base_image:
                    img_bytes = base_image["image"]
                    img_ext = base_image["ext"]

                    img = Image.open(BytesIO(img_bytes))
                    if img.width < 50 or img.height < 50:
                        continue

                    img_hash = hashlib.md5(img_bytes).hexdigest()[:8]
                    filename = f"{STORE_NAME}_p{page_num:03d}_i{img_idx:02d}_{img_hash}.{img_ext}"
                    filepath = os.path.join(IMAGES_PATH, filename)

                    with open(filepath, 'wb') as f:
                        f.write(img_bytes)

                    for img_rect in page.get_image_rects(xref):
                        images.append({
                            'filename': filename,
                            'filepath': filepath,
                            'rect': [img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1],
                            'page': page_num
                        })
                        break
            except Exception as e:
                pass
    except Exception as e:
        log(f"  Error extracting images: {e}")
    return images


def page_to_base64(page, dpi=150):
    """Convierte pagina a base64"""
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("jpeg")
    return base64.b64encode(img_bytes).decode('utf-8')


def analyze_page_with_retry(page_b64, page_num):
    """Analiza pagina con retry y backoff exponencial"""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": EXTRACTION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{page_b64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0.1
            )

            content = response.choices[0].message.content
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'\s*```$', '', content)

            return json.loads(content)

        except Exception as e:
            error_str = str(e)
            if '429' in error_str or 'rate' in error_str.lower():
                delay = BASE_DELAY * (2 ** attempt)
                log(f"  Rate limit hit, waiting {delay}s (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(delay)
            elif '500' in error_str or '503' in error_str:
                delay = BASE_DELAY * (2 ** attempt)
                log(f"  Server error, waiting {delay}s (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(delay)
            else:
                log(f"  API error: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(BASE_DELAY)
                else:
                    return {"products": [], "error": str(e)}

    return {"products": [], "error": "Max retries exceeded"}


def match_images_to_products(products, images):
    """Asocia imagenes a productos por posicion"""
    if not images:
        return products

    page_height = 842

    for product in products:
        pos = product.get('position', '').lower()

        if 'arriba' in pos or 'top' in pos:
            target_y = page_height * 0.25
        elif 'abajo' in pos or 'bottom' in pos:
            target_y = page_height * 0.75
        else:
            target_y = page_height * 0.5

        best_img = None
        best_dist = float('inf')

        for img in images:
            if img.get('used'):
                continue
            img_y = (img['rect'][1] + img['rect'][3]) / 2
            dist = abs(img_y - target_y)
            if dist < best_dist:
                best_dist = dist
                best_img = img

        if best_img and best_dist < page_height * 0.4:
            product['image'] = best_img['filepath']
            product['image_filename'] = best_img['filename']
            best_img['used'] = True

    return products


def main():
    log("="*60)
    log("MCLMOTOS PDF EXTRACTOR - OPTIMIZADO")
    log("="*60)
    log(f"PDF: {PDF_PATH}")
    log(f"Batch size: {BATCH_SIZE} pages")
    log(f"Max retries: {MAX_RETRIES}")
    log("")

    # Clear previous corrupted data
    old_json = os.path.join(OUTPUT_PATH, f'{STORE_NAME}_extracted.json')
    if os.path.exists(old_json):
        os.rename(old_json, old_json + '.backup')
        log("Backed up previous extraction")

    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    log(f"Total pages: {total_pages}")
    log("")

    all_products = []
    total_images = 0

    for page_num in range(1, total_pages + 1):
        log(f"[Page {page_num}/{total_pages}]")

        page = doc[page_num - 1]

        # Extract images
        images = extract_images_from_page(page, page_num)
        total_images += len(images)
        log(f"  Images: {len(images)}")

        # Analyze with Vision AI
        page_b64 = page_to_base64(page)
        result = analyze_page_with_retry(page_b64, page_num)

        products = result.get('products', [])
        log(f"  Products: {len(products)}")

        # Match images
        products = match_images_to_products(products, images)

        # Add metadata
        for p in products:
            p['vendor'] = STORE_NAME
            p['page'] = page_num
            p['extracted_at'] = datetime.now().isoformat()
            if not p.get('sku'):
                p['sku'] = f"{STORE_NAME}-P{page_num:03d}-{len(all_products)+1:04d}"

        all_products.extend(products)

        # Show sample
        if products:
            sample = products[0]
            price_str = f"${sample.get('price', 0)}" if sample.get('price') else "N/A"
            log(f"  Sample: {sample.get('title', 'N/A')[:35]}... {price_str}")

        # Checkpoint every BATCH_SIZE pages
        if page_num % BATCH_SIZE == 0:
            checkpoint_file = os.path.join(OUTPUT_PATH, f'{STORE_NAME}_checkpoint_p{page_num}.json')
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(all_products, f, ensure_ascii=False, indent=2)
            log(f"  Checkpoint saved: {len(all_products)} products")

        # Rate limit pause
        time.sleep(1.5)

    doc.close()

    # Save final results
    output_file = os.path.join(OUTPUT_PATH, f'{STORE_NAME}_extracted.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

    # Stats
    with_price = sum(1 for p in all_products if p.get('price'))
    with_image = sum(1 for p in all_products if p.get('image'))

    log("")
    log("="*60)
    log("EXTRACTION COMPLETE")
    log("="*60)
    log(f"Total products: {len(all_products)}")
    log(f"With price: {with_price} ({round(with_price/len(all_products)*100) if all_products else 0}%)")
    log(f"With image: {with_image} ({round(with_image/len(all_products)*100) if all_products else 0}%)")
    log(f"Total images: {total_images}")
    log(f"Output: {output_file}")
    log("")

    # Sample products
    log("SAMPLE PRODUCTS:")
    log("-" * 40)
    for p in all_products[:5]:
        log(f"  SKU: {p.get('sku', 'N/A')}")
        log(f"  Title: {p.get('title', 'N/A')[:50]}")
        log(f"  Price: ${p.get('price', 0)}")
        log(f"  Image: {'YES' if p.get('image') else 'NO'}")
        log("")


if __name__ == '__main__':
    main()
