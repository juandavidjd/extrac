"""
INDUSTRY SKINS — Configuración Multi-Industria para ODI
========================================================
Versión: 1.0
Fecha: 11 Febrero 2026
Propósito: Definir skins (pieles) por industria manteniendo lógica común

CATRMU = Canal Transversal Multitemático
"Una lógica, infinitas industrias"
"""

import json
import logging
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("industry_skins")

# ============================================================================
# ENUMS
# ============================================================================

class Industry(Enum):
    """Industrias principales de ODI"""
    TRANSPORTE = "TRANSPORTE"
    SALUD = "SALUD"
    ENTRETENIMIENTO = "ENTRETENIMIENTO"
    BELLEZA = "BELLEZA"
    EDUCACION = "EDUCACION"
    UNIVERSAL = "UNIVERSAL"  # CATRMU


class Branch(Enum):
    """Ramas dentro de cada industria"""
    # TRANSPORTE
    MOTOS = "MOTOS"
    AUTOS = "AUTOS"
    BICICLETAS = "BICICLETAS"

    # SALUD
    DENTAL = "DENTAL"
    BRUXISMO = "BRUXISMO"
    CAPILAR = "CAPILAR"
    GENERAL = "GENERAL"

    # ENTRETENIMIENTO
    TURISMO = "TURISMO"
    EVENTOS = "EVENTOS"

    # UNIVERSAL
    ALL = "ALL"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class ColorPalette:
    """Paleta de colores para una skin"""
    primary: str      # Color principal (botones, enlaces)
    secondary: str    # Color secundario (acentos)
    accent: str       # Color de acento (highlights)
    dark: str         # Fondo oscuro
    light: str        # Fondo claro
    success: str = "#10B981"  # Verde
    warning: str = "#F59E0B"  # Amber
    error: str = "#EF4444"    # Rojo
    info: str = "#3B82F6"     # Azul

    def to_css_vars(self) -> str:
        """Genera variables CSS"""
        return f"""
:root {{
    --odi-primary: {self.primary};
    --odi-secondary: {self.secondary};
    --odi-accent: {self.accent};
    --odi-dark: {self.dark};
    --odi-light: {self.light};
    --odi-success: {self.success};
    --odi-warning: {self.warning};
    --odi-error: {self.error};
    --odi-info: {self.info};
}}
"""


@dataclass
class CatalogConfig:
    """Configuración del catálogo para una skin"""
    type: str           # products, services, procedures, treatments
    collection: str     # Nombre de colección ChromaDB
    count: int          # Número de items
    source_path: str    # Path en el servidor


@dataclass
class VoiceConfig:
    """Configuración de voz ElevenLabs"""
    primary_id: Optional[str] = None      # Voice ID principal
    primary_name: str = "Tony Maestro"
    secondary_id: Optional[str] = None    # Voice ID secundario
    secondary_name: str = "Ramona Anfitriona"
    speed: float = 0.85
    stability: float = 0.65


@dataclass
class WhatsAppConfig:
    """Configuración de WhatsApp para la industria"""
    templates: List[str] = field(default_factory=list)
    greeting: str = ""
    farewell: str = ""


@dataclass
class IndustrySkin:
    """
    Skin completa para una industria/rama.
    Contiene toda la configuración visual y de contenido.
    """
    # Identificación
    industry: Industry
    branch: Branch
    name: str
    description: str

    # Dominios
    domain: str
    aliases: List[str] = field(default_factory=list)
    webhook_subdomain: Optional[str] = None

    # Visual
    colors: ColorPalette = field(default_factory=lambda: ColorPalette(
        primary="#06B6D4",
        secondary="#10B981",
        accent="#F97316",
        dark="#0F172A",
        light="#F8FAFC"
    ))
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None

    # Catálogo
    catalog: CatalogConfig = field(default_factory=lambda: CatalogConfig(
        type="products",
        collection="default",
        count=0,
        source_path="/opt/odi/data/"
    ))

    # Voz
    voice: VoiceConfig = field(default_factory=VoiceConfig)

    # WhatsApp
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)

    # Triggers P1 (keywords que activan esta industria)
    triggers: List[str] = field(default_factory=list)

    # Respuesta canónica al activar
    canonical_response: str = ""

    # Estado activo
    is_active: bool = True

    def to_dict(self) -> Dict:
        """Serializa a diccionario"""
        return {
            "industry": self.industry.value,
            "branch": self.branch.value,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "aliases": self.aliases,
            "colors": asdict(self.colors),
            "catalog": asdict(self.catalog),
            "voice": asdict(self.voice),
            "triggers": self.triggers,
            "canonical_response": self.canonical_response,
            "is_active": self.is_active,
        }


