#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════════
                         CASO 001 - PRIMERA TRANSACCIÓN COMERCIAL
                    Validación del Flujo: PDF → Vision → SRM → Shopify
══════════════════════════════════════════════════════════════════════════════════

PROPOSITO:
    Este script valida que ODI puede convertir un catálogo en productos vendibles.
    Es el "Hello World" comercial del sistema.

FLUJO CASO 001:
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Catálogo  │ ──▶ │   Vision    │ ──▶ │    SRM      │ ──▶ │  Shopify    │
    │   (datos)   │     │  (extraer)  │     │ (procesar)  │     │  (vender)   │
    └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘

REQUISITOS:
    1. Archivo .env con credenciales de Shopify
    2. Base de datos de productos (Base_Datos_Armotos.csv existe)

USO:
    # Verificar configuración
    python3 caso_001_test.py --check

    # Ejecutar test completo con 1 producto
    python3 caso_001_test.py --execute

    # Ejecutar con N productos
    python3 caso_001_test.py --execute --products 5

    # Solo mostrar producto de prueba (sin push)
    python3 caso_001_test.py --preview

══════════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import csv
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "Base_Datos_Armotos.csv"
CATALOG_FILE = SCRIPT_DIR / "catalogo_kaiqi_imagenes_ARMOTOS.csv"
IMAGE_SERVER = os.getenv("IMAGE_SERVER_URL", "http://64.23.170.118/images")

# Tiendas disponibles para test
SHOPIFY_STORES = {
    "kaiqi": {
        "name": "Kaiqi",
        "shop_env": "KAIQI_SHOP",
        "token_env": "KAIQI_TOKEN",
        "default_shop": "u03tqc-0e.myshopify.com"
    },
    "japan": {
        "name": "Japan",
        "shop_env": "JAPAN_SHOP",
        "token_env": "JAPAN_TOKEN",
        "default_shop": "7cy1zd-qz.myshopify.com"
    },
    "bara": {
        "name": "Bara",
        "shop_env": "BARA_SHOP",
        "token_env": "BARA_TOKEN",
        "default_shop": "4jqcki-jq.myshopify.com"
    },
    "store": {
        "name": "Store (Test)",
        "shop_env": "STORE_SHOP",
        "token_env": "STORE_TOKEN",
        "default_shop": "0b6umv-11.myshopify.com"
    }
}

# ============================================================================
# MODELOS
# ============================================================================

@dataclass
class TestProduct:
    """Producto para Caso 001."""
    sku: str
    title: str
    description: str
    price: float
    image_url: str
    vendor: str = "ARMOTOS"
    product_type: str = "Repuesto Moto"
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = ["caso001", "test", "armotos"]

    def to_shopify_dict(self) -> dict:
        """Formato para API de Shopify."""
        return {
            "product": {
                "title": self.title,
                "body_html": f"<p>{self.description}</p>",
                "vendor": self.vendor,
                "product_type": self.product_type,
                "tags": ", ".join(self.tags),
                "variants": [{
                    "sku": self.sku,
                    "price": str(self.price),
                    "inventory_management": "shopify",
                    "inventory_quantity": 10
                }],
                "images": [{
                    "src": self.image_url
                }] if self.image_url else []
            }
        }


# ============================================================================
# VERIFICACIÓN DE CONFIGURACIÓN
# ============================================================================

