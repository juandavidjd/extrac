#!/usr/bin/env python3
"""
ODI Pipeline Service - Los 6 Pasos del Metabolismo
==================================================
Servicio que ejecuta el pipeline completo de catálogo a Shopify.

Pipeline:
  1. EXTRAER    - Vision AI extrae productos del PDF
  2. NORMALIZAR - M6.2 normaliza nombres y categorías
  3. ENRIQUECER - LLM genera descripciones SEO
  4. FITMENT    - Asigna compatibilidades moto-pieza
  5. SHOPIFY    - Crea/actualiza productos en tienda
  6. CAMPAÑAS   - Genera assets para Meta/Google

API Endpoints:
  POST /pipeline/start        - Inicia pipeline
  GET  /pipeline/status/{id}  - Estado del job
  GET  /pipeline/jobs         - Lista jobs
  POST /pipeline/retry/{id}   - Reintentar job fallido

Uso:
    uvicorn odi_pipeline_service:app --host 0.0.0.0 --port 8804
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import base64

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Security: Input sanitization
import sys
sys.path.insert(0, "/opt/odi/core")
from odi_sanitizer import validate_llm_products, sanitize_html

# Security: Rate limiting
import sys
sys.path.insert(0, "/opt/odi/core")
from odi_rate_limiter import RateLimitMiddleware
import httpx

# ============================================
# VALIDACIONES ENTRE PASOS
# ============================================
def validate_extraction(products: list) -> tuple:
    if not products:
        return False, "0 productos extraidos"
    sin_sku = [p for p in products if not p.get("sku")]
    if len(sin_sku) > len(products) * 0.1:
        return False, f"{len(sin_sku)} productos sin SKU (>10%)"
    return True, f"{len(products)} productos OK"

def validate_normalization(products: list) -> tuple:
    issues = []
    long_titles = [p for p in products if len(p.get("title", "")) > 60]
    if long_titles:
        issues.append(f"{len(long_titles)} titulos >60 chars")
    no_prefix = [p for p in products if not any(p.get("title", "").startswith(x) for x in ["Empaque", "Kit", "Conector"])]
    if no_prefix and len(no_prefix) > len(products) * 0.05:
        issues.append(f"{len(no_prefix)} sin prefijo tipo")
    if issues:
        return False, "; ".join(issues)
    return True, "Titulos OK"

def validate_enrichment(products: list) -> tuple:
    defaults = [p for p in products if "Default" in str(p.get("description", ""))]
    if defaults and len(defaults) > len(products) * 0.1:
        return False, f"{len(defaults)} con descripcion generica"
    return True, "Enriquecimiento OK"



# OpenAI for Vision
from openai import OpenAI

# Image extraction from PDFs
sys.path.insert(0, "/opt/odi/odi_production/extractors")
try:
    from odi_vision_extractor_v3 import VisionProductDetector
    VISION_DETECTOR_AVAILABLE = True
except ImportError:
    VISION_DETECTOR_AVAILABLE = False
    VisionProductDetector = None

load_dotenv("/opt/odi/.env")
# Image matcher for local images
sys.path.insert(0, "/opt/odi/pipeline")
try:
    from odi_image_matcher import match_products_with_local_images
    IMAGE_MATCHER_AVAILABLE = True
except:
    IMAGE_MATCHER_AVAILABLE = False


# ============================================
# CONFIGURACIÓN
# ============================================
def load_shopify_stores():
    """Load Shopify stores from brand JSON files."""
    import json
    import os
    stores = {}
    brands_dir = '/opt/odi/data/brands'
    if os.path.exists(brands_dir):
        for f in os.listdir(brands_dir):
            if f.endswith('.json'):
                try:
                    with open(os.path.join(brands_dir, f)) as fh:
                        data = json.load(fh)
                    name = f.replace('.json', '').upper()
                    if 'shopify' in data:
                        stores[name] = {
                            'shop': data['shopify'].get('shop'),
                            'token': data['shopify'].get('token')
                        }
                except Exception as e:
                    pass
    return stores

SHOPIFY_STORES = load_shopify_stores()
# Fallback to env vars for stores not in JSON
_ENV_STORES = {
    "KAIQI": {
        "shop": os.getenv("KAIQI_SHOP"),
        "token": os.getenv("KAIQI_TOKEN"),
    },
    "JAPAN": {
        "shop": os.getenv("JAPAN_SHOP"),
        "token": os.getenv("JAPAN_TOKEN"),
    },
    "YOKOMAR": {
        "shop": os.getenv("YOKOMAR_SHOP"),
        "token": os.getenv("YOKOMAR_TOKEN"),
    },
    "IMBRA": {
        "shop": os.getenv("IMBRA_SHOP"),
        "token": os.getenv("IMBRA_TOKEN"),
    },
    "BARA": {
        "shop": os.getenv("BARA_SHOP"),
        "token": os.getenv("BARA_TOKEN"),
    },
    "DUNA": {
        "shop": os.getenv("DUNA_SHOP"),
        "token": os.getenv("DUNA_TOKEN"),
    },
    "DFG": {
        "shop": os.getenv("DFG_SHOP"),
        "token": os.getenv("DFG_TOKEN"),
    },
    "LEO": {
        "shop": os.getenv("LEO_SHOP"),
        "token": os.getenv("LEO_TOKEN"),
    },
    "STORE": {
        "shop": os.getenv("STORE_SHOP"),
        "token": os.getenv("STORE_TOKEN"),
    },
    "VAISAND": {
        "shop": os.getenv("VAISAND_SHOP"),
        "token": os.getenv("VAISAND_TOKEN"),
    },
    "OH_IMPORTACIONES": {
        "shop": os.getenv("OH_IMPORTACIONES_SHOP"),
        "token": os.getenv("OH_IMPORTACIONES_TOKEN"),
    },
    "ARMOTOS": {
        "shop": os.getenv("ARMOTOS_SHOP"),
        "token": os.getenv("ARMOTOS_TOKEN"),
    },
    "MCLMOTOS": {
        "shop": os.getenv("MCLMOTOS_SHOP"),
        "token": os.getenv("MCLMOTOS_TOKEN"),
    },
    "VITTON": {
        "shop": os.getenv("VITTON_SHOP"),
        "token": os.getenv("VITTON_TOKEN"),
    },
    "CBI": {
        "shop": os.getenv("CBI_SHOP"),
        "token": os.getenv("CBI_TOKEN"),
    },

}

JOBS_PATH = Path("/opt/odi/data/pipeline_jobs")
JOBS_PATH.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# OpenAI Client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================
# MODELOS
# ============================================
class PipelineStage(Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    NORMALIZING = "normalizing"
    ENRICHING = "enriching"
    FITTING = "fitting"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineRequest(BaseModel):
    job_id: str
    empresa: str
    shop_key: Optional[str] = None
    source_file: str
    images_folder: str


class Product(BaseModel):
    sku: Optional[str] = None
    title: str
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    compatibility: List[str] = []
    images: List[str] = []
    variants: List[Dict[str, Any]] = []


class PipelineJob(BaseModel):
    job_id: str
    empresa: str
    shop_key: Optional[str]
    source_file: str
    images_folder: str
    stage: str = PipelineStage.PENDING.value
    products: List[Dict[str, Any]] = []
    products_count: int = 0
    uploaded_count: int = 0
    errors: List[str] = []
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = {}


# ============================================
# EXTRACTORES
# ============================================
class VisionExtractor:
    """Extrae productos de PDFs usando Vision AI."""

    EXTRACTION_PROMPT = """Analiza esta página de catálogo de repuestos de motos.
