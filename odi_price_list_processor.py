#!/usr/bin/env python3
"""
==============================================================================
                    ODI PRICE LIST PROCESSOR v1.0
              Extractor Universal de Listas de Precios
==============================================================================

DESCRIPCION:
    Procesa archivos de listas de precios en diferentes formatos (PDF, XLSX, CSV)
    y genera un archivo unificado de precios para enriquecer catálogos.

FORMATOS SOPORTADOS:
    - PDF: Usa GPT-4o Vision para extraer tablas de precios
    - XLSX/XLS: Lee directamente con openpyxl/pandas
    - CSV: Lee con pandas (detecta automáticamente el separador)

SALIDA:
    Genera un CSV normalizado con columnas: CODIGO, PRECIO, DESCUENTO (opcional)

USO:
    python3 odi_price_list_processor.py <archivo> [opciones]

EJEMPLOS:
    python3 odi_price_list_processor.py "LISTA DE PRECIO_28-01-26.pdf" --prefix YOKOMAR
    python3 odi_price_list_processor.py precios.xlsx --output /tmp/precios.csv
    python3 odi_price_list_processor.py --merge-all /path/to/empresa

AUTOR: ODI Team
VERSION: 1.0
==============================================================================
"""

import os
import sys
import json
import re
import time
import base64
import argparse
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict

# ==============================================================================
# DEPENDENCIAS
# ==============================================================================

def check_dependencies():
    """Verifica e importa dependencias."""
    missing = []

    global pd, np, OpenAI

    try:
        import pandas as pd
    except ImportError:
        missing.append("pandas")

    try:
        import numpy as np
    except ImportError:
        missing.append("numpy")

    try:
        from openai import OpenAI
    except ImportError:
        missing.append("openai")

    # openpyxl es opcional pero recomendado
    try:
        import openpyxl
    except ImportError:
        print("NOTA: openpyxl no instalado. Para mejor soporte XLSX: pip install openpyxl")

    if missing:
        print(f"Dependencias faltantes: {', '.join(missing)}")
        print(f"Instalar: pip install {' '.join(missing)}")
        sys.exit(1)

    return True

check_dependencies()
import pandas as pd
import numpy as np
from openai import OpenAI

# Event Emitter para Cortex Visual
try:
    from odi_event_emitter import ODIEventEmitter
    EMITTER_AVAILABLE = True
except ImportError:
    EMITTER_AVAILABLE = False
    ODIEventEmitter = None


# ==============================================================================
# CONFIGURACION
# ==============================================================================

VERSION = "1.0"
SCRIPT_NAME = "ODI Price List Processor"

# Vision API
VISION_MODEL = "gpt-4o"
MAX_TOKENS = 4096
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 2
REQUEST_TIMEOUT = 120
MIN_REQUEST_INTERVAL = 0.5

# PDF conversion
DEFAULT_DPI = 150

# Output
DEFAULT_OUTPUT_DIR = "/tmp/odi_prices"


# ==============================================================================
# LOGGER
# ==============================================================================

class Logger:
    """Logger simple con colores."""

    COLORS = {
        "info": "\033[94m",    # Azul
        "success": "\033[92m", # Verde
        "warning": "\033[93m", # Amarillo
        "error": "\033[91m",   # Rojo
        "debug": "\033[90m",   # Gris
        "reset": "\033[0m"
    }

    def __init__(self, prefix: str = ""):
        self.prefix = prefix

    def log(self, message: str, level: str = "info"):
        color = self.COLORS.get(level, "")
        reset = self.COLORS["reset"]
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {color}{self.prefix}{message}{reset}")

log = Logger()


# ==============================================================================
# UTILIDADES
# ==============================================================================

