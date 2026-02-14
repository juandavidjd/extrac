#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════
                    ODI YOKOMAR EXTRACTOR v1.0
              Extractor y Procesador de Catálogo Yokomar
══════════════════════════════════════════════════════════════════════════════

DESCRIPCION:
    Extractor especializado para procesar el catálogo de Yokomar.
    Combina Base_Datos + Lista_Precios y genera formato ODI normalizado.

CARACTERISTICAS:
    - Procesamiento de Base_Datos_Yokomar.csv + Lista_Precios_Yokomar.csv
    - Extracción automática de marca y modelo de moto
    - Inferencia de categorías basada en palabras clave
    - Normalización de precios
    - Validación de URLs de imágenes
    - Generación de SKU ODI unificado
    - Salida CSV/JSON lista para ODI Semantic Normalizer

INSTALACION:
    pip install pandas

USO:
    python3 odi_yokomar_extractor.py --data-dir /path/to/yokomar
    python3 odi_yokomar_extractor.py --base datos.csv --precios precios.csv
    python3 odi_yokomar_extractor.py --test  # Genera datos de prueba

AUTOR: ODI Team
VERSION: 1.0
══════════════════════════════════════════════════════════════════════════════
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
    import pandas as pd
    PANDAS_OK = True
except ImportError:
    PANDAS_OK = False
    print("Error: pandas requerido. Instalar: pip install pandas")
    sys.exit(1)


# ============================================================================
# CONFIGURACION
# ============================================================================

VERSION = "1.0"
SCRIPT_NAME = "ODI Yokomar Extractor"

# Directorios por defecto
DEFAULT_DATA_DIR = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Yokomar"
DEFAULT_OUTPUT_DIR = "/tmp/odi_yokomar"

# Archivos esperados
BASE_DATOS_FILENAME = "Base_Datos_Yokomar.csv"
LISTA_PRECIOS_FILENAME = "Lista_Precios_Yokomar.csv"

# Configuracion de empresa
EMPRESA_CONFIG = {
    "nombre": "YOKOMAR",
    "prefijo_sku": "YOK",
    "vendor": "YOKOMAR",
    "csv_separator": ";",
    "encoding": "utf-8-sig",
    "price_margin": 1.25,
}


# ============================================================================
# TAXONOMIA DE MARCAS Y MODELOS
# ============================================================================

# Marcas de motos con sus códigos en descripciones Yokomar
MARCAS_MOTO = {
    # Prefijos cortos usados en Yokomar
    'H.': 'HONDA',
    'S.': 'SUZUKI',
    'Y.': 'YAMAHA',
    'K.': 'KAWASAKI',
    'AK.': 'AKT',
    'B.': 'BAJAJ',
    'KTM.': 'KTM',
    'TVS.': 'TVS',
    'HERO.': 'HERO',
    'PULSAR': 'BAJAJ',  # Pulsar es de Bajaj
    'DISCOVER': 'BAJAJ',
    'BOXER': 'BAJAJ',
    'APACHE': 'TVS',
    'GIXXER': 'SUZUKI',
    'FZ': 'YAMAHA',
    'MT': 'YAMAHA',
    'NMAX': 'YAMAHA',
    'XR': 'HONDA',
    'CB': 'HONDA',
    'CBR': 'HONDA',
    'ECO': 'HONDA',
    'WAVE': 'HONDA',
    'NXR': 'HONDA',
    'CG': 'HONDA',
    'SPLENDOR': 'HERO',
    'DUKE': 'KTM',
    'RC': 'KTM',
    'NINJA': 'KAWASAKI',
    'Z': 'KAWASAKI',
    'VERSYS': 'KAWASAKI',
    'DR': 'SUZUKI',
    'GN': 'SUZUKI',
    'EN': 'SUZUKI',
    'AX': 'SUZUKI',
    'BEST': 'AKT',
    'NKD': 'AKT',
    'TTR': 'AKT',
    'DT': 'YAMAHA',
    'RX': 'YAMAHA',
    'LIBERO': 'YAMAHA',
    'CRYPTON': 'YAMAHA',
    'BWS': 'YAMAHA',
}

