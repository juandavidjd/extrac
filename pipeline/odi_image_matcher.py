#!/usr/bin/env python3
"""
ODI Image Matcher v1.0
======================
Une productos existentes con imágenes/crops existentes usando:
1. Coincidencia semántica (descripción vs análisis IA de imagen)
2. Fuzzy matching de nombres

Este script trabaja con datos ya procesados:
- CSV de productos (Base_Datos, productos extraídos, etc.)
- CSV de análisis de imágenes (catalogo_kaiqi_imagenes, etc.)
- Carpeta de crops

Autor: ODI Team
"""

import os
import sys
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher
import glob
from pathlib import Path


try:
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False
    print("❌ Pandas requerido: pip install pandas")
    sys.exit(1)


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

VERSION = "1.0"

# Umbral de similitud para match (0-1)
SIMILARITY_THRESHOLD = 0.4

# Pesos para scoring
WEIGHT_NOMBRE = 0.4
WEIGHT_DESCRIPCION = 0.3
WEIGHT_CATEGORIA = 0.2
WEIGHT_SISTEMA = 0.1
# Directorios de imágenes
PDF_IMAGES_DIR = "/opt/odi/data/pdf_images"
IMAGE_BANK_DIR = "/mnt/volume_sfo3_01/profesion/ecosistema_odi"



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


def normalize_text(text: str) -> str:
    """Normaliza texto para comparación."""
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    # Remover caracteres especiales
    text = re.sub(r'[^a-záéíóúñ0-9\s]', ' ', text)
    # Normalizar espacios
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def similarity_ratio(a: str, b: str) -> float:
    """Calcula similitud entre dos strings (0-1)."""
    if not a or not b:
        return 0.0
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def word_overlap(a: str, b: str) -> float:
    """Calcula porcentaje de palabras compartidas."""
    if not a or not b:
        return 0.0
    words_a = set(normalize_text(a).split())
    words_b = set(normalize_text(b).split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union) if union else 0.0


# ============================================================================
# MAPEO DE CATEGORÍAS
# ============================================================================

CATEGORY_ALIASES = {
    # Análisis IA -> Categoría estándar
    "motor": "MOTOR",
    "culata": "MOTOR",
    "pistón": "MOTOR",
    "piston": "MOTOR",
    "cigueñal": "MOTOR",
    "biela": "MOTOR",
    "valvula": "MOTOR",
    "freno": "FRENOS",
    "frenos": "FRENOS",
    "disco": "FRENOS",
    "pastilla": "FRENOS",
    "zapata": "FRENOS",
    "electrico": "ELECTRICO",
    "eléctrico": "ELECTRICO",
    "bobina": "ELECTRICO",
    "cdi": "ELECTRICO",
    "faro": "ELECTRICO",
    "luz": "ELECTRICO",
    "suspension": "SUSPENSION",
    "suspensión": "SUSPENSION",
    "amortiguador": "SUSPENSION",
    "transmision": "TRANSMISION",
    "transmisión": "TRANSMISION",
    "cadena": "TRANSMISION",
    "piñon": "TRANSMISION",
    "clutch": "TRANSMISION",
    "carroceria": "CARROCERIA",
    "carrocería": "CARROCERIA",
    "plastico": "CARROCERIA",
    "plástico": "CARROCERIA",
    "guardafango": "CARROCERIA",
    "tanque": "CARROCERIA",
    "accesorio": "ACCESORIOS",
    "accesorios": "ACCESORIOS",
    "espejo": "ACCESORIOS",
    "manubrio": "ACCESORIOS",
    "herramienta": "HERRAMIENTAS",
    "herramientas": "HERRAMIENTAS",
    "llave": "HERRAMIENTAS",
    "lujo": "LUJOS",
    "lujos": "LUJOS",
    "embellecimiento": "EMBELLECIMIENTO",
}


def normalize_category(cat: str) -> str:
    """Normaliza categoría a formato estándar."""
    if not cat:
        return "OTROS"
    cat_lower = cat.lower().strip()
    for key, value in CATEGORY_ALIASES.items():
        if key in cat_lower:
            return value
    return cat.upper() if len(cat) < 20 else "OTROS"


