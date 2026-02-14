#!/usr/bin/env python3
"""
ODI Catalog Unifier v1.0
========================
Une productos extraídos con imágenes recortadas (crops) basándose en:
1. Posición vertical en la página (proximidad Y)
2. Coincidencia semántica de descripción (fallback)

Este script resuelve el problema de asociación imagen-producto
donde los crops se generan separadamente de la extracción de datos.

Flujo:
1. Procesa página del catálogo PDF
2. Extrae productos con Vision AI (código, descripción, precio, posición_y)
3. Detecta y recorta regiones de imágenes (crops)
4. Asocia crops a productos por proximidad vertical
5. Genera CSV unificado con columna de imagen

Autor: ODI Team
"""

import os
import sys
import json
import base64
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field, asdict

# Dependencias opcionales
try:
    import cv2
    import numpy as np
    OPENCV_OK = True
except ImportError:
    OPENCV_OK = False
    print("⚠️  OpenCV no disponible. Instalar: pip install opencv-python numpy")

try:
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False
    print("⚠️  Pandas no disponible. Instalar: pip install pandas")

try:
    from openai import OpenAI
    OPENAI_OK = True
except ImportError:
    OPENAI_OK = False
    print("⚠️  OpenAI no disponible. Instalar: pip install openai")


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

VERSION = "1.0"
DEFAULT_DPI = 200
TEMP_DIR = "/tmp/odi_unifier"

# Detección de crops
MIN_CROP_WIDTH = 60
MIN_CROP_HEIGHT = 60
MAX_CROP_AREA_RATIO = 0.4  # Máximo 40% del área de la página
CROP_PADDING = 8

# Asociación
MAX_Y_DISTANCE = 150  # Máxima distancia Y para asociar crop a producto


# ============================================================================
# MODELOS DE DATOS
# ============================================================================

@dataclass
class ProductoExtraido:
    codigo: str = ""
    nombre: str = ""
    descripcion: str = ""
    precio: float = 0.0
    categoria: str = ""
    pagina: int = 0
    y_pos: int = 0  # Posición vertical en la página
    y_normalized: float = 0.0  # Posición normalizada 0-1
    imagen: str = ""  # Ruta del crop asociado

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CropInfo:
    filename: str
    path: str
    x: int
    y: int
    width: int
    height: int
    y_center: int = 0
    y_normalized: float = 0.0
    area: int = 0
    assigned: bool = False

    def __post_init__(self):
        self.y_center = self.y + self.height // 2
        self.area = self.width * self.height


# ============================================================================
# UTILIDADES
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
    colors = {"info": Colors.CYAN, "success": Colors.GREEN,
              "warning": Colors.YELLOW, "error": Colors.RED,
              "header": Colors.BOLD, "dim": Colors.DIM}
    color = colors.get(level, "")
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"{color}[{ts}] {msg}{Colors.RESET}", flush=True)


def clean_price(val) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = ''.join(c for c in val if c.isdigit() or c == '.')
        if cleaned.count('.') > 1:
            cleaned = cleaned.replace('.', '', cleaned.count('.') - 1)
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    return 0.0


def slugify(text: str, max_len: int = 50) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:max_len]


# ============================================================================
# CONVERSIÓN PDF -> IMAGEN
# ============================================================================

def convert_pdf_page(pdf_path: str, page_num: int, output_path: str, dpi: int = DEFAULT_DPI) -> bool:
    """Convierte una página de PDF a imagen usando pdftoppm."""
    try:
        base = output_path.rsplit('.', 1)[0]
        cmd = ["pdftoppm", "-jpeg", "-r", str(dpi),
               "-f", str(page_num), "-l", str(page_num),
               "-singlefile", pdf_path, base]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        log(f"Error convirtiendo página: {e}", "warning")
        return False


# ============================================================================
# DETECCIÓN DE REGIONES DE PRODUCTO (CROPS)
# ============================================================================

