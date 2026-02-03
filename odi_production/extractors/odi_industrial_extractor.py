#!/usr/bin/env python3
"""
==============================================================================
                    ODI INDUSTRIAL EXTRACTOR v2.0
              Extractor Multi-Empresa Multi-Industria
==============================================================================

DESCRIPCION:
    Extractor generico parametrizable por perfiles YAML.
    Soporta cualquier empresa/industria definida en profiles/*.yaml

ARQUITECTURA:
    profiles/
       yokomar.yaml    -> Repuestos motos Colombia
       kaiqi.yaml      -> Repuestos motos China
       bara.yaml       -> Repuestos autos
       vitton.yaml     -> Textiles
       ...

USO:
    python3 odi_industrial_extractor.py --profile yokomar
    python3 odi_industrial_extractor.py --profile kaiqi --data-dir /path/to/data
    python3 odi_industrial_extractor.py --list-profiles

AUTOR: ODI Team
VERSION: 2.0
==============================================================================
"""

import os
import sys
import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field

try:
    import yaml
    YAML_OK = True
except ImportError:
    YAML_OK = False
    print("Error: PyYAML requerido. Instalar: pip install pyyaml")
    sys.exit(1)

try:
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False
    print("Error: pandas requerido. Instalar: pip install pandas")
    sys.exit(1)


# ==============================================================================
# CONFIGURACION
# ==============================================================================

VERSION = "2.0"
SCRIPT_NAME = "ODI Industrial Extractor"

# Directorio de perfiles (relativo al script)
SCRIPT_DIR = Path(__file__).parent.resolve()
PROFILES_DIR = SCRIPT_DIR.parent / "profiles"
DEFAULT_OUTPUT_DIR = "/tmp/odi_output"


# ==============================================================================
# LOGGING Y UTILIDADES
# ==============================================================================

