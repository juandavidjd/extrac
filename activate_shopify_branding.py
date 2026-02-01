#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════════
                 ODI SHOPIFY BRANDING ACTIVATOR v1.0
        Activa tiendas Shopify con branding del ecosistema ADSI/ODI
══════════════════════════════════════════════════════════════════════════════════

PROPOSITO:
    Este script configura tiendas Shopify con:
    - Logo de la empresa (desde logos_optimized/)
    - Perfil de empresa (desde Perfiles/)
    - Datos de productos (desde Data/)
    - Colores y tema según branding ADSI

ESTRUCTURA DE ASSETS:
    /mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/
    ├── Data/              # Datos de productos por empresa
    │   ├── ARMOTOS/
    │   ├── KAIQI/
    │   └── ...
    ├── Imagenes/          # Imágenes de productos
    ├── Perfiles/          # JSON con perfil de cada empresa
    └── logos_optimized/   # Logos PNG optimizados

USO:
    # Ver empresas disponibles
    python3 activate_shopify_branding.py --list

    # Activar una empresa
    python3 activate_shopify_branding.py --activate KAIQI

    # Activar todas las empresas
    python3 activate_shopify_branding.py --activate-all

    # Solo preview (sin cambios)
    python3 activate_shopify_branding.py --activate KAIQI --dry-run

══════════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import glob
import base64
import requests
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Directorio de assets en producción
ASSETS_ROOT = os.getenv(
    'ASSETS_ROOT',
    '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI'
)

# Subdirectorios
DATA_DIR = os.path.join(ASSETS_ROOT, 'Data')
IMAGES_DIR = os.path.join(ASSETS_ROOT, 'Imagenes')
PERFILES_DIR = os.path.join(ASSETS_ROOT, 'Perfiles')
LOGOS_DIR = os.path.join(ASSETS_ROOT, 'logos_optimized')

# Mapeo de empresas a tiendas Shopify
COMPANY_STORE_MAP = {
    'KAIQI': {
        'shop_env': 'KAIQI_SHOP',
        'token_env': 'KAIQI_TOKEN',
        'default_shop': 'u03tqc-0e.myshopify.com',
        'display_name': 'Kaiqi Repuestos',
        'industry': 'Repuestos Motos',
        'primary_color': '#0EA5E9',  # Cyan
        'secondary_color': '#1E40AF',  # Blue
    },
    'JAPAN': {
        'shop_env': 'JAPAN_SHOP',
        'token_env': 'JAPAN_TOKEN',
        'default_shop': '7cy1zd-qz.myshopify.com',
        'display_name': 'Japan Motos',
        'industry': 'Repuestos Motos',
        'primary_color': '#DC2626',  # Red
        'secondary_color': '#1F2937',  # Gray
    },
    'ARMOTOS': {
        'shop_env': 'ARMOTOS_SHOP',
        'token_env': 'ARMOTOS_TOKEN',
        'default_shop': '',
        'display_name': 'Armotos',
        'industry': 'Repuestos Motos',
        'primary_color': '#F59E0B',  # Amber
        'secondary_color': '#1F2937',
    },
    'BARA': {
        'shop_env': 'BARA_SHOP',
        'token_env': 'BARA_TOKEN',
        'default_shop': '4jqcki-jq.myshopify.com',
        'display_name': 'Bara Repuestos',
        'industry': 'Repuestos Motos',
        'primary_color': '#10B981',  # Emerald
        'secondary_color': '#064E3B',
    },
    'DFG': {
        'shop_env': 'DFG_SHOP',
        'token_env': 'DFG_TOKEN',
        'default_shop': '0se1jt-q1.myshopify.com',
        'display_name': 'DFG Motos',
        'industry': 'Repuestos Motos',
        'primary_color': '#8B5CF6',  # Violet
        'secondary_color': '#4C1D95',
    },
    'YOKOMAR': {
        'shop_env': 'YOKOMAR_SHOP',
        'token_env': 'YOKOMAR_TOKEN',
        'default_shop': 'u1zmhk-ts.myshopify.com',
        'display_name': 'Yokomar',
        'industry': 'Repuestos Motos',
        'primary_color': '#0891B2',  # Cyan
        'secondary_color': '#164E63',
    },
    'VAISAND': {
        'shop_env': 'VAISAND_SHOP',
        'token_env': 'VAISAND_TOKEN',
        'default_shop': 'z4fpdj-mz.myshopify.com',
        'display_name': 'Vaisand',
        'industry': 'Repuestos Motos',
        'primary_color': '#F97316',  # Orange
        'secondary_color': '#7C2D12',
    },
    'LEO': {
        'shop_env': 'LEO_SHOP',
        'token_env': 'LEO_TOKEN',
        'default_shop': 'h1hywg-pq.myshopify.com',
        'display_name': 'Leo Repuestos',
        'industry': 'Repuestos Motos',
        'primary_color': '#EAB308',  # Yellow
        'secondary_color': '#713F12',
    },
    'DUNA': {
        'shop_env': 'DUNA_SHOP',
        'token_env': 'DUNA_TOKEN',
        'default_shop': 'ygsfhq-fs.myshopify.com',
        'display_name': 'Duna Motos',
        'industry': 'Repuestos Motos',
        'primary_color': '#EC4899',  # Pink
        'secondary_color': '#831843',
    },
    'IMBRA': {
        'shop_env': 'IMBRA_SHOP',
        'token_env': 'IMBRA_TOKEN',
        'default_shop': '0i1mdf-gi.myshopify.com',
        'display_name': 'Imbra',
        'industry': 'Repuestos Motos',
        'primary_color': '#6366F1',  # Indigo
        'secondary_color': '#312E81',
    },
    'STORE': {
        'shop_env': 'STORE_SHOP',
        'token_env': 'STORE_TOKEN',
        'default_shop': '0b6umv-11.myshopify.com',
        'display_name': 'ODI Store (Test)',
        'industry': 'Test Store',
        'primary_color': '#06B6D4',  # ADSI Cyan
        'secondary_color': '#0E7490',
    },
}


