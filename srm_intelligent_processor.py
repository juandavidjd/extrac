#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════════
                     SRM INTELLIGENT PROCESSOR v4.0
              Procesador Universal Multi-Industria Multi-Tenant
══════════════════════════════════════════════════════════════════════════════════

ARQUITECTURA:
    somosindustrias.com (Master)
    └── Industrias
        ├── somosrepuestosmotos.com (SRM)
        │   └── Clientes: Kaiqi, Japan, Bara, DFG, Yokomar, etc.
        ├── somosferreteria.com
        ├── somoselectronica.com
        └── ...

CAPACIDADES:
    ✓ Auto-detección de industria por contenido
    ✓ Auto-detección de cliente/marca
    ✓ Push directo a Shopify del cliente
    ✓ Soporte multi-formato (PDF, Excel, CSV, Word, TXT, Imágenes, ZIP, URL)
    ✓ Pipeline: Ingesta → Extracción → Normalización → Unificación → Enriquecimiento → Ficha 360°

INSTALACIÓN:
    pip install openai anthropic pandas openpyxl python-docx beautifulsoup4 requests pillow opencv-python shopify

AUTOR: SRM/ODI Team
VERSIÓN: 4.0
══════════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import gc
import re
import json
import csv
import base64
import time
import hashlib
import tempfile
import zipfile
import mimetypes
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ============================================================================
# VERIFICACIÓN DE DEPENDENCIAS
# ============================================================================

CORE_DEPS = ['pandas', 'requests', 'PIL', 'openai']
OPTIONAL_DEPS = ['cv2', 'docx', 'bs4', 'openpyxl', 'anthropic', 'shopify']

def check_dependencies():
    missing_core = []
    missing_optional = []

    for dep in CORE_DEPS:
        try:
            __import__(dep)
        except ImportError:
            missing_core.append(dep)

    for dep in OPTIONAL_DEPS:
        try:
            __import__(dep)
        except ImportError:
            missing_optional.append(dep)

    if missing_core:
        print(f"❌ Dependencias requeridas faltantes: {missing_core}")
        print("   pip install pandas requests pillow openai python-dotenv")
        sys.exit(1)

    if missing_optional:
        print(f"⚠️  Dependencias opcionales faltantes: {missing_optional}")
        print("   pip install opencv-python python-docx beautifulsoup4 openpyxl anthropic ShopifyAPI")

check_dependencies()

import pandas as pd
import numpy as np
import requests
from PIL import Image
from openai import OpenAI

# Event Emitter para Cortex Visual
try:
    from odi_event_emitter import ODIEventEmitter
    EMITTER_AVAILABLE = True
except ImportError:
    EMITTER_AVAILABLE = False
    ODIEventEmitter = None

# Imports opcionales
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import shopify
    SHOPIFY_AVAILABLE = True
except ImportError:
    SHOPIFY_AVAILABLE = False


# ============================================================================
# CONFIGURACIÓN GLOBAL
# ============================================================================

VERSION = "4.0"
SCRIPT_NAME = "SRM Intelligent Processor"

# Directorios
DEFAULT_OUTPUT_DIR = os.getenv('SRM_OUTPUT_DIR', '/tmp/srm_output')
DEFAULT_TEMP_DIR = os.getenv('SRM_TEMP_DIR', '/tmp/srm_temp')
IMAGE_SERVER_URL = os.getenv('IMAGE_SERVER_URL', 'http://64.23.170.118/images')

# API Configuration
VISION_MODEL = "gpt-4o"
TEXT_MODEL = "gpt-4o-mini"
MAX_TOKENS = 4096
MAX_RETRIES = 5
RETRY_DELAY = 2

# AI Provider Selection
AI_PROVIDER = os.getenv('AI_PROVIDER', 'OPENAI').upper()


# ============================================================================
# CONFIGURACIÓN MULTI-TENANT
# ============================================================================

# Industrias soportadas
INDUSTRIES = {
    "autopartes_motos": {
        "name": "Repuestos de Motos y Motocargueros",
        "domain": "somosrepuestosmotos.com",
        "keywords": ["moto", "motocicleta", "motocarguero", "cilindraje", "cc", "2t", "4t",
                    "pistón", "cilindro", "carburador", "cdi", "bobina", "clutch", "piñón",
                    "catalina", "cadena", "amortiguador", "telescopio", "freno", "disco",
                    "pastilla", "zapata", "faro", "direccional", "velocímetro", "tacómetro"],
        "categories": {
            "motor": ["motor", "culata", "pistón", "biela", "cigüeñal", "válvula", "cilindro", "aro", "anillo"],
            "frenos": ["freno", "pastilla", "disco", "zapata", "caliper", "bomba freno", "manigueta"],
            "suspension": ["suspensión", "amortiguador", "telescopio", "resorte", "buje"],
            "transmision": ["transmisión", "cadena", "piñón", "catalina", "clutch", "embrague", "variador"],
            "electrico": ["eléctrico", "bobina", "cdi", "batería", "faro", "luz", "bombillo", "direccional"],
            "carroceria": ["carrocería", "plástico", "guardafango", "tanque", "tapa", "carenaje"],
            "accesorios": ["accesorio", "espejo", "manubrio", "pedal", "estribo", "defensa"],
        }
    },

    "autopartes_carros": {
        "name": "Repuestos de Carros",
        "domain": "somosrepuestoscarros.com",
        "keywords": ["carro", "automóvil", "vehículo", "sedan", "suv", "camioneta",
                    "motor", "caja", "suspensión", "freno", "radiador"],
        "categories": {}
    },

    "ferreteria": {
        "name": "Ferretería y Construcción",
        "domain": "somosferreteria.com",
        "keywords": ["tornillo", "tuerca", "clavo", "martillo", "taladro", "cemento",
                    "pintura", "tubo", "cable", "interruptor", "cerradura"],
        "categories": {}
    },

    "electronica": {
        "name": "Electrónica y Tecnología",
        "domain": "somoselectronica.com",
        "keywords": ["celular", "computador", "tablet", "televisor", "parlante",
                    "cable usb", "cargador", "batería", "pantalla", "teclado"],
        "categories": {}
    },

    "hogar": {
        "name": "Hogar y Decoración",
        "domain": "somoshogar.com",
        "keywords": ["sofá", "mesa", "silla", "cama", "cocina", "baño", "lámpara",
                    "cortina", "tapete", "almohada"],
        "categories": {}
    },

    "industrial": {
        "name": "Industrial y Maquinaria",
        "domain": "somosindustrial.com",
        "keywords": ["motor eléctrico", "bomba", "compresor", "válvula", "plc",
                    "variador", "sensor", "cilindro neumático", "hidráulico"],
        "categories": {}
    },
}