Extrae TODOS los productos visibles con el siguiente formato JSON:

{
  "products": [
    {
      "sku": "código o referencia si visible",
      "title": "nombre del producto",
      "price": precio numérico o null,
      "category": "categoría (ej: frenos, transmisión, eléctrico)",
      "brand": "marca si visible",
      "compatibility": ["lista de motos compatibles si se menciona"]
    }
  ]
}

Reglas:
- Extrae TODOS los productos, no solo algunos
- El precio debe ser numérico (sin símbolo de moneda)
- Si no hay precio visible, usa null
- La categoría debe ser genérica (frenos, aceites, filtros, etc)
- Si ves referencias cruzadas o compatibilidad, inclúyelas

Responde SOLO con el JSON, sin explicaciones."""

    async def extract_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extrae productos de un PDF."""
        import pdfplumber

        all_products = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages[:50]):  # Máximo 50 páginas
                    log.info(f"  Extracting page {i+1}/{len(pdf.pages)}")

                    # Convertir página a imagen
                    img = page.to_image(resolution=150)
                    img_bytes = img.original.tobytes()

                    # También extraer texto directo
                    text = page.extract_text() or ""

                    # Si hay mucho texto, usar OCR simple
                    if len(text) > 100:
                        products = self._extract_from_text(text)
                        all_products.extend(products)
                    else:
                        # Usar Vision API para páginas con imágenes
                        products = await self._extract_with_vision(pdf_path, i)
                        all_products.extend(products)

        except Exception as e:
            log.error(f"PDF extraction error: {e}")

        return all_products

    def _extract_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extrae productos de texto usando LLM."""
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.EXTRACTION_PROMPT},
                    {"role": "user", "content": f"Texto del catálogo:\n\n{text[:8000]}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return validate_llm_products(result.get("products", []))

        except Exception as e:
            log.error(f"Text extraction error: {e}")
            return []

    async def _extract_with_vision(self, pdf_path: str, page_num: int) -> List[Dict[str, Any]]:
        """Extrae productos usando Vision API."""
        try:
            import pdf2image

            images = pdf2image.convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1, dpi=150)
            if not images:
                return []

            # Convertir a base64
            import io
            buffer = io.BytesIO()
            images[0].save(buffer, format="PNG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode()

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.EXTRACTION_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=4096
            )

            # Parsear respuesta
            content = response.choices[0].message.content
            # Limpiar posibles markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content)
            return validate_llm_products(result.get("products", []))

        except Exception as e:
            log.error(f"Vision extraction error: {e}")
            return []


    async def extract_from_excel(self, excel_path: str) -> List[Dict[str, Any]]:
        """Extrae productos de un Excel de lista de precios."""
        import pandas as pd
        
        all_products = []
        
        try:
            df = pd.read_excel(excel_path, sheet_name=0, header=None)
            log.info(f"  Excel loaded: {len(df)} rows")
            
            categoria_actual = None
            
            for idx, row in df.iterrows():
                if idx < 2:
                    continue
                
                col0 = row[0] if len(row) > 0 else None
                col1 = row[1] if len(row) > 1 else None
                col2 = row[2] if len(row) > 2 else None
                col3 = row[3] if len(row) > 3 else None
                
                if pd.notna(col1) and str(col1).strip().upper() == "CODIGO":
                    continue
                
                if pd.isna(col1) or not str(col1).strip():
                    if pd.notna(col0) and str(col0).strip():
                        categoria_actual = str(col0).strip()
                    continue
                
                codigo = str(col1).strip()
                descripcion = str(col2).strip() if pd.notna(col2) else ""
                marca = str(col0).strip() if pd.notna(col0) else ""
                
                try:
                    precio = float(col3) if pd.notna(col3) else 0
                except:
                    precio = 0
                
                if not descripcion or precio <= 0:
                    continue
                
                all_products.append({
                    "sku": codigo,
                    "title": descripcion,
                    "price": precio,
                    "category": categoria_actual,
                    "brand": marca,
                    "compatibility": []
                })
            
            log.info(f"  Extracted {len(all_products)} products from Excel")
            
        except Exception as e:
            log.error(f"Excel extraction error: {e}")
        
        return all_products


    async def extract_from_csv(self, csv_path: str, delimiter: str = ';') -> List[Dict[str, Any]]:
        """Extrae productos de un CSV (ej: Bara, DFG)."""
        import csv
        import re
        
        all_products = []
        
        # Patrones de motos para compatibilidad
        MOTO_PATTERNS = [
            r'(AKT\s*\d+\w*)', r'(NKD\s*\d*)', r'(TTR\s*\d*)', r'(TTX\s*\d*)',
            r'(CR\s*\d+)', r'(DS\s*\d+)', r'(PULSAR\s*\d+\w*)', r'(NS\s*\d+)',
            r'(RS\s*\d+)', r'(DISCOVER\s*\d+\w*)', r'(BOXER\s*\w*)', r'(PLATINO\s*\w*)',
            r'(DOMINAR\s*\d+\w*)', r'(CT\s*\d+)', r'(CB\s*\d+\w*)', r'(CBR\s*\d+\w*)',
            r'(NXR\s*\d+\w*)', r'(XR\s*\d+\w*)', r'(ECO\s*\d+\w*)', r'(SPLENDOR\s*\w*)',
            r'(TORNADO\s*\d*)', r'(TITAN\s*\d+\w*)', r'(BROSS\s*\d*)', r'(WAVE\s*\d*)',
            r'(FZ\s*\d+\w*)', r'(YBR\s*\d+\w*)', r'(FAZER\s*\d+\w*)', r'(MT\s*\d+)',
            r'(R15\s*\w*)', r'(NMAX\s*\d*)', r'(BWS\s*\d+\w*)', r'(CRYPTON\s*\d*)',
            r'(LIBERO\s*\d+\w*)', r'(XTZ\s*\d+\w*)', r'(GIXXER\s*\d+\w*)', r'(GN\s*\d+\w*)',
            r'(BEST\s*\d+\w*)', r'(DR\s*\d+\w*)', r'(HAYATE\s*\d*)', r'(TVS\s*\d+\w*)',
            r'(APACHE\s*\w*)', r'(RTR\s*\d+\w*)', r'(AGILITY\s*\d+\w*)', r'(KYMCO\s*\d*)',
            r'(KLX\s*\d+\w*)', r'(NINJA\s*\d*)', r'(SIGMA\s*\d+\w*)', r'(FLEX\s*\d+\w*)',
            r'(JET\s*\d+\w*)', r'(XM\s*\d+\w*)', r'(CARGUERO\s*\w*)', r'(MOTOCARRO\s*\w*)',
        ]
        
        def extract_compat(title: str) -> List[str]:
            motos = []
            title_upper = title.upper()
            for p in MOTO_PATTERNS:
                matches = re.findall(p, title_upper)
                motos.extend([m.strip() for m in matches if m.strip() and len(m.strip()) >= 2])
            return list(dict.fromkeys(motos))
        
        try:
            # Detectar encoding
            for enc in ['utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    with open(csv_path, 'r', encoding=enc) as f:
                        reader = csv.DictReader(f, delimiter=delimiter)
                        rows = list(reader)
                        break
                except:
                    rows = []
            
            log.info(f"  CSV loaded: {len(rows)} rows")
            
            for row in rows:
                # Detectar columnas (soporta CODIGO/SKU, DESCRIPCION/Producto, PRECIO/Price)
                sku = row.get('CODIGO') or row.get('SKU') or row.get('Codigo') or row.get('sku') or ''
                title = row.get('DESCRIPCION') or row.get('Producto') or row.get('PRODUCTO') or row.get('titulo') or ''
                price_str = row.get('PRECIO') or row.get('Price') or row.get('PVP') or row.get('precio') or '0'
                
                sku = str(sku).strip()
                title = str(title).strip()
                
                # Limpiar precio
                price_clean = re.sub(r'[^\d.,]', '', str(price_str).replace('.', '').replace(',', '.'))
                try:
                    price = float(price_clean) if price_clean else 0
                except:
                    price = 0
                
                if not title or not sku:
                    continue
                
                # V22 FIX: NUNCA price=1.0, usar status=draft
                _status = 'active'
                if price <= 0:
                    _status = 'draft'  # No price = not ready to sell
                
                compatibility = extract_compat(title)
                
                all_products.append({
                    'sku': sku,
                    'title': title[:100],
                    'price': price if price > 0 else 0,
                    'category': None,
                    'brand': None,
                    'compatibility': compatibility,
                    'status': _status  # V22: draft if no price
                })
            
            log.info(f"  Extracted {len(all_products)} products from CSV")
            
        except Exception as e:
            log.error(f"CSV extraction error: {e}")
        
        return all_products

    async def extract_from_json(self, json_path: str, empresa: str) -> List[Dict[str, Any]]:
        """Extract products from JSON file (orden_maestra_v6 format)."""
        import json as json_lib
        products = []
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json_lib.load(f)
            
            # Handle both list and dict formats
            items = data if isinstance(data, list) else data.get('products', [])
            
            for item in items:
                sku = item.get('sku') or item.get('SKU') or ''
                if isinstance(item.get('variants'), list) and item['variants']:
                    sku = sku or item['variants'][0].get('sku', '')
                
                title = item.get('title') or item.get('TITULO') or item.get('producto', '')
                price = item.get('price') or item.get('PRECIO') or 0
                if isinstance(item.get('variants'), list) and item['variants']:
                    price = price or item['variants'][0].get('price', 0)
                
                # Extract compatibility from tags
                tags = item.get('tags', '')
                compat_list = []
                if isinstance(tags, str) and tags:
                    compat_list = [t.strip() for t in tags.split(',') if t.strip()]
                
                products.append({
                    'sku': str(sku).strip() if sku else f'SKU-{len(products)+1}',
                    'title': str(title).strip(),
                    'price': float(price) if price else 0,  # V22: 0 not 1.0
                    'compatibility': compat_list,
                    'empresa': empresa,
                    'source_type': 'json',
                    'body_html': item.get('body_html', ''),
                    'original_data': item
                })
            
            log.info(f"  Extracted {len(products)} products from JSON")
            
        except Exception as e:
            log.error(f"JSON extraction error: {e}")
        
        return products

    async def extract_images_from_pdf(self, pdf_path: str, store_name: str, pages: List[int] = None) -> Dict[str, Any]:
        """Extrae imagenes de productos del PDF usando Vision AI."""
        if not VISION_DETECTOR_AVAILABLE:
            log.warning("VisionProductDetector not available, skipping image extraction")
            return {"images_extracted": 0, "products": []}
        
        try:
            from pdf2image import convert_from_path
            from pdf2image.pdf2image import pdfinfo_from_path
            
            output_dir = f"/opt/odi/data/{store_name}/images"
            os.makedirs(output_dir, exist_ok=True)
            
            detector = VisionProductDetector(use_gemini=True)
            
            info = pdfinfo_from_path(pdf_path)
            total_pages = info.get("Pages", 0)
            
            if pages is None:
                pages = list(range(1, total_pages + 1))  # ALL pages
            
            stats = {"images_extracted": 0, "products": []}
            
            import time as _time
            BATCH_SIZE = 10
            total_pages_count = len(pages)
            
            for batch_idx in range(0, len(pages), BATCH_SIZE):
                batch = pages[batch_idx:batch_idx + BATCH_SIZE]
                log.info(f"  Batch {batch_idx//BATCH_SIZE + 1}: pages {batch[0]}-{batch[-1]} of {total_pages_count}")
                
                for page_num in batch:
                    retries = 3
                    success = False
                    while retries > 0 and not success:
                        try:
                            images = convert_from_path(pdf_path, dpi=200, first_page=page_num, last_page=page_num)
                            if not images:
                                break
                            
                            temp_path = f"/tmp/page_{store_name}_{page_num}.png"
                            images[0].save(temp_path, "PNG")
                            
                            products = detector.detect(temp_path)
                            if products:
                                saved = detector.crop_products(temp_path, products, output_dir, store_name, page_num)
                                stats["images_extracted"] += len(saved)
                                stats["products"].extend(saved)
                            
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                            success = True
                        except Exception as e:
                            retries -= 1
                            if retries > 0:
                                log.warning(f"    Retry page {page_num}: {e}")
                                _time.sleep(2)
                            else:
                                log.error(f"    Failed page {page_num} after 3 retries: {e}")
                    _time.sleep(0.5)
                
                _time.sleep(2)
                log.info(f"    Batch complete: {stats['images_extracted']} images total")
            
            return stats
        except Exception as e:
            log.error(f"Image extraction error: {e}")
            return {"images_extracted": 0, "products": []}


# ============================================
# NORMALIZADOR
# ============================================
class ProductNormalizer:
    """Normaliza productos al estándar SRM."""

    CATEGORIES = {
        "frenos": ["pastilla", "disco", "zapata", "caliper", "bomba"],
        "transmision": ["cadena", "piñon", "corona", "kit arrastre", "tensor"],
        "filtros": ["filtro aceite", "filtro aire", "filtro gasolina"],
        "electrico": ["bujia", "bobina", "cdi", "regulador", "relay"],
        "suspension": ["amortiguador", "telescopico", "resorte", "buje"],
        "aceites": ["aceite", "lubricante", "grasa"],
        "carroceria": ["farola", "stop", "direccional", "espejo", "guardafango"],
    }

    def normalize(self, products: List[Dict[str, Any]], empresa: str) -> List[Dict[str, Any]]:
        """Normaliza lista de productos."""
        normalized = []

        for p in products:
            try:
                norm = {
                    "sku": self._normalize_sku(p.get("sku"), empresa),
                    "title": self._normalize_title(p.get("title", ""), p.get("category")),
                    "description": p.get("description", ""),
                    "price": self._normalize_price(p.get("price")),
                    "category": self._detect_category(p.get("title", ""), p.get("category")),
                    "brand": p.get("brand", empresa),
                    "compatibility": p.get("compatibility", []),
                    "source_empresa": empresa,
                    "normalized_at": datetime.now().isoformat()
                }
                normalized.append(norm)
            except Exception as e:
                log.error(f"Normalization error: {e}")

        return normalized

    def _normalize_sku(self, sku: Optional[str], empresa: str) -> str:
        if sku:
            return f"{empresa[:3].upper()}-{sku}".replace(" ", "-")
        return f"{empresa[:3].upper()}-{datetime.now().strftime('%H%M%S')}"

    def _normalize_title(self, title: str, category: str = None) -> str:
        """Normaliza título: usa nombre exacto de Orden Maestra sin prefijos automáticos."""
        import re
        title = title.strip()
        title = re.sub(r"\s+", " ", title)
        
        # Formatear correctamente (Title Case si está en mayúsculas)
        if title.isupper():
            title = title.title()
        
        # Limitar longitud
        if len(title) > 60:
            title = title[:57].rsplit(" ", 1)[0] + "..."
        
        return title

    def _normalize_price(self, price: Any) -> Optional[float]:
        if price is None:
            return None
        try:
            if isinstance(price, str):
                price = price.replace("$", "").replace(",", "").replace(".", "").strip()
            return float(price)
        except:
            return None

    def _detect_category(self, title: str, category: Optional[str]) -> str:
        title_lower = title.lower()

        for cat, keywords in self.CATEGORIES.items():
            for kw in keywords:
                if kw in title_lower:
                    return cat

        return category or "general"


# ============================================
# ENRIQUECEDOR
# ============================================
class ProductEnricher:
    """Enriquece productos con descripciones SEO."""

    ENRICH_PROMPT = """Genera una descripción SEO para este producto de repuestos de motos:

