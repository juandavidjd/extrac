#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════
                    ODI VISION EXTRACTOR v3.0
              Script Universal de Extracción de Catálogos
══════════════════════════════════════════════════════════════════════════════

DESCRIPCIÓN:
    Extractor industrial de catálogos PDF que genera datos estructurados
    + imágenes individuales de productos listos para e-commerce (Shopify).

CARACTERÍSTICAS:
    ✓ Extracción con GPT-4o Vision (código, nombre, descripción, precio)
    ✓ Detección y recorte automático de imágenes de productos
    ✓ Asociación imagen-producto por posición en página
    ✓ Sistema de checkpoint para procesos largos
    ✓ Manejo eficiente de memoria (página por página)
    ✓ Rate limit handling con backoff exponencial
    ✓ Taxonomía de categorías normalizada
    ✓ Salida CSV/JSON lista para Shopify

INSTALACIÓN:
    pip install openai pandas opencv-python pillow

USO:
    python3 odi_vision_extractor_v3.py <pdf> <páginas> [opciones]

EJEMPLOS:
    python3 odi_vision_extractor_v3.py catalogo.pdf 2-50 --prefix ARM
    python3 odi_vision_extractor_v3.py catalogo.pdf all --output /data/output

AUTOR: ODI Team
VERSIÓN: 3.0
══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import gc
import json
import base64
import re
import time
import signal
import hashlib
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor
import threading

# ============================================================================
# DEPENDENCIAS
# ============================================================================

def check_dependencies():
    """Verifica e importa dependencias."""
    missing = []

    global pd, np, cv2, Image, OpenAI

    try:
        import pandas as pd
    except ImportError:
        missing.append("pandas")

    try:
        import numpy as np
        import cv2
    except ImportError:
        missing.append("opencv-python numpy")

    try:
        from PIL import Image
    except ImportError:
        missing.append("pillow")

    try:
        from openai import OpenAI
    except ImportError:
        missing.append("openai")

    if missing:
        print(f"❌ Dependencias faltantes: {', '.join(missing)}")
        print(f"   Instalar: pip install {' '.join(missing)}")
        sys.exit(1)

    return True

check_dependencies()
import pandas as pd
import numpy as np
import cv2
from PIL import Image
from openai import OpenAI

# Event Emitter para Cortex Visual
try:
    from odi_event_emitter import ODIEventEmitter
    EMITTER_AVAILABLE = True
except ImportError:
    EMITTER_AVAILABLE = False
    ODIEventEmitter = None


# ============================================================================
# CONFIGURACIÓN GLOBAL
# ============================================================================

VERSION = "3.0"
SCRIPT_NAME = "ODI Vision Extractor"

# Directorios por defecto
DEFAULT_OUTPUT_DIR = "/tmp/odi_output"
DEFAULT_TEMP_DIR = "/tmp/odi_temp"
DEFAULT_CHECKPOINT_DIR = "/tmp/odi_checkpoints"

# Configuración de procesamiento
DEFAULT_DPI = 150
MAX_DPI = 300
MIN_DPI = 100

# Configuración de Vision API
VISION_MODEL = "gpt-4o"
MAX_TOKENS = 4096
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 2
MAX_RETRY_DELAY = 60
REQUEST_TIMEOUT = 120

# Throttling
MIN_REQUEST_INTERVAL = 0.5  # Segundos entre requests
CHECKPOINT_INTERVAL = 3     # Guardar checkpoint cada N páginas

# Configuración de detección de imágenes
MIN_CROP_WIDTH = 50
MIN_CROP_HEIGHT = 50
MAX_CROP_RATIO = 0.5        # Máximo 50% del área de página
MIN_CROP_RATIO = 0.005      # Mínimo 0.5% del área
CROP_PADDING = 5
MAX_CROPS_PER_PAGE = 25

# Configuración de asociación
MAX_POSITION_DISTANCE = 0.25  # 25% de la altura de página


# ============================================================================
# TAXONOMÍA DE CATEGORÍAS
# ============================================================================

