#!/usr/bin/env python3
"""
ODI Vision Extractor v2.5
=========================
Extractor industrial de catálogos PDF con CROP de imágenes.
Genera productos + imágenes individuales para Shopify.

Características:
- Extracción de datos con GPT-4o Vision
- CROP automático de productos por detección de contornos
- Asociación imagen-producto por posición
- Estructura lista para Shopify/E-commerce
- Sistema de checkpoint

Autor: ODI Team
Versión: 2.5
"""
import os
import sys
import json
import base64
import gc
import time
import subprocess
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import pandas as pd
from openai import OpenAI

# Intentar importar OpenCV y PIL para crops
try:
    import cv2
    import numpy as np
    from PIL import Image
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("⚠️ OpenCV/PIL no disponible. Instalar: pip install opencv-python pillow")

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

VERSION = "2.5"
DEFAULT_DPI = 150  # Mayor DPI para mejor calidad de crops
MAX_RETRIES = 3
RETRY_DELAY = 2
THROTTLE_DELAY = 0.8
TEMP_DIR = "/tmp/odi_vision"
CHECKPOINT_DIR = "/tmp/odi_checkpoints"

SKU_PREFIX = "ARM"

# Configuración de crops
MIN_CROP_WIDTH = 80
MIN_CROP_HEIGHT = 80
MAX_CROPS_PER_PAGE = 20
CROP_PADDING = 10

# Taxonomía ODI
CATEGORY_MAP = {
    "motor": "MOTOR", "culata": "MOTOR", "piston": "MOTOR", "pistón": "MOTOR",
    "biela": "MOTOR", "cigueñal": "MOTOR", "valvula": "MOTOR", "cilindro": "MOTOR",
    "freno": "FRENOS", "frenos": "FRENOS", "pastilla": "FRENOS", "disco": "FRENOS",
    "zapata": "FRENOS", "caliper": "FRENOS",
    "electrico": "ELECTRICO", "eléctrico": "ELECTRICO", "bobina": "ELECTRICO",
    "cdi": "ELECTRICO", "bateria": "ELECTRICO", "faro": "ELECTRICO", "luz": "ELECTRICO",
    "suspension": "SUSPENSION", "suspensión": "SUSPENSION", "amortiguador": "SUSPENSION",
    "transmision": "TRANSMISION", "cadena": "TRANSMISION", "piñon": "TRANSMISION",
    "catalina": "TRANSMISION", "clutch": "TRANSMISION", "embrague": "TRANSMISION",
    "carroceria": "CARROCERIA", "chasis": "CARROCERIA", "plastico": "CARROCERIA",
    "guardafango": "CARROCERIA", "tanque": "CARROCERIA",
    "herramienta": "HERRAMIENTAS", "herramientas": "HERRAMIENTAS", "llave": "HERRAMIENTAS",
    "banco": "HERRAMIENTAS", "extractor": "HERRAMIENTAS",
    "accesorio": "ACCESORIOS", "accesorios": "ACCESORIOS", "manilar": "ACCESORIOS",
    "espejo": "ACCESORIOS", "manubrio": "ACCESORIOS",
    "lujo": "LUJOS", "lujos": "LUJOS", "casco": "LUJOS", "guante": "LUJOS",
    "embellecimiento": "EMBELLECIMIENTO", "limpieza": "EMBELLECIMIENTO",
}

PROMPT_WITH_COORDS = """Analiza esta página de catálogo industrial de repuestos de motocicletas.

INSTRUCCIONES:
1. Extrae TODOS los productos visibles en la imagen
2. Para cada producto identifica:
   - codigo: Código numérico del producto (4-5 dígitos)
   - nombre: Nombre comercial completo
   - descripcion: Especificaciones técnicas
   - precio: Solo el número, sin símbolos
   - categoria: MOTOR, FRENOS, ELECTRICO, SUSPENSION, TRANSMISION, CARROCERIA, HERRAMIENTAS, ACCESORIOS, LUJOS
   - posicion_vertical: Posición aproximada del producto en la página (1=arriba, 2=medio-arriba, 3=medio, 4=medio-abajo, 5=abajo)

3. Si la página no contiene productos, devuelve lista vacía

RESPONDE ÚNICAMENTE JSON:
{"productos": [{"codigo": "50000", "nombre": "...", "descripcion": "...", "precio": 15000, "categoria": "MOTOR", "posicion_vertical": 2}]}
"""

# ============================================================================
# LOGGING
# ============================================================================

class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