# Modelos comunes
MODELOS_MOTO = [
    # Honda
    'XR125', 'XR150', 'XR150L', 'XR190', 'XR250', 'XR650',
    'CBF125', 'CBF150', 'CBF160', 'CBF190R',
    'CB110', 'CB125', 'CB150', 'CB160', 'CB190R', 'CB250', 'CB300',
    'CB190', 'CB160F', 'CB125F',
    'CBR250', 'CBR300', 'CBR500', 'CBR600', 'CBR650', 'CBR1000',
    'NXR125', 'NXR150', 'NXR160', 'BROS160',
    'WAVE110', 'WAVE100', 'BIZ125',
    'CG125', 'CG150', 'CG160', 'TITAN150', 'TITAN160',
    'ECO DELUXE', 'ECO100', 'ECO DELUXE 100',
    'NAVI', 'NAVI110',
    'XL125', 'XL185', 'XL200',
    'AFRICA TWIN', 'CRF250', 'CRF300', 'CRF450', 'CRF1000', 'CRF1100',

    # Yamaha
    'FZ16', 'FZ25', 'FZ-S', 'FZS', 'FZ15', 'FZ 2.0', 'FZ-FI',
    'MT03', 'MT-03', 'MT07', 'MT-07', 'MT09', 'MT-09', 'MT15', 'MT-15',
    'YBR125', 'YBR250', 'YS250', 'FAZER250', 'FAZER150',
    'NMAX', 'NMAX155', 'NMAX CONNECTED',
    'XTZ125', 'XTZ150', 'XTZ250', 'LANDER250', 'TENERE250', 'TENERE700',
    'CRYPTON', 'CRYPTON110', 'T110',
    'LIBERO', 'LIBERO110', 'LIBERO125',
    'DT125', 'DT175', 'DT200',
    'RX100', 'RX115', 'RX135',
    'BWS', 'BWS125', 'BWS-X', 'AEROX', 'AEROX155',
    'XSR155', 'XSR700', 'XSR900',
    'R15', 'YZF-R15', 'R3', 'YZF-R3', 'R6', 'R7', 'R1',

    # Bajaj
    'PULSAR135', 'PULSAR150', 'PULSAR180', 'PULSAR200',
    'PULSAR NS125', 'PULSAR NS160', 'PULSAR NS200', 'PULSAR NS400',
    'PULSAR 200NS', 'NS200', 'NS160', 'NS125',
    'PULSAR RS200', 'RS200',
    'PULSAR220', 'PULSAR 220F',
    'DISCOVER100', 'DISCOVER125', 'DISCOVER125 ST', 'DISCOVER150',
    'BOXER100', 'BOXER CT', 'BOXER CT100', 'BOXER BM100', 'BOXER BM150',
    'PLATINO', 'PLATINO100', 'PLATINO125',
    'DOMINAR250', 'DOMINAR400', 'DOMINAR',
    'AVENGER', 'AVENGER220', 'AVENGER CRUISE',

    # Suzuki
    'GIXXER150', 'GIXXER155', 'GIXXER SF', 'GIXXER SF 250',
    'GIXXER250', 'GIXXER 250',
    'GSX-S150', 'GSX-R150', 'GSX-S750', 'GSX-R1000',
    'GN125', 'GN125F', 'GN125H',
    'EN125', 'EN125-2A', 'INTRUDER125',
    'AX100', 'AX4', 'AX-4',
    'GS125', 'GS150',
    'VSTROM250', 'VSTROM650', 'V-STROM',
    'DR200', 'DR650',
    'HAYABUSA', 'GSX1300R',
    'BURGMAN', 'BURGMAN200', 'BURGMAN400',
    'ADDRESS', 'ADDRESS110',

    # TVS
    'APACHE RTR', 'APACHE 160', 'APACHE 180', 'APACHE 200',
    'APACHE RTR160', 'APACHE RTR180', 'APACHE RTR200',
    'APACHE RTR 160 4V', 'RTR160', 'RTR180', 'RTR200', 'RTR310',
    'NTORQ', 'NTORQ125',
    'RAIDER', 'RAIDER125',
    'SPORT', 'STAR CITY',
    'RR310', 'RR 310',

    # AKT
    'AKT125', 'AKT125 TT', 'AKT125 SL', 'AKT125 SPECIAL',
    'AKT150', 'AKT150 TT',
    'AKT200', 'AKT 200 SM', 'AKT 200 TT',
    'AK125', 'AK150',
    'BEST125', 'NKD125', 'NKD200',
    'TTR125', 'TTR200',
    'TT125', 'TT150', 'TT200',
    'FLEX', 'FLEX125', 'FLEX150',
    'CR4', 'CR4 125', 'CR5', 'CR5 180',

    # KTM
    'DUKE125', 'DUKE200', 'DUKE250', 'DUKE390', 'DUKE690', 'DUKE790',
    'RC125', 'RC200', 'RC390',
    'ADVENTURE390', 'ADVENTURE790', 'ADVENTURE890', 'ADVENTURE1290',
    '390 ADVENTURE', '790 ADVENTURE', '890 ADVENTURE',
    'EXC', 'SX', 'SX-F',

    # Kawasaki
    'NINJA250', 'NINJA300', 'NINJA400', 'NINJA650', 'NINJA1000', 'ZX-10R',
    'Z250', 'Z300', 'Z400', 'Z650', 'Z900', 'Z1000',
    'ER6N', 'ER-6N', 'ER6F',
    'VERSYS300', 'VERSYS650', 'VERSYS1000',
    'KLR650', 'KLX110', 'KLX150', 'KLX250', 'KLX300',
    'VULCAN', 'VULCAN650', 'VULCAN900',
    'W800',

    # Hero
    'SPLENDOR', 'SPLENDOR PLUS', 'SPLENDOR I3S',
    'PASSION', 'PASSION PRO', 'PASSION XPRO',
    'GLAMOUR', 'GLAMOUR FI',
    'HUNK', 'HUNK 150R', 'HUNK 200R', 'XTREME160R', 'XTREME200R',
    'XPULSE200', 'XPULSE 200', 'XPULSE200T',
    'IGNITOR', 'ECO DELUXE',
    'MAESTRO', 'DESTINI', 'PLEASURE',
]