CATEGORY_TAXONOMY = {
    # Motor
    "motor": "MOTOR", "culata": "MOTOR", "piston": "MOTOR", "pistón": "MOTOR",
    "biela": "MOTOR", "cigueñal": "MOTOR", "cigüeñal": "MOTOR", "valvula": "MOTOR",
    "válvula": "MOTOR", "cilindro": "MOTOR", "camisa": "MOTOR", "aro": "MOTOR",
    "anillo": "MOTOR", "junta": "MOTOR", "empaque": "MOTOR", "reten": "MOTOR",
    "retén": "MOTOR", "balancin": "MOTOR", "balancín": "MOTOR", "arbol": "MOTOR",
    "árbol": "MOTOR", "leva": "MOTOR", "carter": "MOTOR", "cárter": "MOTOR",

    # Frenos
    "freno": "FRENOS", "frenos": "FRENOS", "pastilla": "FRENOS", "disco": "FRENOS",
    "zapata": "FRENOS", "caliper": "FRENOS", "mordaza": "FRENOS", "bomba freno": "FRENOS",
    "manigueta": "FRENOS", "cable freno": "FRENOS", "tambor": "FRENOS",

    # Eléctrico
    "electrico": "ELECTRICO", "eléctrico": "ELECTRICO", "bobina": "ELECTRICO",
    "cdi": "ELECTRICO", "bateria": "ELECTRICO", "batería": "ELECTRICO",
    "faro": "ELECTRICO", "luz": "ELECTRICO", "bombillo": "ELECTRICO",
    "direccional": "ELECTRICO", "flasher": "ELECTRICO", "regulador": "ELECTRICO",
    "rectificador": "ELECTRICO", "estator": "ELECTRICO", "rotor": "ELECTRICO",
    "arranque": "ELECTRICO", "motor arranque": "ELECTRICO", "relay": "ELECTRICO",
    "fusible": "ELECTRICO", "switch": "ELECTRICO", "interruptor": "ELECTRICO",
    "velocimetro": "ELECTRICO", "velocímetro": "ELECTRICO", "tacometro": "ELECTRICO",
    "tablero": "ELECTRICO", "cable": "ELECTRICO", "encendido": "ELECTRICO",

    # Suspensión
    "suspension": "SUSPENSION", "suspensión": "SUSPENSION", "amortiguador": "SUSPENSION",
    "telescopio": "SUSPENSION", "horquilla": "SUSPENSION", "resorte": "SUSPENSION",
    "buje": "SUSPENSION", "rodamiento": "SUSPENSION", "balinera": "SUSPENSION",

    # Transmisión
    "transmision": "TRANSMISION", "transmisión": "TRANSMISION", "cadena": "TRANSMISION",
    "piñon": "TRANSMISION", "piñón": "TRANSMISION", "catalina": "TRANSMISION",
    "sprocket": "TRANSMISION", "clutch": "TRANSMISION", "embrague": "TRANSMISION",
    "disco clutch": "TRANSMISION", "plato": "TRANSMISION", "campana": "TRANSMISION",
    "centrifugo": "TRANSMISION", "centrífugo": "TRANSMISION", "variador": "TRANSMISION",
    "correa": "TRANSMISION", "kit arrastre": "TRANSMISION",

    # Carrocería
    "carroceria": "CARROCERIA", "carrocería": "CARROCERIA", "plastico": "CARROCERIA",
    "plástico": "CARROCERIA", "carenaje": "CARROCERIA", "guardafango": "CARROCERIA",
    "guardabarro": "CARROCERIA", "tanque": "CARROCERIA", "tapa": "CARROCERIA",
    "colepato": "CARROCERIA", "cola": "CARROCERIA", "lateral": "CARROCERIA",
    "salpicadera": "CARROCERIA", "parrilla": "CARROCERIA", "asiento": "CARROCERIA",
    "sillin": "CARROCERIA", "sillín": "CARROCERIA",

    # Dirección
    "direccion": "DIRECCION", "dirección": "DIRECCION", "manubrio": "DIRECCION",
    "manillar": "DIRECCION", "tijera": "DIRECCION", "columna": "DIRECCION",

    # Ruedas
    "rueda": "RUEDAS", "llanta": "RUEDAS", "rin": "RUEDAS", "aro": "RUEDAS",
    "camara": "RUEDAS", "cámara": "RUEDAS", "neumatico": "RUEDAS", "neumático": "RUEDAS",

    # Accesorios
    "accesorio": "ACCESORIOS", "accesorios": "ACCESORIOS", "espejo": "ACCESORIOS",
    "retrovisor": "ACCESORIOS", "parador": "ACCESORIOS", "pata": "ACCESORIOS",
    "pedal": "ACCESORIOS", "pisadera": "ACCESORIOS", "estribo": "ACCESORIOS",
    "defensa": "ACCESORIOS", "slider": "ACCESORIOS", "protector": "ACCESORIOS",
    "maleta": "ACCESORIOS", "baul": "ACCESORIOS", "baúl": "ACCESORIOS",

    # Herramientas
    "herramienta": "HERRAMIENTAS", "herramientas": "HERRAMIENTAS", "llave": "HERRAMIENTAS",
    "extractor": "HERRAMIENTAS", "banco": "HERRAMIENTAS", "dado": "HERRAMIENTAS",

    # Lujos
    "lujo": "LUJOS", "lujos": "LUJOS", "cromado": "LUJOS", "emblema": "LUJOS",
    "calcomania": "LUJOS", "calcomanía": "LUJOS", "adhesivo": "LUJOS",

    # Combustible
    "combustible": "COMBUSTIBLE", "gasolina": "COMBUSTIBLE", "carburador": "COMBUSTIBLE",
    "inyector": "COMBUSTIBLE", "bomba gasolina": "COMBUSTIBLE", "filtro aire": "COMBUSTIBLE",
    "filtro gasolina": "COMBUSTIBLE", "grifo": "COMBUSTIBLE", "petcock": "COMBUSTIBLE",

    # Escape
    "escape": "ESCAPE", "exhosto": "ESCAPE", "silenciador": "ESCAPE", "mofle": "ESCAPE",
    "tubo escape": "ESCAPE", "catalizador": "ESCAPE",
}


# ============================================================================
# LOGGING Y UTILIDADES
# ============================================================================