def categories_match(cat1: str, cat2: str) -> float:
    """Verifica si dos categorías son compatibles (0 o 1)."""
    norm1 = normalize_category(cat1)
    norm2 = normalize_category(cat2)
    if norm1 == norm2:
        return 1.0
    # Categorías relacionadas
    related = {
        ("MOTOR", "REPUESTOS"): 0.5,
        ("FRENOS", "REPUESTOS"): 0.5,
        ("ELECTRICO", "REPUESTOS"): 0.5,
        ("ACCESORIOS", "LUJOS"): 0.7,
        ("LUJOS", "LUJOS_ACCESORIOS"): 0.8,
        ("ACCESORIOS", "LUJOS_ACCESORIOS"): 0.8,
    }
    for (a, b), score in related.items():
        if (norm1 == a and norm2 == b) or (norm1 == b and norm2 == a):
            return score
    return 0.0



# ============================================================================
# BÚSQUEDA EN DIRECTORIOS DE IMÁGENES
# ============================================================================

def search_pdf_images(store_name: str) -> List[Dict]:
    """
    Busca imágenes extraídas de PDFs para una tienda.
    Retorna lista de dicts con path y metadata.
    """
    store_dir = os.path.join(PDF_IMAGES_DIR, store_name)
    images = []
    
    if not os.path.isdir(store_dir):
        return images
    
    for f in os.listdir(store_dir):
        if f.lower().endswith((.png, .jpg, .jpeg, .webp)):
            # Parse filename: STORE_pXXX_iYY_hash.ext
            parts = f.split(_)
            page = 0
            index = 0
            if len(parts) >= 3:
                try:
                    page = int(parts[1][1:]) if parts[1].startswith(p) else 0
                    index = int(parts[2][1:]) if parts[2].startswith(i) else 0
                except:
                    pass
            
            images.append({
                filename: f,
                path: os.path.join(store_dir, f),
                page: page,
                index: index,
                source: pdf_extract
            })
    
    # Ordenar por página e índice
    images.sort(key=lambda x: (x[page], x[index]))
    return images


def search_image_bank(store_name: str) -> List[Dict]:
    """
    Busca imágenes en el banco de imágenes del ecosistema.
    Retorna lista de dicts con path y filename para fuzzy matching.
    """
    store_dir = os.path.join(IMAGE_BANK_DIR, store_name, "imagenes")
    images = []
    
    if not os.path.isdir(store_dir):
        # Intentar variantes del nombre
        for variant in [store_name.upper(), store_name.lower(), store_name.title()]:
            alt_dir = os.path.join(IMAGE_BANK_DIR, variant, "imagenes")
            if os.path.isdir(alt_dir):
                store_dir = alt_dir
                break
    
    if not os.path.isdir(store_dir):
        return images
    
    for f in os.listdir(store_dir):
        if f.lower().endswith((.png, .jpg, .jpeg, .webp)):
            # Extraer nombre limpio para matching
            name_clean = os.path.splitext(f)[0]
            name_clean = name_clean.replace(-,  ).replace(_,  )
            
            images.append({
                filename: f,
                path: os.path.join(store_dir, f),
                name_normalized: normalize_text(name_clean),
                source: image_bank
            })
    
    return images


def fuzzy_match_image(product_desc: str, images: List[Dict], threshold: float = 0.3) -> Optional[Dict]:
    """
    Encuentra la mejor imagen para un producto usando fuzzy matching.
    """
    if not images or not product_desc:
        return None
    
    product_norm = normalize_text(product_desc)
    best_match = None
    best_score = threshold
    
    for img in images:
        # Para imágenes del banco, usar nombre normalizado
        if name_normalized in img:
            score = max(
                similarity_ratio(product_norm, img[name_normalized]),
                word_overlap(product_norm, img[name_normalized])
            )
        else:
            # Para PDF images, usar filename
            filename_norm = normalize_text(os.path.splitext(img[filename])[0])
            score = word_overlap(product_norm, filename_norm)
        
        if score > best_score:
            best_score = score
            best_match = img
    
    return best_match


def match_products_with_local_images(
    products: List[Dict],
    store_name: str,
    use_pdf_images: bool = True,
    use_image_bank: bool = True
) -> List[Dict]:
    """
    Asocia productos con imágenes locales (PDF extracts + banco).
    Modifica los productos in-place agregando campo image_path.
    """
    log(f"🔍 Buscando imágenes locales para {store_name}...")
    
    available_images = []
    
    if use_pdf_images:
        pdf_imgs = search_pdf_images(store_name)
        log(f"   PDF images: {len(pdf_imgs)}")
        available_images.extend(pdf_imgs)
    
    if use_image_bank:
        bank_imgs = search_image_bank(store_name)
        log(f"   Image bank: {len(bank_imgs)}")
        available_images.extend(bank_imgs)
    
    if not available_images:
        log("   ⚠️ No hay imágenes disponibles", "warning")
        return products
    
    matched = 0
    used_images = set()
    
    for i, prod in enumerate(products):
        # Ya tiene imagen?
        if prod.get(image) and not placeholder in str(prod.get(image, )).lower():
            continue
        
        # Buscar match
        desc = str(prod.get(title, ) or prod.get(descripcion, ) or prod.get(name, ))
        
        # Filtrar imágenes ya usadas
        available = [img for img in available_images if img[path] not in used_images]
        
        match = fuzzy_match_image(desc, available)
        
        if match:
            prod[image] = match[path]
            prod[image_source] = match[source]
            used_images.add(match[path])
            matched += 1
    
    log(f"   ✅ Productos con imagen: {matched}/{len(products)}", "success")
    return products