def log(msg: str, level: str = "info"):
    colors = {"info": Colors.CYAN, "success": Colors.GREEN, "warning": Colors.YELLOW,
              "error": Colors.RED, "header": Colors.BOLD, "dim": Colors.DIM}
    color = colors.get(level, "")
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{color}[{timestamp}] {msg}{Colors.RESET}", flush=True)

def print_banner():
    print(f"""
{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║        🔍 ODI VISION EXTRACTOR v{VERSION} + CROPS               ║
║     Extracción + Imágenes para E-commerce                     ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
""")

# ============================================================================
# UTILIDADES
# ============================================================================

def get_pdf_page_count(pdf_path: str) -> Optional[int]:
    try:
        result = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True, timeout=15)
        for line in result.stdout.split('\n'):
            if line.startswith('Pages:'):
                return int(line.split(':')[1].strip())
    except Exception:
        pass
    return None

def parse_pages(pages_str: str, total_pages: Optional[int] = None) -> List[int]:
    pages_str = pages_str.strip().lower()
    if pages_str == "all":
        return list(range(1, (total_pages or 100) + 1))
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

def clean_price(price_val) -> float:
    if isinstance(price_val, (int, float)):
        return float(price_val)
    if isinstance(price_val, str):
        cleaned = ''.join(c for c in price_val if c.isdigit() or c == '.')
        if cleaned.count('.') > 1:
            cleaned = cleaned.replace('.', '', cleaned.count('.') - 1)
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    return 0.0

def normalize_category(cat: str) -> str:
    if not cat:
        return "OTROS"
    c = cat.lower().strip()
    for key, value in CATEGORY_MAP.items():
        if key in c:
            return value
    return cat.upper() if cat.upper() in set(CATEGORY_MAP.values()) else "OTROS"

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:50]

def get_file_hash(filepath: str) -> str:
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()[:12]

# ============================================================================
# CHECKPOINT
# ============================================================================

def get_checkpoint_path(pdf_path: str, prefix: str) -> str:
    pdf_hash = get_file_hash(pdf_path)
    pdf_name = Path(pdf_path).stem[:30]
    return f"{CHECKPOINT_DIR}/{prefix}_{pdf_name}_{pdf_hash}_checkpoint.json"

def load_checkpoint(checkpoint_path: str) -> Tuple[List[Dict], set]:
    if os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('products', []), set(data.get('processed_pages', []))
        except Exception:
            pass
    return [], set()

def save_checkpoint(checkpoint_path: str, products: List[Dict], processed_pages: set):
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
    try:
        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump({'products': products, 'processed_pages': list(processed_pages),
                      'timestamp': datetime.now().isoformat(), 'version': VERSION}, f, ensure_ascii=False)
    except Exception as e:
        log(f"Error guardando checkpoint: {e}", "warning")

# ============================================================================
# CONVERSIÓN PDF -> IMAGEN
# ============================================================================

def convert_page(pdf_path: str, page_num: int, output_path: str, dpi: int) -> bool:
    try:
        base_output = output_path.rsplit('.', 1)[0]
        cmd = ["pdftoppm", "-jpeg", "-r", str(dpi), "-f", str(page_num),
               "-l", str(page_num), "-singlefile", pdf_path, base_output]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        log(f"Error pdftoppm: {e}", "warning")
        return False

# ============================================================================
# DETECCIÓN Y CROP DE IMÁGENES
# ============================================================================

def detect_product_regions(image_path: str) -> List[Dict]:
    """Detecta regiones de productos en una página usando OpenCV."""
    if not OPENCV_AVAILABLE:
        return []

    try:
        img = cv2.imread(image_path)
        if img is None:
            return []

        height, width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Aplicar blur y detección de bordes
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 30, 100)

        # Dilatar para conectar bordes cercanos
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=3)

        # Encontrar contornos
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            # Filtrar por tamaño mínimo
            if w < MIN_CROP_WIDTH or h < MIN_CROP_HEIGHT:
                continue

            # Filtrar regiones muy grandes (probablemente toda la página)
            if w > width * 0.9 and h > height * 0.9:
                continue

            # Calcular posición vertical (1-5)
            pos_vertical = int((y / height) * 5) + 1
            pos_vertical = min(5, max(1, pos_vertical))

            regions.append({
                'x': max(0, x - CROP_PADDING),
                'y': max(0, y - CROP_PADDING),
                'width': min(w + 2*CROP_PADDING, width - x),
                'height': min(h + 2*CROP_PADDING, height - y),
                'area': w * h,
                'posicion_vertical': pos_vertical
            })

        # Ordenar por área (mayor primero) y limitar cantidad
        regions.sort(key=lambda r: r['area'], reverse=True)
        return regions[:MAX_CROPS_PER_PAGE]

    except Exception as e:
        log(f"Error detectando regiones: {e}", "warning")
        return []