class Colors:
    """Códigos de color ANSI para terminal."""
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
    """Logger con formato y colores."""

    LEVELS = {
        'debug': (Colors.DIM, ''),
        'info': (Colors.CYAN, ''),
        'success': (Colors.GREEN, '✓'),
        'warning': (Colors.YELLOW, '⚠'),
        'error': (Colors.RED, '✗'),
        'header': (Colors.BOLD, ''),
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

    def progress(self, current: int, total: int, msg: str = ""):
        pct = (current / total * 100) if total > 0 else 0
        bar_len = 30
        filled = int(bar_len * current / total) if total > 0 else 0
        bar = '█' * filled + '░' * (bar_len - filled)
        print(f"\r{Colors.CYAN}[{bar}] {pct:5.1f}% {msg}{Colors.RESET}", end='', flush=True)
        if current >= total:
            print()

    def elapsed(self) -> str:
        elapsed = time.time() - self.start_time
        if elapsed < 60:
            return f"{elapsed:.1f}s"
        elif elapsed < 3600:
            return f"{elapsed/60:.1f}m"
        else:
            return f"{elapsed/3600:.1f}h"


# Logger global
log = Logger()


def ensure_dir(path: str) -> str:
    """Crea directorio si no existe."""
    os.makedirs(path, exist_ok=True)
    return path


def file_hash(filepath: str, length: int = 12) -> str:
    """Genera hash MD5 corto de un archivo."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            hasher.update(chunk)
    return hasher.hexdigest()[:length]


def clean_text(text: Any) -> str:
    """Limpia y normaliza texto."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def clean_price(value: Any) -> float:
    """Extrae valor numérico de precio."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remover todo excepto dígitos y punto
        cleaned = re.sub(r'[^\d.]', '', value)
        # Manejar múltiples puntos
        if cleaned.count('.') > 1:
            parts = cleaned.split('.')
            cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    return 0.0


def normalize_category(text: str) -> str:
    """Normaliza categoría usando taxonomía."""
    if not text:
        return "OTROS"

    text_lower = text.lower().strip()

    # Buscar en taxonomía
    for keyword, category in CATEGORY_TAXONOMY.items():
        if keyword in text_lower:
            return category

    # Si ya es una categoría válida
    text_upper = text.upper()
    valid_categories = set(CATEGORY_TAXONOMY.values())
    if text_upper in valid_categories:
        return text_upper

    return "OTROS"


def slugify(text: str, max_length: int = 50) -> str:
    """Genera slug URL-friendly."""
    text = text.lower()
    text = re.sub(r'[áàäâ]', 'a', text)
    text = re.sub(r'[éèëê]', 'e', text)
    text = re.sub(r'[íìïî]', 'i', text)
    text = re.sub(r'[óòöô]', 'o', text)
    text = re.sub(r'[úùüû]', 'u', text)
    text = re.sub(r'[ñ]', 'n', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text[:max_length]


# ============================================================================
# MODELOS DE DATOS
# ============================================================================

@dataclass
class ProductData:
    """Datos de un producto extraído."""
    codigo: str = ""
    nombre: str = ""
    descripcion: str = ""
    precio: float = 0.0
    categoria: str = ""
    pagina: int = 0
    posicion_y: float = 0.0  # Posición normalizada 0-1
    imagen: str = ""
    sku_odi: str = ""
    fuente: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def is_valid(self) -> bool:
        """Verifica si el producto tiene datos mínimos válidos."""
        return bool(self.codigo and self.codigo.lower() not in ['', 'null', 'none', 'n/a'])


@dataclass
class CropData:
    """Datos de un recorte de imagen."""
    filename: str = ""
    path: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    area: int = 0
    y_center: int = 0
    y_normalized: float = 0.0
    assigned: bool = False

    def __post_init__(self):
        self.area = self.width * self.height
        self.y_center = self.y + self.height // 2


@dataclass
class ProcessingStats:
    """Estadísticas de procesamiento."""
    pages_processed: int = 0
    pages_failed: int = 0
    products_extracted: int = 0
    products_with_image: int = 0
    crops_detected: int = 0
    crops_assigned: int = 0
    api_calls: int = 0
    api_errors: int = 0
    start_time: float = field(default_factory=time.time)

    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time


# ============================================================================
# SISTEMA DE CHECKPOINT
# ============================================================================

class CheckpointManager:
    """Gestiona checkpoints para procesos resumibles."""

    def __init__(self, pdf_path: str, prefix: str, checkpoint_dir: str = DEFAULT_CHECKPOINT_DIR):
        self.checkpoint_dir = ensure_dir(checkpoint_dir)
        pdf_hash = file_hash(pdf_path)
        pdf_name = Path(pdf_path).stem[:30]
        self.checkpoint_file = os.path.join(
            self.checkpoint_dir,
            f"{prefix}_{pdf_name}_{pdf_hash}.json"
        )
        self.lock = threading.Lock()

    def load(self) -> Tuple[List[dict], set]:
        """Carga checkpoint si existe."""
        if not os.path.exists(self.checkpoint_file):
            return [], set()

        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                products = data.get('products', [])
                pages = set(data.get('processed_pages', []))
                log.log(f"Checkpoint cargado: {len(products)} productos, {len(pages)} páginas", "info")
                return products, pages
        except Exception as e:
            log.log(f"Error cargando checkpoint: {e}", "warning")
            return [], set()

    def save(self, products: List[dict], processed_pages: set):
        """Guarda checkpoint."""
        with self.lock:
            try:
                data = {
                    'products': products,
                    'processed_pages': list(processed_pages),
                    'timestamp': datetime.now().isoformat(),
                    'version': VERSION
                }
                # Escribir a archivo temporal primero
                temp_file = self.checkpoint_file + '.tmp'
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False)
                # Mover atómicamente
                os.replace(temp_file, self.checkpoint_file)
            except Exception as e:
                log.log(f"Error guardando checkpoint: {e}", "warning")

    def clear(self):
        """Elimina checkpoint."""
        if os.path.exists(self.checkpoint_file):
            try:
                os.remove(self.checkpoint_file)
                log.log("Checkpoint eliminado", "debug")
            except:
                pass


# ============================================================================
# CONVERSIÓN PDF A IMAGEN
# ============================================================================

class PDFConverter:
    """Convierte páginas de PDF a imágenes."""

    def __init__(self, dpi: int = DEFAULT_DPI):
        self.dpi = max(MIN_DPI, min(MAX_DPI, dpi))
        self._check_pdftoppm()

    def _check_pdftoppm(self):
        """Verifica que pdftoppm esté instalado."""
        try:
            result = subprocess.run(['pdftoppm', '-v'], capture_output=True, timeout=5)
        except FileNotFoundError:
            log.log("pdftoppm no encontrado. Instalar: apt install poppler-utils", "error")
            sys.exit(1)
        except Exception:
            pass

    def get_page_count(self, pdf_path: str) -> Optional[int]:
        """Obtiene número de páginas del PDF."""
        try:
            result = subprocess.run(
                ['pdfinfo', pdf_path],
                capture_output=True, text=True, timeout=30
            )
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        except Exception:
            pass
        return None

    def convert_page(self, pdf_path: str, page_num: int, output_path: str) -> bool:
        """Convierte una página a imagen JPEG."""
        try:
            base_output = output_path.rsplit('.', 1)[0]
            cmd = [
                'pdftoppm',
                '-jpeg',
                '-r', str(self.dpi),
                '-f', str(page_num),
                '-l', str(page_num),
                '-singlefile',
                pdf_path,
                base_output
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120
            )

            return result.returncode == 0 and os.path.exists(output_path)

        except subprocess.TimeoutExpired:
            log.log(f"Timeout convirtiendo página {page_num}", "warning")
            return False
        except Exception as e:
            log.log(f"Error convirtiendo página {page_num}: {e}", "warning")
            return False


# ============================================================================
# DETECTOR DE REGIONES DE PRODUCTO
# ============================================================================

class ProductRegionDetector:
    """Detecta regiones de productos en imágenes de catálogo."""

    def __init__(self):
        self.min_width = MIN_CROP_WIDTH
        self.min_height = MIN_CROP_HEIGHT
        self.padding = CROP_PADDING
        self.max_crops = MAX_CROPS_PER_PAGE

    def detect(self, image_path: str) -> List[CropData]:
        """Detecta regiones de productos en una imagen."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return []

            height, width = img.shape[:2]
            page_area = height * width
            min_area = page_area * MIN_CROP_RATIO
            max_area = page_area * MAX_CROP_RATIO

            # Preprocesamiento
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Detección de bordes
            edges = cv2.Canny(blurred, 30, 100)

            # Operaciones morfológicas
            kernel = np.ones((5, 5), np.uint8)
            dilated = cv2.dilate(edges, kernel, iterations=2)

            # Encontrar contornos
            contours, _ = cv2.findContours(
                dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h

                # Filtrar por tamaño
                if w < self.min_width or h < self.min_height:
                    continue
                if area < min_area or area > max_area:
                    continue

                # Agregar padding
                x = max(0, x - self.padding)
                y = max(0, y - self.padding)
                w = min(w + 2 * self.padding, width - x)
                h = min(h + 2 * self.padding, height - y)

                crop = CropData(
                    x=x, y=y,
                    width=w, height=h,
                    y_normalized=y / height
                )
                regions.append(crop)

            # Ordenar por área y limitar
            regions.sort(key=lambda r: r.area, reverse=True)
            return regions[:self.max_crops]

        except Exception as e:
            log.log(f"Error detectando regiones: {e}", "warning")
            return []

    def crop_and_save(self, image_path: str, regions: List[CropData],
                      output_dir: str, prefix: str, page_num: int) -> List[CropData]:
        """Recorta y guarda las regiones detectadas."""
        if not regions:
            return []

        try:
            img = cv2.imread(image_path)
            if img is None:
                return []

            ensure_dir(output_dir)
            saved = []

            for i, region in enumerate(regions):
                crop_img = img[
                    region.y:region.y + region.height,
                    region.x:region.x + region.width
                ]

                filename = f"{prefix}_p{page_num:03d}_c{i+1:02d}.jpg"
                path = os.path.join(output_dir, filename)

                cv2.imwrite(path, crop_img, [cv2.IMWRITE_JPEG_QUALITY, 92])

                region.filename = filename
                region.path = path
                saved.append(region)

            return saved

        except Exception as e:
            log.log(f"Error guardando crops: {e}", "warning")
            return []


# ============================================================================
# EXTRACTOR VISION AI
# ============================================================================

EXTRACTION_PROMPT = """Analiza esta página de catálogo de repuestos de motocicletas.

INSTRUCCIONES:
1. Extrae TODOS los productos visibles en la página
2. Para cada producto identifica:
   - codigo: Código del producto (4-6 dígitos, ej: "50100", "03860")
   - nombre: Nombre comercial completo
   - descripcion: Especificaciones técnicas, materiales, compatibilidad
   - precio: Solo el número, sin símbolos ni separadores de miles
   - categoria: Una de: MOTOR, FRENOS, ELECTRICO, SUSPENSION, TRANSMISION, CARROCERIA, ACCESORIOS, HERRAMIENTAS, LUJOS, OTROS
   - posicion_vertical: Número del 1 al 10 indicando posición (1=arriba, 10=abajo)

REGLAS:
- El código es OBLIGATORIO. Si no hay código visible, el producto se omite.
- posicion_vertical es CRÍTICO para asociar imágenes. Indica dónde está el producto en la página.
- Si la página no tiene productos de catálogo, devuelve lista vacía.
- Ignora encabezados, logos, marcas de agua.

RESPONDE ÚNICAMENTE JSON VÁLIDO:
{"productos": [{"codigo": "50100", "nombre": "Kit pistón 150cc", "descripcion": "Kit completo pistón, anillos y pasador para motor 150cc 4T", "precio": 45000, "categoria": "MOTOR", "posicion_vertical": 2}]}
"""


class VisionExtractor:
    """Extrae datos de productos usando GPT-4o Vision."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            log.log("OPENAI_API_KEY no configurada", "error")
            sys.exit(1)

        self.client = OpenAI(api_key=self.api_key)
        self.last_request_time = 0
        self.stats = ProcessingStats()

        # Event Emitter para Cortex Visual (Tony narra)
        if EMITTER_AVAILABLE:
            self.emitter = ODIEventEmitter(source="vision", actor="ODI_VISION_v3")
        else:
            self.emitter = None

    def _throttle(self):
        """Aplica throttling entre requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def extract_page(self, image_path: str, page_num: int) -> List[ProductData]:
        """Extrae productos de una página usando Vision API."""

        # Leer imagen
        with open(image_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')

        # Obtener altura de imagen para normalización
        try:
            img = cv2.imread(image_path)
            img_height = img.shape[0] if img is not None else 1000
        except:
            img_height = 1000

        # Intentar con reintentos y backoff exponencial
        for attempt in range(MAX_RETRIES):
            try:
                self._throttle()
                self.stats.api_calls += 1

                response = self.client.chat.completions.create(
                    model=VISION_MODEL,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": EXTRACTION_PROMPT},
                            {"type": "image_url", "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "high"
                            }}
                        ]
                    }],
                    max_tokens=MAX_TOKENS,
                    response_format={"type": "json_object"},
                    timeout=REQUEST_TIMEOUT
                )

                content = response.choices[0].message.content
                data = json.loads(content)
                productos_raw = data.get("productos", [])

                # Procesar productos
                productos = []
                for p in productos_raw:
                    codigo = clean_text(p.get('codigo', ''))

                    # Validar código
                    if not codigo or codigo.lower() in ['', 'null', 'none', 'n/a']:
                        continue

                    # Calcular posición normalizada
                    pos_vertical = int(p.get('posicion_vertical', 5))
                    pos_vertical = max(1, min(10, pos_vertical))
                    y_normalized = (pos_vertical - 1) / 9

                    producto = ProductData(
                        codigo=codigo,
                        nombre=clean_text(p.get('nombre', '')),
                        descripcion=clean_text(p.get('descripcion', '')),
                        precio=clean_price(p.get('precio', 0)),
                        categoria=normalize_category(p.get('categoria', '')),
                        pagina=page_num,
                        posicion_y=y_normalized
                    )

                    if producto.is_valid():
                        productos.append(producto)

                return productos

            except json.JSONDecodeError as e:
                log.log(f"JSON inválido en intento {attempt + 1}", "warning")
                self.stats.api_errors += 1

            except Exception as e:
                self.stats.api_errors += 1
                error_msg = str(e).lower()

                # Rate limit
                if 'rate_limit' in error_msg or '429' in error_msg:
                    wait_time = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                    log.log(f"Rate limit. Esperando {wait_time}s...", "warning")
                    time.sleep(wait_time)
                    continue

                # Timeout
                elif 'timeout' in error_msg:
                    log.log(f"Timeout en intento {attempt + 1}", "warning")
                    time.sleep(INITIAL_RETRY_DELAY)
                    continue

                # Otros errores
                else:
                    log.log(f"Error API: {str(e)[:100]}", "warning")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(INITIAL_RETRY_DELAY * (attempt + 1))

        return []


