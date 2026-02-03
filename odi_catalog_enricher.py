#!/usr/bin/env python3
"""
==============================================================================
                    ODI CATALOG ENRICHER v1.0
              Enriquecedor de Catalogos con Precios y Datos
==============================================================================

DESCRIPCION:
    Combina datos de catalogos extraidos con precios de multiples fuentes
    (CSV, XLSX, PDF de listas de precios) para generar un catalogo completo.

FLUJO:
    1. Lee catalogo extraido (CSV/JSON del Vision Extractor)
    2. Busca y procesa archivos de precios en el directorio de datos
    3. Mapea precios a productos por codigo
    4. Genera catalogo enriquecido listo para Shopify

USO:
    python3 odi_catalog_enricher.py <catalogo> <directorio_datos> [opciones]

EJEMPLOS:
    python3 odi_catalog_enricher.py YOKOMAR_catalogo.csv /data/Yokomar
    python3 odi_catalog_enricher.py catalogo.json /data/empresa --output catalogo_final.csv

AUTOR: ODI Team
VERSION: 1.0
==============================================================================
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

# ==============================================================================
# DEPENDENCIAS
# ==============================================================================

def check_dependencies():
    """Verifica e importa dependencias."""
    global pd, np

    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        print("Instalar dependencias: pip install pandas numpy")
        sys.exit(1)

    return True

check_dependencies()
import pandas as pd
import numpy as np

# Importar procesador de precios
try:
    from odi_price_list_processor import PriceListProcessor, clean_price, clean_code
except ImportError:
    # Fallback si no esta disponible
    def clean_price(value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = re.sub(r'[^\d.]', '', value)
            try:
                return float(cleaned) if cleaned else 0.0
            except ValueError:
                return 0.0
        return 0.0

    def clean_code(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().upper()

    PriceListProcessor = None


# Event Emitter
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
SCRIPT_NAME = "ODI Catalog Enricher"

# Patrones de archivos de precios
PRICE_FILE_PATTERNS = [
    "Lista_Precios*",
    "LISTA*PRECIO*",
    "*precios*",
    "*PRECIOS*",
    "*price*",
    "*PRICE*"
]

# Extensiones soportadas
SUPPORTED_EXTENSIONS = ['.csv', '.xlsx', '.xls', '.pdf']


# ==============================================================================
# LOGGER
# ==============================================================================

class Logger:
    """Logger simple con colores."""

    COLORS = {
        "info": "\033[94m",
        "success": "\033[92m",
        "warning": "\033[93m",
        "error": "\033[91m",
        "debug": "\033[90m",
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
# NORMALIZADOR DE CODIGOS
# ==============================================================================

class CodeNormalizer:
    """
    Normaliza y mapea codigos de productos para mejorar coincidencias.
    """

    def __init__(self, prefix: str = ""):
        self.prefix = prefix.upper()

    def normalize(self, code: str) -> str:
        """Normaliza un codigo para comparacion."""
        if not code:
            return ""

        code = str(code).strip().upper()

        # Remover prefijos comunes de empresa
        prefixes_to_remove = ['YOKOMAR-', 'YK-', 'KQ-', 'KAIQI-', 'ARM-', 'ARMOTOS-']
        for prefix in prefixes_to_remove:
            if code.startswith(prefix):
                code = code[len(prefix):]
                break

        # Remover caracteres especiales pero mantener alfanumericos
        code = re.sub(r'[^\w]', '', code)

        return code

    def create_variants(self, code: str) -> List[str]:
        """
        Genera variantes de un codigo para busqueda flexible.

        Ejemplo: "YOKOMAR-M110001" genera:
        - "YOKOMAR-M110001"
        - "M110001"
        - "YOKOMARM110001"
        """
        variants = set()
        code_upper = str(code).strip().upper()

        # Original
        variants.add(code_upper)

        # Sin guiones
        variants.add(code_upper.replace('-', ''))

        # Sin prefijo de empresa
        normalized = self.normalize(code_upper)
        variants.add(normalized)

        # Con prefijo de esta empresa
        if self.prefix and not normalized.startswith(self.prefix):
            variants.add(f"{self.prefix}-{normalized}")
            variants.add(f"{self.prefix}{normalized}")

        return list(variants)

    def find_match(self, code: str, price_dict: Dict[str, Any]) -> Optional[str]:
        """
        Busca un codigo en el diccionario de precios usando variantes.

        Returns:
            El codigo encontrado en price_dict, o None si no hay coincidencia.
        """
        variants = self.create_variants(code)

        # Busqueda directa
        for variant in variants:
            if variant in price_dict:
                return variant

        # Busqueda normalizada en ambos lados
        normalized_input = self.normalize(code)
        for price_code in price_dict.keys():
            if self.normalize(price_code) == normalized_input:
                return price_code

        return None


# ==============================================================================
# CATALOG ENRICHER
# ==============================================================================

class CatalogEnricher:
    """
    Enriquece catalogos extraidos con precios de multiples fuentes.
    """

    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self.code_normalizer = CodeNormalizer(prefix)
        self.price_processor = None
        self.emitter = None

        # Inicializar procesador de precios si esta disponible
        if PriceListProcessor:
            self.price_processor = PriceListProcessor()

        # Inicializar emitter
        if EMITTER_AVAILABLE:
            try:
                self.emitter = ODIEventEmitter(source="enricher", actor="ODI_ENRICHER_v1")
            except:
                pass

    def load_catalog(self, catalog_path: str) -> pd.DataFrame:
        """
        Carga un catalogo desde CSV o JSON.

        Args:
            catalog_path: Ruta al archivo de catalogo

        Returns:
            DataFrame con los productos
        """
        ext = Path(catalog_path).suffix.lower()

        if ext == '.json':
            with open(catalog_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.DataFrame(data)

        elif ext == '.csv':
            # Detectar separador
            with open(catalog_path, 'r', encoding='utf-8-sig') as f:
                first_line = f.readline()

            sep = ';' if ';' in first_line else ','
            df = pd.read_csv(catalog_path, sep=sep, encoding='utf-8-sig')

        else:
            raise ValueError(f"Formato no soportado: {ext}")

        log.log(f"Catalogo cargado: {len(df)} productos", "info")
        return df

    def find_price_files(self, data_dir: str) -> List[Path]:
        """
        Busca archivos de precios en un directorio.

        Args:
            data_dir: Directorio a buscar

        Returns:
            Lista de archivos encontrados
        """
        data_path = Path(data_dir)
        if not data_path.exists():
            log.log(f"Directorio no encontrado: {data_dir}", "error")
            return []

        files = []
        for pattern in PRICE_FILE_PATTERNS:
            files.extend(data_path.glob(pattern))

        # Filtrar por extension soportada
        files = [f for f in files if f.suffix.lower() in SUPPORTED_EXTENSIONS]
        files = list(set(files))  # Eliminar duplicados

        log.log(f"Archivos de precios encontrados: {len(files)}", "info")
        for f in files:
            log.log(f"  - {f.name}", "debug")

        return files

    def load_prices_from_files(self, price_files: List[Path]) -> Dict[str, Dict]:
        """
        Carga precios de multiples archivos.

        Args:
            price_files: Lista de archivos de precios

        Returns:
            Diccionario codigo -> {precio, descuento, fuente}
        """
        if not self.price_processor:
            log.log("PriceListProcessor no disponible, usando metodo alternativo", "warning")
            return self._load_prices_basic(price_files)

        all_prices = {}

        for file_path in price_files:
            log.log(f"Procesando: {file_path.name}", "info")
            try:
                prices = self.price_processor.process_file(str(file_path))
                for item in prices:
                    codigo = clean_code(item.get('codigo', ''))
                    if not codigo:
                        continue

                    precio = item.get('precio_con_descuento', item.get('precio', 0))

                    # Guardar si es nuevo o tiene mejor precio
                    if codigo not in all_prices or precio < all_prices[codigo]['precio']:
                        all_prices[codigo] = {
                            'precio': precio,
                            'precio_original': item.get('precio', precio),
                            'descuento': item.get('descuento', 0),
                            'fuente': file_path.name
                        }

            except Exception as e:
                log.log(f"Error procesando {file_path.name}: {e}", "warning")

        log.log(f"Total precios cargados: {len(all_prices)}", "success")
        return all_prices

    def _load_prices_basic(self, price_files: List[Path]) -> Dict[str, Dict]:
        """
        Metodo basico para cargar precios (sin PriceListProcessor).
        Solo soporta CSV.
        """
        all_prices = {}

        for file_path in price_files:
            if file_path.suffix.lower() != '.csv':
                log.log(f"Saltando {file_path.name} (solo CSV soportado)", "warning")
                continue

            try:
                # Detectar separador
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    first_line = f.readline()
                sep = ';' if ';' in first_line else ','

                df = pd.read_csv(file_path, sep=sep, encoding='utf-8-sig')

                # Buscar columnas de codigo y precio
                code_col = None
                price_col = None

                for col in df.columns:
                    col_lower = col.lower()
                    if 'codigo' in col_lower or 'sku' in col_lower or 'ref' in col_lower:
                        code_col = col
                    if 'precio' in col_lower or 'price' in col_lower or 'valor' in col_lower:
                        price_col = col

                if not code_col or not price_col:
                    continue

                for idx, row in df.iterrows():
                    codigo = clean_code(row.get(code_col))
                    precio = clean_price(row.get(price_col))

                    if codigo and precio > 0:
                        all_prices[codigo] = {
                            'precio': precio,
                            'precio_original': precio,
                            'descuento': 0,
                            'fuente': file_path.name
                        }

            except Exception as e:
                log.log(f"Error: {e}", "warning")

        return all_prices

    def enrich_catalog(self, df: pd.DataFrame, prices: Dict[str, Dict]) -> pd.DataFrame:
        """
        Enriquece un catalogo con precios.

        Args:
            df: DataFrame del catalogo
            prices: Diccionario de precios

        Returns:
            DataFrame enriquecido
        """
        # Identificar columna de codigo
        code_col = None
        for col in df.columns:
            col_lower = col.lower()
            if 'codigo' in col_lower or 'sku' in col_lower:
                code_col = col
                break

        if not code_col:
            log.log("No se encontro columna de codigo en el catalogo", "error")
            return df

        log.log(f"Columna de codigo: {code_col}", "info")

        # Agregar columnas de precio si no existen
        if 'precio' not in [c.lower() for c in df.columns]:
            df['precio'] = 0.0
        if 'precio_original' not in [c.lower() for c in df.columns]:
            df['precio_original'] = 0.0
        if 'descuento' not in [c.lower() for c in df.columns]:
            df['descuento'] = 0.0
        if 'precio_fuente' not in [c.lower() for c in df.columns]:
            df['precio_fuente'] = ''

        # Encontrar columnas de precio (case insensitive)
        precio_col = next((c for c in df.columns if c.lower() == 'precio'), 'precio')
        precio_orig_col = next((c for c in df.columns if c.lower() == 'precio_original'), 'precio_original')
        descuento_col = next((c for c in df.columns if c.lower() == 'descuento'), 'descuento')
        fuente_col = next((c for c in df.columns if c.lower() == 'precio_fuente'), 'precio_fuente')

        # Estadisticas
        matched = 0
        not_matched = 0

        # Enriquecer cada producto
        for idx, row in df.iterrows():
            codigo = str(row[code_col]).strip().upper() if pd.notna(row[code_col]) else ""
            if not codigo:
                continue

            # Buscar precio usando normalizador
            matched_code = self.code_normalizer.find_match(codigo, prices)

            if matched_code:
                price_data = prices[matched_code]
                df.at[idx, precio_col] = price_data['precio']
                df.at[idx, precio_orig_col] = price_data.get('precio_original', price_data['precio'])
                df.at[idx, descuento_col] = price_data.get('descuento', 0)
                df.at[idx, fuente_col] = price_data.get('fuente', '')
                matched += 1
            else:
                not_matched += 1

        # Reporte
        total = matched + not_matched
        pct = (matched / total * 100) if total > 0 else 0
        log.log(f"Productos enriquecidos: {matched}/{total} ({pct:.1f}%)", "success")
        if not_matched > 0:
            log.log(f"Productos sin precio: {not_matched}", "warning")

        return df

    def process(self, catalog_path: str, data_dir: str, output_path: str = None) -> pd.DataFrame:
        """
        Proceso completo de enriquecimiento.

        Args:
            catalog_path: Ruta al catalogo extraido
            data_dir: Directorio con archivos de precios
            output_path: Ruta de salida (opcional)

        Returns:
            DataFrame enriquecido
        """
        log.log(f"\n{'='*60}", "info")
        log.log("INICIANDO ENRIQUECIMIENTO DE CATALOGO", "info")
        log.log(f"{'='*60}", "info")

        # Cargar catalogo
        log.log(f"\n[1/4] Cargando catalogo...", "info")
        df = self.load_catalog(catalog_path)

        # Buscar archivos de precios
        log.log(f"\n[2/4] Buscando archivos de precios...", "info")
        price_files = self.find_price_files(data_dir)

        if not price_files:
            log.log("No se encontraron archivos de precios", "warning")
            return df

        # Cargar precios
        log.log(f"\n[3/4] Cargando precios...", "info")
        prices = self.load_prices_from_files(price_files)

        if not prices:
            log.log("No se pudieron cargar precios", "warning")
            return df

        # Enriquecer
        log.log(f"\n[4/4] Enriqueciendo catalogo...", "info")
        df = self.enrich_catalog(df, prices)

        # Guardar si se especifico output
        if output_path:
            self.export(df, output_path)

        return df

    def export(self, df: pd.DataFrame, output_path: str):
        """
        Exporta el catalogo enriquecido.

        Args:
            df: DataFrame a exportar
            output_path: Ruta de salida
        """
        ext = Path(output_path).suffix.lower()

        if ext == '.json':
            df.to_json(output_path, orient='records', force_ascii=False, indent=2)
        else:
            df.to_csv(output_path, index=False, sep=';', encoding='utf-8-sig')

        log.log(f"Catalogo exportado: {output_path}", "success")


# ==============================================================================
# INTEGRACION CON VISION EXTRACTOR
# ==============================================================================

def auto_enrich_after_extraction(
    catalog_csv: str,
    data_dir: str = None,
    output_suffix: str = "_enriched"
) -> Optional[str]:
    """
    Enriquece automaticamente un catalogo despues de la extraccion.
    Diseñado para ser llamado desde odi_vision_extractor_v3.py

    Args:
        catalog_csv: Ruta al CSV del catalogo extraido
        data_dir: Directorio con archivos de precios (auto-detectar si None)
        output_suffix: Sufijo para el archivo enriquecido

    Returns:
        Ruta al archivo enriquecido, o None si falla
    """
    try:
        catalog_path = Path(catalog_csv)

        # Auto-detectar directorio de datos
        if data_dir is None:
            # Buscar en directorio padre y rutas comunes
            possible_dirs = [
                catalog_path.parent,
                catalog_path.parent.parent,
                Path("/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data"),
            ]

            for d in possible_dirs:
                if d.exists():
                    # Buscar subdirectorio con nombre similar al prefijo
                    prefix = catalog_path.stem.split('_')[0].upper()
                    for subdir in d.iterdir():
                        if subdir.is_dir() and prefix.lower() in subdir.name.lower():
                            data_dir = str(subdir)
                            break
                if data_dir:
                    break

        if not data_dir:
            log.log("No se pudo detectar directorio de datos", "warning")
            return None

        # Crear enricher
        prefix = catalog_path.stem.split('_')[0].upper()
        enricher = CatalogEnricher(prefix=prefix)

        # Generar ruta de salida
        output_path = catalog_path.with_stem(catalog_path.stem + output_suffix)

        # Procesar
        enricher.process(str(catalog_path), data_dir, str(output_path))

        return str(output_path) if output_path.exists() else None

    except Exception as e:
        log.log(f"Error en auto-enriquecimiento: {e}", "error")
        return None


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ODI Catalog Enricher - Enriquece catalogos con precios',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s YOKOMAR_catalogo.csv /data/Yokomar
  %(prog)s catalogo.json /data/empresa --output catalogo_final.csv
  %(prog)s --auto YOKOMAR_catalogo.csv
        """
    )

    parser.add_argument('catalog', nargs='?', help='Archivo de catalogo (CSV o JSON)')
    parser.add_argument('data_dir', nargs='?', help='Directorio con archivos de precios')
    parser.add_argument('--output', '-o', help='Archivo de salida')
    parser.add_argument('--prefix', default='', help='Prefijo de empresa para normalizar codigos')
    parser.add_argument('--auto', metavar='CATALOG', help='Modo automatico: detecta directorio de datos')

    args = parser.parse_args()

    print(f"""
{'='*60}
     ODI CATALOG ENRICHER v{VERSION}
     Enriquecedor de Catalogos con Precios
{'='*60}
    """)

    # Modo automatico
    if args.auto:
        result = auto_enrich_after_extraction(args.auto)
        if result:
            print(f"\nCatalogo enriquecido: {result}")
        else:
            print("\nNo se pudo enriquecer el catalogo")
        return

    # Modo normal
    if not args.catalog or not args.data_dir:
        parser.print_help()
        return

    # Extraer prefijo del nombre del archivo si no se especifica
    prefix = args.prefix
    if not prefix:
        prefix = Path(args.catalog).stem.split('_')[0].upper()

    enricher = CatalogEnricher(prefix=prefix)

    # Generar output path si no se especifica
    output_path = args.output
    if not output_path:
        catalog_path = Path(args.catalog)
        output_path = str(catalog_path.with_stem(catalog_path.stem + '_enriched'))

    # Procesar
    df = enricher.process(args.catalog, args.data_dir, output_path)

    # Resumen final
    print(f"\n{'='*60}")
    print(f"  RESUMEN FINAL")
    print(f"{'='*60}")
    print(f"  Productos totales: {len(df)}")

    # Contar productos con precio
    precio_col = next((c for c in df.columns if c.lower() == 'precio'), None)
    if precio_col:
        con_precio = (df[precio_col] > 0).sum()
        sin_precio = (df[precio_col] == 0).sum() + df[precio_col].isna().sum()
        print(f"  Con precio: {con_precio}")
        print(f"  Sin precio: {sin_precio}")

    print(f"  Archivo: {output_path}")

    # Muestra de productos con precio
    if precio_col:
        print(f"\n  MUESTRA (productos con precio):")
        sample = df[df[precio_col] > 0].head(10)
        code_col = next((c for c in df.columns if 'codigo' in c.lower()), df.columns[0])
        for idx, row in sample.iterrows():
            print(f"    {row[code_col]}: ${row[precio_col]:,.0f}")


if __name__ == "__main__":
    main()