# Cilindrajes comunes (para inferir del modelo)
CILINDRAJES = {
    '100': ['100', 'CT100', 'BM100', 'RX100', 'AX100', 'ECO100', 'WAVE100'],
    '110': ['110', 'CB110', 'WAVE110', 'CRYPTON110', 'T110', 'LIBERO110', 'NAVI110', 'ADDRESS110'],
    '125': ['125', 'XR125', 'NXR125', 'CG125', 'GN125', 'EN125', 'YBR125', 'FZ125', 'GS125',
            'XTZ125', 'LIBERO125', 'AKT125', 'AK125', 'BEST125', 'NKD125', 'TTR125', 'FLEX125',
            'CR4 125', 'DUKE125', 'RC125', 'BWS125', 'BIZ125', 'NTORQ125', 'RAIDER125'],
    '135': ['135', 'RX135', 'PULSAR135'],
    '150': ['150', 'XR150', 'NXR150', 'CG150', 'CBF150', 'CBF150', 'CB150', 'GS150', 'XTZ150',
            'GIXXER150', 'GSX150', 'AKT150', 'AK150', 'TTR150', 'TT150', 'FLEX150', 'FAZER150',
            'PULSAR150', 'DISCOVER150', 'GSX-S150', 'GSX-R150'],
    '155': ['155', 'GIXXER155', 'NMAX155', 'XSR155', 'AEROX155'],
    '160': ['160', 'CB160', 'CBF160', 'NXR160', 'BROS160', 'TITAN160', 'CG160',
            'NS160', 'PULSAR NS160', 'APACHE160', 'RTR160', 'XTREME160R'],
    '180': ['180', 'PULSAR180', 'APACHE180', 'RTR180', 'CR5 180'],
    '190': ['190', 'XR190', 'CB190', 'CB190R', 'CBF190R'],
    '200': ['200', 'XL200', 'PULSAR200', 'NS200', 'RS200', 'DOMINAR200', 'DUKE200', 'RC200',
            'APACHE200', 'RTR200', 'AKT200', 'TTR200', 'NKD200', 'TT200', 'DR200', 'HUNK200R',
            'XTREME200R', 'XPULSE200', 'BURGMAN200'],
    '220': ['220', 'PULSAR220', 'AVENGER220'],
    '250': ['250', 'XR250', 'YS250', 'LANDER250', 'FAZER250', 'GIXXER250', 'VSTROM250',
            'DUKE250', 'DOMINAR250', 'NINJA250', 'Z250', 'KLX250', 'TENERE250'],
    '300': ['300', 'CB300', 'CBR300', 'NINJA300', 'Z300', 'VERSYS300', 'KLX300', 'XTZ300',
            'CRF300'],
    '310': ['310', 'RR310', 'RTR310'],
    '390': ['390', 'DUKE390', 'RC390', '390 ADVENTURE'],
    '400': ['400', 'NINJA400', 'Z400', 'DOMINAR400', 'NS400', 'BURGMAN400'],
}


# ============================================================================
# TAXONOMIA DE CATEGORIAS
# ============================================================================