def crop_and_save_regions(image_path: str, regions: List[Dict], output_dir: str,
                          page_num: int, prefix: str) -> List[Dict]:
    """Recorta y guarda las regiones detectadas."""
    if not OPENCV_AVAILABLE or not regions:
        return []

    try:
        img = cv2.imread(image_path)
        if img is None:
            return []

        saved_crops = []
        for i, region in enumerate(regions):
            x, y, w, h = region['x'], region['y'], region['width'], region['height']
            crop = img[y:y+h, x:x+w]

            # Generar nombre único
            crop_filename = f"{prefix}_p{page_num}_crop{i+1}.jpg"
            crop_path = os.path.join(output_dir, crop_filename)

            cv2.imwrite(crop_path, crop, [cv2.IMWRITE_JPEG_QUALITY, 90])

            saved_crops.append({
                'filename': crop_filename,
                'path': crop_path,
                'posicion_vertical': region['posicion_vertical'],
                'area': region['area']
            })

        return saved_crops

    except Exception as e:
        log(f"Error guardando crops: {e}", "warning")
        return []

def assign_crops_to_products(products: List[Dict], crops: List[Dict]) -> List[Dict]:
    """Asigna crops a productos basándose en posición vertical."""
    if not crops:
        return products

    # Ordenar productos por posición vertical
    products_sorted = sorted(products, key=lambda p: p.get('posicion_vertical', 3))
    crops_sorted = sorted(crops, key=lambda c: c.get('posicion_vertical', 3))

    # Asignación por cercanía de posición
    for i, product in enumerate(products_sorted):
        prod_pos = product.get('posicion_vertical', 3)

        # Buscar el crop más cercano disponible
        best_crop = None
        best_distance = float('inf')

        for crop in crops_sorted:
            if crop.get('assigned'):
                continue
            crop_pos = crop.get('posicion_vertical', 3)
            distance = abs(prod_pos - crop_pos)
            if distance < best_distance:
                best_distance = distance
                best_crop = crop

        if best_crop:
            product['imagen'] = best_crop['filename']
            best_crop['assigned'] = True

    return products

# ============================================================================
# EXTRACCIÓN CON VISION AI
# ============================================================================

def extract_page_vision(client: OpenAI, image_path: str, page_num: int) -> List[Dict]:
    """Extrae productos usando GPT-4o Vision con coordenadas."""
    with open(image_path, "rb") as f:
        b64_img = base64.b64encode(f.read()).decode('utf-8')

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT_WITH_COORDS},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_img}",
                            "detail": "high"
                        }}
                    ]
                }],
                max_tokens=4000,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)
            productos = data.get("productos", [])

            productos_validos = []
            for p in productos:
                codigo = str(p.get('codigo', '')).strip()
                if not codigo or codigo.lower() in ['', 'null', 'none']:
                    continue

                p['codigo'] = codigo
                p['precio'] = clean_price(p.get('precio', 0))
                p['categoria'] = normalize_category(p.get('categoria', ''))
                p['nombre'] = str(p.get('nombre', '')).strip()
                p['descripcion'] = str(p.get('descripcion', '')).strip()
                p['posicion_vertical'] = int(p.get('posicion_vertical', 3))
                productos_validos.append(p)

            return productos_validos

        except json.JSONDecodeError:
            log(f"   ⚠️ JSON inválido (intento {attempt+1})", "warning")
        except Exception as e:
            error_msg = str(e).lower()
            if "rate_limit" in error_msg or "429" in error_msg:
                wait_time = RETRY_DELAY * (2 ** attempt)
                log(f"   ⏳ Rate limit, esperando {wait_time}s...", "warning")
                time.sleep(wait_time)
            else:
                log(f"   ⚠️ Error API: {str(e)[:50]}", "warning")

        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY * (attempt + 1))

    return []

# ============================================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================================