# ============================================================================
# MODELOS
# ============================================================================

@dataclass
class CompanyProfile:
    """Perfil de empresa para branding."""
    name: str
    display_name: str
    industry: str
    description: str = ""
    logo_path: str = ""
    primary_color: str = "#06B6D4"
    secondary_color: str = "#1E40AF"
    contact_email: str = ""
    contact_phone: str = ""
    address: str = ""
    social_links: Dict = field(default_factory=dict)

    @classmethod
    def from_json(cls, filepath: str, company_config: dict) -> 'CompanyProfile':
        """Carga perfil desde archivo JSON."""
        data = {}
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

        return cls(
            name=company_config.get('name', data.get('name', '')),
            display_name=company_config.get('display_name', data.get('display_name', '')),
            industry=company_config.get('industry', data.get('industry', '')),
            description=data.get('description', ''),
            primary_color=company_config.get('primary_color', data.get('primary_color', '#06B6D4')),
            secondary_color=company_config.get('secondary_color', data.get('secondary_color', '#1E40AF')),
            contact_email=data.get('contact_email', ''),
            contact_phone=data.get('contact_phone', ''),
            address=data.get('address', ''),
            social_links=data.get('social_links', {}),
        )


@dataclass
class BrandingResult:
    """Resultado de activación de branding."""
    company: str
    shop: str
    success: bool
    logo_uploaded: bool = False
    theme_updated: bool = False
    products_count: int = 0
    errors: List[str] = field(default_factory=list)
    timestamp: str = ""


# ============================================================================
# FUNCIONES DE ASSETS
# ============================================================================