# ============================================================================
# CARGA DE DATOS
# ============================================================================

def load_products_csv(path: str) -> pd.DataFrame:
    """Carga CSV de productos con detección automática de columnas."""
    log(f"📄 Cargando productos: {path}")

    # Intentar diferentes separadores
    for sep in [';', ',', '\t']:
        try:
            df = pd.read_csv(path, sep=sep, encoding='utf-8-sig')
            if len(df.columns) > 1:
                break
        except:
            continue

    log(f"   Columnas: {list(df.columns)}")
    log(f"   Filas: {len(df)}")

    # Mapear columnas comunes
    column_mapping = {}
    for col in df.columns:
        col_lower = col.lower()
        if 'codigo' in col_lower or 'sku' in col_lower or 'code' in col_lower:
            column_mapping[col] = 'codigo'
        elif 'descripcion' in col_lower or 'description' in col_lower or 'nombre' in col_lower:
            column_mapping[col] = 'descripcion'
        elif 'precio' in col_lower or 'price' in col_lower:
            column_mapping[col] = 'precio'
        elif 'categoria' in col_lower or 'category' in col_lower or 'familia' in col_lower:
            column_mapping[col] = 'categoria'
        elif 'imagen' in col_lower or 'image' in col_lower:
            column_mapping[col] = 'imagen_actual'

    if column_mapping:
        df = df.rename(columns=column_mapping)

    return df


def load_images_csv(path: str) -> pd.DataFrame:
    """Carga CSV de análisis de imágenes."""
    log(f"📷 Cargando análisis de imágenes: {path}")

    for sep in [';', ',', '\t']:
        try:
            df = pd.read_csv(path, sep=sep, encoding='utf-8-sig')
            if len(df.columns) > 1:
                break
        except:
            continue

    log(f"   Columnas: {list(df.columns)[:5]}...")
    log(f"   Imágenes: {len(df)}")

    return df


# ============================================================================
# ALGORITMO DE MATCHING
# ============================================================================

def calculate_match_score(producto: dict, imagen: dict) -> Tuple[float, dict]:
    """
    Calcula score de coincidencia entre un producto y una imagen.
    Retorna (score, detalles).
    """
    scores = {}

    # 1. Similitud de nombre/descripción
    prod_desc = str(producto.get('descripcion', ''))
    img_desc = str(imagen.get('Nombre_Comercial_Catalogo', '') or
                   imagen.get('Identificacion_Repuesto', ''))

    scores['nombre'] = max(
        similarity_ratio(prod_desc, img_desc),
        word_overlap(prod_desc, img_desc)
    )

    # 2. Características observadas
    prod_desc_full = f"{prod_desc} {producto.get('nombre', '')}"
    img_caract = str(imagen.get('Caracteristicas_Observadas', ''))

    scores['descripcion'] = word_overlap(prod_desc_full, img_caract)

    # 3. Categoría/Sistema
    prod_cat = str(producto.get('categoria', ''))
    img_sistema = str(imagen.get('Sistema', '') or imagen.get('Componente_Taxonomia', ''))

    scores['categoria'] = categories_match(prod_cat, img_sistema)

    # 4. Subsistema
    img_subsistema = str(imagen.get('SubSistema', ''))
    scores['sistema'] = word_overlap(prod_desc, img_subsistema)

    # Calcular score total ponderado
    total_score = (
        scores['nombre'] * WEIGHT_NOMBRE +
        scores['descripcion'] * WEIGHT_DESCRIPCION +
        scores['categoria'] * WEIGHT_CATEGORIA +
        scores['sistema'] * WEIGHT_SISTEMA
    )

    return total_score, scores


def find_best_match(producto: dict, imagenes: List[dict],
                    used_images: set) -> Tuple[Optional[dict], float, dict]:
    """
    Encuentra la mejor imagen para un producto.
    Retorna (imagen, score, detalles) o (None, 0, {}).
    """
    best_match = None
    best_score = 0.0
    best_details = {}

    for img in imagenes:
        filename = str(img.get('Filename_Original', ''))
        if filename in used_images:
            continue

        score, details = calculate_match_score(producto, img)

        if score > best_score:
            best_score = score
            best_match = img
            best_details = details

    return best_match, best_score, best_details