# ============================================================================
# ASOCIADOR DE IMÁGENES
# ============================================================================

class ImageAssociator:
    """Asocia crops de imágenes a productos por posición."""

    def __init__(self, max_distance: float = MAX_POSITION_DISTANCE):
        self.max_distance = max_distance

    def associate(self, productos: List[ProductData],
                  crops: List[CropData]) -> List[ProductData]:
        """Asocia crops a productos por proximidad vertical."""
        if not crops or not productos:
            return productos

        # Ordenar por posición Y
        productos_sorted = sorted(productos, key=lambda p: p.posicion_y)
        crops_available = [c for c in crops if not c.assigned]

        for producto in productos_sorted:
            if not crops_available:
                break

            # Buscar crop más cercano
            best_crop = None
            best_distance = float('inf')

            for crop in crops_available:
                if crop.assigned:
                    continue

                distance = abs(producto.posicion_y - crop.y_normalized)

                if distance < best_distance:
                    best_distance = distance
                    best_crop = crop

            # Asignar si está dentro del umbral
            if best_crop and best_distance <= self.max_distance:
                producto.imagen = best_crop.filename
                best_crop.assigned = True
                crops_available = [c for c in crops_available if not c.assigned]

        return productos


# ============================================================================
# EXPORTADOR
# ============================================================================