# Clientes por industria (con configuración Shopify)
CLIENTS = {
    "autopartes_motos": {
        "KAIQI": {
            "name": "Kaiqi Parts",
            "type": "fabricante",
            "shop": os.getenv('KAIQI_SHOP', 'u03tqc-0e.myshopify.com'),
            "token": os.getenv('KAIQI_TOKEN'),
            "prefixes": ["KQ", "KAIQI", "KAI"],
            "keywords": ["kaiqi", "kai qi"],
        },
        "JAPAN": {
            "name": "Japan",
            "type": "fabricante",
            "shop": os.getenv('JAPAN_SHOP', '7cy1zd-qz.myshopify.com'),
            "token": os.getenv('JAPAN_TOKEN'),
            "prefixes": ["JP", "JAPAN", "JAP"],
            "keywords": ["japan", "japón"],
        },
        "DUNA": {
            "name": "Duna",
            "type": "fabricante",
            "shop": os.getenv('DUNA_SHOP', 'ygsfhq-fs.myshopify.com'),
            "token": os.getenv('DUNA_TOKEN'),
            "prefixes": ["DUN", "DUNA"],
            "keywords": ["duna"],
        },
        "BARA": {
            "name": "Bara Importaciones",
            "type": "importador",
            "shop": os.getenv('BARA_SHOP', '4jqcki-jq.myshopify.com'),
            "token": os.getenv('BARA_TOKEN'),
            "prefixes": ["BAR", "BARA"],
            "keywords": ["bara", "importaciones bara"],
        },
        "DFG": {
            "name": "DFG",
            "type": "importador",
            "shop": os.getenv('DFG_SHOP', '0se1jt-q1.myshopify.com'),
            "token": os.getenv('DFG_TOKEN'),
            "prefixes": ["DFG"],
            "keywords": ["dfg"],
        },
        "YOKOMAR": {
            "name": "Yokomar",
            "type": "distribuidor",
            "shop": os.getenv('YOKOMAR_SHOP', 'u1zmhk-ts.myshopify.com'),
            "token": os.getenv('YOKOMAR_TOKEN'),
            "prefixes": ["YOK", "YOKOMAR"],
            "keywords": ["yokomar"],
        },
        "VAISAND": {
            "name": "Vaisand",
            "type": "distribuidor",
            "shop": os.getenv('VAISAND_SHOP', 'z4fpdj-mz.myshopify.com'),
            "token": os.getenv('VAISAND_TOKEN'),
            "prefixes": ["VAI", "VAISAND"],
            "keywords": ["vaisand"],
        },
        "LEO": {
            "name": "Leo",
            "type": "almacen",
            "shop": os.getenv('LEO_SHOP', 'h1hywg-pq.myshopify.com'),
            "token": os.getenv('LEO_TOKEN'),
            "prefixes": ["LEO"],
            "keywords": ["leo"],
        },
        "STORE": {
            "name": "Store (Carguero)",
            "type": "almacen",
            "shop": os.getenv('STORE_SHOP', '0b6umv-11.myshopify.com'),
            "token": os.getenv('STORE_TOKEN'),
            "prefixes": ["STR", "STORE", "CARGUERO"],
            "keywords": ["store", "carguero"],
        },
        "IMBRA": {
            "name": "Imbra",
            "type": "fabricante",
            "shop": os.getenv('IMBRA_SHOP', '0i1mdf-gi.myshopify.com'),
            "token": os.getenv('IMBRA_TOKEN'),
            "prefixes": ["IMB", "IMBRA"],
            "keywords": ["imbra"],
        },
    }
}


# ============================================================================
# LOGGING
# ============================================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


class Logger:
    LEVELS = {
        'debug': (Colors.DIM, ''),
        'info': (Colors.CYAN, ''),
        'success': (Colors.GREEN, '✓'),
        'warning': (Colors.YELLOW, '⚠'),
        'error': (Colors.RED, '✗'),
        'header': (Colors.BOLD, ''),
        'step': (Colors.BLUE, '→'),
    }

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.start_time = time.time()

    def log(self, msg: str, level: str = 'info'):
        if not self.verbose and level == 'debug':
            return
        color, icon = self.LEVELS.get(level, (Colors.RESET, ''))
        ts = datetime.now().strftime('%H:%M:%S')
        prefix = f"{icon} " if icon else ""
        print(f"{color}[{ts}] {prefix}{msg}{Colors.RESET}", flush=True)

    def step(self, step_num: int, total: int, name: str):
        print(f"\n{Colors.BOLD}{'='*60}")
        print(f"  PASO {step_num}/{total}: {name.upper()}")
        print(f"{'='*60}{Colors.RESET}\n")

    def elapsed(self) -> str:
        elapsed = time.time() - self.start_time
        if elapsed < 60:
            return f"{elapsed:.1f}s"
        return f"{elapsed/60:.1f}m"


log = Logger()


# ============================================================================
# UTILIDADES
# ============================================================================