def match_products_to_images(productos_df: pd.DataFrame,
                             imagenes_df: pd.DataFrame,
                             threshold: float = SIMILARITY_THRESHOLD) -> pd.DataFrame:
    """
    Asocia productos con imágenes basándose en similitud semántica.
    """
    log(f"\n🔗 Iniciando matching semántico...")
    log(f"   Productos: {len(productos_df)}")
    log(f"   Imágenes disponibles: {len(imagenes_df)}")
    log(f"   Umbral de similitud: {threshold}")

    productos = productos_df.to_dict('records')
    imagenes = imagenes_df.to_dict('records')

    used_images = set()
    matches = []
    no_match = []

    for i, prod in enumerate(productos):
        prod_desc = str(prod.get('descripcion', ''))[:40]

        best_img, score, details = find_best_match(prod, imagenes, used_images)

        if best_img and score >= threshold:
            filename = str(best_img.get('Filename_Original', ''))
            used_images.add(filename)

            prod['imagen_match'] = filename
            prod['match_score'] = round(score, 3)
            prod['match_details'] = str(details)
            matches.append(prod)

            if (i + 1) % 50 == 0 or i < 10:
                log(f"   ✓ [{i+1}] {prod_desc}... → {filename} (score: {score:.2f})", "dim")
        else:
            prod['imagen_match'] = ''
            prod['match_score'] = 0
            prod['match_details'] = ''
            no_match.append(prod)

    log(f"\n📊 Resultados:")
    log(f"   ✅ Productos con imagen: {len(matches)}", "success")
    log(f"   ❌ Productos sin match: {len(no_match)}", "warning")
    log(f"   📷 Imágenes usadas: {len(used_images)}")
    log(f"   📷 Imágenes sin usar: {len(imagenes) - len(used_images)}")

    return pd.DataFrame(matches + no_match)


# ============================================================================
# COPIA DE IMÁGENES
# ============================================================================

def copy_matched_images(df: pd.DataFrame, source_dir: str,
                        dest_dir: str, prefix: str = "IMG") -> pd.DataFrame:
    """Copia imágenes asociadas al directorio de destino con nombres limpios."""
    if not os.path.isdir(source_dir):
        log(f"⚠️ Directorio fuente no existe: {source_dir}", "warning")
        return df

    os.makedirs(dest_dir, exist_ok=True)

    copied = 0
    df['imagen_final'] = ''

    for idx, row in df.iterrows():
        img_match = str(row.get('imagen_match', ''))
        if not img_match:
            continue

        # Buscar archivo en source_dir
        src_path = os.path.join(source_dir, img_match)
        if not os.path.exists(src_path):
            # Intentar buscar recursivamente
            for root, dirs, files in os.walk(source_dir):
                if img_match in files:
                    src_path = os.path.join(root, img_match)
                    break

        if not os.path.exists(src_path):
            continue

        # Generar nombre limpio
        codigo = str(row.get('codigo', f'prod_{idx}'))
        ext = os.path.splitext(img_match)[1] or '.jpg'
        clean_name = f"{prefix}_{codigo}{ext}"
        dest_path = os.path.join(dest_dir, clean_name)

        # Evitar colisión
        counter = 1
        while os.path.exists(dest_path):
            clean_name = f"{prefix}_{codigo}_{counter}{ext}"
            dest_path = os.path.join(dest_dir, clean_name)
            counter += 1

        try:
            shutil.copy2(src_path, dest_path)
            df.at[idx, 'imagen_final'] = clean_name
            copied += 1
        except Exception as e:
            log(f"   Error copiando {img_match}: {e}", "warning")

    log(f"📦 Imágenes copiadas: {copied}", "success")
    return df


# ============================================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================================