class Exporter:
    """Exporta resultados a CSV y JSON."""

    def __init__(self, output_dir: str, prefix: str):
        self.output_dir = ensure_dir(output_dir)
        self.prefix = prefix

    def export(self, productos: List[ProductData], pdf_name: str) -> Tuple[str, str]:
        """Exporta productos a CSV y JSON."""
        if not productos:
            log.log("No hay productos para exportar", "warning")
            return "", ""

        # Crear DataFrame
        records = []
        for p in productos:
            p.sku_odi = f"{self.prefix}-{p.codigo}"
            p.fuente = pdf_name
            records.append(p.to_dict())

        df = pd.DataFrame(records)

        # Eliminar duplicados por código
        original_count = len(df)
        df = df.drop_duplicates(subset=['codigo'], keep='first')
        duplicates = original_count - len(df)

        # Ordenar columnas
        columns_order = [
            'sku_odi', 'codigo', 'nombre', 'descripcion', 'precio',
            'categoria', 'imagen', 'pagina', 'fuente'
        ]
        df = df[[c for c in columns_order if c in df.columns]]

        # Ordenar por página y código
        df = df.sort_values(['pagina', 'codigo']).reset_index(drop=True)

        # Guardar CSV
        csv_path = os.path.join(self.output_dir, f"{self.prefix}_catalogo.csv")
        df.to_csv(csv_path, sep=';', index=False, encoding='utf-8')

        # Guardar JSON
        json_path = os.path.join(self.output_dir, f"{self.prefix}_catalogo.json")
        df.to_json(json_path, orient='records', force_ascii=False, indent=2)

        return csv_path, json_path