class Colors:
    """Codigos de color ANSI para terminal."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def log(msg: str, level: str = 'info'):
    """Log con formato y colores."""
    colors = {
        'info': Colors.CYAN, 'success': Colors.GREEN,
        'warning': Colors.YELLOW, 'error': Colors.RED,
        'header': Colors.BOLD, 'dim': Colors.DIM
    }
    icons = {
        'success': '+', 'warning': '!', 'error': 'x'
    }
    color = colors.get(level, '')
    icon = icons.get(level, ' ')
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"{color}[{ts}] {icon} {msg}{Colors.RESET}", flush=True)


def clean_text(text: Any) -> str:
    """Limpia y normaliza texto."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def clean_price(value: Any) -> float:
    """Extrae valor numerico de precio."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r'[^\d.]', '', value)
        if cleaned.count('.') > 1:
            parts = cleaned.split('.')
            cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    return 0.0


def is_valid_url(url: str) -> bool:
    """Verifica si una URL es valida."""
    if not url:
        return False
    return url.startswith('http://') or url.startswith('https://')


# ==============================================================================
# CARGADOR DE PERFILES
# ==============================================================================

class ProfileLoader:
    """Carga y gestiona perfiles de empresa desde YAML."""

    def __init__(self, profiles_dir: Path = PROFILES_DIR):
        self.profiles_dir = profiles_dir

    def list_profiles(self) -> List[str]:
        """Lista perfiles disponibles."""
        if not self.profiles_dir.exists():
            return []
        return [f.stem for f in self.profiles_dir.glob("*.yaml")]

    def load(self, profile_name: str) -> Dict[str, Any]:
        """Carga un perfil por nombre."""
        profile_path = self.profiles_dir / f"{profile_name}.yaml"

        if not profile_path.exists():
            raise FileNotFoundError(f"Perfil no encontrado: {profile_path}")

        log(f"Cargando perfil: {profile_name}")

        with open(profile_path, 'r', encoding='utf-8') as f:
            profile = yaml.safe_load(f)

        # Validar estructura minima
        required = ['empresa', 'archivos', 'categorias']
        for key in required:
            if key not in profile:
                raise ValueError(f"Perfil invalido: falta seccion '{key}'")

        return profile

    def get_profile_info(self, profile_name: str) -> Dict[str, str]:
        """Obtiene info basica de un perfil sin cargarlo completo."""
        profile_path = self.profiles_dir / f"{profile_name}.yaml"
        if not profile_path.exists():
            return {}

        with open(profile_path, 'r', encoding='utf-8') as f:
            # Solo leer las primeras lineas
            content = f.read(2000)

        # Parse parcial
        try:
            profile = yaml.safe_load(content)
            empresa = profile.get('empresa', {})
            return {
                'nombre': empresa.get('nombre', profile_name),
                'industria': empresa.get('industria', 'desconocida'),
                'region': empresa.get('region', 'N/A')
            }
        except:
            return {'nombre': profile_name}


# ==============================================================================
# MODELOS DE DATOS
# ==============================================================================

@dataclass
class ProductoODI:
    """Producto normalizado ODI (generico)."""
    sku_odi: str = ""
    codigo: str = ""
    nombre: str = ""
    descripcion: str = ""
    precio: float = 0.0
    imagen: str = ""
    categoria: str = "OTROS"
    # Campos especificos de industria (opcionales)
    marca: str = ""
    modelo: str = ""
    atributo_1: str = ""  # cilindraje, talla, etc.
    atributo_2: str = ""
    url_producto: str = ""
    vendor: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def is_valid(self) -> bool:
        """Verifica si el producto tiene datos minimos validos."""
        return bool(self.codigo and self.codigo.lower() not in ['', 'null', 'none', 'n/a'])


@dataclass
class ProcessingStats:
    """Estadisticas de procesamiento."""
    total_base: int = 0
    total_precios: int = 0
    productos_procesados: int = 0
    productos_con_precio: int = 0
    productos_con_imagen: int = 0
    productos_con_marca: int = 0
    productos_con_modelo: int = 0
    productos_por_categoria: Dict[str, int] = field(default_factory=dict)


# ==============================================================================
# EXTRACTORES SEMANTICOS (GENERICOS)
# ==============================================================================

class MarcaExtractor:
    """Extractor de marca desde descripcion, configurable por perfil."""

    def __init__(self, profile: Dict[str, Any]):
        marcas_config = profile.get('marcas_moto', {})
        self.prefijos = marcas_config.get('prefijos', {})
        self.keywords = marcas_config.get('keywords', {})
        self.marcas_completas = marcas_config.get('marcas_completas', [])

    def extract(self, descripcion: str) -> str:
        """Extrae marca de la descripcion."""
        if not descripcion:
            return ""

        desc_upper = descripcion.upper()

        # Buscar por prefijos especificos
        for prefix, marca in self.prefijos.items():
            if f" {prefix} " in f" {desc_upper} " or desc_upper.startswith(prefix):
                return marca
            prefix_clean = prefix.rstrip('.')
            if f" {prefix_clean} " in f" {desc_upper} ":
                return marca

        # Buscar por keywords
        for keyword, marca in self.keywords.items():
            if keyword.upper() in desc_upper:
                return marca

        # Buscar marcas completas
        for marca in self.marcas_completas:
            if marca.upper() in desc_upper:
                return marca

        return ""


class ModeloExtractor:
    """Extractor de modelo desde descripcion, configurable por perfil."""

    def __init__(self, profile: Dict[str, Any]):
        modelos_config = profile.get('modelos_moto', {})
        # Aplanar todos los modelos de todas las marcas
        self.modelos = []
        for marca, lista in modelos_config.items():
            if isinstance(lista, list):
                self.modelos.extend(lista)

    def extract(self, descripcion: str) -> str:
        """Extrae modelo de la descripcion."""
        if not descripcion:
            return ""

        desc_upper = descripcion.upper()

        # Ordenar por longitud (mas especifico primero)
        modelos_sorted = sorted(self.modelos, key=len, reverse=True)

        for modelo in modelos_sorted:
            modelo_upper = modelo.upper()
            if modelo_upper in desc_upper:
                return modelo_upper
            # Sin espacios/guiones
            modelo_compact = modelo_upper.replace(' ', '').replace('-', '')
            if modelo_compact in desc_upper.replace(' ', '').replace('-', ''):
                return modelo_upper

        # Patrones genericos de modelo
        patterns = [
            r'\b([A-Z]{1,3}\d{2,4}[A-Z]?)\b',  # CB190R, XR150L
            r'\b([A-Z]{2,4}\s*\d{3})\b',        # NS 200
        ]

        for pattern in patterns:
            match = re.search(pattern, desc_upper)
            if match:
                return match.group(0).strip()

        return ""


class AtributoExtractor:
    """Extractor de atributos especificos (cilindraje, talla, etc.)."""

    def __init__(self, profile: Dict[str, Any]):
        self.cilindrajes = profile.get('cilindrajes', {})

    def extract_cilindraje(self, descripcion: str, modelo: str = "") -> str:
        """Extrae cilindraje de la descripcion o modelo."""
        if not descripcion:
            return ""

        desc_upper = descripcion.upper()

        # Patron explicito
        patterns = [
            r'\b(\d{2,4})\s*CC\b',
            r'\b(\d{2,4})\s*C\.C\.\b',
            r'\bCC\s*(\d{2,4})\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, desc_upper)
            if match:
                return match.group(1)

        # Inferir del modelo/descripcion
        texto_busqueda = f"{descripcion} {modelo}".upper()
        for cc, keywords in self.cilindrajes.items():
            for kw in keywords:
                if kw.upper() in texto_busqueda:
                    return cc

        return ""


class CategoriaExtractor:
    """Extractor de categoria desde descripcion, configurable por perfil."""

    def __init__(self, profile: Dict[str, Any]):
        self.categorias = profile.get('categorias', {})

    def extract(self, descripcion: str) -> str:
        """Extrae categoria del producto basado en palabras clave."""
        if not descripcion:
            return "OTROS"

        desc_upper = descripcion.upper()

        best_category = "OTROS"
        best_matches = 0

        for cat_key, cat_info in self.categorias.items():
            matches = 0
            keywords = cat_info.get('keywords', [])
            for keyword in keywords:
                if keyword.upper() in desc_upper:
                    matches += 1

            if matches > best_matches:
                best_matches = matches
                best_category = cat_info.get('nombre', cat_key.upper())

        return best_category


# ==============================================================================
# PROCESADOR INDUSTRIAL (GENERICO)
# ==============================================================================

class IndustrialProcessor:
    """Procesador generico de catalogos industriales."""

    def __init__(self, profile: Dict[str, Any], config: Dict[str, Any]):
        self.profile = profile
        self.config = config

        # Configuracion de empresa
        self.empresa = profile.get('empresa', {})
        self.archivos = profile.get('archivos', {})

        # Directorios
        self.data_dir = config.get('data_dir') or self.archivos.get('directorio_default', '.')
        self.output_dir = config.get('output_dir', DEFAULT_OUTPUT_DIR)

        # Extractores
        self.marca_extractor = MarcaExtractor(profile)
        self.modelo_extractor = ModeloExtractor(profile)
        self.atributo_extractor = AtributoExtractor(profile)
        self.categoria_extractor = CategoriaExtractor(profile)

        # Estadisticas
        self.stats = ProcessingStats()

    def _get_column_value(self, row: dict, field_name: str) -> Any:
        """Obtiene valor de columna usando mapeo del perfil."""
        mapeo = self.profile.get('mapeo_columnas', {})
        posibles = mapeo.get(field_name, [field_name])

        for col in posibles:
            if col in row and row[col] is not None:
                return row[col]

        return None

    def _find_file(self, pattern: str) -> Optional[Path]:
        """Busca archivo que coincida con el patron."""
        data_path = Path(self.data_dir)
        if not data_path.exists():
            return None

        for f in data_path.glob(pattern):
            return f

        # Buscar sin extension
        for f in data_path.iterdir():
            if pattern.replace('*', '') in f.name:
                return f

        return None

    def load_base_datos(self, path: Optional[str] = None) -> pd.DataFrame:
        """Carga archivo base de datos."""
        if path:
            file_path = Path(path)
        else:
            pattern = self.archivos.get('base_datos_pattern', 'Base_Datos*.csv')
            file_path = self._find_file(pattern)

        if not file_path or not file_path.exists():
            log(f"Archivo base no encontrado en {self.data_dir}", "error")
            return pd.DataFrame()

        log(f"Cargando Base: {file_path.name}")

        try:
            df = pd.read_csv(
                file_path,
                sep=self.archivos.get('csv_separator', ';'),
                encoding=self.archivos.get('encoding', 'utf-8-sig')
            )
            self.stats.total_base = len(df)
            log(f"  Productos en base: {len(df)}", "success")
            return df
        except Exception as e:
            log(f"Error cargando base: {e}", "error")
            return pd.DataFrame()

    def load_lista_precios(self, path: Optional[str] = None) -> pd.DataFrame:
        """Carga archivo de precios (opcional)."""
        if path:
            file_path = Path(path)
        else:
            pattern = self.archivos.get('lista_precios_pattern', 'Lista_Precios*.csv')
            file_path = self._find_file(pattern)

        if not file_path or not file_path.exists():
            log(f"Archivo de precios no encontrado (opcional)", "warning")
            return pd.DataFrame()

        log(f"Cargando Precios: {file_path.name}")

        try:
            df = pd.read_csv(
                file_path,
                sep=self.archivos.get('csv_separator', ';'),
                encoding=self.archivos.get('encoding', 'utf-8-sig')
            )
            self.stats.total_precios = len(df)
            log(f"  Registros de precio: {len(df)}", "success")
            return df
        except Exception as e:
            log(f"Error cargando precios: {e}", "warning")
            return pd.DataFrame()

    def merge_data(self, df_base: pd.DataFrame, df_precios: pd.DataFrame) -> pd.DataFrame:
        """Une Base con Precios."""
        if df_base.empty:
            return pd.DataFrame()

        if df_precios.empty:
            log("Sin archivo de precios, continuando sin precios", "warning")
            df_base['PRECIO'] = 0
            return df_base

        # Buscar columnas de codigo
        codigo_cols_base = [c for c in df_base.columns if 'CODIGO' in c.upper() or 'SKU' in c.upper()]
        codigo_cols_precios = [c for c in df_precios.columns if 'CODIGO' in c.upper() or 'SKU' in c.upper()]

        if not codigo_cols_base or not codigo_cols_precios:
            log("No se encontro columna CODIGO para merge", "warning")
            df_base['PRECIO'] = 0
            return df_base

        codigo_base = codigo_cols_base[0]
        codigo_precios = codigo_cols_precios[0]

        # Buscar columna de precio
        precio_cols = [c for c in df_precios.columns if 'PRECIO' in c.upper() or 'PRICE' in c.upper()]
        if not precio_cols:
            log("No se encontro columna PRECIO", "warning")
            df_base['PRECIO'] = 0
            return df_base

        precio_col = precio_cols[0]

        # Preparar y hacer merge
        df_precios_clean = df_precios[[codigo_precios, precio_col]].copy()
        df_precios_clean.columns = ['CODIGO_MERGE', 'PRECIO']

        df_merged = df_base.merge(
            df_precios_clean,
            left_on=codigo_base,
            right_on='CODIGO_MERGE',
            how='left'
        )

        if 'CODIGO_MERGE' in df_merged.columns:
            df_merged = df_merged.drop(columns=['CODIGO_MERGE'])

        df_merged['PRECIO'] = df_merged['PRECIO'].fillna(0)

        productos_con_precio = (df_merged['PRECIO'] > 0).sum()
        log(f"Merge completado: {len(df_merged)} productos, {productos_con_precio} con precio", "success")

        return df_merged

    def process_product(self, row: dict, index: int) -> ProductoODI:
        """Procesa una fila y genera ProductoODI."""
        prefijo = self.empresa.get('prefijo_sku', 'ODI')
        vendor = self.empresa.get('vendor', self.empresa.get('nombre', 'ODI'))

        # Obtener campos usando mapeo
        codigo = str(self._get_column_value(row, 'codigo') or '').strip()
        descripcion = str(self._get_column_value(row, 'descripcion') or '').strip()
        precio = clean_price(self._get_column_value(row, 'precio') or row.get('PRECIO', 0))
        imagen = str(self._get_column_value(row, 'imagen') or '').strip()
        url_producto = str(self._get_column_value(row, 'url_producto') or '').strip()

        # Generar SKU ODI
        sku_odi = f"{prefijo}-{index+1:05d}"

        # Extraer campos semanticos
        marca = self.marca_extractor.extract(descripcion)
        modelo = self.modelo_extractor.extract(descripcion)
        atributo_1 = self.atributo_extractor.extract_cilindraje(descripcion, modelo)
        categoria = self.categoria_extractor.extract(descripcion)

        # Validar imagen
        if not is_valid_url(imagen):
            imagen = ""

        return ProductoODI(
            sku_odi=sku_odi,
            codigo=codigo,
            nombre=descripcion,
            descripcion=descripcion,
            precio=precio,
            imagen=imagen,
            categoria=categoria,
            marca=marca,
            modelo=modelo,
            atributo_1=atributo_1,
            url_producto=url_producto,
            vendor=vendor
        )

    def process(self) -> List[ProductoODI]:
        """Ejecuta el procesamiento completo."""
        self._print_banner()

        # Cargar datos
        df_base = self.load_base_datos(self.config.get('base_file'))
        df_precios = self.load_lista_precios(self.config.get('precios_file'))

        if df_base.empty:
            log("No hay datos para procesar", "error")
            return []

        # Merge
        df = self.merge_data(df_base, df_precios)

        if df.empty:
            log("Error en merge de datos", "error")
            return []

        # Procesar productos
        log("Procesando productos...")
        productos = []

        for i, row in df.iterrows():
            producto = self.process_product(row.to_dict(), i)
            if producto.is_valid():
                productos.append(producto)

                # Estadisticas
                if producto.precio > 0:
                    self.stats.productos_con_precio += 1
                if producto.imagen:
                    self.stats.productos_con_imagen += 1
                if producto.marca:
                    self.stats.productos_con_marca += 1
                if producto.modelo:
                    self.stats.productos_con_modelo += 1

                cat = producto.categoria
                self.stats.productos_por_categoria[cat] = \
                    self.stats.productos_por_categoria.get(cat, 0) + 1

        self.stats.productos_procesados = len(productos)
        log(f"Productos procesados: {len(productos)}", "success")

        return productos

    def export(self, productos: List[ProductoODI]) -> Tuple[str, str]:
        """Exporta productos a CSV y JSON."""
        if not productos:
            log("No hay productos para exportar", "warning")
            return "", ""

        os.makedirs(self.output_dir, exist_ok=True)

        # Crear DataFrame
        records = [p.to_dict() for p in productos]
        df = pd.DataFrame(records)

        # Renombrar columnas para compatibilidad
        rename_map = {
            'marca': 'marca_moto',
            'modelo': 'modelo_moto',
            'atributo_1': 'cilindraje'
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        # Ordenar columnas
        columns_order = [
            'sku_odi', 'codigo', 'nombre', 'descripcion', 'precio',
            'categoria', 'marca_moto', 'modelo_moto', 'cilindraje',
            'imagen', 'url_producto', 'vendor'
        ]
        df = df[[c for c in columns_order if c in df.columns]]

        # Timestamp y prefijo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = self.empresa.get('prefijo_sku', 'ODI')

        # Guardar CSV
        csv_filename = f"{prefix}_catalogo_{timestamp}.csv"
        csv_path = os.path.join(self.output_dir, csv_filename)
        df.to_csv(csv_path, sep=';', index=False, encoding='utf-8')
        log(f"CSV exportado: {csv_path}", "success")

        # CSV para normalizer
        proc = self.profile.get('procesamiento', {})
        if proc.get('generar_csv_normalizer', True):
            normalizer_csv = os.path.join(self.output_dir, f"{prefix}_REAL_INPUT.csv")
            df.to_csv(normalizer_csv, sep=';', index=False, encoding='utf-8')
            log(f"CSV normalizer: {normalizer_csv}", "success")

        # JSON
        json_path = ""
        if proc.get('generar_json', True):
            json_filename = f"{prefix}_catalogo_{timestamp}.json"
            json_path = os.path.join(self.output_dir, json_filename)
            df.to_json(json_path, orient='records', force_ascii=False, indent=2)
            log(f"JSON exportado: {json_path}", "success")

        return csv_path, json_path

    def _print_banner(self):
        """Imprime banner de inicio."""
        nombre = self.empresa.get('nombre', 'ODI')
        industria = self.empresa.get('industria', 'industrial')

        print(f"""
{Colors.BOLD}+{'='*62}+
|{' '*10}ODI INDUSTRIAL EXTRACTOR v{VERSION}{' '*16}|
|{' '*15}{nombre:^20}{' '*17}|
|{' '*12}Industria: {industria:^20}{' '*9}|
+{'='*62}+{Colors.RESET}
""")
        log(f"Directorio datos: {self.data_dir}")
        log(f"Directorio salida: {self.output_dir}")

    def print_stats(self):
        """Imprime estadisticas finales."""
        s = self.stats

        print(f"""
{Colors.BOLD}{'='*60}
 RESUMEN DE PROCESAMIENTO - {self.empresa.get('nombre', 'ODI')}
{'='*60}{Colors.RESET}

