#!/usr/bin/env python3
"""
ARMOTOS Issue Fixer v1.0
Fixes: 1) Concatenated prices, 2) Short titles, 3) Generic benefits
"""

import os
import sys
import json
import re
import time
import requests

sys.path.insert(0, "/opt/odi")
from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")

SHOP = os.getenv("ARMOTOS_SHOP")
TOKEN = os.getenv("ARMOTOS_TOKEN")
API_VERSION = "2025-07"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# Category-specific benefits (16 categories)
BENEFICIOS_SRM = {
    "Frenos": [
        "Coeficiente de fricción optimizado para frenado progresivo",
        "Compuesto resistente al calor y fade",
        "Compatible con discos OEM y aftermarket",
        "Vida útil extendida bajo uso intensivo"
    ],
    "Transmision": [
        "Acero templado de alta resistencia al desgaste",
        "Paso y dientes calibrados para transmisión suave",
        "Tratamiento anticorrosivo de larga duración",
        "Reduce vibración y ruido en operación"
    ],
    "Iluminacion": [
        "Luminosidad superior para máxima visibilidad",
        "Bajo consumo energético optimizado",
        "Resistente a vibraciones y humedad",
        "Instalación plug & play sin modificaciones"
    ],
    "Suspension": [
        "Absorción de impactos superior en todo terreno",
        "Sellado hermético anti-fugas garantizado",
        "Ajuste preciso para geometría original",
        "Durabilidad comprobada en condiciones extremas"
    ],
    "Lubricantes": [
        "Protección superior contra desgaste y fricción",
        "Estabilidad térmica en altas temperaturas",
        "Limpieza activa del motor durante operación",
        "Intervalos de cambio extendidos certificados"
    ],
    "Filtros": [
        "Eficiencia de filtración superior al 98%",
        "Flujo de aire optimizado sin restricción",
        "Material filtrante de alta capacidad",
        "Fácil instalación y reemplazo"
    ],
    "Electrico": [
        "Componentes electrónicos de grado automotriz",
        "Protección contra sobrecarga y cortocircuito",
        "Conexiones selladas contra humedad",
        "Compatibilidad verificada con sistema OEM"
    ],
    "Llantas": [
        "Compuesto de caucho de alto agarre",
        "Diseño de banda para evacuación de agua",
        "Estructura reforzada anti-pinchazos",
        "Balanceo uniforme garantizado"
    ],
    "Escape": [
        "Acero inoxidable resistente a corrosión",
        "Diseño de flujo optimizado para rendimiento",
        "Reducción de temperatura y ruido",
        "Acabado cromado de larga duración"
    ],
    "Motor": [
        "Tolerancias de precisión micrométrica",
        "Material de aleación de alta resistencia",
        "Tratamiento térmico para dureza óptima",
        "Compatibilidad garantizada con especificaciones OEM"
    ],
    "Carroceria": [
        "Material ABS de alto impacto",
        "Ajuste preciso con clips originales",
        "Resistente a rayos UV y decoloración",
        "Acabado de pintura compatible"
    ],
    "Rodamientos": [
        "Acero cromado de alta pureza",
        "Sellado 2RS para protección total",
        "Lubricación permanente de fábrica",
        "Tolerancia de precisión ABEC certificada"
    ],
    "Cables": [
        "Cable de acero trenzado de alta resistencia",
        "Funda exterior resistente a abrasión",
        "Recorrido suave sin fricción",
        "Terminales reforzados anti-desgaste"
    ],
    "Manubrio": [
        "Ergonomía optimizada para menor fatiga",
        "Material antideslizante de alta adherencia",
        "Absorción de vibraciones integrada",
        "Diseño universal de fácil instalación"
    ],
    "Herramientas": [
        "Acero al cromo-vanadio profesional",
        "Tratamiento anticorrosivo duradero",
        "Diseño ergonómico para uso prolongado",
        "Precisión dimensional garantizada"
    ],
    "General": [
        "Repuesto de calidad certificada",
        "Fabricado bajo estándares internacionales",
        "Compatible con múltiples modelos",
        "Garantía de satisfacción ARMOTOS"
    ]
}