# ============================================================================
# PROCESADOR PRINCIPAL
# ============================================================================

class CatalogProcessor:
    """Procesador principal de catálogos."""

    def __init__(self, config: dict):
        self.config = config
        self.pdf_path = config['pdf_path']
        self.pages = config['pages']
        self.output_dir = config.get('output_dir', DEFAULT_OUTPUT_DIR)
        self.prefix = config.get('prefix', 'CAT')
        self.dpi = config.get('dpi', DEFAULT_DPI)
        self.use_checkpoint = config.get('use_checkpoint', True)
        self.save_crops = config.get('save_crops', True)

        # Crear directorios
        self.pages_dir = ensure_dir(os.path.join(self.output_dir, "pages"))
        self.crops_dir = ensure_dir(os.path.join(self.output_dir, "crops"))

        # Componentes
        self.converter = PDFConverter(self.dpi)
        self.detector = ProductRegionDetector()
        self.extractor = VisionExtractor()
        self.associator = ImageAssociator()
        self.exporter = Exporter(self.output_dir, self.prefix)

        # Estado
        self.stats = ProcessingStats()
        self.all_products: List[ProductData] = []
        self.processed_pages: set = set()
        self.emitter = None  # Event emitter para Cortex Visual (opcional)

        # Checkpoint
        if self.use_checkpoint:
            self.checkpoint = CheckpointManager(
                self.pdf_path, self.prefix,
                config.get('checkpoint_dir', DEFAULT_CHECKPOINT_DIR)
            )
        else:
            self.checkpoint = None

    def _load_checkpoint(self):
        """Carga estado desde checkpoint."""
        if not self.checkpoint:
            return

        products_data, self.processed_pages = self.checkpoint.load()
        self.all_products = [ProductData(**p) for p in products_data]
        self.stats.products_extracted = len(self.all_products)

    def _save_checkpoint(self):
        """Guarda estado a checkpoint."""
        if not self.checkpoint:
            return

        products_data = [p.to_dict() for p in self.all_products]
        self.checkpoint.save(products_data, self.processed_pages)

    def _process_page(self, page_num: int) -> List[ProductData]:
        """Procesa una página del catálogo."""
        log.log(f"Procesando página {page_num}...")

        # Convertir página a imagen
        page_img = os.path.join(self.pages_dir, f"page_{page_num:03d}.jpg")

        if not self.converter.convert_page(self.pdf_path, page_num, page_img):
            log.log(f"   No se pudo convertir página {page_num}", "warning")
            self.stats.pages_failed += 1
            return []

        # Detectar y guardar crops
        crops = []
        if self.save_crops:
            regions = self.detector.detect(page_img)
            if regions:
                crops = self.detector.crop_and_save(
                    page_img, regions, self.crops_dir, self.prefix, page_num
                )
                self.stats.crops_detected += len(crops)
                log.log(f"   {len(crops)} crops detectados", "debug")

        # Extraer productos con Vision
        productos = self.extractor.extract_page(page_img, page_num)

        if not productos:
            log.log(f"   Sin productos en página {page_num}", "debug")
            return []

        log.log(f"   {len(productos)} productos extraídos", "success")

        # Asociar crops a productos
        if crops and productos:
            productos = self.associator.associate(productos, crops)
            assigned = sum(1 for p in productos if p.imagen)
            self.stats.crops_assigned += assigned
            if assigned:
                log.log(f"   {assigned} imágenes asociadas", "debug")

        self.stats.pages_processed += 1
        return productos

    def process(self) -> Tuple[str, str]:
        """Ejecuta el procesamiento completo."""

        # Banner
        self._print_banner()

        # Cargar checkpoint
        self._load_checkpoint()

        # Filtrar páginas pendientes
        pages_pending = [p for p in self.pages if p not in self.processed_pages]

        # === EMIT: Vision Start ===
        if self.emitter:
            self.emitter.vision_start(os.path.basename(self.pdf_path), len(self.pages))

        if not pages_pending:
            log.log("Todas las páginas ya procesadas", "success")
        else:
            log.log(f"Páginas pendientes: {len(pages_pending)}")
            log.log("-" * 50)

            try:
                for i, page_num in enumerate(pages_pending, 1):
                    log.log(f"\n[{i}/{len(pages_pending)}] Página {page_num}", "header")

                    # === EMIT: Page Start ===
                    if self.emitter:
                        self.emitter.vision_page_start(page_num, len(self.pages))

                    productos = self._process_page(page_num)
                    self.all_products.extend(productos)
                    self.stats.products_extracted += len(productos)
                    self.stats.products_with_image += sum(1 for p in productos if p.imagen)

                    # === EMIT: Products Found ===
                    if self.emitter:
                        for p in productos:
                            self.emitter.vision_product_found(
                                p.codigo,
                                p.nombre[:50],
                                p.precio,
                                p.categoria,
                                p.imagen
                            )

                    # === EMIT: Page Complete ===
                    if self.emitter:
                        crops_this_page = sum(1 for p in productos if p.imagen)
                        self.emitter.vision_page_complete(
                            page_num,
                            len(self.pages),
                            len(productos),
                            crops_this_page
                        )

                    self.processed_pages.add(page_num)

                    # Checkpoint periódico
                    if i % CHECKPOINT_INTERVAL == 0:
                        self._save_checkpoint()

                    # Limpiar memoria
                    gc.collect()

            except KeyboardInterrupt:
                log.log("\n\nInterrupción detectada. Guardando progreso...", "warning")
                self._save_checkpoint()
                raise

            # Checkpoint final
            self._save_checkpoint()

        # Exportar resultados
        log.log("\n" + "=" * 50)
        log.log("EXPORTANDO RESULTADOS", "header")

        pdf_name = Path(self.pdf_path).name
        csv_path, json_path = self.exporter.export(self.all_products, pdf_name)

        # Limpiar checkpoint si completó
        if self.checkpoint and len(self.processed_pages) >= len(self.pages):
            self.checkpoint.clear()

        # === EMIT: Vision Complete ===
        if self.emitter:
            self.emitter.vision_complete(len(self.all_products), log.elapsed())

        # Estadísticas finales
        self._print_stats(csv_path, json_path)

        return csv_path, json_path

    def _print_banner(self):
        """Imprime banner de inicio."""
        print(f"""
{Colors.BOLD}╔══════════════════════════════════════════════════════════════════╗
║                  🔍 {SCRIPT_NAME} v{VERSION}                       ║
║            Extractor Universal de Catálogos PDF                  ║
╚══════════════════════════════════════════════════════════════════╝{Colors.RESET}
""")
        log.log(f"PDF: {os.path.basename(self.pdf_path)}")
        log.log(f"Páginas: {len(self.pages)} ({min(self.pages)}-{max(self.pages)})")
        log.log(f"Output: {self.output_dir}")
        log.log(f"Prefijo SKU: {self.prefix}")
        log.log(f"DPI: {self.dpi}")

    def _print_stats(self, csv_path: str, json_path: str):
        """Imprime estadísticas finales."""
        s = self.stats
        productos_con_imagen = sum(1 for p in self.all_products if p.imagen)
        productos_con_precio = sum(1 for p in self.all_products if p.precio > 0)

        print(f"""
{Colors.BOLD}{'='*60}
📊 RESUMEN FINAL
{'='*60}{Colors.RESET}

{Colors.GREEN}✓ Páginas procesadas:{Colors.RESET}  {s.pages_processed}
{Colors.YELLOW}⚠ Páginas fallidas:{Colors.RESET}    {s.pages_failed}
{Colors.GREEN}✓ Productos extraídos:{Colors.RESET} {len(self.all_products)}
{Colors.GREEN}✓ Con imagen:{Colors.RESET}          {productos_con_imagen}
{Colors.GREEN}✓ Con precio:{Colors.RESET}          {productos_con_precio}
{Colors.CYAN}○ Crops detectados:{Colors.RESET}    {s.crops_detected}
{Colors.CYAN}○ Crops asignados:{Colors.RESET}     {s.crops_assigned}
{Colors.DIM}○ Llamadas API:{Colors.RESET}        {s.api_calls}
{Colors.DIM}○ Errores API:{Colors.RESET}         {s.api_errors}
{Colors.DIM}○ Tiempo total:{Colors.RESET}        {log.elapsed()}

{Colors.BOLD}📁 ARCHIVOS GENERADOS:{Colors.RESET}
   📄 CSV:  {csv_path}
   📄 JSON: {json_path}
   🖼️  Crops: {self.crops_dir}
""")

        # Muestra de productos
        if self.all_products:
            print(f"{Colors.BOLD}📋 MUESTRA (primeros 10):{Colors.RESET}")
            for p in self.all_products[:10]:
                img = "📷" if p.imagen else "  "
                print(f"   {img} {p.sku_odi:14} ${p.precio:>10,.0f}  {p.nombre[:35]}")

        # Categorías
        if self.all_products:
            categorias = {}
            for p in self.all_products:
                categorias[p.categoria] = categorias.get(p.categoria, 0) + 1

            print(f"\n{Colors.BOLD}📂 CATEGORÍAS:{Colors.RESET}")
            for cat, count in sorted(categorias.items(), key=lambda x: -x[1]):
                pct = count / len(self.all_products) * 100
                print(f"   {cat:20} {count:4} ({pct:5.1f}%)")

        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}\n")