def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def detect_file_type(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    type_map = {
        '.pdf': 'pdf', '.xlsx': 'excel', '.xls': 'excel', '.csv': 'csv',
        '.docx': 'word', '.doc': 'word', '.txt': 'txt',
        '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.webp': 'image',
        '.zip': 'zip', '.rar': 'zip',
    }
    return type_map.get(ext, 'unknown')


def clean_text(text: Any) -> str:
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    return re.sub(r'\s+', ' ', text.strip())


def clean_price(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r'[^\d.,]', '', value).replace(',', '.')
        if cleaned.count('.') > 1:
            parts = cleaned.split('.')
            cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    return 0.0


# ============================================================================
# DETECTOR DE INDUSTRIA Y CLIENTE
# ============================================================================

class IndustryDetector:
    """Detecta automáticamente la industria del contenido."""

    def __init__(self):
        self.industries = INDUSTRIES
        self.clients = CLIENTS

    def detect_industry(self, text: str, filename: str = "") -> Tuple[str, float]:
        """Detecta la industria basándose en keywords."""
        text_lower = (text + " " + filename).lower()
        scores = {}

        for industry_id, config in self.industries.items():
            score = 0
            for keyword in config.get('keywords', []):
                if keyword in text_lower:
                    score += 1

            if score > 0:
                scores[industry_id] = score

        if not scores:
            return 'autopartes_motos', 0.0  # Default

        best = max(scores.items(), key=lambda x: x[1])
        total_keywords = len(self.industries[best[0]].get('keywords', []))
        confidence = min(best[1] / max(total_keywords * 0.3, 1), 1.0)

        return best[0], confidence

    def detect_client(self, text: str, industry: str, filename: str = "") -> Tuple[Optional[str], float]:
        """Detecta el cliente/marca basándose en prefijos y keywords."""
        text_lower = (text + " " + filename).lower()
        text_upper = (text + " " + filename).upper()

        industry_clients = self.clients.get(industry, {})

        for client_id, config in industry_clients.items():
            # Buscar por prefijos
            for prefix in config.get('prefixes', []):
                if prefix in text_upper:
                    return client_id, 0.9

            # Buscar por keywords
            for keyword in config.get('keywords', []):
                if keyword in text_lower:
                    return client_id, 0.8

        return None, 0.0

    def detect_category(self, text: str, industry: str) -> str:
        """Detecta categoría dentro de la industria."""
        text_lower = text.lower()
        industry_config = self.industries.get(industry, {})
        categories = industry_config.get('categories', {})

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category.upper().replace('_', ' ')

        return "OTROS"


# ============================================================================
# MODELOS DE DATOS
# ============================================================================

@dataclass
class ProductData:
    """Datos de producto extraído."""
    id: str = ""
    codigo: str = ""
    sku: str = ""
    nombre: str = ""
    descripcion: str = ""
    descripcion_corta: str = ""
    precio: float = 0.0
    precio_comparacion: float = 0.0
    categoria: str = ""
    subcategoria: str = ""
    marca: str = ""
    modelo: str = ""
    imagen: str = ""
    imagenes: List[str] = field(default_factory=list)
    atributos: Dict[str, Any] = field(default_factory=dict)
    fitment: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    stock: int = 0
    peso: float = 0.0
    peso_unit: str = "kg"
    fuente: str = ""
    pagina: int = 0
    industria: str = ""
    cliente: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d['imagenes'] = ','.join(self.imagenes) if self.imagenes else ''
        d['tags'] = ','.join(self.tags) if self.tags else ''
        d['atributos'] = json.dumps(self.atributos, ensure_ascii=False) if self.atributos else ''
        d['fitment'] = json.dumps(self.fitment, ensure_ascii=False) if self.fitment else ''
        return d

    def to_shopify(self) -> dict:
        """Convierte a formato Shopify Product."""
        return {
            "product": {
                "title": self.nombre,
                "body_html": f"<p>{self.descripcion}</p>",
                "vendor": self.marca or self.cliente,
                "product_type": self.categoria,
                "tags": self.tags,
                "variants": [{
                    "sku": self.sku,
                    "price": str(self.precio),
                    "compare_at_price": str(self.precio_comparacion) if self.precio_comparacion else None,
                    "inventory_quantity": self.stock,
                    "weight": self.peso,
                    "weight_unit": self.peso_unit,
                }],
                "images": [{"src": img} for img in self.imagenes if img] if self.imagenes else [],
            }
        }

    def is_valid(self) -> bool:
        return bool(self.codigo or self.nombre)


@dataclass
class ProcessingResult:
    """Resultado del procesamiento."""
    success: bool = False
    products: List[ProductData] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    source_file: str = ""
    source_type: str = ""
    detected_industry: str = ""
    detected_client: str = ""
    processing_time: float = 0.0


# ============================================================================
# CLIENTE AI MULTI-PROVEEDOR
# ============================================================================

class AIClient:
    """Cliente de AI que soporta múltiples proveedores."""

    def __init__(self, provider: str = None):
        self.provider = provider or AI_PROVIDER

        if self.provider == 'OPENAI':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY no configurada")
            self.client = OpenAI(api_key=api_key)

        elif self.provider == 'ANTHROPIC' and ANTHROPIC_AVAILABLE:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY no configurada")
            self.client = anthropic.Anthropic(api_key=api_key)

        else:
            # Fallback a OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            self.client = OpenAI(api_key=api_key) if api_key else None

    def analyze_image(self, image_path: str, prompt: str) -> dict:
        """Analiza una imagen con Vision AI."""
        with open(image_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')

        for attempt in range(MAX_RETRIES):
            try:
                if self.provider == 'OPENAI':
                    response = self.client.chat.completions.create(
                        model=VISION_MODEL,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}",
                                    "detail": "high"
                                }}
                            ]
                        }],
                        max_tokens=MAX_TOKENS,
                        response_format={"type": "json_object"}
                    )
                    return json.loads(response.choices[0].message.content)

                elif self.provider == 'ANTHROPIC':
                    response = self.client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=MAX_TOKENS,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "image", "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_b64
                                }},
                                {"type": "text", "text": prompt + "\n\nResponde SOLO JSON válido."}
                            ]
                        }]
                    )
                    # Extraer JSON de la respuesta
                    text = response.content[0].text
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                    return {}

            except Exception as e:
                if 'rate_limit' in str(e).lower():
                    time.sleep(RETRY_DELAY * (2 ** attempt))
                else:
                    log.log(f"Error AI: {str(e)[:50]}", "warning")
                    time.sleep(RETRY_DELAY)

        return {}

    def analyze_text(self, text: str, prompt: str) -> dict:
        """Analiza texto con LLM."""
        for attempt in range(MAX_RETRIES):
            try:
                if self.provider == 'OPENAI':
                    response = self.client.chat.completions.create(
                        model=TEXT_MODEL,
                        messages=[{"role": "user", "content": f"{prompt}\n\nTEXTO:\n{text[:10000]}"}],
                        response_format={"type": "json_object"},
                        max_tokens=2000
                    )
                    return json.loads(response.choices[0].message.content)

                elif self.provider == 'ANTHROPIC':
                    response = self.client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=2000,
                        messages=[{"role": "user", "content": f"{prompt}\n\nTEXTO:\n{text[:10000]}\n\nResponde SOLO JSON."}]
                    )
                    text_resp = response.content[0].text
                    json_match = re.search(r'\{.*\}', text_resp, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                    return {}

            except Exception as e:
                log.log(f"Error AI texto: {str(e)[:50]}", "warning")
                time.sleep(RETRY_DELAY)

        return {}


# ============================================================================
# CLIENTE SHOPIFY
# ============================================================================

class ShopifyClient:
    """Cliente para interactuar con tiendas Shopify."""

    def __init__(self, shop_url: str, access_token: str):
        self.shop_url = shop_url
        self.access_token = access_token
        self.api_version = os.getenv('SHOPIFY_API_VERSION', '2024-01')
        self.base_url = f"https://{shop_url}/admin/api/{self.api_version}"

    def _headers(self) -> dict:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

    def create_product(self, product: ProductData) -> Optional[dict]:
        """Crea un producto en Shopify."""
        try:
            url = f"{self.base_url}/products.json"
            data = product.to_shopify()

            response = requests.post(url, headers=self._headers(), json=data, timeout=30)

            if response.status_code == 201:
                return response.json()
            else:
                log.log(f"Shopify error: {response.status_code} - {response.text[:100]}", "warning")
                return None

        except Exception as e:
            log.log(f"Error Shopify: {e}", "warning")
            return None

    def update_product(self, product_id: str, product: ProductData) -> Optional[dict]:
        """Actualiza un producto existente."""
        try:
            url = f"{self.base_url}/products/{product_id}.json"
            data = product.to_shopify()

            response = requests.put(url, headers=self._headers(), json=data, timeout=30)

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            log.log(f"Error Shopify update: {e}", "warning")
            return None

    def find_product_by_sku(self, sku: str) -> Optional[dict]:
        """Busca producto por SKU."""
        try:
            url = f"{self.base_url}/products.json?fields=id,title,variants"
            response = requests.get(url, headers=self._headers(), timeout=30)

            if response.status_code == 200:
                products = response.json().get('products', [])
                for product in products:
                    for variant in product.get('variants', []):
                        if variant.get('sku') == sku:
                            return product
            return None

        except Exception as e:
            log.log(f"Error Shopify search: {e}", "warning")
            return None


# ============================================================================
# PROCESADORES DE ARCHIVOS
# ============================================================================

class BaseProcessor(ABC):
    """Clase base para procesadores."""

    def __init__(self, config: dict):
        self.config = config
        self.output_dir = config.get('output_dir', DEFAULT_OUTPUT_DIR)
        self.prefix = config.get('prefix', 'SRM')
        self.detector = IndustryDetector()
        self.ai_client = None

    def _get_ai_client(self) -> AIClient:
        if not self.ai_client:
            self.ai_client = AIClient()
        return self.ai_client

    @abstractmethod
    def process(self, filepath: str) -> ProcessingResult:
        pass


class PDFProcessor(BaseProcessor):
    """Procesa archivos PDF con detección automática."""

    def process(self, filepath: str) -> ProcessingResult:
        log.log(f"Procesando PDF: {Path(filepath).name}", "step")
        result = ProcessingResult(source_file=filepath, source_type="pdf")
        start_time = time.time()

        try:
            ai = self._get_ai_client()
            pages_dir = ensure_dir(os.path.join(self.output_dir, "pages"))
            crops_dir = ensure_dir(os.path.join(self.output_dir, "crops"))

            # Obtener páginas a procesar
            page_count = self._get_page_count(filepath)
            pages = self.config.get('pages') or list(range(1, min((page_count or 50) + 1, 100)))

            log.log(f"   Páginas: {len(pages)}")

            # Procesar primera página para detectar industria/cliente
            first_page_img = os.path.join(pages_dir, "page_001.jpg")
            if self._convert_page(filepath, pages[0], first_page_img):
                # Análisis rápido para detección
                detection_result = ai.analyze_image(first_page_img, """
                Analiza esta página de catálogo e identifica:
                1. ¿Qué tipo de productos contiene? (motos, carros, ferretería, electrónica, etc.)
                2. ¿Hay alguna marca o empresa identificable?

                RESPONDE JSON: {"tipo_productos": "...", "industria": "...", "marca": "...", "empresa": "..."}
                """)

                # Detectar industria
                detection_text = json.dumps(detection_result)
                result.detected_industry, _ = self.detector.detect_industry(
                    detection_text, Path(filepath).name
                )
                result.detected_client, _ = self.detector.detect_client(
                    detection_text, result.detected_industry, Path(filepath).name
                )

                log.log(f"   Industria detectada: {result.detected_industry}", "success")
                if result.detected_client:
                    log.log(f"   Cliente detectado: {result.detected_client}", "success")

            # Procesar todas las páginas
            for i, page_num in enumerate(pages, 1):
                log.log(f"   [{i}/{len(pages)}] Página {page_num}...")

                page_img = os.path.join(pages_dir, f"page_{page_num:03d}.jpg")
                if not self._convert_page(filepath, page_num, page_img):
                    continue

                # Extraer productos
                products = self._extract_products(ai, page_img, page_num, result.detected_industry)

                # Detectar crops
                if CV2_AVAILABLE:
                    crops = self._detect_crops(page_img, crops_dir, page_num)
                    if crops and products:
                        products = self._associate_crops(products, crops)

                # Asignar industria y cliente a productos
                for p in products:
                    p.industria = result.detected_industry
                    p.cliente = result.detected_client or self.prefix

                result.products.extend(products)
                log.log(f"      {len(products)} productos", "success")

                gc.collect()

            result.success = True

        except Exception as e:
            result.errors.append(str(e))
            log.log(f"Error: {e}", "error")

        result.processing_time = time.time() - start_time
        return result

    def _get_page_count(self, filepath: str) -> Optional[int]:
        try:
            result = subprocess.run(['pdfinfo', filepath], capture_output=True, text=True, timeout=30)
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        except:
            pass
        return None

    def _convert_page(self, pdf_path: str, page_num: int, output_path: str) -> bool:
        try:
            base = output_path.rsplit('.', 1)[0]
            dpi = self.config.get('dpi', 150)
            cmd = ['pdftoppm', '-jpeg', '-r', str(dpi), '-f', str(page_num),
                   '-l', str(page_num), '-singlefile', pdf_path, base]
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            return result.returncode == 0 and os.path.exists(output_path)
        except:
            return False

    def _extract_products(self, ai: AIClient, image_path: str, page_num: int, industry: str) -> List[ProductData]:
        industry_name = INDUSTRIES.get(industry, {}).get('name', 'productos')

        prompt = f"""Analiza esta página de catálogo de {industry_name}.

EXTRAE todos los productos con:
- codigo: Código/referencia
- nombre: Nombre comercial
- descripcion: Especificaciones técnicas
- precio: Valor numérico
- categoria: Categoría del producto
- marca: Marca visible
- posicion_vertical: 1-10 (1=arriba)

RESPONDE JSON: {{"productos": [...]}}"""

        data = ai.analyze_image(image_path, prompt)
        products = []

        for p in data.get("productos", []):
            product = ProductData(
                codigo=clean_text(p.get('codigo', '')),
                nombre=clean_text(p.get('nombre', '')),
                descripcion=clean_text(p.get('descripcion', '')),
                precio=clean_price(p.get('precio', 0)),
                categoria=self.detector.detect_category(
                    p.get('nombre', '') + ' ' + p.get('categoria', ''),
                    industry
                ),
                marca=clean_text(p.get('marca', '')),
                pagina=page_num,
                fuente=Path(image_path).name
            )

            if p.get('posicion_vertical'):
                product.atributos['posicion_y'] = int(p['posicion_vertical'])

            if product.is_valid():
                product.sku = f"{self.prefix}-{product.codigo}" if product.codigo else ""
                products.append(product)

        return products

    def _detect_crops(self, image_path: str, output_dir: str, page_num: int) -> List[dict]:
        if not CV2_AVAILABLE:
            return []

        try:
            img = cv2.imread(image_path)
            if img is None:
                return []

            height, width = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 30, 100)
            kernel = np.ones((5, 5), np.uint8)
            dilated = cv2.dilate(edges, kernel, iterations=2)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            crops = []
            for i, contour in enumerate(contours):
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h

                if w < 50 or h < 50 or area > (height * width * 0.5):
                    continue

                crop_img = img[y:y+h, x:x+w]
                filename = f"{self.prefix}_p{page_num:03d}_c{i+1:02d}.jpg"
                path = os.path.join(output_dir, filename)
                cv2.imwrite(path, crop_img, [cv2.IMWRITE_JPEG_QUALITY, 90])

                crops.append({
                    'filename': filename,
                    'path': path,
                    'y_normalized': y / height,
                    'assigned': False
                })

            return crops[:20]
        except:
            return []

    def _associate_crops(self, products: List[ProductData], crops: List[dict]) -> List[ProductData]:
        for product in sorted(products, key=lambda p: p.atributos.get('posicion_y', 5)):
            pos_y = (product.atributos.get('posicion_y', 5) - 1) / 9

            best_crop = None
            best_distance = float('inf')

            for crop in crops:
                if crop['assigned']:
                    continue
                distance = abs(pos_y - crop['y_normalized'])
                if distance < best_distance:
                    best_distance = distance
                    best_crop = crop

            if best_crop and best_distance < 0.25:
                product.imagen = best_crop['filename']
                if best_crop.get('path'):
                    product.imagenes = [f"{IMAGE_SERVER_URL}/{best_crop['filename']}"]
                best_crop['assigned'] = True

        return products