def detect_product_regions(image_path: str) -> List[CropInfo]:
    """
    Detecta regiones de productos en una página usando OpenCV.
    Retorna lista de CropInfo con posición y dimensiones.
    """
    if not OPENCV_OK:
        return []

    try:
        img = cv2.imread(image_path)
        if img is None:
            return []

        height, width = img.shape[:2]
        page_area = height * width
        max_crop_area = page_area * MAX_CROP_AREA_RATIO

        # Preprocesamiento
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Detección de bordes
        edges = cv2.Canny(blurred, 30, 100)

        # Dilatar para conectar bordes cercanos
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)

        # Encontrar contornos
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions = []
        for i, contour in enumerate(contours):
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h

            # Filtrar por tamaño
            if w < MIN_CROP_WIDTH or h < MIN_CROP_HEIGHT:
                continue
            if area > max_crop_area:
                continue

            # Agregar padding
            x = max(0, x - CROP_PADDING)
            y = max(0, y - CROP_PADDING)
            w = min(w + 2*CROP_PADDING, width - x)
            h = min(h + 2*CROP_PADDING, height - y)

            crop = CropInfo(
                filename=f"crop_{i}.jpg",
                path="",
                x=x, y=y,
                width=w, height=h,
                y_normalized=y / height
            )
            regions.append(crop)

        # Ordenar por área (mayor primero) y limitar
        regions.sort(key=lambda r: r.area, reverse=True)
        return regions[:20]

    except Exception as e:
        log(f"Error detectando regiones: {e}", "warning")
        return []


def crop_and_save(image_path: str, regions: List[CropInfo],
                  output_dir: str, prefix: str, page_num: int) -> List[CropInfo]:
    """Recorta y guarda las regiones detectadas."""
    if not OPENCV_OK or not regions:
        return []

    try:
        img = cv2.imread(image_path)
        if img is None:
            return []

        os.makedirs(output_dir, exist_ok=True)
        saved = []

        for i, region in enumerate(regions):
            crop = img[region.y:region.y+region.height,
                      region.x:region.x+region.width]

            filename = f"{prefix}_p{page_num}_crop{i+1}.jpg"
            path = os.path.join(output_dir, filename)

            cv2.imwrite(path, crop, [cv2.IMWRITE_JPEG_QUALITY, 90])

            region.filename = filename
            region.path = path
            saved.append(region)

        return saved

    except Exception as e:
        log(f"Error guardando crops: {e}", "warning")
        return []


# ============================================================================
# EXTRACCIÓN DE PRODUCTOS CON VISION AI
# ============================================================================

PROMPT_EXTRACCION = """Analiza esta página de catálogo de repuestos de motocicletas.

INSTRUCCIONES:
1. Extrae TODOS los productos visibles
2. Para cada producto identifica:
   - codigo: Código numérico (4-6 dígitos)
   - nombre: Nombre comercial
   - descripcion: Especificaciones técnicas
   - precio: Solo número, sin símbolos
   - categoria: MOTOR, FRENOS, ELECTRICO, SUSPENSION, TRANSMISION, CARROCERIA, ACCESORIOS
   - posicion_pagina: Número del 1 al 10 indicando posición vertical (1=arriba, 10=abajo)

IMPORTANTE: El campo posicion_pagina es CRÍTICO para asociar imágenes.
Indica en qué parte vertical de la página está el producto.

RESPONDE SOLO JSON:
{"productos": [{"codigo": "50000", "nombre": "...", "descripcion": "...", "precio": 15000, "categoria": "MOTOR", "posicion_pagina": 3}]}
"""


def extract_products_vision(client, image_path: str, page_num: int) -> List[ProductoExtraido]:
    """Extrae productos de una página usando GPT-4o Vision."""
    if not OPENAI_OK:
        return []

    try:
        # Leer y obtener dimensiones de la imagen
        img = cv2.imread(image_path) if OPENCV_OK else None
        img_height = img.shape[0] if img is not None else 1000

        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT_EXTRACCION},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{b64}",
                        "detail": "high"
                    }}
                ]
            }],
            max_tokens=4000,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        productos_raw = data.get("productos", [])

        productos = []
        for p in productos_raw:
            codigo = str(p.get('codigo', '')).strip()
            if not codigo or codigo.lower() in ['', 'null', 'none']:
                continue

            pos_pagina = int(p.get('posicion_pagina', 5))
            y_normalized = (pos_pagina - 1) / 9  # Normalizar 1-10 a 0-1
            y_pos = int(y_normalized * img_height)

            prod = ProductoExtraido(
                codigo=codigo,
                nombre=str(p.get('nombre', '')).strip(),
                descripcion=str(p.get('descripcion', '')).strip(),
                precio=clean_price(p.get('precio', 0)),
                categoria=str(p.get('categoria', 'OTROS')).upper(),
                pagina=page_num,
                y_pos=y_pos,
                y_normalized=y_normalized
            )
            productos.append(prod)

        return productos

    except Exception as e:
        log(f"Error extrayendo productos: {e}", "warning")
        return []


