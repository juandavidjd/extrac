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
import httpx

# OpenAI for Vision
from openai import OpenAI

load_dotenv("/opt/odi/.env")

# ============================================
# CONFIGURACIÓN
# ============================================
SHOPIFY_STORES = {
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
            return result.get("products", [])

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
            return result.get("products", [])

        except Exception as e:
            log.error(f"Vision extraction error: {e}")
            return []


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
                    "title": self._normalize_title(p.get("title", "")),
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

    def _normalize_title(self, title: str) -> str:
        # Capitalizar correctamente
        title = title.strip()
        if title.isupper():
            title = title.title()
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

    async def enrich(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enriquece productos con descripciones."""
        enriched = []

        for p in products:
            if not p.get("description"):
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
                    p["description"] = response.choices[0].message.content.strip()
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
        self.base_url = f"https://{shop}/admin/api/2024-01"
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
                "body_html": product.get("description", ""),
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
                "body_html": product.get("description", ""),
            }
        }

        response = await client.put(
            f"{self.base_url}/products/{product_id}.json",
            headers=self.headers,
            json=shopify_product
        )

        return response.json()


# ============================================
# PIPELINE EXECUTOR
# ============================================
class PipelineExecutor:
    """Ejecuta el pipeline completo."""

    def __init__(self):
        self.extractor = VisionExtractor()
        self.normalizer = ProductNormalizer()
        self.enricher = ProductEnricher()
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

            products = await self.extractor.extract_from_pdf(request.source_file)
            log.info(f"[{job.job_id}] Extracted {len(products)} products")

            if not products:
                job.stage = PipelineStage.FAILED.value
                job.errors.append("No products extracted")
                self._save_job(job)
                return job

            # 2. NORMALIZAR
            log.info(f"[{job.job_id}] Stage 2: NORMALIZING")
            job.stage = PipelineStage.NORMALIZING.value
            self._save_job(job)

            products = self.normalizer.normalize(products, request.empresa)

            # 3. ENRIQUECER
            log.info(f"[{job.job_id}] Stage 3: ENRICHING")
            job.stage = PipelineStage.ENRICHING.value
            self._save_job(job)

            products = await self.enricher.enrich(products)

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

            # 6. CAMPAÑAS (TODO)
            # Generar assets para Meta/Google

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8804)