# ============================================================================
# SKINS PREDEFINIDAS
# ============================================================================

# TRANSPORTE / MOTOS (SRM)
SKIN_SRM = IndustrySkin(
    industry=Industry.TRANSPORTE,
    branch=Branch.MOTOS,
    name="SRM - Somos Repuestos Motos",
    description="Distribuidor híbrido de repuestos de motocicletas",
    domain="somosrepuestosmotos.com",
    aliases=["larocamotorepuestos.com"],
    webhook_subdomain="odi.larocamotorepuestos.com",
    colors=ColorPalette(
        primary="#06B6D4",    # Cyan
        secondary="#10B981",  # Verde
        accent="#F97316",     # Naranja
        dark="#0F172A",       # Slate 900
        light="#F8FAFC",      # Slate 50
    ),
    catalog=CatalogConfig(
        type="products",
        collection="srm_catalog",
        count=13575,
        source_path="/mnt/volume_sfo3_01/catalogos/"
    ),
    voice=VoiceConfig(
        primary_id="qpjUiwx7YUVAavnmh2sF",
        primary_name="Tony Maestro",
    ),
    whatsapp=WhatsAppConfig(
        templates=["odi_saludo", "odi_order_confirm_v2", "odi_order_status", "odi_shipping_update"],
        greeting="Hola, soy ODI de La Roca Motorepuestos. ¿Qué repuesto necesitas?",
        farewell="Gracias por contactarnos. Cuando necesites repuestos, aquí estamos.",
    ),
    triggers=[
        "repuesto", "repuestos", "moto", "motos", "motocicleta",
        "llanta", "casco", "aceite", "freno", "cadena",
        "piñón", "filtro", "batería", "faro", "espejo",
        "manubrio", "pedal", "suspensión", "carburador",
        "la roca", "srm", "somosrepuestos"
    ],
    canonical_response=(
        "Entendido. ¿Qué repuesto necesitas?\n"
        "Puedo buscar por nombre, referencia o moto compatible."
    ),
)

# SALUD / DENTAL (Matzu)
SKIN_MATZU = IndustrySkin(
    industry=Industry.SALUD,
    branch=Branch.DENTAL,
    name="Matzu Dental Aesthetics",
    description="Turismo odontológico en Medellín, Colombia",
    domain="matzudentalaesthetics.com",
    aliases=[],
    colors=ColorPalette(
        primary="#14B8A6",    # Teal
        secondary="#3B82F6",  # Azul
        accent="#F59E0B",     # Amber
        dark="#0F172A",
        light="#F0FDFA",      # Teal 50
    ),
    catalog=CatalogConfig(
        type="procedures",
        collection="matzu_procedures",
        count=15,
        source_path="/mnt/volume_sfo3_01/matzu/"
    ),
    voice=VoiceConfig(
        primary_name="Especialista Dental",
    ),
    whatsapp=WhatsAppConfig(
        templates=["odi_saludo"],
        greeting="Hola, soy ODI de Matzu Dental. ¿En qué procedimiento estás interesado?",
        farewell="Gracias por tu interés. Te contactaremos pronto con tu plan de tratamiento.",
    ),
    triggers=[
        "odontología", "odontologia", "dentista", "dental",
        "implante", "implantes", "diseño de sonrisa", "carillas",
        "blanqueamiento", "ortodoncia", "brackets", "invisalign",
        "corona dental", "endodoncia", "extracción dental",
        "prótesis dental", "matzu", "turismo dental",
        "turismo odontológico", "turismo odontologico"
    ],
    canonical_response=(
        "Entendido. Cambio a modo Turismo Dental.\n\n"
        "Trabajo con clínicas especializadas en Medellín, Colombia.\n"
        "Para darte la mejor información, cuéntame:\n\n"
        "1. ¿Qué procedimiento te interesa?\n"
        "2. ¿Cuándo planeas viajar?\n"
        "3. ¿Ya tienes un presupuesto en mente?"
    ),
)