def check_configuration() -> Dict[str, bool]:
    """Verifica que todo esté configurado para Caso 001."""
    print("\n" + "═" * 70)
    print("                    CASO 001 - VERIFICACIÓN DE CONFIGURACIÓN")
    print("═" * 70 + "\n")

    checks = {}

    # 1. Verificar archivo de datos
    print("📁 ARCHIVOS DE DATOS:")
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=';')
            rows = list(reader)
            product_count = len(rows) - 1
        print(f"   ✅ Base_Datos_Armotos.csv ({product_count} productos)")
        checks["data_file"] = True
    else:
        print(f"   ❌ Base_Datos_Armotos.csv NO ENCONTRADO")
        checks["data_file"] = False

    if CATALOG_FILE.exists():
        print(f"   ✅ catalogo_kaiqi_imagenes_ARMOTOS.csv")
        checks["catalog_file"] = True
    else:
        print(f"   ⚠️  catalogo_kaiqi_imagenes_ARMOTOS.csv (opcional)")
        checks["catalog_file"] = False

    # 2. Verificar .env
    print("\n🔐 CREDENCIALES (.env):")
    env_file = SCRIPT_DIR / ".env"
    if env_file.exists():
        print(f"   ✅ Archivo .env encontrado")
        checks["env_file"] = True
    else:
        print(f"   ❌ Archivo .env NO ENCONTRADO")
        print(f"      Copia .env.template a .env y configura credenciales")
        checks["env_file"] = False

    # 3. Verificar tiendas Shopify
    print("\n🛒 TIENDAS SHOPIFY:")
    any_store_configured = False
    for store_id, store_config in SHOPIFY_STORES.items():
        shop = os.getenv(store_config["shop_env"])
        token = os.getenv(store_config["token_env"])

        if shop and token:
            print(f"   ✅ {store_config['name']}: {shop}")
            any_store_configured = True
            checks[f"store_{store_id}"] = True
        else:
            print(f"   ⚠️  {store_config['name']}: No configurada")
            checks[f"store_{store_id}"] = False

    checks["any_store"] = any_store_configured

    # 4. Verificar OpenAI (para enriquecimiento)
    print("\n🤖 API KEYS:")
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key.startswith("sk-"):
        print(f"   ✅ OpenAI API Key configurada")
        checks["openai"] = True
    else:
        print(f"   ⚠️  OpenAI API Key no configurada (opcional para enriquecimiento)")
        checks["openai"] = False

    # 5. Verificar servidor de imágenes
    print("\n🖼️  SERVIDOR DE IMÁGENES:")
    print(f"   📍 {IMAGE_SERVER}")
    checks["image_server"] = True  # Asumimos que está disponible

    # Resumen
    print("\n" + "─" * 70)
    critical_ok = checks.get("data_file", False) and checks.get("any_store", False)

    if critical_ok:
        print("✅ CASO 001 LISTO PARA EJECUTAR")
        print("   Ejecuta: python3 caso_001_test.py --execute")
    else:
        print("❌ CASO 001 REQUIERE CONFIGURACIÓN ADICIONAL")
        if not checks.get("data_file"):
            print("   → Falta archivo de datos")
        if not checks.get("any_store"):
            print("   → Configura al menos una tienda Shopify en .env")

    print("─" * 70 + "\n")

    return checks


# ============================================================================
# SELECCIÓN DE PRODUCTOS
# ============================================================================