CATEGORY_TAXONOMY = {
    # Motor
    'motor': {
        'keywords': ['CILINDRO', 'PISTON', 'PISTÓN', 'ANILLO', 'BIELA', 'CIGÜEÑAL',
                     'CIGUEÑAL', 'VALVULA', 'VÁLVULA', 'ARBOL DE LEVAS', 'ÁRBOL DE LEVAS',
                     'CAMISA', 'EMPAQUE', 'CULATA', 'TAPA', 'BALANCIN', 'BALANCÍN',
                     'RETEN', 'RETÉN', 'JUNTA', 'CARTER', 'CÁRTER', 'LEVA',
                     'KIT PISTON', 'KIT PISTÓN', 'KIT MOTOR', 'ARO', 'SEGMENT'],
        'category': 'MOTOR'
    },
    'electrico': {
        'keywords': ['SWITCH', 'BOBINA', 'CDI', 'REGULADOR', 'ESTATOR', 'FARO',
                     'DIRECCIONAL', 'STOP', 'BOMBILLO', 'FLASHER', 'RELAY', 'RELÉ',
                     'BATERIA', 'BATERÍA', 'RECTIFICADOR', 'VELOCIMETRO', 'VELOCÍMETRO',
                     'TACOMETRO', 'TACÓMETRO', 'TABLERO', 'ENCENDIDO', 'INTERRUPTOR',
                     'FUSIBLE', 'CABLEADO', 'ALTERNADOR', 'MOTOR ARRANQUE', 'ARRANQUE',
                     'LED', 'LUZ', 'LUCES', 'FOCO', 'BUJIA', 'BUJÍA'],
        'category': 'ELECTRICO'
    },
    'transmision': {
        'keywords': ['CADENA', 'PIÑON', 'PIÑÓN', 'CATALINA', 'KIT ARRASTRE',
                     'CLUTCH', 'EMBRAGUE', 'DISCO CLUTCH', 'PLATO PRESION',
                     'PLATO PRESIÓN', 'CAMPANA', 'VARIADOR', 'CORREA', 'SPROCKET',
                     'KIT DE ARRASTRE', 'KIT TRANSMISION', 'KIT TRANSMISIÓN',
                     'CENTRIFUGO', 'CENTRÍFUGO', 'POLEA'],
        'category': 'TRANSMISION'
    },
    'suspension': {
        'keywords': ['AMORTIGUADOR', 'TIJERA', 'TELESCOPIO', 'RESORTE', 'BUJE',
                     'HORQUILLA', 'BASCULANTE', 'ROTULA', 'RÓTULA', 'MUÑÓN',
                     'MESA', 'MONO SHOCK', 'MONOSHOCK', 'BARRA TELESCOPICA',
                     'BARRA TELESCÓPICA'],
        'category': 'SUSPENSION'
    },
    'frenos': {
        'keywords': ['PASTILLA', 'DISCO FRENO', 'MORDAZA', 'BOMBA FRENO', 'GUAYA FRENO',
                     'CABLE FRENO', 'CALIPER', 'CALIBRE', 'MANIGUETA', 'ZAPATA',
                     'TAMBOR', 'LIQUIDO FRENO', 'LÍQUIDO FRENO', 'DOT4', 'DOT 4',
                     'FRENO', 'BRAKE'],
        'category': 'FRENOS'
    },
    'carroceria': {
        'keywords': ['CARENAJE', 'GUARDABARRO', 'GUARDAFANGO', 'TANQUE', 'SILLA',
                     'ASIENTO', 'MANUBRIO', 'ESPEJO', 'PALANCA', 'COLEPATO',
                     'COLA', 'LATERAL', 'TAPA LATERAL', 'PARRILLA', 'SALPICADERA',
                     'TAPA TANQUE', 'PLASTICO', 'PLÁSTICO', 'CARCASA', 'CUBIERTA',
                     'TAPABARROS', 'DEFENSA', 'PORTA PLACA', 'PORTAPLACA'],
        'category': 'CARROCERIA'
    },
    'accesorios': {
        'keywords': ['FILTRO', 'GUAYA', 'CABLE', 'MANIGUETA', 'PEDAL', 'ESTRIBO',
                     'PISADERA', 'SLIDER', 'PROTECTOR', 'MALETA', 'BAUL', 'BAÚL',
                     'PARADOR', 'PATA', 'PATA CENTRAL', 'PATA LATERAL', 'RODAMIENTO',
                     'BALINERA', 'RETENEDOR', 'EMPAQUE', 'O-RING', 'ORING'],
        'category': 'ACCESORIOS'
    },
    'combustible': {
        'keywords': ['CARBURADOR', 'INYECTOR', 'BOMBA GASOLINA', 'FILTRO AIRE',
                     'FILTRO GASOLINA', 'GRIFO', 'PETCOCK', 'ACELERADOR',
                     'CABLE ACELERADOR', 'ESTRANGULADOR', 'CHOKE', 'TPS'],
        'category': 'COMBUSTIBLE'
    },
    'escape': {
        'keywords': ['ESCAPE', 'EXHOSTO', 'SILENCIADOR', 'MOFLE', 'TUBO ESCAPE',
                     'CATALIZADOR', 'HEADER', 'MÚLTIPLE', 'MULTIPLE'],
        'category': 'ESCAPE'
    },
    'direccion': {
        'keywords': ['DIRECCION', 'DIRECCIÓN', 'COLUMNA', 'TIJERA DIRECCION',
                     'ROTULA DIRECCION', 'CAJA DIRECCION', 'MANILLAR'],
        'category': 'DIRECCION'
    },
    'lubricantes': {
        'keywords': ['ACEITE', 'LUBRICANTE', 'GRASA', '10W40', '10W-40', '20W50',
                     '20W-50', '4T', '2T', 'SINTETICO', 'SINTÉTICO', 'MINERAL',
                     'MOTUL', 'CASTROL', 'SHELL', 'YAMALUBE', 'MOBIL'],
        'category': 'LUBRICANTES'
    },
    'herramientas': {
        'keywords': ['LLAVE', 'EXTRACTOR', 'HERRAMIENTA', 'DADO', 'BANCO', 'GATO',
                     'ELEVADOR', 'CALIBRADOR', 'MANOMETRO', 'MANÓMETRO', 'TORQUIMETRO'],
        'category': 'HERRAMIENTAS'
    },
    'lujos': {
        'keywords': ['LUJO', 'CROMADO', 'EMBLEMA', 'CALCOMANIA', 'CALCOMANÍA',
                     'ADHESIVO', 'STICKER', 'KIT CALCOMANIA', 'EMBLEMA', 'VINILO'],
        'category': 'LUJOS'
    },
}


# ============================================================================
# LOGGING Y UTILIDADES
# ============================================================================

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


# ============================================================================
# MODELOS DE DATOS
# ============================================================================

@dataclass
class ProductoYokomar:
    """Datos de un producto de Yokomar."""
    sku_odi: str = ""
    codigo: str = ""
    nombre: str = ""
    descripcion: str = ""
    precio: float = 0.0
    imagen: str = ""
    categoria: str = "OTROS"
    marca_moto: str = ""
    modelo_moto: str = ""
    cilindraje: str = ""
    url_producto: str = ""

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
    productos_merged: int = 0
    productos_con_precio: int = 0
    productos_con_imagen: int = 0
    productos_con_marca: int = 0
    productos_con_modelo: int = 0
    productos_por_categoria: Dict[str, int] = field(default_factory=dict)


# ============================================================================
# EXTRACTORES SEMANTICOS
# ============================================================================