Producto: {title}
Categoría: {category}
Marca: {brand}

La descripción debe:
- Tener 2-3 oraciones
- Mencionar beneficios para el usuario
- Incluir palabras clave relevantes para SEO
- Ser en español colombiano
- NO incluir precios
- NO inventar especificaciones técnicas

Responde SOLO con la descripción, sin comillas ni formato especial."""

    async def enrich(self, products: List[Dict[str, Any]], source_type: str = 'pdf') -> List[Dict[str, Any]]:
        """Enriquece productos. V19: ChromaDB query + category fallback."""
        from ficha_360_template import build_ficha_360
        from core.chromadb_enrichment import query_chromadb_for_enrichment, get_category_fallback
        from core.odi_image_generator import AIImageGenerator

        img_gen = AIImageGenerator()
        enriched = []

        for p in products:
            title = p.get('title', '')

            # V19: Get product type and query ChromaDB
            product_type = img_gen.extract_product_type(title)

            try:
                enrichment = await query_chromadb_for_enrichment(title, product_type)
            except Exception as e:
                log.debug(f"ChromaDB query failed: {e}")
                enrichment = get_category_fallback(product_type)

            # Build technical context from enrichment
            technical_context = {}
            if enrichment.material:
                technical_context['material'] = enrichment.material
            if enrichment.specifications:
                technical_context['especificaciones'] = enrichment.specifications
            if enrichment.dimensions:
                technical_context['dimensiones'] = enrichment.dimensions
            if enrichment.compatibility:
                technical_context['compatibilidad_verificada'] = enrichment.compatibility

            if source_type in ('csv', 'excel', 'json'):
                # Template-driven with ChromaDB context
                compat = ', '.join(p.get('compatibility', [])) or ''  # V22 fix: no Universal default
                body = build_ficha_360(
                    title=title,
                    sku=p.get('sku', ''),
                    compatibilidad=compat,
                    empresa=p.get('brand', p.get('source_empresa', 'ODI')),
                    technical_context=technical_context
                )
                p['description'] = body
                p['body_html'] = body
                p['_enrichment_source'] = enrichment.source
            elif not p.get("description"):
                try:
                    response = openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "user",
                                "content": self.ENRICH_PROMPT.format(
                                    title=p.get("title", ""),
                                    category=p.get("category", "general"),
                                    brand=p.get("brand", "")
                                )
                            }
                        ],
                        temperature=0.7,
                        max_tokens=200
                    )
                    p["description"] = sanitize_html(response.choices[0].message.content.strip())
                except Exception as e:
                    log.error(f"Enrichment error: {e}")
                    p["description"] = f"Repuesto de calidad para motos. {p.get('category', '')}."

            enriched.append(p)

        return enriched


# ============================================
# SHOPIFY UPLOADER
# ============================================
class ShopifyUploader:
    """Sube productos a Shopify."""

    def __init__(self, shop: str, token: str):
        self.shop = shop
        self.token = token
        self.base_url = f"https://{shop}/admin/api/2025-07"
        self.headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json"
        }

    async def upload_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sube productos a Shopify."""
        results = {"created": 0, "updated": 0, "errors": []}

        async with httpx.AsyncClient(timeout=30.0) as client:
            for p in products:
                try:
                    # Verificar si existe
                    existing = await self._find_by_sku(client, p.get("sku"))

                    if existing:
                        # Actualizar
                        await self._update_product(client, existing["id"], p)
                        results["updated"] += 1
                    else:
                        # Crear
                        await self._create_product(client, p)
                        results["created"] += 1
                        await asyncio.sleep(0.6)  # Rate limit

                except Exception as e:
                    results["errors"].append(f"{p.get('sku')}: {str(e)}")
                    log.error(f"Shopify upload error: {e}")

        return results

    async def _find_by_sku(self, client: httpx.AsyncClient, sku: str) -> Optional[Dict]:
        """Busca producto por SKU."""
        try:
            response = await client.get(
                f"{self.base_url}/products.json",
                headers=self.headers,
                params={"fields": "id,variants", "limit": 1}
            )
            # Simplificado - en producción buscar por SKU real
            return None
        except:
            return None

    async def _create_product(self, client: httpx.AsyncClient, product: Dict[str, Any]):
        """Crea producto en Shopify."""
        shopify_product = {
            "product": {
                "title": product.get("title"),
                "body_html": sanitize_html(product.get("description", "")),
                "vendor": product.get("brand", ""),
                "product_type": product.get("category", ""),
                "tags": ",".join(product.get("compatibility", [])),
                "variants": [
                    {
                        "sku": product.get("sku"),
                        "price": str(product.get("price", 0) or 0),
                        "inventory_management": "shopify"
                    }
                ]
            }
        }


        # Agregar imagen si existe (FIX 3)
        import base64 as _b64
        img_path = product.get("image_path") or product.get("image")
        if img_path and os.path.exists(str(img_path)):
            try:
                with open(img_path, "rb") as _imgf:
                    _img_b64 = _b64.b64encode(_imgf.read()).decode("utf-8")
                _sku = product.get("sku", "product")
                shopify_product["product"]["images"] = [{"attachment": _img_b64, "filename": f"{_sku}.png"}]
            except Exception as _ierr:
                log.warning(f"Could not attach image: {_ierr}")

        response = await client.post(
            f"{self.base_url}/products.json",
            headers=self.headers,
            json=shopify_product
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Shopify error: {response.status_code} - {response.text}")

        return response.json()

    async def _update_product(self, client: httpx.AsyncClient, product_id: int, product: Dict[str, Any]):
        """Actualiza producto existente."""
        shopify_product = {
            "product": {
                "id": product_id,
                "title": product.get("title"),
                "body_html": sanitize_html(product.get("description", "")),
            }
        }

        response = await client.put(
            f"{self.base_url}/products/{product_id}.json",
            headers=self.headers,
            json=shopify_product
        )

        return response.json()




# ============================================
# PASO 5: IMAGE MAPPER
# ============================================
class ImageMapper:
    def __init__(self):
        self.openai_key = os.getenv('OPENAI_API_KEY')
    
    async def extract_and_map(self, pdf_path, products, shop, token):
        import fitz
        if not pdf_path or not pdf_path.lower().endswith('.pdf') or not Path(pdf_path).exists():
            return {'mapped': 0, 'uploaded': 0}
        pages_dir = Path(f'/opt/odi/data/temp_pages')
        pages_dir.mkdir(exist_ok=True)
        try:
            doc = fitz.open(pdf_path)
            page_files = []
            for i, page in enumerate(doc):
                if i < 2: continue
                pix = page.get_pixmap(dpi=150)
                pp = pages_dir / f'p{i}.png'
                pix.save(str(pp))
                page_files.append(pp)
            doc.close()
            log.info(f'  {len(page_files)} paginas PDF')
            return {'mapped': len(page_files), 'uploaded': 0}
        finally:
            import shutil
            if pages_dir.exists(): shutil.rmtree(pages_dir, ignore_errors=True)


# ============================================
# PASO 7: AUDITOR
# ============================================
class PipelineAuditor:
    CRITERIA = [
        ('titulo_descriptivo', lambda p: len(p.get('title', '')) > 10 and not p.get('title', '').replace(' ', '').replace('-', '').isdigit()),
        ('descripcion_especifica', lambda p: len(p.get('description', '')) > 50 and 'genéric' not in p.get('description', '').lower() and 'consultar' not in p.get('description', '').lower()),
        ('compatibilidad_real', lambda p: bool(p.get('compatibility')) or any(m in p.get('title', '').lower() for m in ['akt', 'pulsar', 'yamaha', 'honda', 'suzuki', 'bajaj', 'tvs', 'hero', 'kymco'])),
        ('categoria_no_default', lambda p: p.get('category') and p.get('category') != 'Default' and len(p.get('category', '')) > 3),
        ('beneficios_especificos', lambda p: any(b in p.get('description', '').lower() for b in ['durabilidad', 'rendimiento', 'calidad', 'resistente', 'compatible', 'original', 'garantiza'])),
        ('precio_valido', lambda p: p.get('price') and float(p.get('price', 0)) > 0),
        ('sku_presente', lambda p: bool(p.get('sku')) and len(p.get('sku', '')) > 3),
    ]
    
    def audit(self, products, sample_size=30):
        import random
        sample = products if len(products) <= sample_size else random.sample(products, sample_size)
        results = {n: sum(1 for p in sample if c(p)) for n, c in self.CRITERIA}
        total = len(sample) * len(self.CRITERIA)
        passed = sum(results.values())
        score = (passed / total * 100) if total > 0 else 0
        grade = 'A+' if score >= 98 else 'A' if score >= 95 else 'B' if score >= 85 else 'F'
        return {'sample': len(sample), 'score': round(score,1), 'grade': grade, 'criteria': results}


# ============================================
# PASO 8: CHROMADB INDEXER
# ============================================
class ChromaDBIndexer:
    async def index_products(self, products, empresa):
        try:
            import chromadb
            client = chromadb.HttpClient(host='localhost', port=8000)
            coll = client.get_or_create_collection('odi_products')
            for p in products:
                coll.upsert(ids=[f'{empresa}_{p.get(sku,)}'], documents=[f'{p.get(title,)} {p.get(description,)}'], metadatas=[{'sku': p.get('sku',''), 'empresa': empresa, 'type': 'product'}])
            return {'indexed': len(products)}
        except Exception as e:
            return {'error': str(e)}

# ============================================
# PIPELINE EXECUTOR
# ============================================
class PipelineExecutor:
    """Ejecuta el pipeline completo."""

    def __init__(self):
        self.extractor = VisionExtractor()
        self.normalizer = ProductNormalizer()
        self.enricher = ProductEnricher()
        self.image_mapper = ImageMapper()
        self.auditor = PipelineAuditor()
        self.indexer = ChromaDBIndexer()
        self.jobs: Dict[str, PipelineJob] = {}

    def _load_job(self, job_id: str) -> Optional[PipelineJob]:
        job_file = JOBS_PATH / f"{job_id}.json"
        if job_file.exists():
            with open(job_file) as f:
                return PipelineJob(**json.load(f))
        return self.jobs.get(job_id)

    def _save_job(self, job: PipelineJob):
        self.jobs[job.job_id] = job
        job_file = JOBS_PATH / f"{job.job_id}.json"
        with open(job_file, "w") as f:
            json.dump(job.model_dump(), f, indent=2, default=str)

    async def execute(self, request: PipelineRequest) -> PipelineJob:
        """Ejecuta el pipeline completo."""
        job = PipelineJob(
            job_id=request.job_id,
            empresa=request.empresa,
            shop_key=request.shop_key,
            source_file=request.source_file,
            images_folder=request.images_folder,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        self._save_job(job)

        try:
            # 1. EXTRAER
            log.info(f"[{job.job_id}] Stage 1: EXTRACTING")
            job.stage = PipelineStage.EXTRACTING.value
            self._save_job(job)

            # Detectar tipo de archivo y usar extractor adecuado
            source_lower = request.source_file.lower()
            if source_lower.endswith((".xlsx", ".xls")):
                products = await self.extractor.extract_from_excel(request.source_file)
            elif source_lower.endswith(".json"):
                products = await self.extractor.extract_from_json(request.source_file, request.empresa)
            elif source_lower.endswith(".csv"):
                products = await self.extractor.extract_from_csv(request.source_file)
            else:
                products = await self.extractor.extract_from_pdf(request.source_file)
            log.info(f"[{job.job_id}] Extracted {len(products)} products")

            # Extract product images from PDF
            if request.source_file.lower().endswith(".pdf"):
                log.info(f"[{job.job_id}] Extracting product images...")
                img_stats = await self.extractor.extract_images_from_pdf(
                    request.source_file, request.empresa
                )
                log.info(f"[{job.job_id}] Extracted {img_stats.get('images_extracted', 0)} product images")
                job.metadata["images_extracted"] = img_stats.get('images_extracted', 0)

            valid, msg = validate_extraction(products)
            if not valid:
                job.stage = PipelineStage.FAILED.value
                job.errors.append(f"Validacion extraccion: {msg}")
                self._save_job(job)
                log.error(f"[{job.job_id}] FAIL: {msg}")
                return job
            log.info(f"[{job.job_id}] Validacion extraccion: {msg}")

            # 2. NORMALIZAR
            log.info(f"[{job.job_id}] Stage 2: NORMALIZING")
            job.stage = PipelineStage.NORMALIZING.value
            self._save_job(job)

            products = self.normalizer.normalize(products, request.empresa)
            
            # Validar normalización
            valid, msg = validate_normalization(products)
            log.info(f"[{job.job_id}] Validacion normalizacion: {msg}")
            if not valid:
                log.warning(f"[{job.job_id}] Normalizacion con issues: {msg}")

            # 3. ENRIQUECER
            log.info(f"[{job.job_id}] Stage 3: ENRICHING")
            job.stage = PipelineStage.ENRICHING.value
            self._save_job(job)

            # Determinar source_type
            source_type = "json" if source_lower.endswith(".json") else "csv" if source_lower.endswith(".csv") else "excel" if source_lower.endswith((".xlsx", ".xls")) else "pdf"
            products = await self.enricher.enrich(products, source_type=source_type)
            
            # Validar enriquecimiento
            valid, msg = validate_enrichment(products)
            log.info(f"[{job.job_id}] Validacion enriquecimiento: {msg}")

            # 4. FITMENT (simplificado por ahora)
            log.info(f"[{job.job_id}] Stage 4: FITTING")
            job.stage = PipelineStage.FITTING.value
            self._save_job(job)
            # TODO: Integrar con M6.2 Fitment

            job.products = products
            job.products_count = len(products)

            # 5. SHOPIFY
            if request.shop_key and request.shop_key in SHOPIFY_STORES:
                log.info(f"[{job.job_id}] Stage 5: UPLOADING to {request.shop_key}")
                job.stage = PipelineStage.UPLOADING.value
                self._save_job(job)

                store = SHOPIFY_STORES[request.shop_key]
                if store.get("shop") and store.get("token"):
                    uploader = ShopifyUploader(store["shop"], store["token"])
                    result = await uploader.upload_products(products)
                    job.uploaded_count = result["created"] + result["updated"]
                    job.errors.extend(result.get("errors", []))
                else:
                    log.warning(f"[{job.job_id}] Shopify not configured for {request.shop_key}")

            # 6. IMAGES (si hay PDF catálogo)
            if request.source_file and request.source_file.lower().endswith('.pdf'):
                log.info(f'[{job.job_id}] Stage 6: IMAGES')
                try:
                    store = SHOPIFY_STORES.get(request.shop_key, {})
                    img_result = await self.image_mapper.extract_and_map(
                        request.source_file, products, store.get('shop', ''), store.get('token', '')
                    )
                    job.metadata['images'] = img_result
                    log.info(f'[{job.job_id}] Images: {img_result}')
                except Exception as e:
                    log.warning(f'[{job.job_id}] Images skipped: {e}')

            # 7. AUDIT
            log.info(f'[{job.job_id}] Stage 7: AUDIT')
            audit_result = self.auditor.audit(products)
            job.metadata['audit'] = audit_result
            log.info(f"[{job.job_id}] Audit: {audit_result['grade']} ({audit_result['score']}%)")

            # 8. CHROMADB
            log.info(f'[{job.job_id}] Stage 8: CHROMADB')
            try:
                index_result = await self.indexer.index_products(products, request.empresa)
                job.metadata['chromadb'] = index_result
                log.info(f'[{job.job_id}] ChromaDB: {index_result}')
            except Exception as e:
                log.warning(f'[{job.job_id}] ChromaDB skipped: {e}')

            # COMPLETADO
            job.stage = PipelineStage.COMPLETED.value
            job.updated_at = datetime.now().isoformat()
            self._save_job(job)

            log.info(f"[{job.job_id}] Pipeline COMPLETED: {job.products_count} products, {job.uploaded_count} uploaded")

        except Exception as e:
            log.error(f"[{job.job_id}] Pipeline FAILED: {e}")
            job.stage = PipelineStage.FAILED.value
            job.errors.append(str(e))
            job.updated_at = datetime.now().isoformat()
            self._save_job(job)

        return job


# ============================================
# FASTAPI APP
# ============================================
app = FastAPI(
    title="ODI Pipeline Service",
    description="Pipeline de 6 pasos: Catálogo → Shopify",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting: 15 req/min for pipeline (heavier operations), burst 5/5s
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=15,
    burst_limit=5,
    exclude_paths=["/health", "/docs", "/openapi.json", "/stores"],
)

executor = PipelineExecutor()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "odi-pipeline", "timestamp": datetime.now().isoformat()}


@app.post("/pipeline/start")
async def start_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    """Inicia el pipeline de forma asíncrona."""
    background_tasks.add_task(executor.execute, request)
    return {"job_id": request.job_id, "status": "started", "message": "Pipeline started in background"}


@app.get("/pipeline/status/{job_id}")
async def get_status(job_id: str):
    """Obtiene estado de un job."""
    job = executor._load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump()


@app.get("/pipeline/jobs")
async def list_jobs(limit: int = 20):
    """Lista jobs recientes."""
    jobs = []
    for job_file in sorted(JOBS_PATH.glob("*.json"), reverse=True)[:limit]:
        with open(job_file) as f:
            jobs.append(json.load(f))
    return {"jobs": jobs, "count": len(jobs)}


@app.get("/stores")
async def list_stores():
    """Lista tiendas configuradas."""
    return {
        name: {"configured": bool(config.get("shop") and config.get("token"))}
        for name, config in SHOPIFY_STORES.items()
    }




# ============================================
# UPLOAD ENDPOINT WITH IMAGE MATCHING
# ============================================

class UploadRequest(BaseModel):
    store: str
    match_images: bool = True

@app.post("/pipeline/upload")
async def upload_with_image_matching(request: UploadRequest, background_tasks: BackgroundTasks):
    """
    Upload products from JSON with automatic image matching.
    Searches in pdf_images and image bank.
    """
    store = request.store.upper()
    
    if store not in SHOPIFY_STORES:
        raise HTTPException(status_code=400, detail=f"Store {store} not configured")
    
    shop = SHOPIFY_STORES[store]["shop"]
    token = SHOPIFY_STORES[store]["token"]
    
    if not shop or not token:
        raise HTTPException(status_code=400, detail=f"No credentials for {store}")
    
    # Load products from JSON
    json_path = f"/opt/odi/data/orden_maestra_v6/{store}_products.json"
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail=f"JSON not found: {json_path}")
    
    with open(json_path, "r") as f:
        products = json.load(f)
    
    # Image matching
    matched_count = 0
    if request.match_images and IMAGE_MATCHER_AVAILABLE:
        try:
            products = match_products_with_local_images(products, store)
            matched_count = sum(1 for p in products if p.get("image") and not "placeholder" in str(p.get("image", "")).lower())
        except Exception as e:
            logging.warning(f"Image matching failed: {e}")
    
    # Upload
    uploader = ShopifyUploader(shop, token)
    
    async def do_upload():
        return await uploader.upload_products(products)
    
    background_tasks.add_task(do_upload)
    
    return {
        "status": "started",
        "store": store,
        "products": len(products),
        "with_images": matched_count,
        "match_images": request.match_images
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8804)

    async def upload_image_to_product(self, client: httpx.AsyncClient, product_id: int, image_path: str) -> bool:
        """Sube imagen a producto existente via POST /products/{id}/images.json"""
        import base64 as _b64
        
        if not os.path.exists(image_path):
            return False
        
        try:
            with open(image_path, "rb") as f:
                img_b64 = _b64.b64encode(f.read()).decode("utf-8")
            
            payload = {
                "image": {
                    "attachment": img_b64,
                    "filename": os.path.basename(image_path)
                }
            }
            
            response = await client.post(
                f"{self.base_url}/products/{product_id}/images.json",
                headers=self.headers,
                json=payload
            )
            
            return response.status_code in [200, 201]
        except Exception as e:
            log.error(f"Image upload error for product {product_id}: {e}")
            return False