{Colors.GREEN}+ Productos en Base:{Colors.RESET}       {s.total_base:,}
{Colors.GREEN}+ Productos procesados:{Colors.RESET}   {s.productos_procesados:,}
{Colors.GREEN}+ Con precio:{Colors.RESET}             {s.productos_con_precio:,}
{Colors.GREEN}+ Con imagen:{Colors.RESET}             {s.productos_con_imagen:,}
{Colors.CYAN}o Con marca detectada:{Colors.RESET}    {s.productos_con_marca:,}
{Colors.CYAN}o Con modelo detectado:{Colors.RESET}   {s.productos_con_modelo:,}

{Colors.BOLD}Por categoria:{Colors.RESET}""")

        for cat, count in sorted(s.productos_por_categoria.items(), key=lambda x: -x[1]):
            total = sum(s.productos_por_categoria.values())
            pct = count / total * 100 if total else 0
            print(f"  {cat:20} {count:5,} ({pct:5.1f}%)")

        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}\n")


# ==============================================================================
# CLI
# ==============================================================================

def list_profiles():
    """Lista perfiles disponibles."""
    loader = ProfileLoader()
    profiles = loader.list_profiles()

    print(f"\n{Colors.BOLD}Perfiles disponibles:{Colors.RESET}")
    print(f"{'='*50}")

    if not profiles:
        print(f"  {Colors.YELLOW}No hay perfiles en {PROFILES_DIR}{Colors.RESET}")
        return

    for name in sorted(profiles):
        info = loader.get_profile_info(name)
        nombre = info.get('nombre', name)
        industria = info.get('industria', 'N/A')
        region = info.get('region', 'N/A')
        print(f"  {Colors.GREEN}{name:15}{Colors.RESET} - {nombre} ({industria}, {region})")

    print(f"\n{Colors.DIM}Uso: python3 {os.path.basename(__file__)} --profile <nombre>{Colors.RESET}\n")


def print_help():
    """Imprime ayuda."""
    print(f"""
{Colors.BOLD}{SCRIPT_NAME} v{VERSION}{Colors.RESET}
{'='*60}