class MarcaModeloExtractor:
    """Extractor de marca y modelo de moto desde descripcion."""

    def __init__(self):
        self.marcas = MARCAS_MOTO
        self.modelos = MODELOS_MOTO
        self.cilindrajes = CILINDRAJES

    def extract_marca(self, descripcion: str) -> str:
        """Extrae marca de moto de la descripcion."""
        if not descripcion:
            return ""

        desc_upper = descripcion.upper()

        # Buscar por prefijos especificos de Yokomar
        for prefix, marca in self.marcas.items():
            # Buscar como prefijo o palabra separada
            if f" {prefix} " in f" {desc_upper} " or desc_upper.startswith(prefix):
                return marca
            # Buscar sin punto
            prefix_clean = prefix.rstrip('.')
            if f" {prefix_clean} " in f" {desc_upper} ":
                return marca

        # Buscar marcas completas
        marcas_completas = ['HONDA', 'YAMAHA', 'SUZUKI', 'KAWASAKI', 'BAJAJ',
                           'TVS', 'AKT', 'KTM', 'HERO', 'AUTECO', 'KYMCO',
                           'BENELLI', 'CFMOTO', 'ROYAL ENFIELD', 'BMW']
        for marca in marcas_completas:
            if marca in desc_upper:
                return marca

        return ""

    def extract_modelo(self, descripcion: str) -> str:
        """Extrae modelo de moto de la descripcion."""
        if not descripcion:
            return ""

        desc_upper = descripcion.upper()

        # Buscar modelos (ordenados por longitud para match mas especifico primero)
        modelos_sorted = sorted(self.modelos, key=len, reverse=True)

        for modelo in modelos_sorted:
            modelo_upper = modelo.upper()
            # Buscar modelo exacto o como parte
            if modelo_upper in desc_upper:
                return modelo_upper
            # Buscar sin espacios
            modelo_compact = modelo_upper.replace(' ', '').replace('-', '')
            if modelo_compact in desc_upper.replace(' ', '').replace('-', ''):
                return modelo_upper

        # Buscar patrones de modelo (ej: CB190R, XR150L, NS200)
        patterns = [
            r'\b([A-Z]{1,3}\d{2,4}[A-Z]?)\b',  # CB190R, XR150L
            r'\b([A-Z]{2,4}\s*\d{3})\b',        # NS 200, FZ 25
            r'\bPULSAR\s*(\d{3})\b',             # PULSAR 200
            r'\bAPACHE\s*(RTR)?\s*(\d{3})\b',    # APACHE RTR 200
        ]

        for pattern in patterns:
            match = re.search(pattern, desc_upper)
            if match:
                return match.group(0).strip()

        return ""

    def extract_cilindraje(self, descripcion: str, modelo: str = "") -> str:
        """Extrae cilindraje de la descripcion o lo infiere del modelo."""
        if not descripcion:
            return ""

        # Buscar patron explicito de cilindraje
        desc_upper = descripcion.upper()
        patterns = [
            r'\b(\d{2,4})\s*CC\b',
            r'\b(\d{2,4})\s*C\.C\.\b',
            r'\bCC\s*(\d{2,4})\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, desc_upper)
            if match:
                return match.group(1)

        # Inferir del modelo
        texto_busqueda = f"{descripcion} {modelo}".upper()
        for cc, keywords in self.cilindrajes.items():
            for kw in keywords:
                if kw in texto_busqueda:
                    return cc

        return ""


class CategoriaExtractor:
    """Extractor de categoria desde descripcion."""

    def __init__(self):
        self.taxonomy = CATEGORY_TAXONOMY

    def extract(self, descripcion: str) -> str:
        """Extrae categoria del producto basado en palabras clave."""
        if not descripcion:
            return "OTROS"

        desc_upper = descripcion.upper()

        # Buscar categoria con mayor coincidencia
        best_category = "OTROS"
        best_matches = 0

        for cat_info in self.taxonomy.values():
            matches = 0
            for keyword in cat_info['keywords']:
                if keyword in desc_upper:
                    matches += 1

            if matches > best_matches:
                best_matches = matches
                best_category = cat_info['category']

        return best_category


# ============================================================================
# PROCESADOR DE YOKOMAR
# ============================================================================

class YokomarProcessor:
    """Procesador principal de catalogos Yokomar."""

    def __init__(self, config: dict):
        self.config = config
        self.data_dir = config.get('data_dir', DEFAULT_DATA_DIR)
        self.output_dir = config.get('output_dir', DEFAULT_OUTPUT_DIR)
        self.empresa = EMPRESA_CONFIG

        # Extractores
        self.marca_modelo_extractor = MarcaModeloExtractor()
        self.categoria_extractor = CategoriaExtractor()

        # Estadisticas
        self.stats = ProcessingStats()

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
        """Carga Base_Datos_Yokomar.csv."""
        if path:
            file_path = Path(path)
        else:
            file_path = self._find_file(f"*{BASE_DATOS_FILENAME}*")
            if not file_path:
                file_path = self._find_file("Base_Datos*.csv")

        if not file_path or not file_path.exists():
            log(f"Archivo Base_Datos no encontrado en {self.data_dir}", "error")
            return pd.DataFrame()

        log(f"Cargando Base_Datos: {file_path.name}")

        try:
            df = pd.read_csv(
                file_path,
                sep=self.empresa['csv_separator'],
                encoding=self.empresa['encoding']
            )
            self.stats.total_base = len(df)
            log(f"  Productos en base: {len(df)}", "success")
            return df
        except Exception as e:
            log(f"Error cargando Base_Datos: {e}", "error")
            return pd.DataFrame()

    def load_lista_precios(self, path: Optional[str] = None) -> pd.DataFrame:
        """Carga Lista_Precios_Yokomar.csv."""
        if path:
            file_path = Path(path)
        else:
            file_path = self._find_file(f"*{LISTA_PRECIOS_FILENAME}*")
            if not file_path:
                file_path = self._find_file("Lista_Precios*.csv")

        if not file_path or not file_path.exists():
            log(f"Archivo Lista_Precios no encontrado (opcional)", "warning")
            return pd.DataFrame()

        log(f"Cargando Lista_Precios: {file_path.name}")

        try:
            df = pd.read_csv(
                file_path,
                sep=self.empresa['csv_separator'],
                encoding=self.empresa['encoding']
            )
            self.stats.total_precios = len(df)
            log(f"  Productos con precio: {len(df)}", "success")
            return df
        except Exception as e:
            log(f"Error cargando Lista_Precios: {e}", "warning")
            return pd.DataFrame()

    def merge_data(self, df_base: pd.DataFrame, df_precios: pd.DataFrame) -> pd.DataFrame:
        """Une Base_Datos con Lista_Precios."""
        if df_base.empty:
            return pd.DataFrame()

        if df_precios.empty:
            log("Sin archivo de precios, continuando sin precios", "warning")
            df_base['PRECIO'] = 0
            return df_base

        # Buscar columna de codigo en ambos dataframes
        codigo_cols_base = [c for c in df_base.columns if 'CODIGO' in c.upper() or 'SKU' in c.upper()]
        codigo_cols_precios = [c for c in df_precios.columns if 'CODIGO' in c.upper() or 'SKU' in c.upper()]

        if not codigo_cols_base or not codigo_cols_precios:
            log("No se encontro columna CODIGO para hacer merge", "warning")
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

        # Preparar precios para merge
        df_precios_clean = df_precios[[codigo_precios, precio_col]].copy()
        df_precios_clean.columns = ['CODIGO_MERGE', 'PRECIO']

        # Merge
        df_merged = df_base.merge(
            df_precios_clean,
            left_on=codigo_base,
            right_on='CODIGO_MERGE',
            how='left'
        )

        # Limpiar
        if 'CODIGO_MERGE' in df_merged.columns:
            df_merged = df_merged.drop(columns=['CODIGO_MERGE'])

        df_merged['PRECIO'] = df_merged['PRECIO'].fillna(0)

        self.stats.productos_merged = len(df_merged)
        self.stats.productos_con_precio = (df_merged['PRECIO'] > 0).sum()

        log(f"Merge completado: {len(df_merged)} productos", "success")
        log(f"  Con precio: {self.stats.productos_con_precio}", "dim")

        return df_merged

    def process_product(self, row: dict, index: int) -> ProductoYokomar:
        """Procesa una fila y extrae producto estructurado."""

        # Obtener campos con diferentes nombres posibles
        codigo = str(row.get('CODIGO', row.get('codigo', row.get('SKU', '')))).strip()
        descripcion = str(row.get('DESCRIPCION', row.get('descripcion', row.get('Title', '')))).strip()
        precio = clean_price(row.get('PRECIO', row.get('precio', 0)))
        imagen = str(row.get('Imagen_URL_Origen', row.get('imagen', row.get('Image Src', '')))).strip()
        url_producto = str(row.get('URL_Producto', '')).strip()

        # Generar SKU ODI
        sku_odi = f"{self.empresa['prefijo_sku']}-{index+1:05d}"

        # Extraer marca y modelo
        marca = self.marca_modelo_extractor.extract_marca(descripcion)
        modelo = self.marca_modelo_extractor.extract_modelo(descripcion)
        cilindraje = self.marca_modelo_extractor.extract_cilindraje(descripcion, modelo)

        # Extraer categoria
        categoria = self.categoria_extractor.extract(descripcion)

        # Validar imagen
        if not is_valid_url(imagen):
            imagen = ""

        return ProductoYokomar(
            sku_odi=sku_odi,
            codigo=codigo,
            nombre=descripcion,
            descripcion=descripcion,
            precio=precio,
            imagen=imagen,
            categoria=categoria,
            marca_moto=marca,
            modelo_moto=modelo,
            cilindraje=cilindraje,
            url_producto=url_producto
        )

    def process(self) -> List[ProductoYokomar]:
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
                if producto.marca_moto:
                    self.stats.productos_con_marca += 1
                if producto.modelo_moto:
                    self.stats.productos_con_modelo += 1

                cat = producto.categoria
                self.stats.productos_por_categoria[cat] = \
                    self.stats.productos_por_categoria.get(cat, 0) + 1

        log(f"Productos procesados: {len(productos)}", "success")

        return productos

    def export(self, productos: List[ProductoYokomar]) -> Tuple[str, str]:
        """Exporta productos a CSV y JSON."""
        if not productos:
            log("No hay productos para exportar", "warning")
            return "", ""

        os.makedirs(self.output_dir, exist_ok=True)

        # Crear DataFrame
        records = [p.to_dict() for p in productos]
        df = pd.DataFrame(records)

        # Ordenar columnas
        columns_order = [
            'sku_odi', 'codigo', 'nombre', 'descripcion', 'precio',
            'categoria', 'marca_moto', 'modelo_moto', 'cilindraje',
            'imagen', 'url_producto'
        ]
        df = df[[c for c in columns_order if c in df.columns]]

        # Timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = self.empresa['prefijo_sku']

        # Guardar CSV
        csv_filename = f"{prefix}_catalogo_{timestamp}.csv"
        csv_path = os.path.join(self.output_dir, csv_filename)
        df.to_csv(csv_path, sep=';', index=False, encoding='utf-8')
        log(f"CSV exportado: {csv_path}", "success")

        # Guardar CSV para normalizer (formato esperado)
        normalizer_csv = os.path.join(self.output_dir, f"{prefix}_REAL_INPUT.csv")
        df.to_csv(normalizer_csv, sep=';', index=False, encoding='utf-8')
        log(f"CSV para normalizer: {normalizer_csv}", "success")

        # Guardar JSON
        json_filename = f"{prefix}_catalogo_{timestamp}.json"
        json_path = os.path.join(self.output_dir, json_filename)
        df.to_json(json_path, orient='records', force_ascii=False, indent=2)
        log(f"JSON exportado: {json_path}", "success")

        return csv_path, json_path

    def _print_banner(self):
        """Imprime banner de inicio."""
        print(f"""
{Colors.BOLD}+{'='*62}+
|{' '*15}YOKOMAR EXTRACTOR v{VERSION}{' '*18}|
|{' '*10}Organismo Digital Industrial (ODI){' '*17}|
+{'='*62}+{Colors.RESET}
""")
        log(f"Directorio datos: {self.data_dir}")
        log(f"Directorio salida: {self.output_dir}")

    def print_stats(self):
        """Imprime estadisticas finales."""
        s = self.stats

        print(f"""
{Colors.BOLD}{'='*60}
 RESUMEN DE PROCESAMIENTO
{'='*60}{Colors.RESET}

{Colors.GREEN}+ Productos en Base_Datos:{Colors.RESET}  {s.total_base:,}
{Colors.GREEN}+ Productos con precio:{Colors.RESET}    {s.productos_con_precio:,}
{Colors.GREEN}+ Productos con imagen:{Colors.RESET}    {s.productos_con_imagen:,}
{Colors.CYAN}o Con marca detectada:{Colors.RESET}     {s.productos_con_marca:,}
{Colors.CYAN}o Con modelo detectado:{Colors.RESET}    {s.productos_con_modelo:,}

{Colors.BOLD}Por categoria:{Colors.RESET}""")

        for cat, count in sorted(s.productos_por_categoria.items(), key=lambda x: -x[1]):
            pct = count / sum(s.productos_por_categoria.values()) * 100 if s.productos_por_categoria else 0
            print(f"  {cat:20} {count:5,} ({pct:5.1f}%)")

        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}\n")


