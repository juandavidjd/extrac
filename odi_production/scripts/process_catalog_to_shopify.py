#!/usr/bin/env python3
"""
ODI Catalog Processor - Genera archivos Shopify desde catálogos de empresas
Procesa CSV de empresas del ecosistema ODI y genera formato Shopify

Uso:
    python3 process_catalog_to_shopify.py --empresa kaiqi
    python3 process_catalog_to_shopify.py --all
"""

import csv
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
import json
import re

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

BASE_PATH = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI"
DATA_PATH = f"{BASE_PATH}/Data"
IMAGES_PATH = f"{BASE_PATH}/Imagenes"
OUTPUT_PATH = "/opt/odi/shopify_output"

# Mapeo de empresas a sus tiendas Shopify
EMPRESA_CONFIG = {
    "Kaiqi": {
        "shop_domain": "kaiqiparts.myshopify.com",
        "vendor": "KAIQI PARTS",
        "tags_base": ["repuestos", "motos", "kaiqi"],
        "csv_separator": ";",
        "price_margin": 1.3  # 30% margen
    },
    "Bara": {
        "shop_domain": "baraimportaciones.myshopify.com",
        "vendor": "BARA IMPORTACIONES",
        "tags_base": ["repuestos", "motos", "bara"],
        "csv_separator": ";",
        "price_margin": 1.25
    },
    "DFG": {
        "shop_domain": "dfgmotos.myshopify.com",
        "vendor": "DFG MOTOS",
        "tags_base": ["repuestos", "motos", "dfg"],
        "csv_separator": ";",
        "price_margin": 1.28
    },
    "Yokomar": {
        "shop_domain": "yokomar.myshopify.com",
        "vendor": "YOKOMAR",
        "tags_base": ["repuestos", "motos", "yokomar"],
        "csv_separator": ";",
        "price_margin": 1.25
    },
    "Imbra": {
        "shop_domain": "imbramotos.myshopify.com",
        "vendor": "IMBRA",
        "tags_base": ["repuestos", "motos", "imbra"],
        "csv_separator": ";",
        "price_margin": 1.3
    },
    "Duna": {
        "shop_domain": "dunamotos.myshopify.com",
        "vendor": "DUNA MOTOS",
        "tags_base": ["repuestos", "motos", "duna"],
        "csv_separator": ";",
        "price_margin": 1.25
    },
    "Japan": {
        "shop_domain": "japanmotos.myshopify.com",
        "vendor": "JAPAN MOTOS",
        "tags_base": ["repuestos", "motos", "japan"],
        "csv_separator": ";",
        "price_margin": 1.3
    },
    "Leo": {
        "shop_domain": "leomotos.myshopify.com",
        "vendor": "LEO MOTOS",
        "tags_base": ["repuestos", "motos", "leo"],
        "csv_separator": ";",
        "price_margin": 1.25
    },
    "Vaisand": {
        "shop_domain": "vaisand.myshopify.com",
        "vendor": "VAISAND",
        "tags_base": ["repuestos", "motos", "vaisand"],
        "csv_separator": ";",
        "price_margin": 1.28
    },
    "Store": {
        "shop_domain": "storemotos.myshopify.com",
        "vendor": "STORE MOTOS",
        "tags_base": ["repuestos", "motos", "store"],
        "csv_separator": ";",
        "price_margin": 1.3
    },
    "Armotos": {
        "shop_domain": "armotos.myshopify.com",
        "vendor": "ARMOTOS",
        "tags_base": ["repuestos", "motos", "armotos"],
        "csv_separator": ";",
        "price_margin": 1.28
    },
    "Vitton": {
        "shop_domain": "vitton.myshopify.com",
        "vendor": "VITTON",
        "tags_base": ["repuestos", "motos", "vitton"],
        "csv_separator": ";",
        "price_margin": 1.25
    },
    "CBI": {
        "shop_domain": "cbi.myshopify.com",
        "vendor": "CBI MOTOS",
        "tags_base": ["repuestos", "motos", "cbi"],
        "csv_separator": ";",
        "price_margin": 1.3
    }
}