# ============================================================================
# CLI
# ============================================================================

def parse_pages(pages_str: str, max_pages: Optional[int] = None) -> List[int]:
    """Parsea string de páginas a lista."""
    pages_str = pages_str.strip().lower()

    if pages_str == 'all':
        if max_pages:
            return list(range(1, max_pages + 1))
        else:
            return list(range(1, 101))  # Default máximo

    pages = set()
    for part in pages_str.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                pages.update(range(start, end + 1))
            except ValueError:
                pass
        else:
            try:
                pages.add(int(part))
            except ValueError:
                pass

    return sorted(pages)


def print_help():
    """Imprime ayuda."""
    print(f"""
{Colors.BOLD}{SCRIPT_NAME} v{VERSION}{Colors.RESET}
{'='*60}

{Colors.CYAN}USO:{Colors.RESET}
    python3 {os.path.basename(__file__)} <pdf> <páginas> [opciones]

{Colors.CYAN}ARGUMENTOS:{Colors.RESET}
    pdf        Ruta al archivo PDF del catálogo
    páginas    Rango de páginas: "2-50", "1,3,5-10", "all"

{Colors.CYAN}OPCIONES:{Colors.RESET}
    --output, -o DIR      Directorio de salida (default: {DEFAULT_OUTPUT_DIR})
    --prefix PREFIX       Prefijo para SKU (default: CAT)
    --dpi DPI            Resolución de imagen (default: {DEFAULT_DPI})
    --no-crops           No guardar imágenes recortadas
    --no-checkpoint      Deshabilitar sistema de checkpoint
    --help, -h           Mostrar esta ayuda

{Colors.CYAN}EJEMPLOS:{Colors.RESET}
    # Procesar páginas 2-50 de un catálogo
    python3 {os.path.basename(__file__)} catalogo.pdf 2-50 --prefix ARM

    # Procesar todo el catálogo con salida personalizada
    python3 {os.path.basename(__file__)} catalogo.pdf all --output /data/armotos

    # Procesar sin guardar crops
    python3 {os.path.basename(__file__)} catalogo.pdf 2-20 --no-crops

{Colors.CYAN}SALIDA:{Colors.RESET}
    output/
    ├── PREFIX_catalogo.csv      # Datos estructurados
    ├── PREFIX_catalogo.json     # Formato JSON
    ├── pages/                   # Imágenes de páginas
    │   └── page_001.jpg
    └── crops/                   # Recortes de productos
        └── PREFIX_p001_c01.jpg

{Colors.CYAN}VARIABLES DE ENTORNO:{Colors.RESET}
    OPENAI_API_KEY       API key de OpenAI (requerido)

{Colors.CYAN}DEPENDENCIAS:{Colors.RESET}
    pip install openai pandas opencv-python pillow
    apt install poppler-utils  # Para pdftoppm
""")