# ============================================================================
# GENERADOR DE DATOS DE PRUEBA
# ============================================================================

def generate_test_data(output_dir: str) -> str:
    """Genera datos de prueba para Yokomar."""
    import random

    log("Generando datos de prueba para Yokomar...")

    os.makedirs(output_dir, exist_ok=True)

    # Productos de ejemplo
    productos = [
        # Motor
        ("50001", "CILINDRO H. XR150L", "MOTOR", 85000),
        ("50002", "KIT PISTON CB190R STD", "MOTOR", 120000),
        ("50003", "BIELA PULSAR NS200", "MOTOR", 95000),
        ("50004", "EMPAQUE CULATA Y. FZ25", "MOTOR", 25000),
        ("50005", "VALVULA ADMISION GIXXER 150", "MOTOR", 35000),

        # Electrico
        ("60001", "CDI BAJAJ PULSAR 200", "ELECTRICO", 85000),
        ("60002", "REGULADOR CB190R", "ELECTRICO", 65000),
        ("60003", "BOBINA ALTA AKT 125", "ELECTRICO", 45000),
        ("60004", "FARO LED UNIVERSAL 7\"", "ELECTRICO", 120000),
        ("60005", "ESTATOR WAVE 110", "ELECTRICO", 145000),

        # Transmision
        ("70001", "KIT ARRASTRE 428 AKT125", "TRANSMISION", 75000),
        ("70002", "CADENA DID 520 ORO", "TRANSMISION", 180000),
        ("70003", "CLUTCH COMPLETO NS200", "TRANSMISION", 165000),
        ("70004", "CATALINA 42T PULSAR", "TRANSMISION", 35000),

        # Frenos
        ("80001", "PASTILLA FRENO PULSAR 200NS DEL", "FRENOS", 28000),
        ("80002", "DISCO FRENO DELANTERO CB190", "FRENOS", 95000),
        ("80003", "BOMBA FRENO TRASERA UNIVERSAL", "FRENOS", 55000),

        # Suspension
        ("90001", "AMORTIGUADOR TRASERO XR150", "SUSPENSION", 185000),
        ("90002", "TELESCOPIO COMPLETO CB160", "SUSPENSION", 320000),
        ("90003", "BUJE TIJERA DELANTERO PULSAR", "SUSPENSION", 15000),

        # Carroceria
        ("10001", "TANQUE GASOLINA DISCOVER 125", "CARROCERIA", 185000),
        ("10002", "GUARDABARRO DELANTERO BWS", "CARROCERIA", 45000),
        ("10003", "SILLA COMPLETA BOXER CT", "CARROCERIA", 95000),

        # Accesorios
        ("11001", "FILTRO AIRE K&N UNIVERSAL", "ACCESORIOS", 85000),
        ("11002", "ESPEJO RETROVISOR CROMADO PAR", "ACCESORIOS", 22000),
        ("11003", "SLIDER CARENAJE PAR UNIVERSAL", "ACCESORIOS", 85000),
    ]

    # Generar CSV Base_Datos
    base_file = os.path.join(output_dir, "Base_Datos_Yokomar_TEST.csv")
    with open(base_file, 'w', encoding='utf-8-sig') as f:
        f.write("CODIGO;DESCRIPCION;Imagen_URL_Origen;URL_Producto\n")
        for codigo, desc, cat, precio in productos:
            img_url = f"https://yokomar.com/images/{codigo}.jpg"
            prod_url = f"https://yokomar.com/producto/{codigo}"
            f.write(f"{codigo};{desc};{img_url};{prod_url}\n")

    # Generar CSV Lista_Precios
    precios_file = os.path.join(output_dir, "Lista_Precios_Yokomar_TEST.csv")
    with open(precios_file, 'w', encoding='utf-8-sig') as f:
        f.write("CODIGO;PRECIO\n")
        for codigo, desc, cat, precio in productos:
            # Agregar variacion al precio
            precio_var = int(precio * random.uniform(0.95, 1.05))
            f.write(f"{codigo};{precio_var}\n")

    log(f"Datos de prueba generados en: {output_dir}", "success")
    log(f"  Base_Datos: {base_file}")
    log(f"  Lista_Precios: {precios_file}")

    return output_dir