{Colors.CYAN}DESCRIPCION:{Colors.RESET}
    Extractor multi-empresa parametrizable por perfiles YAML.
    Cada empresa tiene su propio perfil con taxonomia y configuracion.

{Colors.CYAN}USO:{Colors.RESET}
    python3 {os.path.basename(__file__)} --profile <nombre> [opciones]

{Colors.CYAN}OPCIONES:{Colors.RESET}
    --profile NAME      Nombre del perfil (ej: yokomar, kaiqi, bara)
    --list-profiles     Listar perfiles disponibles
    --data-dir DIR      Directorio con archivos de datos
    --base FILE         Archivo base de datos (*.csv)
    --precios FILE      Archivo de precios (*.csv)
    --output, -o DIR    Directorio de salida (default: {DEFAULT_OUTPUT_DIR})
    --help, -h          Mostrar esta ayuda

{Colors.CYAN}EJEMPLOS:{Colors.RESET}
    # Listar perfiles
    python3 {os.path.basename(__file__)} --list-profiles

    # Procesar Yokomar desde directorio por defecto
    python3 {os.path.basename(__file__)} --profile yokomar

    # Procesar con directorio especifico
    python3 {os.path.basename(__file__)} --profile yokomar --data-dir /path/to/data

    # Procesar con archivos especificos
    python3 {os.path.basename(__file__)} --profile yokomar --base datos.csv --precios precios.csv