def ensure_dir(path: str) -> str:
    """Crea directorio si no existe."""
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def clean_price(value: Any) -> float:
    """Limpia y convierte un valor a precio flotante."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remover todo excepto digitos, punto y coma
        cleaned = value.strip()
        # Detectar formato europeo (1.234,56) vs americano (1,234.56)
        if ',' in cleaned and '.' in cleaned:
            if cleaned.rfind(',') > cleaned.rfind('.'):
                # Formato europeo: 1.234,56
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # Formato americano: 1,234.56
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned and '.' not in cleaned:
            # Podria ser 1234,56 o 1,234
            if cleaned.count(',') == 1 and len(cleaned.split(',')[1]) <= 2:
                # Probablemente decimal: 1234,56
                cleaned = cleaned.replace(',', '.')
            else:
                # Probablemente miles: 1,234,567
                cleaned = cleaned.replace(',', '')

        # Remover simbolos de moneda y espacios
        cleaned = re.sub(r'[^\d.]', '', cleaned)

        # Manejar multiples puntos
        if cleaned.count('.') > 1:
            parts = cleaned.split('.')
            cleaned = ''.join(parts[:-1]) + '.' + parts[-1]

        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    return 0.0


def clean_code(value: Any) -> str:
    """Limpia un codigo de producto."""
    if value is None:
        return ""
    code = str(value).strip().upper()
    # Remover caracteres especiales pero mantener alfanumericos y guiones
    code = re.sub(r'[^\w\-]', '', code)
    return code


def detect_csv_separator(file_path: str) -> str:
    """Detecta el separador de un archivo CSV."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        first_lines = ''.join([f.readline() for _ in range(5)])

    # Contar ocurrencias
    separators = {';': 0, ',': 0, '\t': 0, '|': 0}
    for sep in separators:
        separators[sep] = first_lines.count(sep)

    # Retornar el mas comun
    return max(separators, key=separators.get)


# ==============================================================================
# PROCESADOR DE PDF CON VISION AI
# ==============================================================================

PRICE_LIST_PROMPT = """Analiza esta pagina de lista de precios de repuestos.

INSTRUCCIONES:
1. Extrae TODOS los productos con precio visibles en la pagina
2. Para cada producto identifica:
   - codigo: Codigo/referencia del producto (CRITICO - debe coincidir exactamente)
   - precio: Precio numerico SIN simbolos ni separadores de miles
   - descuento: Porcentaje de descuento si existe (solo el numero, ej: 10 para 10%)
   - precio_con_descuento: Precio final si hay descuento aplicado

REGLAS:
- Extrae el codigo EXACTAMENTE como aparece (ej: "M110001", "YK-5432", "50100")
- Los precios deben ser solo numeros (ej: 45000, no "$45.000" ni "45,000")
- Si hay multiples columnas de precios (mayorista, minorista, etc), usa el precio MAS BAJO
- Si no hay codigo visible para un precio, omite esa linea
- Incluye productos aunque no tengan descuento

FORMATO DE RESPUESTA:
Responde SOLO con un JSON array. Ejemplo:
[
  {"codigo": "M110001", "precio": 45000, "descuento": 0, "precio_con_descuento": 45000},
  {"codigo": "YK-5432", "precio": 120000, "descuento": 10, "precio_con_descuento": 108000}
]

Si la pagina no tiene lista de precios (solo logos, portada, etc), responde: []
"""