# Headers de Shopify CSV
SHOPIFY_HEADERS = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Product Category", "Type",
    "Tags", "Published", "Option1 Name", "Option1 Value", "Option2 Name",
    "Option2 Value", "Option3 Name", "Option3 Value", "Variant SKU",
    "Variant Grams", "Variant Inventory Tracker", "Variant Inventory Qty",
    "Variant Inventory Policy", "Variant Fulfillment Service", "Variant Price",
    "Variant Compare At Price", "Variant Requires Shipping", "Variant Taxable",
    "Variant Barcode", "Image Src", "Image Position", "Image Alt Text",
    "Gift Card", "SEO Title", "SEO Description", "Google Shopping / Google Product Category",
    "Google Shopping / Gender", "Google Shopping / Age Group", "Google Shopping / MPN",
    "Google Shopping / AdWords Grouping", "Google Shopping / AdWords Labels",
    "Google Shopping / Condition", "Google Shopping / Custom Product",
    "Google Shopping / Custom Label 0", "Google Shopping / Custom Label 1",
    "Google Shopping / Custom Label 2", "Google Shopping / Custom Label 3",
    "Google Shopping / Custom Label 4", "Variant Image", "Variant Weight Unit",
    "Variant Tax Code", "Cost per item", "Price / International",
    "Compare At Price / International", "Status"
]

# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE UTILIDAD
# ══════════════════════════════════════════════════════════════════════════════

def clean_text(text):
    """Limpia texto para uso en Shopify"""
    if not text:
        return ""
    text = str(text).strip()
    # Remover caracteres especiales
    text = re.sub(r'[^\w\s\-/°®™.,()]', '', text)
    return text

def create_handle(title, sku):
    """Crea handle URL-friendly para Shopify"""
    handle = f"{title}-{sku}".lower()
    handle = re.sub(r'[^a-z0-9\-]', '-', handle)
    handle = re.sub(r'-+', '-', handle)
    handle = handle.strip('-')
    return handle[:200]  # Shopify limit

def extract_moto_info(description):
    """Extrae información de moto de la descripción"""
    marcas = ['YAMAHA', 'HONDA', 'SUZUKI', 'KAWASAKI', 'BAJAJ', 'PULSAR', 'KTM',
              'TVS', 'AKT', 'HERO', 'AUTECO', 'KYMCO', 'BENELLI', 'CFMOTO']

    description_upper = description.upper()
    found_marca = None

    for marca in marcas:
        if marca in description_upper:
            found_marca = marca
            break

    # Buscar año
    year_match = re.search(r'\b(20[0-2][0-9]|19[89][0-9])\b', description)
    year = year_match.group(0) if year_match else None

    # Buscar cilindraje
    cc_match = re.search(r'\b(\d{2,4})\s*cc\b', description, re.IGNORECASE)
    cc = f"{cc_match.group(1)}cc" if cc_match else None

    return {
        "marca": found_marca,
        "year": year,
        "cilindraje": cc
    }

def generate_html_description(description, moto_info, vendor):
    """Genera descripción HTML para Shopify"""
    html = f"""<div class="product-description">
<h3>{clean_text(description)}</h3>
<ul class="specs">
"""
    if moto_info.get("marca"):
        html += f'<li><strong>Compatible con:</strong> {moto_info["marca"]}</li>\n'
    if moto_info.get("year"):
        html += f'<li><strong>Año:</strong> {moto_info["year"]}</li>\n'
    if moto_info.get("cilindraje"):
        html += f'<li><strong>Cilindraje:</strong> {moto_info["cilindraje"]}</li>\n'

    html += f"""</ul>
<p class="vendor">Distribuido por <strong>{vendor}</strong></p>
<p class="warranty">✓ Garantía de calidad</p>
<p class="shipping">✓ Envío a todo Colombia</p>
</div>"""
    return html