def detect_category(nombre):
    """Detect SRM category from product name"""
    nombre_lower = str(nombre).lower()
    cats = {
        "freno": "Frenos", "pastilla": "Frenos", "disco": "Frenos", "banda": "Frenos",
        "cadena": "Transmision", "corona": "Transmision", "piñon": "Transmision", "pinon": "Transmision",
        "bombillo": "Iluminacion", "direccional": "Iluminacion", "faro": "Iluminacion", "led": "Iluminacion",
        "amortiguador": "Suspension", "caucho": "Suspension", "buje": "Suspension", "resorte": "Suspension",
        "aceite": "Lubricantes", "lubricante": "Lubricantes",
        "filtro": "Filtros",
        "bateria": "Electrico", "fusible": "Electrico", "relay": "Electrico", "cdi": "Electrico", "bobina": "Electrico",
        "llanta": "Llantas", "neumatico": "Llantas", "camara": "Llantas", "rin": "Llantas",
        "escape": "Escape", "exosto": "Escape", "silenciador": "Escape",
        "piston": "Motor", "biela": "Motor", "valvula": "Motor", "cilindro": "Motor",
        "guardabarro": "Carroceria", "tapa": "Carroceria", "carenaje": "Carroceria",
        "rodamiento": "Rodamientos", "balinera": "Rodamientos", "retenedor": "Rodamientos",
        "cable": "Cables", "guaya": "Cables",
        "manubrio": "Manubrio", "espejo": "Manubrio", "manigueta": "Manubrio", "puño": "Manubrio",
        "llave": "Herramientas", "destornillador": "Herramientas", "alicate": "Herramientas",
        "copa": "Herramientas", "banco": "Herramientas", "dado": "Herramientas",
    }
    for kw, cat in cats.items():
        if kw in nombre_lower:
            return cat
    return "General"

def generate_ficha_360(title, sku, price, compat, category):
    """Generate proper Ficha 360 with category-specific benefits"""
    beneficios = BENEFICIOS_SRM.get(category, BENEFICIOS_SRM["General"])

    # Build benefits HTML
    benefits_html = "\n".join([f"<li>{b}</li>" for b in beneficios])

    ficha = f"""<div class="ficha-360">
<h3>📋 Descripción</h3>
<p>{title} - Repuesto de calidad para motocicleta. Código: {sku}</p>

<h3>🔧 Información Técnica</h3>
<ul>
<li>Código: {sku}</li>
<li>Categoría: {category}</li>
<li>Condición: Nuevo</li>
</ul>

<h3>🏍️ Compatibilidad</h3>
<p>{compat if compat else 'Universal - Consultar aplicación específica'}</p>

<h3>📦 Variantes</h3>
<p>Presentación estándar. Consultar disponibilidad de colores y tamaños.</p>

<h3>✅ Beneficios</h3>
<ul>
{benefits_html}
</ul>

<h3>💡 Recomendaciones</h3>
<ul>
<li>Verificar compatibilidad con su modelo antes de instalar</li>
<li>Instalación por técnico calificado recomendada</li>
<li>Conservar empaque para referencias futuras</li>
</ul>

<h3>🏭 Proveedor</h3>
<p><strong>ARMOTOS</strong> - Repuestos de calidad para su motocicleta</p>
</div>"""
    return ficha

def load_v10_data():
    """Load V10 JSON data"""
    with open("/opt/odi/data/ARMOTOS/json/all_products.json") as f:
        products = json.load(f)

    v10_map = {}
    for p in products:
        codigo = p.get("codigo", "")
        if isinstance(codigo, list):
            for c in codigo:
                v10_map[str(c)] = p
        else:
            v10_map[str(codigo)] = p
    return v10_map

def get_shopify_products():
    """Fetch all Shopify products"""
    products = []
    url = f"https://{SHOP}/admin/api/{API_VERSION}/products.json?limit=250"

    while url:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        data = resp.json()
        products.extend(data.get("products", []))

        link = resp.headers.get("Link", "")
        url = None
        if "next" in link:
            for part in link.split(","):
                if "next" in part:
                    url = part.split(";")[0].strip().strip("<>")
                    break

    return products

def clean_price(price_str):
    """Extract first valid price from price string"""
    if not price_str:
        return None

    # Handle "$209 / $223 / $238" format - take first
    prices = re.findall(r'\$?([\d,.]+)', str(price_str))
    if prices:
        try:
            price = float(prices[0].replace(",", "").replace(".", ""))
            # Sanity check - if too low, multiply
            if price < 500:
                price = price * 1000
            return price
        except:
            pass
    return None