class ExcelProcessor(BaseProcessor):
    """Procesa archivos Excel."""

    def process(self, filepath: str) -> ProcessingResult:
        log.log(f"Procesando Excel: {Path(filepath).name}", "step")
        result = ProcessingResult(source_file=filepath, source_type="excel")
        start_time = time.time()

        try:
            xls = pd.ExcelFile(filepath)

            # Detectar industria del contenido
            all_text = ""
            for sheet in xls.sheet_names[:3]:
                df = pd.read_excel(filepath, sheet_name=sheet, nrows=50)
                all_text += " ".join(df.astype(str).values.flatten()[:500])

            result.detected_industry, _ = self.detector.detect_industry(all_text, filepath)
            result.detected_client, _ = self.detector.detect_client(
                all_text, result.detected_industry, filepath
            )

            log.log(f"   Industria: {result.detected_industry}", "success")

            for sheet_name in xls.sheet_names:
                log.log(f"   Hoja: {sheet_name}")
                df = pd.read_excel(filepath, sheet_name=sheet_name)

                if df.empty:
                    continue

                products = self._extract_from_dataframe(df, sheet_name, result.detected_industry)

                for p in products:
                    p.industria = result.detected_industry
                    p.cliente = result.detected_client or self.prefix

                result.products.extend(products)
                log.log(f"      {len(products)} productos", "success")

            result.success = True

        except Exception as e:
            result.errors.append(str(e))
            log.log(f"Error: {e}", "error")

        result.processing_time = time.time() - start_time
        return result

    def _extract_from_dataframe(self, df: pd.DataFrame, source: str, industry: str) -> List[ProductData]:
        df.columns = [str(c).lower().strip() for c in df.columns]

        column_maps = {
            'codigo': ['codigo', 'code', 'ref', 'referencia', 'sku', 'id', 'part'],
            'nombre': ['nombre', 'name', 'descripcion', 'description', 'producto', 'titulo'],
            'precio': ['precio', 'price', 'valor', 'value', 'costo', 'pvp'],
            'categoria': ['categoria', 'category', 'familia', 'tipo', 'linea'],
            'marca': ['marca', 'brand', 'fabricante'],
            'stock': ['stock', 'cantidad', 'qty', 'existencia'],
        }

        mapped = {}
        for field, options in column_maps.items():
            for opt in options:
                if opt in df.columns:
                    mapped[field] = opt
                    break

        products = []
        for _, row in df.iterrows():
            product = ProductData(
                codigo=clean_text(row.get(mapped.get('codigo', ''), '')),
                nombre=clean_text(row.get(mapped.get('nombre', ''), '')),
                precio=clean_price(row.get(mapped.get('precio', ''), 0)),
                categoria=self.detector.detect_category(
                    str(row.get(mapped.get('categoria', ''), '')),
                    industry
                ),
                marca=clean_text(row.get(mapped.get('marca', ''), '')),
                stock=int(row.get(mapped.get('stock', ''), 0) or 0),
                fuente=source
            )

            if product.is_valid():
                product.sku = f"{self.prefix}-{product.codigo}" if product.codigo else ""
                products.append(product)

        return products


