#!/usr/bin/env python3
"""
ODI PDF EXTRACTOR v4.0 - Extraccion Industrial de Catalogos
============================================================

FEATURES:
- PyMuPDF para extraer imagenes directamente del PDF
- Vision AI (GPT-4o o Gemini) para analizar paginas
- Asociacion imagen-producto por posicion en pagina
- Output JSON listo para Shopify

USO:
    python3 pdf_extractor_v4.py ARMOTOS
    python3 pdf_extractor_v4.py MCLMOTOS --pages 1-50
    python3 pdf_extractor_v4.py VITTON --provider gemini
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
from typing import List, Dict, Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image

# API clients
from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')

# Configuracion
BASE_PATH = '/mnt/volume_sfo3_01/profesion/ecosistema_odi'
OUTPUT_PATH = '/opt/odi/data/pdf_extracted'
IMAGES_PATH = '/opt/odi/data/pdf_images'

# PDFs por tienda
PDF_FILES = {
    'ARMOTOS': 'CATALOGO NOVIEMBRE V01-2025 NF.pdf',
    'MCLMOTOS': 'REPUESTOS CATÁLOGO 2025 ACTUALIZADO  16 DE DICIEMBRE.pdf',
    'VITTON': 'Catalogo digital Vitton sas-1.pdf',
    'CBI': 'CATALOGO-BITHOGA-2021-V7.pdf',
}

# Vision prompt para extraccion
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
      "position": "posicion aproximada en la pagina (arriba-izquierda, centro, etc)"
    }
  ],
  "page_category": "categoria general de la pagina si hay encabezado"
}

REGLAS:
- Titulo LIMPIO: sin codigos mezclados, profesional para e-commerce
- Precio: solo el numero, sin formato. Si dice "$15.000" -> 15000
- Si no hay precio visible, usar null
- SKU: codigo alfanumerico si existe
- Extraer TODOS los productos, no solo algunos

Responde SOLO con el JSON, sin texto adicional."""