# ============================================
# V19 PIPELINE VALIDATION TEST
# ============================================
async def test_v19_pipeline(store: str, limit: int = 100):
    """Test V19 pipeline enrichment for a store."""
    import requests
    import random
    import re
    from core.odi_image_generator import AIImageGenerator
    from core.chromadb_enrichment import query_chromadb_for_enrichment, get_category_fallback
    from core.ficha_360_template import build_ficha_360
    
    def normalize_title_v2(title: str) -> str:
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
    
    def extract_compatibility(title: str, store: str) -> str:
        title_lower = title.lower()
        matches = []
        brands = {'pulsar': 'Pulsar', 'discover': 'Discover', 'boxer': 'Boxer', 'fz': 'FZ', 
                  'ybr': 'YBR', 'xtz': 'XTZ', 'akt': 'AKT', 'tvs': 'TVS', 'cb': 'CB'}
        for key, val in brands.items():
            if key in title_lower:
                cc_match = re.search(rf'{key}\s*(\d{{2,3}})', title_lower)
                if cc_match:
                    matches.append(f'{val} {cc_match.group(1)}')
                else:
                    matches.append(val)
        if matches:
            return ', '.join(list(dict.fromkeys(matches))[:4])
        return f'Motos compatibles - {store}'
    
    store = store.upper()
    config_path = f'/opt/odi/data/brands/{store.lower()}.json'
    
    with open(config_path) as f:
        config = json.load(f)
    
    shop = config['shopify']['shop']
    token = config['shopify']['token']
    
    print(f'=== V19 PIPELINE TEST - {store} ===')
    print(f'Fetching {limit} products from Shopify...')
    
    products = []
    url = f'https://{shop}/admin/api/2024-01/products.json?limit=250&fields=id,title,variants'
    headers = {'X-Shopify-Access-Token': token}
    
    while url and len(products) < limit:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        for p in r.json().get('products', []):
            sku = p['variants'][0].get('sku', '') if p.get('variants') else ''
            products.append({'id': p['id'], 'title': p['title'], 'sku': sku})
            if len(products) >= limit:
                break
        link = r.headers.get('Link', '')
        url = None
        if 'rel="next"' in link and len(products) < limit:
            for part in link.split(','):
                if 'rel="next"' in part:
                    url = part.split('<')[1].split('>')[0]
                    break
    
    print(f'Fetched {len(products)} products\n')
    
    img_gen = AIImageGenerator()
    results = []
    sources = {}
    types = {}
    
    for i, p in enumerate(products):
        title = p.get('title', '')
        sku = p.get('sku', '')
        normalized_title = normalize_title_v2(title)
        product_type = img_gen.extract_product_type(title)
        
        try:
            enrichment = await query_chromadb_for_enrichment(title, product_type)
        except Exception:
            enrichment = get_category_fallback(product_type)
        
        compatibility = extract_compatibility(title, store)
        
        results.append({
            'sku': sku,
            'original_title': title,
            'normalized_title': normalized_title,
            'product_type': product_type,
            'enrichment_source': enrichment.source,
            'enrichment_score': enrichment.score,
            'material': enrichment.material,
            'compatibility': compatibility,
        })
        
        sources[enrichment.source] = sources.get(enrichment.source, 0) + 1
        types[product_type] = types.get(product_type, 0) + 1
        
        if (i + 1) % 50 == 0:
            print(f'  Processed {i + 1}/{len(products)}...')
    
    print('\nESTADISTICAS:')
    print('  Enrichment sources:')
    for src, cnt in sorted(sources.items(), key=lambda x: -x[1]):
        pct = cnt / len(results) * 100
        print(f'    {src}: {cnt} ({pct:.0f}%)')
    
    print(f'\n  Top product types:')
    for typ, cnt in sorted(types.items(), key=lambda x: -x[1])[:10]:
        print(f'    {typ}: {cnt}')
    
    print('\n' + '='*60)
    print('VERIFICACION DE CALIDAD')
    print('='*60)
    
    all_caps = sum(1 for r in results if r['normalized_title'].isupper())
    default_cnt = sources.get('default', 0)
    
    print(f'  Titulos ALL CAPS: {all_caps} (debe ser 0)')
    print(f'  Templates default: {default_cnt}')
    
    print('\n' + '='*60)
    print('RESUMEN')
    print('='*60)
    print(f'Total: {len(results)}')
    print(f'ChromaDB: {sources.get("chromadb", 0)}')
    print(f'Category: {sources.get("category_template", 0)}')
    print(f'Default: {sources.get("default", 0)}')
    
    return results
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='ODI Pipeline Service')
    parser.add_argument('--test', type=str, help='Test V19 pipeline for STORE')
    parser.add_argument('--limit', type=int, default=100, help='Limit products for test')
    parser.add_argument('--serve', action='store_true', help='Start API server')
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(test_v19_pipeline(args.test, args.limit))
    elif args.serve or len(sys.argv) == 1:
        import uvicorn
        uvicorn.run(app, host='0.0.0.0', port=8804)
    else:
        parser.print_help()