# ============================================================================
# CLI
# ============================================================================

def print_help():
    """Imprime ayuda."""
    print(f"""
{Colors.BOLD}{SCRIPT_NAME} v{VERSION}{Colors.RESET}
{'='*60}

{Colors.CYAN}USO:{Colors.RESET}
    python3 {os.path.basename(__file__)} [opciones]

{Colors.CYAN}OPCIONES:{Colors.RESET}
    --data-dir DIR      Directorio con archivos Yokomar
    --base FILE         Archivo Base_Datos*.csv
    --precios FILE      Archivo Lista_Precios*.csv
    --output, -o DIR    Directorio de salida (default: {DEFAULT_OUTPUT_DIR})
    --test              Generar y procesar datos de prueba
    --help, -h          Mostrar esta ayuda

{Colors.CYAN}EJEMPLOS:{Colors.RESET}
    # Procesar desde directorio por defecto
    python3 {os.path.basename(__file__)}

    # Procesar desde directorio especifico
    python3 {os.path.basename(__file__)} --data-dir /path/to/yokomar

    # Especificar archivos directamente
    python3 {os.path.basename(__file__)} --base datos.csv --precios precios.csv

    # Generar y procesar datos de prueba
    python3 {os.path.basename(__file__)} --test

{Colors.CYAN}SALIDA:{Colors.RESET}
    output/
    +-- YOK_catalogo_YYYYMMDD_HHMMSS.csv    # Catalogo procesado
    +-- YOK_catalogo_YYYYMMDD_HHMMSS.json   # Formato JSON
    +-- YOK_REAL_INPUT.csv                   # Listo para ODI Normalizer
""")