class PDFExtractor:
    def __init__(self, store: str, provider: str = 'openai'):
        self.store = store
        self.provider = provider
        self.output_dir = os.path.join(OUTPUT_PATH, store)
        self.images_dir = os.path.join(IMAGES_PATH, store)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)

        # Init AI client
        if provider == 'openai':
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        elif provider == 'gemini':
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            self.model = genai.GenerativeModel('gemini-1.5-flash')

        self.products = []
        self.images_extracted = 0

    def get_pdf_path(self) -> str:
        if self.store not in PDF_FILES:
            raise ValueError(f"Store {self.store} not configured")
        return os.path.join(BASE_PATH, self.store, 'catalogo', PDF_FILES[self.store])

    def extract_images_from_page(self, page: fitz.Page, page_num: int) -> List[Dict]:
        """Extrae imagenes de una pagina usando PyMuPDF"""
        images = []
        img_list = page.get_images()

        for img_idx, img_info in enumerate(img_list):
            try:
                xref = img_info[0]
                base_image = page.parent.extract_image(xref)

                if base_image:
                    img_bytes = base_image["image"]
                    img_ext = base_image["ext"]

                    # Skip tiny images (likely icons/logos)
                    img = Image.open(BytesIO(img_bytes))
                    if img.width < 50 or img.height < 50:
                        continue

                    # Generate unique filename
                    img_hash = hashlib.md5(img_bytes).hexdigest()[:8]
                    filename = f"{self.store}_p{page_num:03d}_i{img_idx:02d}_{img_hash}.{img_ext}"
                    filepath = os.path.join(self.images_dir, filename)

                    # Save image
                    with open(filepath, 'wb') as f:
                        f.write(img_bytes)

                    # Get image position on page
                    for img_rect in page.get_image_rects(xref):
                        images.append({
                            'filename': filename,
                            'filepath': filepath,
                            'width': img.width,
                            'height': img.height,
                            'rect': [img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1],
                            'page': page_num
                        })
                        break

                    self.images_extracted += 1

            except Exception as e:
                print(f"    Error extracting image {img_idx}: {e}")

        return images

    def page_to_base64(self, page: fitz.Page, dpi: int = 150) -> str:
        """Convierte pagina PDF a imagen base64"""
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("jpeg")
        return base64.b64encode(img_bytes).decode('utf-8')

    def analyze_page_openai(self, page_b64: str) -> Dict:
        """Analiza pagina con GPT-4o Vision"""
        try:
            response = self.client.chat.completions.create(
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
            # Clean JSON from markdown
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'\s*```$', '', content)

            return json.loads(content)

        except Exception as e:
            print(f"    OpenAI error: {e}")
            return {"products": [], "error": str(e)}

    def analyze_page_gemini(self, page_b64: str) -> Dict:
        """Analiza pagina con Gemini Vision"""
        try:
            img_bytes = base64.b64decode(page_b64)
            img = Image.open(BytesIO(img_bytes))

            response = self.model.generate_content(
                [EXTRACTION_PROMPT, img],
                generation_config={"temperature": 0.1, "max_output_tokens": 4096}
            )

            content = response.text
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'\s*```$', '', content)

            return json.loads(content)

        except Exception as e:
            print(f"    Gemini error: {e}")
            return {"products": [], "error": str(e)}

    def match_images_to_products(self, products: List[Dict], images: List[Dict]) -> List[Dict]:
        """Asocia imagenes a productos por posicion en pagina"""
        if not images:
            return products

        page_height = 842  # A4 aprox

        for product in products:
            pos = product.get('position', '').lower()

            # Determinar zona vertical del producto
            if 'arriba' in pos or 'top' in pos:
                target_y = page_height * 0.25
            elif 'abajo' in pos or 'bottom' in pos:
                target_y = page_height * 0.75
            else:
                target_y = page_height * 0.5

            # Encontrar imagen mas cercana
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

    def process(self, pages_range: str = 'all'):
        """Procesa el PDF completo o rango de paginas"""
        pdf_path = self.get_pdf_path()
        print(f"\n{'='*60}")
        print(f"PDF EXTRACTOR v4.0 - {self.store}")
        print(f"{'='*60}")
        print(f"PDF: {pdf_path}")
        print(f"Provider: {self.provider}")
        print()

        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"Total pages: {total_pages}")

        # Parse pages range
        if pages_range == 'all':
            start_page, end_page = 1, total_pages
        else:
            parts = pages_range.split('-')
            start_page = int(parts[0])
            end_page = int(parts[1]) if len(parts) > 1 else start_page

        print(f"Processing pages: {start_page}-{end_page}")
        print()

        all_products = []

        for page_num in range(start_page, min(end_page + 1, total_pages + 1)):
            print(f"[Page {page_num}/{end_page}]")

            page = doc[page_num - 1]

            # 1. Extract images from page
            images = self.extract_images_from_page(page, page_num)
            print(f"  Images extracted: {len(images)}")

            # 2. Analyze page with Vision AI
            page_b64 = self.page_to_base64(page)

            if self.provider == 'openai':
                result = self.analyze_page_openai(page_b64)
            else:
                result = self.analyze_page_gemini(page_b64)

            products = result.get('products', [])
            print(f"  Products found: {len(products)}")

            # 3. Match images to products
            products = self.match_images_to_products(products, images)

            # 4. Add metadata
            for p in products:
                p['vendor'] = self.store
                p['page'] = page_num
                p['extracted_at'] = datetime.now().isoformat()
                if not p.get('sku'):
                    p['sku'] = f"{self.store}-P{page_num:03d}-{len(all_products)+1:04d}"

            all_products.extend(products)

            # Show sample
            if products:
                sample = products[0]
                print(f"  Sample: {sample.get('title', 'N/A')[:40]}... ${sample.get('price', 0)}")

            # Rate limit
            time.sleep(1)

        doc.close()

        # Save results
        output_file = os.path.join(self.output_dir, f'{self.store}_extracted.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, ensure_ascii=False, indent=2)

        print()
        print(f"{'='*60}")
        print(f"EXTRACTION COMPLETE")
        print(f"{'='*60}")
        print(f"Products: {len(all_products)}")
        print(f"Images: {self.images_extracted}")
        print(f"Output: {output_file}")
        print()

        # Show 5 sample products
        print("SAMPLE PRODUCTS:")
        print("-" * 40)
        for p in all_products[:5]:
            print(f"  SKU: {p.get('sku', 'N/A')}")
            print(f"  Title: {p.get('title', 'N/A')}")
            print(f"  Price: ${p.get('price', 0)}")
            print(f"  Image: {'YES' if p.get('image') else 'NO'}")
            print()

        return all_products


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 pdf_extractor_v4.py <STORE> [--pages 1-50] [--provider openai|gemini]")
        print("Stores: ARMOTOS, MCLMOTOS, VITTON, CBI")
        sys.exit(1)

    store = sys.argv[1].upper()
    pages = 'all'
    provider = 'openai'

    # Parse args
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == '--pages' and i + 1 < len(sys.argv):
            pages = sys.argv[i + 1]
        if arg == '--provider' and i + 1 < len(sys.argv):
            provider = sys.argv[i + 1]

    extractor = PDFExtractor(store, provider)
    extractor.process(pages)


if __name__ == '__main__':
    main()