def process_matching(
    products_csv: str,
    images_csv: str,
    output_dir: str,
    images_source_dir: Optional[str] = None,
    prefix: str = "ODI",
    threshold: float = SIMILARITY_THRESHOLD
) -> None:
    """Ejecuta el proceso completo de matching."""

    print(f"""
{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║           🔗 ODI IMAGE MATCHER v{VERSION}                        ║
║      Asociación semántica imagen-producto                    ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
""")

    os.makedirs(output_dir, exist_ok=True)

    # Cargar datos
    productos_df = load_products_csv(products_csv)
    imagenes_df = load_images_csv(images_csv)

    # Ejecutar matching
    result_df = match_products_to_images(productos_df, imagenes_df, threshold)

    # Copiar imágenes si hay directorio fuente
    if images_source_dir and os.path.isdir(images_source_dir):
        log(f"\n📁 Copiando imágenes desde: {images_source_dir}")
        dest_images = os.path.join(output_dir, "imagenes")
        result_df = copy_matched_images(result_df, images_source_dir, dest_images, prefix)

    # Guardar resultados
    log(f"\n💾 Guardando resultados...")

    csv_path = os.path.join(output_dir, f"{prefix}_productos_con_imagen.csv")
    result_df.to_csv(csv_path, sep=';', index=False, encoding='utf-8-sig')
    log(f"   📄 CSV: {csv_path}", "success")

    # Estadísticas finales
    con_imagen = (result_df['imagen_match'] != '').sum()
    sin_imagen = (result_df['imagen_match'] == '').sum()

    log(f"\n{'='*50}")
    log(f"📊 RESUMEN FINAL", "header")
    log(f"{'='*50}")
    log(f"   Total productos: {len(result_df)}")
    log(f"   ✅ Con imagen asociada: {con_imagen} ({100*con_imagen/len(result_df):.1f}%)")
    log(f"   ❌ Sin imagen: {sin_imagen}")

    # Muestra de matches
    log(f"\n📋 MEJORES MATCHES:")
    top_matches = result_df[result_df['match_score'] > 0].nlargest(5, 'match_score')
    for _, row in top_matches.iterrows():
        desc = str(row.get('descripcion', ''))[:35]
        img = str(row.get('imagen_match', ''))[:25]
        score = row.get('match_score', 0)
        log(f"   ★ {desc}... → {img} (score: {score:.2f})")

    log(f"\n{'='*50}")
    log("✅ PROCESO COMPLETADO", "success")
    log(f"{'='*50}\n")


# ============================================================================
# CLI
# ============================================================================

def print_help():
    print(f"""
{Colors.BOLD}ODI Image Matcher v{VERSION}{Colors.RESET}
{'='*55}

{Colors.CYAN}Uso:{Colors.RESET}
    python3 odi_image_matcher.py <productos.csv> <imagenes.csv> [opciones]

{Colors.CYAN}Argumentos:{Colors.RESET}
    productos.csv    CSV con productos (debe tener columna descripcion)
    imagenes.csv     CSV con análisis de imágenes (catalogo_kaiqi_imagenes)

{Colors.CYAN}Opciones:{Colors.RESET}
    --output, -o       Directorio de salida
    --images-dir       Carpeta con imágenes originales (para copiar)
    --prefix           Prefijo para archivos de salida
    --threshold        Umbral de similitud (0-1, default: 0.4)

{Colors.CYAN}Ejemplos:{Colors.RESET}
    python3 odi_image_matcher.py Base_Datos_Armotos.csv catalogo_kaiqi_imagenes.csv

    python3 odi_image_matcher.py \\
        Base_Datos_Armotos.csv \\
        catalogo_kaiqi_imagenes_ARMOTOS.csv \\
        --output /tmp/matched \\
        --images-dir /path/to/crops \\
        --prefix ARM

{Colors.CYAN}Salida:{Colors.RESET}
    output/
    ├── PREFIX_productos_con_imagen.csv  # Productos + columna imagen_match
    └── imagenes/                         # Imágenes copiadas (si --images-dir)
""")


def main():
    if len(sys.argv) < 3 or '--help' in sys.argv or '-h' in sys.argv:
        print_help()
        sys.exit(0 if '--help' in sys.argv else 1)

    products_csv = sys.argv[1]
    images_csv = sys.argv[2]

    output_dir = "/tmp/odi_matched"
    images_source = None
    prefix = "ODI"
    threshold = SIMILARITY_THRESHOLD

    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg in ['--output', '-o'] and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            i += 2
        elif arg == '--images-dir' and i + 1 < len(sys.argv):
            images_source = sys.argv[i + 1]
            i += 2
        elif arg == '--prefix' and i + 1 < len(sys.argv):
            prefix = sys.argv[i + 1].upper()
            i += 2
        elif arg == '--threshold' and i + 1 < len(sys.argv):
            threshold = float(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    if not os.path.exists(products_csv):
        log(f"❌ Archivo no encontrado: {products_csv}", "error")
        sys.exit(1)

    if not os.path.exists(images_csv):
        log(f"❌ Archivo no encontrado: {images_csv}", "error")
        sys.exit(1)

    process_matching(products_csv, images_csv, output_dir, images_source, prefix, threshold)


if __name__ == "__main__":
    main()