class VisionPriceExtractor:
    """Extrae precios de imagenes usando GPT-4o Vision."""

    def __init__(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            log.log("OPENAI_API_KEY no configurada", "error")
            sys.exit(1)
        self.client = OpenAI(api_key=api_key)
        self.last_request_time = 0

    def _throttle(self):
        """Respeta rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def _encode_image(self, image_path: str) -> str:
        """Codifica imagen a base64."""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def extract_prices(self, image_path: str) -> List[Dict]:
        """Extrae precios de una imagen de lista de precios."""
        self._throttle()

        try:
            image_b64 = self._encode_image(image_path)

            for attempt in range(MAX_RETRIES):
                try:
                    response = self.client.chat.completions.create(
                        model=VISION_MODEL,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": PRICE_LIST_PROMPT},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_b64}",
                                            "detail": "high"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=MAX_TOKENS,
                        timeout=REQUEST_TIMEOUT
                    )

                    content = response.choices[0].message.content.strip()

                    # Limpiar respuesta
                    if content.startswith('```'):
                        content = re.sub(r'^```\w*\n?', '', content)
                        content = re.sub(r'\n?```$', '', content)

                    # Parsear JSON
                    try:
                        prices = json.loads(content)
                        if isinstance(prices, list):
                            return prices
                    except json.JSONDecodeError:
                        # Intentar extraer JSON del contenido
                        match = re.search(r'\[.*\]', content, re.DOTALL)
                        if match:
                            try:
                                prices = json.loads(match.group())
                                return prices
                            except:
                                pass

                    return []

                except Exception as e:
                    if "rate_limit" in str(e).lower():
                        delay = INITIAL_RETRY_DELAY * (2 ** attempt)
                        log.log(f"Rate limit, esperando {delay}s...", "warning")
                        time.sleep(delay)
                    elif attempt < MAX_RETRIES - 1:
                        time.sleep(INITIAL_RETRY_DELAY)
                    else:
                        raise

            return []

        except Exception as e:
            log.log(f"Error extrayendo precios: {e}", "error")
            return []


class PDFPriceProcessor:
    """Procesa PDFs de listas de precios."""

    def __init__(self, dpi: int = DEFAULT_DPI):
        self.dpi = dpi
        self.extractor = VisionPriceExtractor()
        self._check_pdftoppm()

    def _check_pdftoppm(self):
        """Verifica que pdftoppm este instalado."""
        try:
            subprocess.run(['pdftoppm', '-v'], capture_output=True, timeout=5)
        except FileNotFoundError:
            log.log("pdftoppm no encontrado. Instalar: apt install poppler-utils", "error")
            sys.exit(1)
        except Exception:
            pass

    def get_page_count(self, pdf_path: str) -> Optional[int]:
        """Obtiene numero de paginas del PDF."""
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
        """Convierte una pagina a imagen JPEG."""
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

            result = subprocess.run(cmd, capture_output=True, timeout=120)
            return result.returncode == 0 and os.path.exists(output_path)

        except Exception as e:
            log.log(f"Error convirtiendo pagina {page_num}: {e}", "warning")
            return False

    def process(self, pdf_path: str, pages: str = "all",
                progress_callback=None) -> List[Dict]:
        """
        Procesa un PDF de lista de precios.

        Args:
            pdf_path: Ruta al archivo PDF
            pages: Rango de paginas ("all", "2-50", "1,3,5-10")
            progress_callback: Funcion para reportar progreso

        Returns:
            Lista de diccionarios con codigo, precio, descuento
        """
        if not os.path.exists(pdf_path):
            log.log(f"Archivo no encontrado: {pdf_path}", "error")
            return []

        # Obtener numero de paginas
        total_pages = self.get_page_count(pdf_path)
        if not total_pages:
            log.log("No se pudo obtener numero de paginas", "error")
            return []

        log.log(f"PDF tiene {total_pages} paginas", "info")

        # Parsear rango de paginas
        page_list = self._parse_pages(pages, total_pages)
        log.log(f"Procesando {len(page_list)} paginas", "info")

        # Crear directorio temporal
        temp_dir = tempfile.mkdtemp(prefix="odi_prices_")

        all_prices = []

        try:
            for i, page_num in enumerate(page_list):
                # Reportar progreso
                if progress_callback:
                    progress_callback(i + 1, len(page_list), page_num)

                log.log(f"Procesando pagina {page_num}/{total_pages}...", "info")

                # Convertir pagina a imagen
                image_path = os.path.join(temp_dir, f"page_{page_num:03d}.jpg")
                if not self.convert_page(pdf_path, page_num, image_path):
                    log.log(f"Error convirtiendo pagina {page_num}", "warning")
                    continue

                # Extraer precios
                prices = self.extractor.extract_prices(image_path)

                if prices:
                    log.log(f"  -> {len(prices)} precios extraidos", "success")
                    for p in prices:
                        p['pagina'] = page_num
                    all_prices.extend(prices)
                else:
                    log.log(f"  -> Sin precios en esta pagina", "debug")

                # Limpiar imagen
                try:
                    os.remove(image_path)
                except:
                    pass

        finally:
            # Limpiar directorio temporal
            try:
                os.rmdir(temp_dir)
            except:
                pass

        log.log(f"Total precios extraidos: {len(all_prices)}", "success")
        return all_prices

    def _parse_pages(self, pages_str: str, total: int) -> List[int]:
        """Parsea especificacion de paginas."""
        if pages_str.lower() == "all":
            return list(range(1, total + 1))

        result = []
        for part in pages_str.split(','):
            if '-' in part:
                start, end = part.split('-')
                start = int(start.strip())
                end = min(int(end.strip()), total)
                result.extend(range(start, end + 1))
            else:
                page = int(part.strip())
                if 1 <= page <= total:
                    result.append(page)

        return sorted(set(result))


# ==============================================================================
# PROCESADOR DE EXCEL
# ==============================================================================

class ExcelPriceProcessor:
    """Procesa archivos XLSX/XLS de listas de precios."""

    # Nombres comunes de columnas de codigo
    CODE_COLUMNS = ['CODIGO', 'codigo', 'Codigo', 'SKU', 'sku', 'Sku',
                    'REFERENCIA', 'referencia', 'Referencia', 'REF', 'ref',
                    'ITEM', 'item', 'Item', 'ARTICULO', 'articulo', 'Articulo',
                    'COD', 'cod', 'Cod', 'CODE', 'code', 'Code']

    # Nombres comunes de columnas de precio
    PRICE_COLUMNS = ['PRECIO', 'precio', 'Precio', 'PRICE', 'price', 'Price',
                     'VALOR', 'valor', 'Valor', 'COSTO', 'costo', 'Costo',
                     'PRECIO_LISTA', 'precio_lista', 'PVP', 'pvp',
                     'PRECIO UNITARIO', 'Precio Unitario', 'P.UNIT', 'P. Unit',
                     'PRECIO_VENTA', 'PRECIO VENTA', 'PRECIO_PUBLICO']

    # Nombres comunes de columnas de descuento
    DISCOUNT_COLUMNS = ['DESCUENTO', 'descuento', 'Descuento', 'DESC', 'desc',
                        'DISCOUNT', 'discount', 'Discount', '%DESC', '%DESCUENTO',
                        'PORCENTAJE', 'porcentaje']

    def process(self, file_path: str, sheet_name: Optional[str] = None) -> List[Dict]:
        """
        Procesa un archivo Excel.

        Args:
            file_path: Ruta al archivo XLSX/XLS
            sheet_name: Nombre de la hoja (None = primera hoja)

        Returns:
            Lista de diccionarios con codigo, precio, descuento
        """
        if not os.path.exists(file_path):
            log.log(f"Archivo no encontrado: {file_path}", "error")
            return []

        try:
            # Leer Excel
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(file_path)

            log.log(f"Archivo leido: {len(df)} filas", "info")
            log.log(f"Columnas: {list(df.columns)}", "debug")

            # Encontrar columnas
            code_col = self._find_column(df.columns, self.CODE_COLUMNS)
            price_col = self._find_column(df.columns, self.PRICE_COLUMNS)
            discount_col = self._find_column(df.columns, self.DISCOUNT_COLUMNS)

            if not code_col:
                log.log("No se encontro columna de codigo", "error")
                return []

            if not price_col:
                log.log("No se encontro columna de precio", "error")
                return []

            log.log(f"Columna codigo: {code_col}", "info")
            log.log(f"Columna precio: {price_col}", "info")
            if discount_col:
                log.log(f"Columna descuento: {discount_col}", "info")

            # Procesar filas
            prices = []
            for idx, row in df.iterrows():
                codigo = clean_code(row.get(code_col))
                precio = clean_price(row.get(price_col))

                if not codigo or precio <= 0:
                    continue

                item = {
                    'codigo': codigo,
                    'precio': precio,
                    'descuento': 0,
                    'precio_con_descuento': precio
                }

                if discount_col and pd.notna(row.get(discount_col)):
                    desc = clean_price(row.get(discount_col))
                    if 0 < desc < 100:
                        item['descuento'] = desc
                        item['precio_con_descuento'] = precio * (1 - desc/100)

                prices.append(item)

            log.log(f"Precios extraidos: {len(prices)}", "success")
            return prices

        except Exception as e:
            log.log(f"Error procesando Excel: {e}", "error")
            return []

    def _find_column(self, columns, candidates: List[str]) -> Optional[str]:
        """Encuentra una columna por nombre."""
        for col in columns:
            col_str = str(col).strip()
            if col_str in candidates:
                return col_str
            # Buscar coincidencia parcial
            for cand in candidates:
                if cand.lower() in col_str.lower():
                    return col_str
        return None


# ==============================================================================
# PROCESADOR DE CSV
# ==============================================================================

class CSVPriceProcessor:
    """Procesa archivos CSV de listas de precios."""

    CODE_COLUMNS = ExcelPriceProcessor.CODE_COLUMNS
    PRICE_COLUMNS = ExcelPriceProcessor.PRICE_COLUMNS
    DISCOUNT_COLUMNS = ExcelPriceProcessor.DISCOUNT_COLUMNS

    def process(self, file_path: str, separator: Optional[str] = None) -> List[Dict]:
        """
        Procesa un archivo CSV.

        Args:
            file_path: Ruta al archivo CSV
            separator: Separador (None = auto-detectar)

        Returns:
            Lista de diccionarios con codigo, precio, descuento
        """
        if not os.path.exists(file_path):
            log.log(f"Archivo no encontrado: {file_path}", "error")
            return []

        try:
            # Detectar separador si no se especifica
            if separator is None:
                separator = detect_csv_separator(file_path)
                log.log(f"Separador detectado: '{separator}'", "debug")

            # Leer CSV
            df = pd.read_csv(file_path, sep=separator, encoding='utf-8-sig')

            log.log(f"Archivo leido: {len(df)} filas", "info")

            # Encontrar columnas
            code_col = self._find_column(df.columns, self.CODE_COLUMNS)
            price_col = self._find_column(df.columns, self.PRICE_COLUMNS)
            discount_col = self._find_column(df.columns, self.DISCOUNT_COLUMNS)

            if not code_col:
                log.log("No se encontro columna de codigo", "error")
                return []

            if not price_col:
                log.log("No se encontro columna de precio", "error")
                return []

            # Procesar filas
            prices = []
            for idx, row in df.iterrows():
                codigo = clean_code(row.get(code_col))
                precio = clean_price(row.get(price_col))

                if not codigo or precio <= 0:
                    continue

                item = {
                    'codigo': codigo,
                    'precio': precio,
                    'descuento': 0,
                    'precio_con_descuento': precio
                }

                if discount_col and pd.notna(row.get(discount_col)):
                    desc = clean_price(row.get(discount_col))
                    if 0 < desc < 100:
                        item['descuento'] = desc
                        item['precio_con_descuento'] = precio * (1 - desc/100)

                prices.append(item)

            log.log(f"Precios extraidos: {len(prices)}", "success")
            return prices

        except Exception as e:
            log.log(f"Error procesando CSV: {e}", "error")
            return []

    def _find_column(self, columns, candidates: List[str]) -> Optional[str]:
        """Encuentra una columna por nombre."""
        for col in columns:
            col_str = str(col).strip()
            if col_str in candidates:
                return col_str
            for cand in candidates:
                if cand.lower() in col_str.lower():
                    return col_str
        return None


# ==============================================================================
# PROCESADOR UNIFICADO
# ==============================================================================

class PriceListProcessor:
    """
    Procesador unificado de listas de precios.
    Detecta automaticamente el formato y procesa el archivo.
    """

    def __init__(self):
        self.pdf_processor = None
        self.excel_processor = ExcelPriceProcessor()
        self.csv_processor = CSVPriceProcessor()
        self.emitter = None

        if EMITTER_AVAILABLE:
            try:
                self.emitter = ODIEventEmitter(source="price_processor", actor="ODI_PRICES_v1")
            except:
                pass

    def process_file(self, file_path: str, **kwargs) -> List[Dict]:
        """
        Procesa un archivo de precios (detecta formato automaticamente).

        Args:
            file_path: Ruta al archivo
            **kwargs: Argumentos adicionales segun formato

        Returns:
            Lista de diccionarios con precios
        """
        ext = Path(file_path).suffix.lower()

        log.log(f"Procesando: {Path(file_path).name}", "info")
        log.log(f"Formato detectado: {ext}", "info")

        if ext == '.pdf':
            if self.pdf_processor is None:
                self.pdf_processor = PDFPriceProcessor()
            return self.pdf_processor.process(file_path, **kwargs)

        elif ext in ['.xlsx', '.xls']:
            return self.excel_processor.process(file_path, **kwargs)

        elif ext == '.csv':
            return self.csv_processor.process(file_path, **kwargs)

        else:
            log.log(f"Formato no soportado: {ext}", "error")
            return []

    def process_directory(self, dir_path: str, patterns: List[str] = None) -> Dict[str, List[Dict]]:
        """
        Procesa todos los archivos de precios en un directorio.

        Args:
            dir_path: Ruta al directorio
            patterns: Patrones de archivos (default: ["Lista_Precios*", "LISTA*PRECIO*"])

        Returns:
            Diccionario con nombre de archivo -> lista de precios
        """
        if patterns is None:
            patterns = [
                "Lista_Precios*",
                "LISTA*PRECIO*",
                "*precios*",
                "*PRECIOS*"
            ]

        dir_path = Path(dir_path)
        if not dir_path.exists():
            log.log(f"Directorio no encontrado: {dir_path}", "error")
            return {}

        # Buscar archivos
        files = []
        for pattern in patterns:
            files.extend(dir_path.glob(pattern))

        # Filtrar por extension soportada
        supported_ext = ['.pdf', '.xlsx', '.xls', '.csv']
        files = [f for f in files if f.suffix.lower() in supported_ext]
        files = list(set(files))  # Eliminar duplicados

        if not files:
            log.log(f"No se encontraron archivos de precios en {dir_path}", "warning")
            return {}

        log.log(f"Encontrados {len(files)} archivos de precios", "info")

        results = {}
        for file in sorted(files):
            log.log(f"\n{'='*60}", "info")
            prices = self.process_file(str(file))
            if prices:
                results[file.name] = prices

        return results

    def merge_prices(self, price_lists: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """
        Combina multiples listas de precios en un diccionario unico.
        Si hay duplicados, usa el precio mas bajo.

        Args:
            price_lists: Diccionario de nombre_archivo -> lista de precios

        Returns:
            Diccionario codigo -> {precio, descuento, fuente}
        """
        merged = {}

        for source, prices in price_lists.items():
            for item in prices:
                codigo = item.get('codigo', '').strip().upper()
                if not codigo:
                    continue

                precio = item.get('precio_con_descuento', item.get('precio', 0))

                if codigo not in merged or precio < merged[codigo]['precio']:
                    merged[codigo] = {
                        'precio': precio,
                        'precio_original': item.get('precio', precio),
                        'descuento': item.get('descuento', 0),
                        'fuente': source
                    }

        log.log(f"Precios unicos despues de merge: {len(merged)}", "success")
        return merged

    def export_prices(self, prices: Dict[str, Dict], output_path: str):
        """
        Exporta precios a CSV normalizado.

        Args:
            prices: Diccionario codigo -> {precio, descuento, fuente}
            output_path: Ruta del archivo de salida
        """
        rows = []
        for codigo, data in sorted(prices.items()):
            rows.append({
                'CODIGO': codigo,
                'PRECIO': data.get('precio', 0),
                'PRECIO_ORIGINAL': data.get('precio_original', 0),
                'DESCUENTO': data.get('descuento', 0),
                'FUENTE': data.get('fuente', '')
            })

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False, sep=';')
        log.log(f"Precios exportados a: {output_path}", "success")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ODI Price List Processor - Extrae precios de PDF/XLSX/CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s "LISTA DE PRECIO.pdf" --prefix YOKOMAR
  %(prog)s precios.xlsx --output /tmp/precios.csv
  %(prog)s --merge-all /path/to/empresa --output precios_unificados.csv
  %(prog)s archivo.csv --separator ";"
        """
    )

    parser.add_argument('input', nargs='?', help='Archivo o directorio a procesar')
    parser.add_argument('--pages', default='all', help='Paginas a procesar para PDF (ej: "2-50", "all")')
    parser.add_argument('--prefix', default='', help='Prefijo para archivos de salida')
    parser.add_argument('--output', '-o', help='Archivo de salida')
    parser.add_argument('--separator', help='Separador CSV (auto-detectar si no se especifica)')
    parser.add_argument('--merge-all', metavar='DIR', help='Procesar y combinar todos los archivos de un directorio')
    parser.add_argument('--dpi', type=int, default=DEFAULT_DPI, help='DPI para conversion PDF')

    args = parser.parse_args()

    print(f"""
{'='*60}
     ODI PRICE LIST PROCESSOR v{VERSION}
     Extractor Universal de Listas de Precios
{'='*60}
    """)

    processor = PriceListProcessor()

    # Modo: procesar directorio
    if args.merge_all:
        results = processor.process_directory(args.merge_all)
        if results:
            merged = processor.merge_prices(results)

            # Exportar
            if args.output:
                output_path = args.output
            else:
                prefix = args.prefix or Path(args.merge_all).name
                output_path = f"{DEFAULT_OUTPUT_DIR}/{prefix}_precios_unificados.csv"

            ensure_dir(os.path.dirname(output_path))
            processor.export_prices(merged, output_path)

            # Resumen
            print(f"\n{'='*60}")
            print(f"  RESUMEN")
            print(f"{'='*60}")
            print(f"  Archivos procesados: {len(results)}")
            print(f"  Precios unicos: {len(merged)}")
            print(f"  Archivo de salida: {output_path}")

        return

    # Modo: procesar archivo individual
    if not args.input:
        parser.print_help()
        return

    input_path = args.input

    if os.path.isdir(input_path):
        # Procesar directorio
        results = processor.process_directory(input_path)
        if results:
            merged = processor.merge_prices(results)

            if args.output:
                output_path = args.output
            else:
                prefix = args.prefix or Path(input_path).name
                output_path = f"{DEFAULT_OUTPUT_DIR}/{prefix}_precios.csv"

            ensure_dir(os.path.dirname(output_path))
            processor.export_prices(merged, output_path)

    else:
        # Procesar archivo individual
        kwargs = {'pages': args.pages} if args.pages else {}
        if args.separator:
            kwargs['separator'] = args.separator

        prices = processor.process_file(input_path, **kwargs)

        if prices:
            # Convertir a diccionario
            price_dict = {}
            for item in prices:
                codigo = item.get('codigo', '').strip().upper()
                if codigo:
                    price_dict[codigo] = {
                        'precio': item.get('precio_con_descuento', item.get('precio', 0)),
                        'precio_original': item.get('precio', 0),
                        'descuento': item.get('descuento', 0),
                        'fuente': Path(input_path).name
                    }

            # Exportar
            if args.output:
                output_path = args.output
            else:
                prefix = args.prefix or Path(input_path).stem
                output_path = f"{DEFAULT_OUTPUT_DIR}/{prefix}_precios.csv"

            ensure_dir(os.path.dirname(output_path))
            processor.export_prices(price_dict, output_path)

            # Resumen
            print(f"\n{'='*60}")
            print(f"  RESUMEN")
            print(f"{'='*60}")
            print(f"  Precios extraidos: {len(prices)}")
            print(f"  Precios unicos: {len(price_dict)}")
            print(f"  Archivo de salida: {output_path}")

            # Muestra
            print(f"\n  MUESTRA (primeros 10):")
            for codigo, data in list(price_dict.items())[:10]:
                print(f"    {codigo}: ${data['precio']:,.0f}")


if __name__ == "__main__":
    main()