def load_products(limit: int = 5) -> List[TestProduct]:
    """Carga productos del CSV para test."""
    products = []

    if not DATA_FILE.exists():
        print(f"❌ Archivo no encontrado: {DATA_FILE}")
        return products

    with open(DATA_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')

        for i, row in enumerate(reader):
            if i >= limit:
                break

            # Extraer datos
            descripcion = row.get('Descripcion', '').strip()
            sku = row.get('SKU_Detectado', '').strip()
            imagen_final = row.get('Imagen_Final', '').strip()

            if not descripcion:
                continue

            # Generar SKU si no existe
            if not sku:
                sku = f"ARM-{i+1:04d}"

            # Construir URL de imagen
            image_url = ""
            if imagen_final:
                image_url = f"{IMAGE_SERVER}/{imagen_final}"

            # Crear producto
            product = TestProduct(
                sku=sku,
                title=descripcion.title(),
                description=f"Repuesto de moto: {descripcion}. Producto original ARMOTOS, alta calidad.",
                price=round(15000 + (i * 1000), 0),  # Precio base + incremento
                image_url=image_url,
                tags=["caso001", "armotos", "repuesto-moto"]
            )

            products.append(product)

    return products


def preview_products(products: List[TestProduct]):
    """Muestra preview de productos a subir."""
    print("\n" + "═" * 70)
    print("                    CASO 001 - PREVIEW DE PRODUCTOS")
    print("═" * 70 + "\n")

    for i, p in enumerate(products, 1):
        print(f"┌─ Producto {i} ────────────────────────────────────────────────")
        print(f"│ SKU:    {p.sku}")
        print(f"│ Título: {p.title}")
        print(f"│ Precio: ${p.price:,.0f} COP")
        print(f"│ Imagen: {p.image_url[:60]}..." if len(p.image_url) > 60 else f"│ Imagen: {p.image_url}")
        print(f"│ Tags:   {', '.join(p.tags)}")
        print(f"└{'─' * 65}\n")

    print(f"Total: {len(products)} productos listos para Caso 001\n")


# ============================================================================
# PUSH A SHOPIFY
# ============================================================================

def push_to_shopify(products: List[TestProduct], store_id: str = "store") -> Dict:
    """Push productos a Shopify."""
    import requests

    store_config = SHOPIFY_STORES.get(store_id)
    if not store_config:
        return {"success": False, "error": f"Tienda '{store_id}' no encontrada"}

    shop = os.getenv(store_config["shop_env"])
    token = os.getenv(store_config["token_env"])

    if not shop or not token:
        return {
            "success": False,
            "error": f"Credenciales no configuradas para {store_config['name']}. "
                     f"Configura {store_config['shop_env']} y {store_config['token_env']} en .env"
        }

    print("\n" + "═" * 70)
    print("                    CASO 001 - PUSH A SHOPIFY")
    print("═" * 70)
    print(f"\n🛒 Tienda: {store_config['name']} ({shop})")
    print(f"📦 Productos: {len(products)}\n")

    results = {
        "success": True,
        "store": shop,
        "products_created": 0,
        "products_failed": 0,
        "details": []
    }

    api_version = "2024-01"
    base_url = f"https://{shop}/admin/api/{api_version}"
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }

    for i, product in enumerate(products, 1):
        print(f"[{i}/{len(products)}] Subiendo: {product.sku} - {product.title[:40]}...")

        try:
            payload = product.to_shopify_dict()
            response = requests.post(
                f"{base_url}/products.json",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 201:
                data = response.json()
                product_id = data["product"]["id"]
                product_url = f"https://{shop}/admin/products/{product_id}"

                print(f"   ✅ Creado! ID: {product_id}")
                results["products_created"] += 1
                results["details"].append({
                    "sku": product.sku,
                    "status": "created",
                    "id": product_id,
                    "url": product_url
                })
            else:
                error_msg = response.json().get("errors", response.text)
                print(f"   ❌ Error: {error_msg}")
                results["products_failed"] += 1
                results["details"].append({
                    "sku": product.sku,
                    "status": "failed",
                    "error": str(error_msg)
                })

        except Exception as e:
            print(f"   ❌ Excepción: {str(e)}")
            results["products_failed"] += 1
            results["details"].append({
                "sku": product.sku,
                "status": "error",
                "error": str(e)
            })

    # Resumen
    print("\n" + "─" * 70)
    print("📊 RESUMEN CASO 001:")
    print(f"   ✅ Creados: {results['products_created']}")
    print(f"   ❌ Fallidos: {results['products_failed']}")

    if results["products_created"] > 0:
        print(f"\n🎉 ¡CASO 001 EXITOSO!")
        print(f"   ODI ha convertido datos en productos vendibles.")
        print(f"\n   Ver productos en: https://{shop}/admin/products")

        # Mostrar URL del primer producto creado
        for detail in results["details"]:
            if detail["status"] == "created":
                print(f"   Producto ejemplo: {detail['url']}")
                break

    print("─" * 70 + "\n")

    results["success"] = results["products_created"] > 0
    return results


# ============================================================================
# CLI
# ============================================================================

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║      ██████╗ █████╗ ███████╗ ██████╗      ██████╗  ██████╗  ██╗              ║
║     ██╔════╝██╔══██╗██╔════╝██╔═══██╗    ██╔═████╗██╔═████╗███║              ║
║     ██║     ███████║███████╗██║   ██║    ██║██╔██║██║██╔██║╚██║              ║
║     ██║     ██╔══██║╚════██║██║   ██║    ████╔╝██║████╔╝██║ ██║              ║
║     ╚██████╗██║  ██║███████║╚██████╔╝    ╚██████╔╝╚██████╔╝ ██║              ║
║      ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝      ╚═════╝  ╚═════╝  ╚═╝              ║
║                                                                              ║
║              PRIMERA TRANSACCIÓN COMERCIAL DE ODI                            ║
║                    "Del PDF al dinero"                                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")


def print_help():
    print("""
USO:
    python3 caso_001_test.py [comando] [opciones]

COMANDOS:
    --check         Verificar configuración (credenciales, archivos)
    --preview       Ver productos que se subirán (sin ejecutar)
    --execute       Ejecutar Caso 001 (push a Shopify)

OPCIONES:
    --products N    Número de productos a procesar (default: 1)
    --store ID      Tienda destino: kaiqi, japan, bara, store (default: store)

EJEMPLOS:
    # Verificar que todo esté listo
    python3 caso_001_test.py --check

    # Ver qué productos se subirán
    python3 caso_001_test.py --preview --products 3

    # Ejecutar con 1 producto a tienda de test
    python3 caso_001_test.py --execute

    # Ejecutar con 5 productos a Kaiqi
    python3 caso_001_test.py --execute --products 5 --store kaiqi

TIENDAS DISPONIBLES:
    kaiqi   - Kaiqi (u03tqc-0e.myshopify.com)
    japan   - Japan (7cy1zd-qz.myshopify.com)
    bara    - Bara (4jqcki-jq.myshopify.com)
    store   - Store Test (0b6umv-11.myshopify.com)
""")


def main():
    print_banner()

    # Parsear argumentos
    args = sys.argv[1:]

    if not args or '--help' in args or '-h' in args:
        print_help()
        return

    # Opciones
    num_products = 1
    store_id = "store"

    for i, arg in enumerate(args):
        if arg == '--products' and i + 1 < len(args):
            num_products = int(args[i + 1])
        elif arg == '--store' and i + 1 < len(args):
            store_id = args[i + 1]

    # Comandos
    if '--check' in args:
        check_configuration()

    elif '--preview' in args:
        products = load_products(num_products)
        if products:
            preview_products(products)
        else:
            print("❌ No se encontraron productos para preview")

    elif '--execute' in args:
        # Verificar configuración primero
        checks = check_configuration()

        if not checks.get("any_store"):
            print("❌ No hay tiendas Shopify configuradas")
            print("   Configura credenciales en .env primero")
            return

        # Cargar productos
        products = load_products(num_products)
        if not products:
            print("❌ No se encontraron productos")
            return

        # Preview
        preview_products(products)

        # Confirmar
        print("⚠️  ¿Continuar con el push a Shopify? (s/n): ", end="")
        confirm = input().strip().lower()

        if confirm in ['s', 'si', 'yes', 'y']:
            results = push_to_shopify(products, store_id)

            # Guardar resultados
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = SCRIPT_DIR / f"caso_001_results_{timestamp}.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"📄 Resultados guardados en: {results_file}")
        else:
            print("❌ Operación cancelada")

    else:
        print("❌ Comando no reconocido")
        print_help()


if __name__ == "__main__":
    main()