def main():
    print("=" * 70)
    print("ARMOTOS ISSUE FIXER")
    print("=" * 70)

    # Load data
    print("\n[1] Loading data...")
    v10_map = load_v10_data()
    print(f"    V10 products: {len(v10_map)}")

    shopify_products = get_shopify_products()
    print(f"    Shopify products: {len(shopify_products)}")

    # Identify issues
    print("\n[2] Identifying issues...")

    to_fix = []
    for p in shopify_products:
        pid = p["id"]
        title = p.get("title", "")
        body = p.get("body_html", "") or ""
        variants = p.get("variants", [])

        sku = None
        price = 0
        for v in variants:
            if v.get("sku"):
                sku = str(v.get("sku")).strip()
            price = float(v.get("price", 0))

        if not sku:
            continue

        v10_data = v10_map.get(sku, {})
        v10_nombre = v10_data.get("nombre", "")
        v10_precio = v10_data.get("precio", "")
        v10_compat = v10_data.get("compatibilidad", "")
        if isinstance(v10_compat, list):
            v10_compat = ", ".join(v10_compat)

        issues = []
        fixes = {}

        # Issue 1: Concatenated price
        if price > 1000000:
            correct_price = clean_price(v10_precio)
            if correct_price and correct_price < 1000000:
                issues.append("price_concat")
                fixes["price"] = correct_price

        # Issue 2: Short title
        clean_title = title.replace(" - Armotos", "").replace("- Armotos", "").strip()
        if len(clean_title) < 15 and v10_nombre and len(v10_nombre) > 15:
            issues.append("short_title")
            # Build better title
            new_title = v10_nombre.title()
            # Remove codes from title
            new_title = re.sub(r'\b\d{5}\b', '', new_title)
            new_title = re.sub(r'\s+', ' ', new_title).strip()
            if not new_title.lower().endswith("armotos"):
                new_title = f"{new_title} - Armotos"
            fixes["title"] = new_title

        # Issue 3: Generic benefits - regenerate body for all
        category = detect_category(v10_nombre or title)
        new_body = generate_ficha_360(
            fixes.get("title", title).replace(" - Armotos", ""),
            sku,
            fixes.get("price", price),
            v10_compat,
            category
        )
        fixes["body_html"] = new_body
        fixes["category"] = category

        if issues or True:  # Always update body for proper benefits
            to_fix.append({
                "id": pid,
                "sku": sku,
                "old_title": title,
                "old_price": price,
                "issues": issues,
                "fixes": fixes
            })

    # Filter to only those with actual issues for reporting
    with_issues = [f for f in to_fix if f["issues"]]
    print(f"    Products with price/title issues: {len(with_issues)}")
    print(f"    Total to update (benefits): {len(to_fix)}")

    # Apply fixes
    print("\n[3] Applying fixes...")
    print("-" * 70)

    results = {"price_fixed": 0, "title_fixed": 0, "body_updated": 0, "errors": 0}

    for i, item in enumerate(to_fix):
        pid = item["id"]
        fixes = item["fixes"]
        issues = item["issues"]

        update_data = {"product": {"id": pid}}

        if "price" in fixes:
            # Update variant price
            url = f"https://{SHOP}/admin/api/{API_VERSION}/products/{pid}.json"
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                product_data = resp.json().get("product", {})
                variants = product_data.get("variants", [])
                if variants:
                    var_id = variants[0]["id"]
                    var_url = f"https://{SHOP}/admin/api/{API_VERSION}/variants/{var_id}.json"
                    var_resp = requests.put(var_url, json={"variant": {"id": var_id, "price": str(fixes["price"])}}, headers=HEADERS, timeout=30)
                    if var_resp.status_code == 200:
                        results["price_fixed"] += 1

        if "title" in fixes:
            update_data["product"]["title"] = fixes["title"]
            results["title_fixed"] += 1

        if "body_html" in fixes:
            update_data["product"]["body_html"] = fixes["body_html"]

        # Update product
        url = f"https://{SHOP}/admin/api/{API_VERSION}/products/{pid}.json"
        resp = requests.put(url, json=update_data, headers=HEADERS, timeout=30)

        if resp.status_code == 200:
            results["body_updated"] += 1
        else:
            results["errors"] += 1

        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{len(to_fix)}] Updated...")

        time.sleep(0.3)

    # Summary
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"  Precios corregidos: {results['price_fixed']}")
    print(f"  Títulos corregidos: {results['title_fixed']}")
    print(f"  Body HTML actualizado: {results['body_updated']}")
    print(f"  Errores: {results['errors']}")
    print("=" * 70)

if __name__ == "__main__":
    main()