def process_pdf(
    pdf_path: str,
    pages: List[int],
    output_dir: str,
    dpi: int = DEFAULT_DPI,
    sku_prefix: str = SKU_PREFIX,
    save_crops: bool = True,
    use_checkpoint: bool = True
) -> pd.DataFrame:
    """Procesa el PDF extrayendo datos e imágenes."""

    if not os.path.exists(pdf_path):
        log(f"❌ Archivo no encontrado: {pdf_path}", "error")
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log("❌ OPENAI_API_KEY no configurada", "error")
        sys.exit(1)

    # Crear directorios
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    pages_dir = os.path.join(output_dir, "pages")
    crops_dir = os.path.join(output_dir, "crops")
    os.makedirs(pages_dir, exist_ok=True)
    if save_crops:
        os.makedirs(crops_dir, exist_ok=True)

    client = OpenAI(api_key=api_key)

    # Checkpoint
    checkpoint_path = get_checkpoint_path(pdf_path, sku_prefix)
    all_products = []
    processed_pages = set()

    if use_checkpoint:
        all_products, processed_pages = load_checkpoint(checkpoint_path)
        if processed_pages:
            log(f"📥 Checkpoint: {len(all_products)} productos, {len(processed_pages)} páginas", "success")

    pages_to_process = [p for p in pages if p not in processed_pages]

    # Header
    print_banner()
    log(f"📄 PDF: {os.path.basename(pdf_path)}")
    log(f"📑 Páginas: {len(pages)} total | {len(pages_to_process)} pendientes")
    log(f"⚙️  Config: DPI={dpi} | SKU={sku_prefix} | Crops={'✓' if save_crops else '✗'}")
    log(f"📁 Output: {output_dir}")
    log("-" * 60)

    if not pages_to_process:
        log("✅ Todas las páginas ya procesadas", "success")
    else:
        start_time = time.time()
        total_crops = 0

        for i, page_num in enumerate(pages_to_process, 1):
            log(f"🔍 [{i}/{len(pages_to_process)}] Página {page_num}...")

            # Convertir página
            page_img_path = os.path.join(pages_dir, f"page_{page_num}.jpg")
            if not convert_page(pdf_path, page_num, page_img_path, dpi):
                log(f"   ⚠️ No se pudo convertir", "warning")
                processed_pages.add(page_num)
                continue

            # Extraer productos con Vision
            productos = extract_page_vision(client, page_img_path, page_num)

            # Detectar y guardar crops
            crops = []
            if save_crops and OPENCV_AVAILABLE and productos:
                regions = detect_product_regions(page_img_path)
                if regions:
                    crops = crop_and_save_regions(page_img_path, regions, crops_dir,
                                                   page_num, sku_prefix)
                    total_crops += len(crops)
                    log(f"   📷 {len(crops)} crops guardados", "dim")

            # Asignar crops a productos
            if crops:
                productos = assign_crops_to_products(productos, crops)

            # Agregar metadata
            if productos:
                for p in productos:
                    p['pagina'] = page_num
                    p['fuente'] = os.path.basename(pdf_path)
                    if 'imagen' not in p:
                        p['imagen'] = ''
                    all_products.append(p)
                log(f"   ✅ {len(productos)} productos", "success")
            else:
                log(f"   ℹ️  Sin productos", "dim")

            processed_pages.add(page_num)

            # Checkpoint cada 5 páginas
            if use_checkpoint and i % 5 == 0:
                save_checkpoint(checkpoint_path, all_products, processed_pages)

            gc.collect()
            time.sleep(THROTTLE_DELAY)

        elapsed = time.time() - start_time

        if use_checkpoint:
            save_checkpoint(checkpoint_path, all_products, processed_pages)

    # Crear DataFrame
    df = pd.DataFrame(all_products)

    if len(df) > 0:
        total_antes = len(df)
        df = df.drop_duplicates(subset=['codigo'], keep='first')
        duplicados = total_antes - len(df)

        # Generar SKU
        df['sku_odi'] = df['codigo'].apply(lambda c: f"{sku_prefix}-{c}")

        # Ordenar columnas
        cols = ['sku_odi', 'codigo', 'nombre', 'descripcion', 'precio', 'categoria',
                'imagen', 'pagina', 'fuente']
        df = df[[c for c in cols if c in df.columns]]
        df = df.sort_values(['pagina', 'codigo']).reset_index(drop=True)

        # Guardar CSV
        csv_path = os.path.join(output_dir, f"{sku_prefix}_catalogo.csv")
        df.to_csv(csv_path, sep=';', index=False, encoding='utf-8')

        # Guardar JSON
        json_path = os.path.join(output_dir, f"{sku_prefix}_catalogo.json")
        df.to_json(json_path, orient='records', force_ascii=False, indent=2)

        # Estadísticas
        log("")
        log("=" * 60, "header")
        log("📊 RESUMEN FINAL", "header")
        log("=" * 60, "header")
        log(f"   ✅ Productos únicos: {len(df)}", "success")
        log(f"   📄 Páginas procesadas: {len(processed_pages)}")
        log(f"   🔄 Duplicados: {duplicados}")
        log(f"   💰 Con precio: {(df['precio'] > 0).sum()}")

        if save_crops:
            con_imagen = (df['imagen'] != '').sum()
            log(f"   📷 Con imagen: {con_imagen}")

        log(f"   💾 CSV: {csv_path}", "success")
        log(f"   📁 JSON: {json_path}", "success")
        if save_crops:
            log(f"   🖼️  Crops: {crops_dir}", "success")

        # Muestra
        log("")
        log("-" * 60)
        log("📋 MUESTRA:", "header")
        for _, row in df.head(10).iterrows():
            sku = row.get('sku_odi', '?')
            precio = row.get('precio', 0)
            nombre = str(row.get('nombre', ''))[:28]
            img = '📷' if row.get('imagen') else '  '
            log(f"   {img} {sku:12} ${precio:>10,.0f}  {nombre}")

        # Categorías
        log("")
        log("-" * 60)
        log("📂 CATEGORÍAS:", "header")
        for cat, count in df['categoria'].value_counts().items():
            pct = count / len(df) * 100
            log(f"   {cat:15} {count:4} ({pct:5.1f}%)")

    else:
        log("⚠️ No se encontraron productos", "warning")
        df = pd.DataFrame(columns=['sku_odi','codigo','nombre','descripcion','precio',
                                   'categoria','imagen','pagina','fuente'])

    log("")
    log("=" * 60, "header")

    # Limpiar checkpoint si completó
    if use_checkpoint and len(processed_pages) >= len(pages):
        if os.path.exists(checkpoint_path):
            os.remove(checkpoint_path)
            log("🧹 Checkpoint eliminado", "dim")

    return df