class CSVProcessor(BaseProcessor):
    """Procesa archivos CSV."""

    def process(self, filepath: str) -> ProcessingResult:
        log.log(f"Procesando CSV: {Path(filepath).name}", "step")
        result = ProcessingResult(source_file=filepath, source_type="csv")

        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                sample = f.read(4096)

            sep = max([';', ',', '\t', '|'], key=lambda s: sample.count(s))
            df = pd.read_csv(filepath, sep=sep, encoding='utf-8-sig')

            # Detectar industria
            all_text = " ".join(df.astype(str).values.flatten()[:500])
            result.detected_industry, _ = self.detector.detect_industry(all_text, filepath)
            result.detected_client, _ = self.detector.detect_client(
                all_text, result.detected_industry, filepath
            )

            excel_proc = ExcelProcessor(self.config)
            excel_proc.detector = self.detector
            products = excel_proc._extract_from_dataframe(df, Path(filepath).name, result.detected_industry)

            for p in products:
                p.industria = result.detected_industry
                p.cliente = result.detected_client or self.prefix

            result.products = products
            result.success = True
            log.log(f"   {len(products)} productos", "success")

        except Exception as e:
            result.errors.append(str(e))
            log.log(f"Error: {e}", "error")

        return result


class ImageProcessor(BaseProcessor):
    """Procesa imágenes individuales."""

    def process(self, filepath: str) -> ProcessingResult:
        log.log(f"Procesando imagen: {Path(filepath).name}", "step")
        result = ProcessingResult(source_file=filepath, source_type="image")

        try:
            ai = self._get_ai_client()

            data = ai.analyze_image(filepath, """
Analiza esta imagen de producto e identifica:
- tipo_industria: motos, carros, ferreteria, electronica, hogar, industrial
- codigo: código visible
- nombre: nombre descriptivo para catálogo
- descripcion: descripción técnica
- categoria: categoría del producto
- marca: marca identificable
- atributos: {material, color, medidas, etc.}
- tags: [palabras clave]

RESPONDE JSON con estos campos.""")

            # Detectar industria
            result.detected_industry, _ = self.detector.detect_industry(
                json.dumps(data), filepath
            )

            product = ProductData(
                codigo=clean_text(data.get('codigo', '')),
                nombre=clean_text(data.get('nombre', '')),
                descripcion=clean_text(data.get('descripcion', '')),
                categoria=self.detector.detect_category(
                    data.get('categoria', ''), result.detected_industry
                ),
                marca=clean_text(data.get('marca', '')),
                imagen=Path(filepath).name,
                imagenes=[f"{IMAGE_SERVER_URL}/{Path(filepath).name}"],
                tags=data.get('tags', []),
                industria=result.detected_industry,
                fuente=Path(filepath).name
            )

            if product.nombre:
                product.sku = f"{self.prefix}-{product.codigo or 'IMG'}"
                result.products.append(product)

            result.success = True
            log.log(f"   Producto: {product.nombre[:50]}", "success")

        except Exception as e:
            result.errors.append(str(e))
            log.log(f"Error: {e}", "error")

        return result