def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description=f'{SCRIPT_NAME} v{VERSION}',
        add_help=False
    )

    parser.add_argument('--data-dir', type=str, default=DEFAULT_DATA_DIR,
                        help='Directorio con archivos Yokomar')
    parser.add_argument('--base', type=str, help='Archivo Base_Datos*.csv')
    parser.add_argument('--precios', type=str, help='Archivo Lista_Precios*.csv')
    parser.add_argument('--output', '-o', type=str, default=DEFAULT_OUTPUT_DIR,
                        help='Directorio de salida')
    parser.add_argument('--test', action='store_true',
                        help='Generar y procesar datos de prueba')
    parser.add_argument('--help', '-h', action='store_true', help='Mostrar ayuda')

    args = parser.parse_args()

    if args.help:
        print_help()
        sys.exit(0)

    # Modo test
    if args.test:
        test_dir = os.path.join(args.output, "test_data")
        generate_test_data(test_dir)
        args.data_dir = test_dir

    # Configuracion
    config = {
        'data_dir': args.data_dir,
        'output_dir': args.output,
        'base_file': args.base,
        'precios_file': args.precios,
    }

    # Procesar
    try:
        processor = YokomarProcessor(config)
        productos = processor.process()

        if productos:
            csv_path, json_path = processor.export(productos)
            processor.print_stats()

            log("Proceso completado exitosamente", "success")
            log(f"  Archivo CSV: {csv_path}")
            log(f"  Listo para: python3 odi_semantic_normalizer.py {csv_path}")
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