# SALUD / BRUXISMO (COVER'S)
SKIN_COVERS = IndustrySkin(
    industry=Industry.SALUD,
    branch=Branch.BRUXISMO,
    name="COVER'S Lab",
    description="Especialistas en bruxismo y protección dental",
    domain="mis-cubiertas.com",
    aliases=[],
    colors=ColorPalette(
        primary="#8B5CF6",    # Violeta
        secondary="#06B6D4",  # Cyan
        accent="#10B981",     # Verde
        dark="#1E1B4B",       # Indigo 950
        light="#F5F3FF",      # Violet 50
    ),
    catalog=CatalogConfig(
        type="products",
        collection="covers_products",
        count=8,
        source_path="/mnt/volume_sfo3_01/COVER'S/"
    ),
    whatsapp=WhatsAppConfig(
        greeting="Hola, soy ODI de COVER'S Lab. ¿Sufres de bruxismo o necesitas protección dental?",
    ),
    triggers=[
        "bruxismo", "rechinar dientes", "guarda oclusal",
        "placa de bruxismo", "protector dental", "covers",
        "cover's", "smokover", "protector nocturno"
    ],
    canonical_response=(
        "Entendido. Cambio a modo Bruxismo.\n\n"
        "COVER'S Lab es especialista en protección dental.\n"
        "¿Necesitas una guarda oclusal o protector deportivo?"
    ),
)

# SALUD / CAPILAR (Cabezas Sanas)
SKIN_CABEZAS = IndustrySkin(
    industry=Industry.SALUD,
    branch=Branch.CAPILAR,
    name="Cabezas Sanas",
    description="Tricología y tratamientos capilares",
    domain="cabezasanas.com",
    aliases=[],
    colors=ColorPalette(
        primary="#F59E0B",    # Amber
        secondary="#10B981",  # Verde
        accent="#06B6D4",     # Cyan
        dark="#1C1917",       # Stone 900
        light="#FFFBEB",      # Amber 50
    ),
    catalog=CatalogConfig(
        type="treatments",
        collection="cabezas_treatments",
        count=12,
        source_path="/mnt/volume_sfo3_01/Cabezas Sanas/"
    ),
    triggers=[
        "cabeza sana", "cabezas sanas", "alopecia",
        "caída del cabello", "tricología", "tricologia",
        "tricólogo", "tricologo", "tratamiento capilar",
        "injerto capilar", "trasplante de cabello",
        "calvicie", "pelo", "cabello"
    ],
    canonical_response=(
        "Entendido. Cambio a modo Salud Capilar.\n\n"
        "Cabezas Sanas ofrece tratamientos de tricología.\n"
        "¿Qué problema capilar estás experimentando?"
    ),
)

# UNIVERSAL (CATRMU)
SKIN_CATRMU = IndustrySkin(
    industry=Industry.UNIVERSAL,
    branch=Branch.ALL,
    name="CATRMU",
    description="Canal Transversal Multitemático - ODI Universal",
    domain="catrmu.com",
    aliases=["ecosistema-adsi.com", "liveodi.com", "somosindustriasodi.com"],
    colors=ColorPalette(
        primary="#EC4899",    # Pink
        secondary="#8B5CF6",  # Violeta
        accent="#06B6D4",     # Cyan
        dark="#0F0F23",       # Custom dark
        light="#FDF2F8",      # Pink 50
    ),
    catalog=CatalogConfig(
        type="all",
        collection="catrmu_universal",
        count=0,  # Dinámico
        source_path="/opt/odi/data/"
    ),
    triggers=[],  # CATRMU detecta y rutea automáticamente
    canonical_response=(
        "Soy ODI. Puedo ayudarte en cualquier área:\n"
        "• Repuestos de motos\n"
        "• Turismo dental\n"
        "• Salud capilar\n"
        "• Emprendimiento\n\n"
        "¿Qué necesitas hoy?"
    ),
)


# ============================================================================
# REGISTRO DE SKINS
# ============================================================================

SKINS_REGISTRY: Dict[str, IndustrySkin] = {
    "SRM": SKIN_SRM,
    "MATZU": SKIN_MATZU,
    "COVERS": SKIN_COVERS,
    "CABEZAS": SKIN_CABEZAS,
    "CATRMU": SKIN_CATRMU,
}