# ============================================================================
# CLI
# ============================================================================

def print_help():
    print(f"""
{Colors.BOLD}ODI Vision Extractor v{VERSION} + CROPS{Colors.RESET}
{'='*55}

{Colors.CYAN}Uso:{Colors.RESET}
    python3 odi_vision_extractor.py <pdf> <páginas> [opciones]

{Colors.CYAN}Opciones:{Colors.RESET}
    --output, -o     Directorio de salida
    --dpi            Resolución (default: 150)
    --prefix         Prefijo SKU (default: ARM)
    --no-crops       No guardar imágenes recortadas
    --no-checkpoint  Deshabilitar checkpoint

{Colors.CYAN}Ejemplos:{Colors.RESET}
    python3 odi_vision_extractor.py catalogo.pdf 2-20
    python3 odi_vision_extractor.py catalogo.pdf all --output /tmp/armotos
    python3 odi_vision_extractor.py catalogo.pdf 2-50 --prefix DFG --no-crops

{Colors.CYAN}Salida:{Colors.RESET}
    output/
    ├── ARM_catalogo.csv      # Datos estructurados
    ├── ARM_catalogo.json     # Datos en JSON
    ├── pages/                # Imágenes de páginas
    │   └── page_1.jpg
    └── crops/                # Recortes de productos
        └── ARM_p1_crop1.jpg
""")

def main():
    if len(sys.argv) < 3 or '--help' in sys.argv or '-h' in sys.argv:
        print_help()
        sys.exit(0 if '--help' in sys.argv else 1)

    pdf_path = sys.argv[1]
    pages_arg = sys.argv[2]

    output_dir = "/tmp/odi_output"
    dpi = DEFAULT_DPI
    sku_prefix = SKU_PREFIX
    save_crops = True
    use_checkpoint = True

    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ['--output', '-o'] and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            i += 2
        elif arg == '--dpi' and i + 1 < len(sys.argv):
            dpi = int(sys.argv[i + 1])
            i += 2
        elif arg == '--prefix' and i + 1 < len(sys.argv):
            sku_prefix = sys.argv[i + 1].upper()
            i += 2
        elif arg == '--no-crops':
            save_crops = False
            i += 1
        elif arg == '--no-checkpoint':
            use_checkpoint = False
            i += 1
        else:
            i += 1

    if not os.path.exists(pdf_path):
        log(f"❌ Archivo no encontrado: {pdf_path}", "error")
        sys.exit(1)

    total_pages = None
    if pages_arg.lower() == 'all':
        total_pages = get_pdf_page_count(pdf_path)
        if total_pages:
            log(f"📖 PDF: {total_pages} páginas")

    pages = parse_pages(pages_arg, total_pages)
    if not pages:
        log("❌ Páginas inválidas", "error")
        sys.exit(1)

    process_pdf(pdf_path, pages, output_dir, dpi, sku_prefix, save_crops, use_checkpoint)

if __name__ == "__main__":
    main()