class URLProcessor(BaseProcessor):
    """Procesa URLs (scraping)."""

    def process(self, url: str) -> ProcessingResult:
        log.log(f"Scraping: {url}", "step")
        result = ProcessingResult(source_file=url, source_type="url")

        if not BS4_AVAILABLE:
            result.errors.append("BeautifulSoup no disponible")
            return result

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extraer texto para detección
            text = soup.get_text(separator=' ', strip=True)[:5000]
            result.detected_industry, _ = self.detector.detect_industry(text, url)

            # Buscar productos
            products = self._extract_products(soup, url, result.detected_industry)

            if not products:
                # Usar AI como fallback
                ai = self._get_ai_client()
                data = ai.analyze_text(text, """
Extrae productos de este contenido web.
RESPONDE JSON: {"productos": [{"codigo": "", "nombre": "", "descripcion": "", "precio": 0}]}
""")
                for p in data.get("productos", []):
                    product = ProductData(
                        codigo=clean_text(p.get('codigo', '')),
                        nombre=clean_text(p.get('nombre', '')),
                        descripcion=clean_text(p.get('descripcion', '')),
                        precio=clean_price(p.get('precio', 0)),
                        industria=result.detected_industry,
                        fuente=url
                    )
                    if product.is_valid():
                        products.append(product)

            result.products = products
            result.success = True
            log.log(f"   {len(products)} productos", "success")

        except Exception as e:
            result.errors.append(str(e))
            log.log(f"Error: {e}", "error")

        return result

    def _extract_products(self, soup: BeautifulSoup, url: str, industry: str) -> List[ProductData]:
        products = []

        selectors = ['.product', '.producto', '.item', '[data-product]', '.product-card']

        for selector in selectors:
            elements = soup.select(selector)
            if not elements:
                continue

            for elem in elements:
                name_elem = elem.select_one('h1, h2, h3, .title, .name, .product-title')
                name = name_elem.get_text(strip=True) if name_elem else ''

                price_elem = elem.select_one('.price, .precio, [class*="price"]')
                price = clean_price(price_elem.get_text(strip=True)) if price_elem else 0

                sku_elem = elem.select_one('.sku, .codigo, [class*="sku"]')
                sku = sku_elem.get_text(strip=True) if sku_elem else ''

                img_elem = elem.select_one('img')
                img = img_elem.get('src', '') if img_elem else ''
                if img and not img.startswith('http'):
                    img = urllib.parse.urljoin(url, img)

                if name:
                    product = ProductData(
                        codigo=sku,
                        nombre=name,
                        precio=price,
                        imagen=img,
                        imagenes=[img] if img else [],
                        industria=industry,
                        fuente=url
                    )
                    product.sku = f"{self.prefix}-{sku}" if sku else ""
                    products.append(product)

            break

        return products


class ZIPProcessor(BaseProcessor):
    """Procesa archivos ZIP."""

    def process(self, filepath: str) -> ProcessingResult:
        log.log(f"Procesando ZIP: {Path(filepath).name}", "step")
        result = ProcessingResult(source_file=filepath, source_type="zip")

        try:
            extract_dir = ensure_dir(os.path.join(self.output_dir, "extracted"))

            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            for root, dirs, files in os.walk(extract_dir):
                for file in files[:500]:
                    file_path = os.path.join(root, file)
                    file_type = detect_file_type(file_path)

                    if file_type == 'unknown':
                        continue

                    processor = get_processor(file_type, self.config)
                    if processor:
                        sub_result = processor.process(file_path)
                        result.products.extend(sub_result.products)

                        if not result.detected_industry and sub_result.detected_industry:
                            result.detected_industry = sub_result.detected_industry

            result.success = True
            log.log(f"   Total: {len(result.products)} productos", "success")

        except Exception as e:
            result.errors.append(str(e))
            log.log(f"Error: {e}", "error")

        return result


# ============================================================================
# FACTORY
# ============================================================================

def get_processor(file_type: str, config: dict) -> Optional[BaseProcessor]:
    processors = {
        'pdf': PDFProcessor,
        'excel': ExcelProcessor,
        'csv': CSVProcessor,
        'image': ImageProcessor,
        'url': URLProcessor,
        'zip': ZIPProcessor,
    }

    # Word y TXT usan el mismo enfoque que Excel/CSV con AI
    if file_type == 'word' and DOCX_AVAILABLE:
        return None  # TODO: Implementar WordProcessor
    if file_type == 'txt':
        return None  # TODO: Implementar TXTProcessor

    processor_class = processors.get(file_type)
    return processor_class(config) if processor_class else None


# ============================================================================
# PIPELINE PRINCIPAL
# ============================================================================