# ============================================================================
# ALGORITMO DE ASOCIACIÓN CROP-PRODUCTO
# ============================================================================

def associate_crops_to_products(productos: List[ProductoExtraido],
                                crops: List[CropInfo],
                                img_height: int = 1000) -> List[ProductoExtraido]:
    """
    Asocia crops a productos basándose en proximidad vertical.

    Algoritmo:
    1. Para cada producto, buscar el crop más cercano en posición Y
    2. Si la distancia es menor que MAX_Y_DISTANCE, asignar
    3. Marcar crop como usado para evitar duplicados
    """
    if not crops:
        return productos

    # Ordenar productos y crops por posición Y
    productos_sorted = sorted(productos, key=lambda p: p.y_normalized)
    crops_available = [c for c in crops]  # Copia para no modificar original

    for producto in productos_sorted:
        prod_y = producto.y_normalized

        best_crop = None
        best_distance = float('inf')

        for crop in crops_available:
            if crop.assigned:
                continue

            # Calcular distancia normalizada
            distance = abs(prod_y - crop.y_normalized)

            if distance < best_distance:
                best_distance = distance
                best_crop = crop

        # Asignar si está dentro del umbral
        if best_crop and best_distance < 0.3:  # 30% de la página
            producto.imagen = best_crop.filename
            best_crop.assigned = True
            log(f"   ✓ {producto.codigo} → {best_crop.filename} (dist: {best_distance:.2f})", "dim")

    return productos


# ============================================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================================