def main():
    """Punto de entrada principal."""

    # Verificar argumentos
    if len(sys.argv) < 3 or '--help' in sys.argv or '-h' in sys.argv:
        print_help()
        sys.exit(0 if '--help' in sys.argv or '-h' in sys.argv else 1)

    # Parsear argumentos
    pdf_path = sys.argv[1]
    pages_arg = sys.argv[2]

    # Valores por defecto
    config = {
        'pdf_path': pdf_path,
        'output_dir': DEFAULT_OUTPUT_DIR,
        'prefix': 'CAT',
        'dpi': DEFAULT_DPI,
        'use_checkpoint': True,
        'save_crops': True,
    }

    # Parsear opciones
    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg in ['--output', '-o'] and i + 1 < len(sys.argv):
            config['output_dir'] = sys.argv[i + 1]
            i += 2
        elif arg == '--prefix' and i + 1 < len(sys.argv):
            config['prefix'] = sys.argv[i + 1].upper()
            i += 2
        elif arg == '--dpi' and i + 1 < len(sys.argv):
            config['dpi'] = int(sys.argv[i + 1])
            i += 2
        elif arg == '--no-crops':
            config['save_crops'] = False
            i += 1
        elif arg == '--no-checkpoint':
            config['use_checkpoint'] = False
            i += 1
        else:
            i += 1

    # Validar PDF
    if not os.path.exists(pdf_path):
        log.log(f"Archivo no encontrado: {pdf_path}", "error")
        sys.exit(1)

    # Obtener número de páginas si es 'all'
    max_pages = None
    if pages_arg.lower() == 'all':
        converter = PDFConverter()
        max_pages = converter.get_page_count(pdf_path)
        if max_pages:
            log.log(f"PDF tiene {max_pages} páginas")

    # Parsear páginas
    pages = parse_pages(pages_arg, max_pages)
    if not pages:
        log.log("Rango de páginas inválido", "error")
        sys.exit(1)

    config['pages'] = pages

    # Procesar
    try:
        processor = CatalogProcessor(config)
        processor.process()
    except KeyboardInterrupt:
        log.log("\nProceso interrumpido por usuario", "warning")
        sys.exit(130)
    except Exception as e:
        log.log(f"Error fatal: {e}", "error")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