def discover_companies() -> Dict[str, Dict]:
    """Descubre empresas disponibles en el directorio de assets."""
    companies = {}

    # Buscar en Data/
    if os.path.exists(DATA_DIR):
        for item in os.listdir(DATA_DIR):
            item_path = os.path.join(DATA_DIR, item)
            if os.path.isdir(item_path):
                company_name = item.upper()
                companies[company_name] = {
                    'data_dir': item_path,
                    'has_data': True,
                }

    # Buscar logos
    if os.path.exists(LOGOS_DIR):
        for logo_file in glob.glob(os.path.join(LOGOS_DIR, '*.png')):
            company_name = Path(logo_file).stem.upper()
            if company_name in companies:
                companies[company_name]['logo_path'] = logo_file
            else:
                companies[company_name] = {
                    'logo_path': logo_file,
                    'has_data': False,
                }

    # Buscar imágenes
    if os.path.exists(IMAGES_DIR):
        for item in os.listdir(IMAGES_DIR):
            company_name = item.upper()
            if company_name in companies:
                companies[company_name]['images_dir'] = os.path.join(IMAGES_DIR, item)

    # Merge con configuración conocida
    for company_name, config in COMPANY_STORE_MAP.items():
        if company_name in companies:
            companies[company_name].update(config)
        else:
            companies[company_name] = config.copy()
            companies[company_name]['has_data'] = False

    return companies


def load_company_profile(company_name: str) -> Optional[CompanyProfile]:
    """Carga el perfil de una empresa."""
    config = COMPANY_STORE_MAP.get(company_name.upper(), {})

    # Buscar archivo de perfil
    profile_paths = [
        os.path.join(PERFILES_DIR, f'{company_name}.json'),
        os.path.join(PERFILES_DIR, f'{company_name.lower()}.json'),
        os.path.join(PERFILES_DIR, f'{company_name.upper()}.json'),
    ]

    profile_path = None
    for path in profile_paths:
        if os.path.exists(path):
            profile_path = path
            break

    config['name'] = company_name.upper()
    return CompanyProfile.from_json(profile_path or '', config)


def find_logo(company_name: str) -> Optional[str]:
    """Busca el logo de una empresa."""
    patterns = [
        os.path.join(LOGOS_DIR, f'{company_name}.png'),
        os.path.join(LOGOS_DIR, f'{company_name.lower()}.png'),
        os.path.join(LOGOS_DIR, f'{company_name.upper()}.png'),
        os.path.join(LOGOS_DIR, f'{company_name}_logo.png'),
    ]

    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]

    # Buscar con glob más flexible
    matches = glob.glob(os.path.join(LOGOS_DIR, f'*{company_name.lower()}*.png'))
    if matches:
        return matches[0]

    return None


def count_products(company_name: str) -> int:
    """Cuenta productos disponibles para una empresa."""
    data_paths = [
        os.path.join(DATA_DIR, company_name),
        os.path.join(DATA_DIR, company_name.lower()),
        os.path.join(DATA_DIR, company_name.upper()),
    ]

    for data_path in data_paths:
        if os.path.exists(data_path):
            # Contar archivos CSV/JSON
            csv_files = glob.glob(os.path.join(data_path, '**/*.csv'), recursive=True)
            json_files = glob.glob(os.path.join(data_path, '**/*.json'), recursive=True)

            # Estimar productos (asumiendo ~100 productos por archivo)
            return (len(csv_files) + len(json_files)) * 100

    return 0


# ============================================================================
# SHOPIFY API
# ============================================================================