def process_catalog_page(
    pdf_path: str,
    page_num: int,
    output_dir: str,
    prefix: str = "CAT",
    dpi: int = DEFAULT_DPI
) -> List[ProductoExtraido]:
    """Procesa una página del catálogo: extrae productos y asocia imágenes."""

    os.makedirs(output_dir, exist_ok=True)
    pages_dir = os.path.join(output_dir, "pages")
    crops_dir = os.path.join(output_dir, "crops")
    os.makedirs(pages_dir, exist_ok=True)
    os.makedirs(crops_dir, exist_ok=True)

    # 1. Convertir página a imagen
    page_img = os.path.join(pages_dir, f"page_{page_num}.jpg")
    log(f"📄 Convirtiendo página {page_num}...")

    if not convert_pdf_page(pdf_path, page_num, page_img, dpi):
        log(f"   ❌ No se pudo convertir", "error")
        return []

    # Obtener altura de imagen
    img_height = 1000
    if OPENCV_OK:
        img = cv2.imread(page_img)
        if img is not None:
            img_height = img.shape[0]

    # 2. Detectar y guardar crops
    log(f"🔍 Detectando regiones de productos...")
    regions = detect_product_regions(page_img)
    crops = crop_and_save(page_img, regions, crops_dir, prefix, page_num)
    log(f"   📷 {len(crops)} crops detectados")

    # 3. Extraer productos con Vision AI
    log(f"🤖 Extrayendo productos con Vision AI...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log("   ⚠️ OPENAI_API_KEY no configurada", "warning")
        return []

    client = OpenAI(api_key=api_key)
    productos = extract_products_vision(client, page_img, page_num)
    log(f"   📦 {len(productos)} productos extraídos")

    # 4. Asociar crops a productos
    if productos and crops:
        log(f"🔗 Asociando crops a productos...")
        productos = associate_crops_to_products(productos, crops, img_height)
        con_imagen = sum(1 for p in productos if p.imagen)
        log(f"   ✅ {con_imagen}/{len(productos)} productos con imagen asociada", "success")

    return productos


def process_catalog(
    pdf_path: str,
    pages: List[int],
    output_dir: str,
    prefix: str = "CAT",
    dpi: int = DEFAULT_DPI
) -> None:
    """Procesa múltiples páginas del catálogo."""

    if not os.path.exists(pdf_path):
        log(f"❌ Archivo no encontrado: {pdf_path}", "error")
        sys.exit(1)

    print(f"""
{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║           🔗 ODI CATALOG UNIFIER v{VERSION}                      ║
║        Une productos con imágenes de catálogo                ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
""")

    log(f"📄 PDF: {os.path.basename(pdf_path)}")
    log(f"📑 Páginas: {pages}")
    log(f"📁 Output: {output_dir}")
    log("-" * 50)

    all_products = []

    for i, page_num in enumerate(pages, 1):
        log(f"\n{'='*50}")
        log(f"📖 [{i}/{len(pages)}] Procesando página {page_num}", "header")
        log(f"{'='*50}")

        productos = process_catalog_page(pdf_path, page_num, output_dir, prefix, dpi)
        all_products.extend(productos)

    # Guardar resultados
    if all_products and PANDAS_OK:
        log(f"\n{'='*50}")
        log("💾 GUARDANDO RESULTADOS", "header")
        log(f"{'='*50}")

        df = pd.DataFrame([p.to_dict() for p in all_products])

        # Agregar SKU
        df['sku_odi'] = df['codigo'].apply(lambda c: f"{prefix}-{c}")

        # Ordenar columnas
        cols = ['sku_odi', 'codigo', 'nombre', 'descripcion', 'precio',
                'categoria', 'imagen', 'pagina']
        df = df[[c for c in cols if c in df.columns]]

        # Guardar CSV
        csv_path = os.path.join(output_dir, f"{prefix}_catalogo_unificado.csv")
        df.to_csv(csv_path, sep=';', index=False, encoding='utf-8')
        log(f"   📄 CSV: {csv_path}", "success")

        # Guardar JSON
        json_path = os.path.join(output_dir, f"{prefix}_catalogo_unificado.json")
        df.to_json(json_path, orient='records', force_ascii=False, indent=2)
        log(f"   📄 JSON: {json_path}", "success")

        # Estadísticas
        log(f"\n📊 RESUMEN:")
        log(f"   Total productos: {len(df)}")
        log(f"   Con imagen: {(df['imagen'] != '').sum()}")
        log(f"   Sin imagen: {(df['imagen'] == '').sum()}")
        log(f"   Con precio: {(df['precio'] > 0).sum()}")

        # Muestra
        log(f"\n📋 MUESTRA:")
        for _, row in df.head(5).iterrows():
            img_icon = "📷" if row.get('imagen') else "  "
            log(f"   {img_icon} {row['sku_odi']:12} ${row['precio']:>10,.0f}  {row['nombre'][:30]}")

    log(f"\n{'='*50}")
    log("✅ PROCESO COMPLETADO", "success")
    log(f"{'='*50}\n")


# ============================================================================
# CLI
# ============================================================================

def parse_pages(pages_str: str, max_pages: int = 100) -> List[int]:
    pages_str = pages_str.strip().lower()
    if pages_str == "all":
        return list(range(1, max_pages + 1))

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
    print(f"""
{Colors.BOLD}ODI Catalog Unifier v{VERSION}{Colors.RESET}
{'='*50}

{Colors.CYAN}Uso:{Colors.RESET}
    python3 odi_catalog_unifier.py <pdf> <páginas> [opciones]

{Colors.CYAN}Argumentos:{Colors.RESET}
    pdf        Ruta al archivo PDF del catálogo
    páginas    Rango de páginas: "2-20", "1,3,5", "all"

{Colors.CYAN}Opciones:{Colors.RESET}
    --output, -o    Directorio de salida (default: /tmp/odi_unified)
    --prefix        Prefijo para SKU (default: CAT)
    --dpi           Resolución de imagen (default: 200)

{Colors.CYAN}Ejemplos:{Colors.RESET}
    python3 odi_catalog_unifier.py catalogo.pdf 2-20
    python3 odi_catalog_unifier.py catalogo.pdf 2-50 --prefix ARM --output /tmp/armotos

{Colors.CYAN}Salida:{Colors.RESET}
    output/
    ├── CAT_catalogo_unificado.csv    # Productos con columna 'imagen'
    ├── CAT_catalogo_unificado.json
    ├── pages/                         # Imágenes de páginas
    └── crops/                         # Recortes de productos
""")


def main():
    if len(sys.argv) < 3 or '--help' in sys.argv or '-h' in sys.argv:
        print_help()
        sys.exit(0 if '--help' in sys.argv else 1)

    pdf_path = sys.argv[1]
    pages_arg = sys.argv[2]

    output_dir = "/tmp/odi_unified"
    prefix = "CAT"
    dpi = DEFAULT_DPI

    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ['--output', '-o'] and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            i += 2
        elif arg == '--prefix' and i + 1 < len(sys.argv):
            prefix = sys.argv[i + 1].upper()
            i += 2
        elif arg == '--dpi' and i + 1 < len(sys.argv):
            dpi = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    pages = parse_pages(pages_arg)
    if not pages:
        log("❌ Páginas inválidas", "error")
        sys.exit(1)

    process_catalog(pdf_path, pages, output_dir, prefix, dpi)


if __name__ == "__main__":
    main()