# Mapeo de dominio a skin
DOMAIN_TO_SKIN: Dict[str, str] = {
    "somosrepuestosmotos.com": "SRM",
    "larocamotorepuestos.com": "SRM",
    "odi.larocamotorepuestos.com": "SRM",
    "matzudentalaesthetics.com": "MATZU",
    "mis-cubiertas.com": "COVERS",
    "cabezasanas.com": "CABEZAS",
    "catrmu.com": "CATRMU",
    "ecosistema-adsi.com": "CATRMU",
    "liveodi.com": "CATRMU",
    "somosindustriasodi.com": "CATRMU",
}


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def get_skin_by_domain(domain: str) -> Optional[IndustrySkin]:
    """Obtiene la skin correspondiente a un dominio"""
    # Limpiar dominio
    domain = domain.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]

    skin_key = DOMAIN_TO_SKIN.get(domain)
    if skin_key:
        return SKINS_REGISTRY.get(skin_key)

    # Fallback a CATRMU
    return SKIN_CATRMU


def get_skin_by_trigger(message: str) -> Optional[IndustrySkin]:
    """Detecta skin por triggers en el mensaje"""
    message_lower = message.lower()

    # Ordenar skins por número de triggers (más específicas primero)
    for skin_key, skin in sorted(
        SKINS_REGISTRY.items(),
        key=lambda x: len(x[1].triggers),
        reverse=True
    ):
        if skin_key == "CATRMU":
            continue  # CATRMU es fallback

        for trigger in skin.triggers:
            if trigger in message_lower:
                logger.info(f"[SKIN] Detected {skin_key} by trigger: {trigger}")
                return skin

    return None


def get_skin_by_key(key: str) -> Optional[IndustrySkin]:
    """Obtiene skin por clave del registro"""
    return SKINS_REGISTRY.get(key.upper())


def list_active_skins() -> List[Dict]:
    """Lista todas las skins activas"""
    return [
        {"key": key, "name": skin.name, "domain": skin.domain, "industry": skin.industry.value}
        for key, skin in SKINS_REGISTRY.items()
        if skin.is_active
    ]


def export_skins_config(path: str = "/opt/odi/config/skins_config.json"):
    """Exporta configuración de skins a JSON"""
    config = {
        key: skin.to_dict()
        for key, skin in SKINS_REGISTRY.items()
    }

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    logger.info(f"[SKIN] Exported {len(config)} skins to {path}")
    return path


# ============================================================================
# CLI / TEST
# ============================================================================

def run_tests():
    """Tests básicos de skins"""
    print("\n" + "="*60)
    print("INDUSTRY SKINS — TEST SUITE")
    print("="*60 + "\n")

    tests = [
        ("somosrepuestosmotos.com", "SRM"),
        ("larocamotorepuestos.com", "SRM"),
        ("matzudentalaesthetics.com", "MATZU"),
        ("mis-cubiertas.com", "COVERS"),
        ("cabezasanas.com", "CABEZAS"),
        ("catrmu.com", "CATRMU"),
        ("unknown.com", "CATRMU"),  # Fallback
    ]

    passed = 0
    for domain, expected in tests:
        skin = get_skin_by_domain(domain)
        actual = next((k for k, v in SKINS_REGISTRY.items() if v == skin), None)

        if actual == expected:
            print(f"✅ {domain} → {actual}")
            passed += 1
        else:
            print(f"❌ {domain} → {actual} (expected {expected})")

    print(f"\n{passed}/{len(tests)} tests passed\n")

    # Test triggers
    print("Trigger Detection Tests:")
    trigger_tests = [
        ("necesito un repuesto para mi moto", "SRM"),
        ("quiero implantes dentales", "MATZU"),
        ("sufro de bruxismo", "COVERS"),
        ("tengo alopecia", "CABEZAS"),
    ]

    for msg, expected in trigger_tests:
        skin = get_skin_by_trigger(msg)
        actual = next((k for k, v in SKINS_REGISTRY.items() if v == skin), "NONE")
        status = "✅" if actual == expected else "❌"
        print(f"{status} \"{msg[:40]}...\" → {actual}")

    print("\n" + "="*60)
    print("Skins Activas:")
    for skin in list_active_skins():
        print(f"  • {skin['key']}: {skin['name']} ({skin['domain']})")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_tests()

    # Exportar configuración
    export_skins_config()
    print("Configuración exportada a /opt/odi/config/skins_config.json")