{Colors.CYAN}PERFILES:{Colors.RESET}
    Los perfiles se almacenan en: {PROFILES_DIR}/
    Cada perfil define:
    - Configuracion de empresa (nombre, prefijo SKU, vendor)
    - Mapeo de columnas de entrada
    - Taxonomia de marcas/modelos (para industria moto)
    - Taxonomia de categorias
    - Configuracion de Shopify

{Colors.CYAN}CREAR NUEVO PERFIL:{Colors.RESET}
    1. Copiar profiles/_template.yaml a profiles/<empresa>.yaml
    2. Editar configuracion, taxonomia y categorias
    3. Ejecutar: python3 {os.path.basename(__file__)} --profile <empresa>
""")


def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description=f'{SCRIPT_NAME} v{VERSION}',
        add_help=False
    )

    parser.add_argument('--profile', type=str, help='Nombre del perfil')
    parser.add_argument('--list-profiles', action='store_true', help='Listar perfiles')
    parser.add_argument('--data-dir', type=str, help='Directorio de datos')
    parser.add_argument('--base', type=str, help='Archivo base')
    parser.add_argument('--precios', type=str, help='Archivo precios')
    parser.add_argument('--output', '-o', type=str, default=DEFAULT_OUTPUT_DIR, help='Directorio salida')
    parser.add_argument('--help', '-h', action='store_true', help='Mostrar ayuda')

    args = parser.parse_args()

    if args.help:
        print_help()
        sys.exit(0)

    if args.list_profiles:
        list_profiles()
        sys.exit(0)

    if not args.profile:
        print(f"{Colors.RED}Error: Debe especificar --profile <nombre>{Colors.RESET}")
        print(f"Use --list-profiles para ver perfiles disponibles")
        print(f"Use --help para ver ayuda completa")
        sys.exit(1)

    # Cargar perfil
    try:
        loader = ProfileLoader()
        profile = loader.load(args.profile)
    except FileNotFoundError as e:
        log(str(e), "error")
        log("Use --list-profiles para ver perfiles disponibles", "warning")
        sys.exit(1)
    except Exception as e:
        log(f"Error cargando perfil: {e}", "error")
        sys.exit(1)

    # Configuracion
    config = {
        'data_dir': args.data_dir,
        'output_dir': args.output,
        'base_file': args.base,
        'precios_file': args.precios,
    }

    # Procesar
    try:
        processor = IndustrialProcessor(profile, config)
        productos = processor.process()

        if productos:
            csv_path, json_path = processor.export(productos)
            processor.print_stats()

            log("Proceso completado exitosamente", "success")
            log(f"  Archivo CSV: {csv_path}")
            log(f"  Siguiente paso: python3 odi_semantic_normalizer.py {csv_path}")
        else:
            log("No se generaron productos", "warning")
            sys.exit(1)

    except KeyboardInterrupt:
        log("\nProceso interrumpido por usuario", "warning")
        sys.exit(130)
    except Exception as e:
        log(f"Error fatal: {e}", "error")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