class SRMPipeline:
    """Pipeline completo SRM Intelligent."""

    def __init__(self, config: dict):
        self.config = config
        self.output_dir = ensure_dir(config.get('output_dir', DEFAULT_OUTPUT_DIR))
        self.prefix = config.get('prefix', 'SRM')
        self.push_to_shopify = config.get('push_shopify', False)
        self.all_products: List[ProductData] = []
        self.detected_industry = ""
        self.detected_client = ""

        # Event Emitter para Cortex Visual (Tony narra)
        if EMITTER_AVAILABLE:
            self.emitter = ODIEventEmitter(source="srm", actor="SRM_PROCESSOR_v4")
        else:
            self.emitter = None

    def process(self, source: str) -> Tuple[str, str]:
        """Ejecuta pipeline completo."""
        self._print_banner()

        # === EMIT: Pipeline Start ===
        if self.emitter:
            self.emitter.srm_pipeline_start(source)

        # 1. INGESTA
        log.step(1, 6, "INGESTA")
        if self.emitter:
            self.emitter.srm_step(1, "INGESTA", {"source": os.path.basename(source)})
        result = self._ingest(source)

        if not result.success:
            log.log(f"Error: {result.errors}", "error")
            if self.emitter:
                self.emitter.error(f"Ingesta fallida: {result.errors}")
            return "", ""

        self.all_products = result.products
        self.detected_industry = result.detected_industry
        self.detected_client = result.detected_client

        log.log(f"Productos: {len(self.all_products)}", "success")
        log.log(f"Industria: {self.detected_industry}", "success")

        # === EMIT: Industry/Client Detected ===
        if self.emitter and self.detected_industry:
            self.emitter.srm_industry_detected(self.detected_industry, 0.9)
        if self.detected_client:
            log.log(f"Cliente: {self.detected_client}", "success")
            if self.emitter:
                self.emitter.srm_client_detected(self.detected_client, "auto-detected")

        # 2. EXTRACCIÓN (completada en ingesta)
        log.step(2, 6, "EXTRACCIÓN")
        if self.emitter:
            self.emitter.srm_step(2, "EXTRACCION", {"products_found": len(self.all_products)})
        log.log(f"Datos extraídos de {result.source_type}", "success")

        # 3. NORMALIZACIÓN
        log.step(3, 6, "NORMALIZACIÓN")
        if self.emitter:
            self.emitter.srm_step(3, "NORMALIZACION", {"products_before": len(self.all_products)})
        self._normalize()

        # 4. UNIFICACIÓN
        log.step(4, 6, "UNIFICACIÓN")
        if self.emitter:
            self.emitter.srm_step(4, "UNIFICACION", {"products": len(self.all_products)})
        self._unify()

        # 5. ENRIQUECIMIENTO
        log.step(5, 6, "ENRIQUECIMIENTO")
        if self.emitter:
            self.emitter.srm_step(5, "ENRIQUECIMIENTO", {"products": len(self.all_products)})
        self._enrich()

        # 6. FICHA 360° / EXPORTACIÓN
        log.step(6, 6, "FICHA 360°")
        if self.emitter:
            self.emitter.srm_step(6, "FICHA_360", {"products": len(self.all_products)})
        csv_path, json_path = self._export()

        # Push a Shopify si está configurado
        if self.push_to_shopify and self.detected_client:
            if self.emitter:
                client_config = CLIENTS.get(self.detected_industry, {}).get(self.detected_client, {})
                shop = client_config.get('shop', 'unknown')
                self.emitter.srm_shopify_push(shop, len(self.all_products))
            self._push_to_shopify()

        # === EMIT: Pipeline Complete ===
        if self.emitter:
            self.emitter.srm_complete(len(self.all_products), csv_path, json_path)

        self._print_summary(csv_path, json_path)
        return csv_path, json_path

    def _ingest(self, source: str) -> ProcessingResult:
        if source.startswith('http://') or source.startswith('https://'):
            processor = URLProcessor(self.config)
            return processor.process(source)

        if not os.path.exists(source):
            return ProcessingResult(errors=[f"Archivo no encontrado: {source}"])

        file_type = detect_file_type(source)
        log.log(f"Tipo: {file_type}")

        processor = get_processor(file_type, self.config)
        if not processor:
            return ProcessingResult(errors=[f"Tipo no soportado: {file_type}"])

        return processor.process(source)

    def _normalize(self):
        seen = set()
        normalized = []

        for p in self.all_products:
            p.nombre = clean_text(p.nombre)
            p.descripcion = clean_text(p.descripcion)
            p.codigo = re.sub(r'[^a-zA-Z0-9-]', '', p.codigo)

            if p.codigo:
                if p.codigo in seen:
                    continue
                seen.add(p.codigo)

            if not p.sku and p.codigo:
                p.sku = f"{self.prefix}-{p.codigo}"

            normalized.append(p)

        log.log(f"Normalizados: {len(normalized)} (duplicados: {len(self.all_products) - len(normalized)})", "success")
        self.all_products = normalized

    def _unify(self):
        detector = IndustryDetector()
        for p in self.all_products:
            if not p.categoria or p.categoria == "OTROS":
                p.categoria = detector.detect_category(p.nombre, self.detected_industry)

            if not p.descripcion_corta and p.descripcion:
                p.descripcion_corta = p.descripcion[:150]

        categories = {}
        for p in self.all_products:
            categories[p.categoria] = categories.get(p.categoria, 0) + 1

        log.log(f"Categorías: {len(categories)}", "success")

    def _enrich(self):
        for p in self.all_products:
            if not p.id:
                p.id = f"{self.prefix}-{hashlib.md5(f'{p.codigo}{p.nombre}'.encode()).hexdigest()[:8]}"

            if not p.tags:
                tags = [p.categoria.lower()] if p.categoria else []
                if p.marca:
                    tags.append(p.marca.lower())
                tags.extend(p.nombre.lower().split()[:3])
                p.tags = list(set(tags))

        log.log(f"Enriquecidos: {len(self.all_products)}", "success")

    def _export(self) -> Tuple[str, str]:
        if not self.all_products:
            return "", ""

        records = [p.to_dict() for p in self.all_products]
        df = pd.DataFrame(records)

        priority_cols = ['sku', 'codigo', 'nombre', 'descripcion', 'precio',
                        'categoria', 'marca', 'imagen', 'stock', 'industria', 'cliente']
        cols = [c for c in priority_cols if c in df.columns]
        cols += [c for c in df.columns if c not in cols]
        df = df[cols]

        csv_path = os.path.join(self.output_dir, f"{self.prefix}_catalogo.csv")
        df.to_csv(csv_path, sep=';', index=False, encoding='utf-8')

        json_path = os.path.join(self.output_dir, f"{self.prefix}_catalogo.json")
        export_data = {
            "metadata": {
                "version": VERSION,
                "generated": datetime.now().isoformat(),
                "industry": self.detected_industry,
                "client": self.detected_client,
                "total_products": len(self.all_products),
            },
            "products": records
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        log.log(f"CSV: {csv_path}", "success")
        log.log(f"JSON: {json_path}", "success")

        return csv_path, json_path

    def _push_to_shopify(self):
        """Push productos a Shopify del cliente detectado."""
        if not SHOPIFY_AVAILABLE:
            log.log("Shopify SDK no disponible", "warning")
            return

        client_config = CLIENTS.get(self.detected_industry, {}).get(self.detected_client)
        if not client_config:
            log.log(f"Cliente {self.detected_client} no configurado", "warning")
            return

        shop = client_config.get('shop')
        token = client_config.get('token')

        if not shop or not token:
            log.log(f"Credenciales Shopify incompletas para {self.detected_client}", "warning")
            return

        log.log(f"Pushing a Shopify: {shop}...")
        shopify_client = ShopifyClient(shop, token)

        created = 0
        updated = 0
        errors = 0

        for product in self.all_products:
            try:
                # Buscar si existe
                existing = shopify_client.find_product_by_sku(product.sku)

                if existing:
                    result = shopify_client.update_product(existing['id'], product)
                    if result:
                        updated += 1
                else:
                    result = shopify_client.create_product(product)
                    if result:
                        created += 1

                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                errors += 1
                log.log(f"Error Shopify: {e}", "warning")

        log.log(f"Shopify: {created} creados, {updated} actualizados, {errors} errores", "success")

    def _print_banner(self):
        print(f"""
{Colors.BOLD}╔══════════════════════════════════════════════════════════════════════╗
║                    🚀 {SCRIPT_NAME} v{VERSION}                       ║
║              Procesador Universal Multi-Industria Multi-Tenant       ║
╚══════════════════════════════════════════════════════════════════════╝{Colors.RESET}
""")

    def _print_summary(self, csv_path: str, json_path: str):
        with_price = sum(1 for p in self.all_products if p.precio > 0)
        with_image = sum(1 for p in self.all_products if p.imagen)

        industry_name = INDUSTRIES.get(self.detected_industry, {}).get('name', self.detected_industry)

        print(f"""
{Colors.BOLD}{'='*70}
📊 RESUMEN - FICHA 360°
{'='*70}{Colors.RESET}

{Colors.GREEN}✓ Industria:{Colors.RESET}          {industry_name}
{Colors.GREEN}✓ Cliente:{Colors.RESET}            {self.detected_client or 'No detectado'}
{Colors.GREEN}✓ Total productos:{Colors.RESET}   {len(self.all_products)}
{Colors.GREEN}✓ Con precio:{Colors.RESET}        {with_price}
{Colors.GREEN}✓ Con imagen:{Colors.RESET}        {with_image}
{Colors.CYAN}○ Tiempo:{Colors.RESET}            {log.elapsed()}

{Colors.BOLD}📁 ARCHIVOS:{Colors.RESET}
   {csv_path}
   {json_path}

{Colors.BOLD}{'='*70}{Colors.RESET}
""")


# ============================================================================
# CLI
# ============================================================================

def print_help():
    industries = ", ".join(INDUSTRIES.keys())

    print(f"""
{Colors.BOLD}{SCRIPT_NAME} v{VERSION}{Colors.RESET}
{'='*70}

{Colors.CYAN}USO:{Colors.RESET}
    python3 srm_intelligent_processor.py <archivo_o_url> [opciones]

{Colors.CYAN}FORMATOS:{Colors.RESET}
    PDF, Excel, CSV, Word, TXT, Imágenes, ZIP, URLs

{Colors.CYAN}OPCIONES:{Colors.RESET}
    --output, -o DIR      Directorio de salida
    --prefix PREFIX       Prefijo SKU (default: SRM)
    --industry INDUSTRY   Forzar industria: {industries}
    --client CLIENT       Forzar cliente (KAIQI, BARA, DFG, etc.)
    --pages PAGES         Páginas PDF: "2-50", "all"
    --push-shopify        Push automático a Shopify del cliente
    --help, -h            Mostrar ayuda

{Colors.CYAN}EJEMPLOS:{Colors.RESET}
    # Auto-detecta industria y cliente
    python3 srm_intelligent_processor.py catalogo_kaiqi.pdf

    # Forzar industria
    python3 srm_intelligent_processor.py productos.xlsx --industry autopartes_motos

    # Push a Shopify
    python3 srm_intelligent_processor.py catalogo.pdf --push-shopify

    # Scraping
    python3 srm_intelligent_processor.py "https://competencia.com/catalogo"

{Colors.CYAN}VARIABLES DE ENTORNO:{Colors.RESET}
    OPENAI_API_KEY, ANTHROPIC_API_KEY
    KAIQI_SHOP, KAIQI_TOKEN, BARA_SHOP, BARA_TOKEN, etc.
""")


def main():
    if '--help' in sys.argv or '-h' in sys.argv or len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    config = {
        'source': sys.argv[1],
        'output_dir': DEFAULT_OUTPUT_DIR,
        'prefix': 'SRM',
        'push_shopify': False,
    }

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ['--output', '-o'] and i + 1 < len(sys.argv):
            config['output_dir'] = sys.argv[i + 1]
            i += 2
        elif arg == '--prefix' and i + 1 < len(sys.argv):
            config['prefix'] = sys.argv[i + 1].upper()
            i += 2
        elif arg == '--industry' and i + 1 < len(sys.argv):
            config['force_industry'] = sys.argv[i + 1]
            i += 2
        elif arg == '--client' and i + 1 < len(sys.argv):
            config['force_client'] = sys.argv[i + 1].upper()
            i += 2
        elif arg == '--pages' and i + 1 < len(sys.argv):
            pages_str = sys.argv[i + 1]
            if pages_str.lower() != 'all':
                pages = set()
                for part in pages_str.split(','):
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        pages.update(range(start, end + 1))
                    else:
                        pages.add(int(part))
                config['pages'] = sorted(pages)
            i += 2
        elif arg == '--push-shopify':
            config['push_shopify'] = True
            i += 1
        else:
            i += 1

    # Validar API key
    if not os.getenv('OPENAI_API_KEY') and not os.getenv('ANTHROPIC_API_KEY'):
        log.log("Se requiere OPENAI_API_KEY o ANTHROPIC_API_KEY", "error")
        sys.exit(1)

    try:
        pipeline = SRMPipeline(config)
        pipeline.process(config['source'])
    except KeyboardInterrupt:
        log.log("\nInterrumpido", "warning")
        sys.exit(130)
    except Exception as e:
        log.log(f"Error: {e}", "error")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