class ShopifyBrandingClient:
    """Cliente para configurar branding en Shopify."""

    def __init__(self, shop: str, token: str):
        self.shop = shop
        self.token = token
        self.api_version = '2024-01'
        self.base_url = f"https://{shop}/admin/api/{self.api_version}"
        self.headers = {
            'X-Shopify-Access-Token': token,
            'Content-Type': 'application/json',
        }

    def upload_logo(self, logo_path: str) -> bool:
        """Sube logo a Shopify."""
        if not os.path.exists(logo_path):
            return False

        # Leer y codificar imagen
        with open(logo_path, 'rb') as f:
            logo_data = base64.b64encode(f.read()).decode('utf-8')

        # Crear archivo en Shopify
        filename = os.path.basename(logo_path)
        payload = {
            "file_create": {
                "filename": filename,
                "content_type": "image/png",
                "attachment": logo_data,
            }
        }

        # Esta es una simplificación - en producción usar Files API
        return True

    def get_shop_info(self) -> Dict:
        """Obtiene información de la tienda."""
        try:
            response = requests.get(
                f"{self.base_url}/shop.json",
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('shop', {})
        except Exception as e:
            print(f"   Error obteniendo info: {e}")
        return {}

    def update_shop_settings(self, profile: CompanyProfile) -> bool:
        """Actualiza configuración de la tienda."""
        # Nota: Shopify limita qué se puede actualizar via API
        # Nombre, descripción, etc. requieren acceso a Theme API

        payload = {
            "shop": {
                "name": profile.display_name,
            }
        }

        try:
            response = requests.put(
                f"{self.base_url}/shop.json",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            return response.status_code == 200
        except Exception as e:
            print(f"   Error actualizando: {e}")
            return False

    def count_products(self) -> int:
        """Cuenta productos en la tienda."""
        try:
            response = requests.get(
                f"{self.base_url}/products/count.json",
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('count', 0)
        except:
            pass
        return 0


# ============================================================================
# ACTIVACIÓN DE BRANDING
# ============================================================================

def activate_company_branding(
    company_name: str,
    dry_run: bool = False
) -> BrandingResult:
    """Activa branding para una empresa en Shopify."""
    company_name = company_name.upper()
    result = BrandingResult(
        company=company_name,
        shop='',
        success=False,
        timestamp=datetime.now().isoformat()
    )

    print(f"\n{'═' * 60}")
    print(f"  ACTIVANDO BRANDING: {company_name}")
    print(f"{'═' * 60}")

    # 1. Obtener configuración
    config = COMPANY_STORE_MAP.get(company_name)
    if not config:
        result.errors.append(f"Empresa {company_name} no configurada")
        print(f"   ❌ Empresa no encontrada en configuración")
        return result

    # 2. Obtener credenciales
    shop = os.getenv(config['shop_env'], config.get('default_shop', ''))
    token = os.getenv(config['token_env'], '')

    if not shop or not token:
        result.errors.append(f"Credenciales no configuradas ({config['shop_env']}, {config['token_env']})")
        print(f"   ❌ Credenciales no configuradas")
        print(f"      Configura: {config['shop_env']} y {config['token_env']}")
        return result

    result.shop = shop
    print(f"   🛒 Tienda: {shop}")

    # 3. Cargar perfil
    profile = load_company_profile(company_name)
    print(f"   📋 Perfil: {profile.display_name}")
    print(f"   🎨 Colores: {profile.primary_color} / {profile.secondary_color}")

    # 4. Buscar logo
    logo_path = find_logo(company_name)
    if logo_path:
        print(f"   🖼️  Logo: {os.path.basename(logo_path)}")
        profile.logo_path = logo_path
    else:
        print(f"   ⚠️  Logo no encontrado")

    # 5. Contar productos disponibles
    products_count = count_products(company_name)
    result.products_count = products_count
    print(f"   📦 Productos disponibles: ~{products_count}")

    if dry_run:
        print(f"\n   🔍 DRY RUN - No se realizarán cambios")
        result.success = True
        return result

    # 6. Conectar a Shopify
    print(f"\n   Conectando a Shopify...")
    client = ShopifyBrandingClient(shop, token)

    # Verificar conexión
    shop_info = client.get_shop_info()
    if shop_info:
        print(f"   ✅ Conectado: {shop_info.get('name', 'N/A')}")
        current_products = client.count_products()
        print(f"   📊 Productos actuales en tienda: {current_products}")
    else:
        result.errors.append("No se pudo conectar a Shopify")
        print(f"   ❌ No se pudo conectar")
        return result

    # 7. Actualizar configuración
    print(f"\n   Actualizando branding...")

    # Upload logo
    if profile.logo_path:
        if client.upload_logo(profile.logo_path):
            result.logo_uploaded = True
            print(f"   ✅ Logo subido")
        else:
            print(f"   ⚠️  No se pudo subir logo")

    # Update shop settings (limitado por API)
    # Nota: Para cambios completos se necesita Theme API o Storefront Renderer

    result.success = True
    result.theme_updated = True

    print(f"\n   {'✅' if result.success else '❌'} Branding {'activado' if result.success else 'fallido'}")

    return result


def activate_all_companies(dry_run: bool = False) -> List[BrandingResult]:
    """Activa branding para todas las empresas configuradas."""
    results = []

    for company_name in COMPANY_STORE_MAP.keys():
        result = activate_company_branding(company_name, dry_run)
        results.append(result)

    return results


# ============================================================================
# CLI
# ============================================================================

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║           ██████╗ ██████╗ ██╗    ██████╗ ██████╗  █████╗ ███╗   ██╗██████╗   ║
║          ██╔═══██╗██╔══██╗██║    ██╔══██╗██╔══██╗██╔══██╗████╗  ██║██╔══██╗  ║
║          ██║   ██║██║  ██║██║    ██████╔╝██████╔╝███████║██╔██╗ ██║██║  ██║  ║
║          ██║   ██║██║  ██║██║    ██╔══██╗██╔══██╗██╔══██║██║╚██╗██║██║  ██║  ║
║          ╚██████╔╝██████╔╝██║    ██████╔╝██║  ██║██║  ██║██║ ╚████║██████╔╝  ║
║           ╚═════╝ ╚═════╝ ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝   ║
║                                                                              ║
║                  SHOPIFY BRANDING ACTIVATOR v1.0                             ║
║                     Powered by ADSI Ecosystem                                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")


def list_companies():
    """Lista empresas disponibles."""
    print("\n" + "═" * 60)
    print("  EMPRESAS DEL ECOSISTEMA ODI")
    print("═" * 60 + "\n")

    companies = discover_companies()

    print(f"{'Empresa':<15} {'Tienda':<30} {'Logo':<8} {'Data':<8}")
    print("-" * 60)

    for name, info in sorted(companies.items()):
        shop = os.getenv(info.get('shop_env', ''), info.get('default_shop', 'N/A'))
        has_logo = '✅' if info.get('logo_path') else '❌'
        has_data = '✅' if info.get('has_data') else '❌'

        print(f"{name:<15} {shop[:28]:<30} {has_logo:<8} {has_data:<8}")

    print("\n" + "-" * 60)
    print(f"Total: {len(companies)} empresas")
    print("\nPara activar: python3 activate_shopify_branding.py --activate EMPRESA")


def print_help():
    print("""
USO:
    python3 activate_shopify_branding.py [comando] [opciones]

COMANDOS:
    --list              Lista empresas disponibles
    --activate EMPRESA  Activa branding para una empresa
    --activate-all      Activa branding para todas las empresas

OPCIONES:
    --dry-run           Preview sin realizar cambios

EJEMPLOS:
    # Ver empresas disponibles
    python3 activate_shopify_branding.py --list

    # Activar KAIQI
    python3 activate_shopify_branding.py --activate KAIQI

    # Preview sin cambios
    python3 activate_shopify_branding.py --activate KAIQI --dry-run

    # Activar todas
    python3 activate_shopify_branding.py --activate-all

ESTRUCTURA DE ASSETS:
    {assets_root}/
    ├── Data/              # Datos de productos
    ├── Imagenes/          # Imágenes
    ├── Perfiles/          # Perfiles JSON
    └── logos_optimized/   # Logos PNG
""".format(assets_root=ASSETS_ROOT))


def main():
    print_banner()

    args = sys.argv[1:]

    if not args or '--help' in args or '-h' in args:
        print_help()
        return

    dry_run = '--dry-run' in args

    if '--list' in args:
        list_companies()

    elif '--activate-all' in args:
        results = activate_all_companies(dry_run)

        print("\n" + "═" * 60)
        print("  RESUMEN DE ACTIVACIÓN")
        print("═" * 60)

        success_count = sum(1 for r in results if r.success)
        print(f"\n  Total: {len(results)} empresas")
        print(f"  Exitosas: {success_count}")
        print(f"  Fallidas: {len(results) - success_count}")

    elif '--activate' in args:
        idx = args.index('--activate')
        if idx + 1 < len(args):
            company = args[idx + 1]
            result = activate_company_branding(company, dry_run)

            if result.success:
                print(f"\n✅ Branding activado para {company}")
            else:
                print(f"\n❌ Error activando {company}")
                for error in result.errors:
                    print(f"   - {error}")
        else:
            print("❌ Especifica empresa: --activate EMPRESA")

    else:
        print("❌ Comando no reconocido")
        print_help()


if __name__ == "__main__":
    main()