def get_product_type(description):
    """Determina el tipo de producto basado en la descripción"""
    types = {
        "pastilla": "Pastillas de Freno",
        "freno": "Sistema de Frenos",
        "filtro": "Filtros",
        "aceite": "Lubricantes",
        "cadena": "Cadenas y Piñones",
        "llanta": "Llantas",
        "bateria": "Baterías",
        "espejo": "Espejos",
        "bujia": "Bujías",
        "faro": "Iluminación",
        "manubrio": "Manubrios",
        "carburador": "Carburadores",
        "clutch": "Embrague",
        "amortiguador": "Suspensión",
        "kit": "Kits de Repuestos"
    }

    desc_lower = description.lower()
    for keyword, product_type in types.items():
        if keyword in desc_lower:
            return product_type

    return "Repuestos Motos"

# ══════════════════════════════════════════════════════════════════════════════
# PROCESADOR PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def process_empresa(empresa_name):
    """Procesa catálogo de una empresa y genera CSV para Shopify"""

    print(f"\n{'='*60}")
    print(f"  Procesando: {empresa_name}")
    print(f"{'='*60}")

    # Configuración de la empresa
    config = EMPRESA_CONFIG.get(empresa_name)
    if not config:
        print(f"❌ Empresa '{empresa_name}' no configurada")
        return None

    # Buscar archivo Base_Datos
    data_dir = Path(DATA_PATH) / empresa_name
    if not data_dir.exists():
        print(f"❌ Directorio no encontrado: {data_dir}")
        return None

    base_datos_file = None
    for f in data_dir.glob("Base_Datos*.csv"):
        base_datos_file = f
        break

    if not base_datos_file:
        print(f"❌ Archivo Base_Datos*.csv no encontrado en {data_dir}")
        return None

    print(f"📄 Archivo fuente: {base_datos_file.name}")

    # Buscar archivo de precios
    precios_file = None
    for f in data_dir.glob("Lista_Precios*.csv"):
        precios_file = f
        break

    precios_map = {}
    if precios_file:
        print(f"💰 Archivo precios: {precios_file.name}")
        try:
            with open(precios_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=config['csv_separator'])
                for row in reader:
                    sku = row.get('CODIGO', row.get('SKU', row.get('codigo', '')))
                    precio = row.get('PRECIO', row.get('precio', row.get('PRICE', '0')))
                    if sku and precio:
                        try:
                            precios_map[sku.strip()] = float(str(precio).replace(',', '').replace('$', '').strip())
                        except:
                            pass
        except Exception as e:
            print(f"⚠️ Error leyendo precios: {e}")

    # Leer catálogo base
    products = []
    try:
        with open(base_datos_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=config['csv_separator'])

            for row in reader:
                # Mapear campos (diferentes formatos posibles)
                description = row.get('DESCRIPCION', row.get('descripcion', row.get('Title', '')))
                sku = row.get('CODIGO', row.get('codigo', row.get('SKU', '')))
                image_url = row.get('Imagen_URL_Origen', row.get('imagen', row.get('Image Src', '')))
                url_producto = row.get('URL_Producto', '')

                if not description or not sku:
                    continue

                description = clean_text(description)
                sku = clean_text(sku)

                # Obtener precio
                base_price = precios_map.get(sku, 50000)  # Precio default
                sale_price = base_price * config['price_margin']

                # Extraer info de moto
                moto_info = extract_moto_info(description)

                # Generar tags
                tags = list(config['tags_base'])
                if moto_info.get('marca'):
                    tags.append(moto_info['marca'].lower())
                product_type = get_product_type(description)
                tags.append(product_type.lower().replace(' ', '-'))

                # Crear producto Shopify
                product = {
                    "Handle": create_handle(description, sku),
                    "Title": description[:255],
                    "Body (HTML)": generate_html_description(description, moto_info, config['vendor']),
                    "Vendor": config['vendor'],
                    "Product Category": "Vehicles & Parts > Vehicle Parts & Accessories",
                    "Type": product_type,
                    "Tags": ", ".join(tags),
                    "Published": "true",
                    "Option1 Name": "Title",
                    "Option1 Value": "Default Title",
                    "Option2 Name": "",
                    "Option2 Value": "",
                    "Option3 Name": "",
                    "Option3 Value": "",
                    "Variant SKU": sku,
                    "Variant Grams": "500",
                    "Variant Inventory Tracker": "shopify",
                    "Variant Inventory Qty": "100",
                    "Variant Inventory Policy": "continue",
                    "Variant Fulfillment Service": "manual",
                    "Variant Price": f"{sale_price:.2f}",
                    "Variant Compare At Price": f"{base_price * 1.5:.2f}",
                    "Variant Requires Shipping": "true",
                    "Variant Taxable": "true",
                    "Variant Barcode": "",
                    "Image Src": image_url,
                    "Image Position": "1",
                    "Image Alt Text": description[:100],
                    "Gift Card": "false",
                    "SEO Title": f"{description[:60]} | {config['vendor']}",
                    "SEO Description": f"Compra {description[:100]} en {config['vendor']}. Envío a todo Colombia. Garantía de calidad.",
                    "Google Shopping / Google Product Category": "Vehicles & Parts > Vehicle Parts & Accessories > Motor Vehicle Parts",
                    "Google Shopping / Gender": "",
                    "Google Shopping / Age Group": "",
                    "Google Shopping / MPN": sku,
                    "Google Shopping / AdWords Grouping": "Repuestos Motos",
                    "Google Shopping / AdWords Labels": "",
                    "Google Shopping / Condition": "new",
                    "Google Shopping / Custom Product": "",
                    "Google Shopping / Custom Label 0": empresa_name,
                    "Google Shopping / Custom Label 1": product_type,
                    "Google Shopping / Custom Label 2": moto_info.get('marca', ''),
                    "Google Shopping / Custom Label 3": "",
                    "Google Shopping / Custom Label 4": "",
                    "Variant Image": image_url,
                    "Variant Weight Unit": "g",
                    "Variant Tax Code": "",
                    "Cost per item": f"{base_price:.2f}",
                    "Price / International": "",
                    "Compare At Price / International": "",
                    "Status": "draft"  # Empezar en draft para revisión
                }

                products.append(product)

    except Exception as e:
        print(f"❌ Error procesando catálogo: {e}")
        import traceback
        traceback.print_exc()
        return None

    print(f"✅ Productos procesados: {len(products)}")

    # Crear directorio de salida
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    # Guardar CSV para Shopify
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path(OUTPUT_PATH) / f"shopify_{empresa_name.lower()}_{timestamp}.csv"

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=SHOPIFY_HEADERS)
        writer.writeheader()
        writer.writerows(products)

    print(f"📦 Archivo generado: {output_file}")
    print(f"   → {len(products)} productos listos para importar a Shopify")

    # También guardar JSON para referencia
    json_file = Path(OUTPUT_PATH) / f"products_{empresa_name.lower()}_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

    print(f"📋 Backup JSON: {json_file}")

    return {
        "empresa": empresa_name,
        "products_count": len(products),
        "output_csv": str(output_file),
        "output_json": str(json_file)
    }

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='ODI Catalog Processor for Shopify')
    parser.add_argument('--empresa', type=str, help='Nombre de la empresa a procesar')
    parser.add_argument('--all', action='store_true', help='Procesar todas las empresas')
    parser.add_argument('--list', action='store_true', help='Listar empresas disponibles')

    args = parser.parse_args()

    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    ODI CATALOG PROCESSOR FOR SHOPIFY                           ║
║                    Organismo Digital Industrial v1.0                           ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)

    if args.list:
        print("Empresas configuradas:")
        for empresa in EMPRESA_CONFIG.keys():
            data_dir = Path(DATA_PATH) / empresa
            status = "✅" if data_dir.exists() else "❌"
            print(f"  {status} {empresa}")
        return

    if args.all:
        results = []
        for empresa in EMPRESA_CONFIG.keys():
            result = process_empresa(empresa)
            if result:
                results.append(result)

        print(f"\n{'='*60}")
        print(f"  RESUMEN DE PROCESAMIENTO")
        print(f"{'='*60}")
        total = sum(r['products_count'] for r in results)
        print(f"  Total empresas: {len(results)}")
        print(f"  Total productos: {total}")
        print(f"  Archivos en: {OUTPUT_PATH}")

    elif args.empresa:
        # Capitalizar primera letra para match
        empresa = args.empresa.capitalize()
        result = process_empresa(empresa)
        if result:
            print(f"\n✅ Procesamiento completo")
            print(f"   Archivo: {result['output_csv']}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
