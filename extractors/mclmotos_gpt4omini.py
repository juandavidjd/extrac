#!/usr/bin/env python3
"""
MCLMOTOS Extractor - GPT-4o-mini (rate limits más altos)
- Delay 3s entre requests
- Batches de 10 páginas con pausa 30s
- Usa imágenes ya extraídas
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

import fitz
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')

PDF_PATH = '/mnt/volume_sfo3_01/profesion/ecosistema_odi/MCLMOTOS/catalogo/REPUESTOS CATÁLOGO 2025 ACTUALIZADO  16 DE DICIEMBRE.pdf'
OUTPUT_PATH = '/opt/odi/data/pdf_extracted/MCLMOTOS'
IMAGES_PATH = '/opt/odi/data/pdf_images/MCLMOTOS'
STORE_NAME = 'MCLMOTOS'

BATCH_SIZE = 10
BATCH_PAUSE = 30
REQUEST_DELAY = 3
MAX_RETRIES = 3

os.makedirs(OUTPUT_PATH, exist_ok=True)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

PROMPT = """Analiza esta página de catálogo de repuestos de motocicleta.
Extrae TODOS los productos en JSON:
{
  "products": [
    {"sku": "código", "title": "nombre limpio", "price": número_sin_formato, "category": "MOTOR|TRANSMISION|FRENOS|ELECTRICO|SUSPENSION|CARROCERIA|ACCESORIOS"}
  ]
}
Precio: "$15.000" = 15000. Sin precio = null. Solo JSON."""

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def page_to_base64(page, dpi=120):
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix=mat)
    return base64.b64encode(pix.tobytes("jpeg")).decode()

def analyze_page(page_b64, page_num):
    for attempt in range(MAX_RETRIES):
        try:
            r = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{page_b64}"}}
                ]}],
                max_tokens=2048,
                temperature=0.1
            )
            content = r.choices[0].message.content
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            return json.loads(content)
        except Exception as e:
            if '429' in str(e):
                wait = (2 ** attempt) * 5
                log(f"  Rate limit, waiting {wait}s")
                time.sleep(wait)
            else:
                log(f"  Error: {e}")
                time.sleep(REQUEST_DELAY)
    return {"products": []}

def get_images_for_page(page_num):
    """Get already extracted images for this page"""
    images = []
    for f in os.listdir(IMAGES_PATH):
        if f.startswith(f"{STORE_NAME}_p{page_num:03d}_"):
            images.append(os.path.join(IMAGES_PATH, f))
    return images

def main():
    log("="*50)
    log("MCLMOTOS - GPT-4o-mini Extraction")
    log("="*50)

    doc = fitz.open(PDF_PATH)
    total = len(doc)
    log(f"Pages: {total}")

    all_products = []

    for page_num in range(1, total + 1):
        log(f"[Page {page_num}/{total}]")

        page = doc[page_num - 1]
        page_b64 = page_to_base64(page)

        result = analyze_page(page_b64, page_num)
        products = result.get('products', [])

        # Associate images
        page_images = get_images_for_page(page_num)
        for i, p in enumerate(products):
            p['vendor'] = STORE_NAME
            p['page'] = page_num
            p['sku'] = p.get('sku') or f"{STORE_NAME}-P{page_num:03d}-{i+1:02d}"
            if i < len(page_images):
                p['image'] = page_images[i]

        all_products.extend(products)
        log(f"  Found: {len(products)} products")

        time.sleep(REQUEST_DELAY)

        # Batch pause
        if page_num % BATCH_SIZE == 0:
            log(f"  Batch pause {BATCH_PAUSE}s...")
            with open(f"{OUTPUT_PATH}/{STORE_NAME}_checkpoint.json", 'w') as f:
                json.dump(all_products, f, ensure_ascii=False, indent=2)
            time.sleep(BATCH_PAUSE)

    doc.close()

    # Save final
    with open(f"{OUTPUT_PATH}/{STORE_NAME}_extracted.json", 'w') as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

    log("")
    log("="*50)
    log(f"COMPLETE: {len(all_products)} products")
    log(f"With image: {sum(1 for p in all_products if p.get('image'))}")
    log("="*50)

if __name__ == '__main__':
    main()
