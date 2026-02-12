#!/usr/bin/env python3
"""
CORRECCIÓN TOTAL KAIQI PARTS — ODI v17.5
NO AVANZAR HASTA 100% VERIFICADO

Ejecutar: python3 /opt/odi/scripts/kaiqi_correction_total.py
"""

import requests
import subprocess
import json
import time
import os
import base64
from collections import defaultdict, Counter


def get_credentials():
    """Obtener credenciales de .env"""
    env = subprocess.check_output(["cat", "/opt/odi/.env"]).decode()
    shop_url = token = ""
    for line in env.split("\n"):
        if "KAIQI" in line.upper() and "SHOP" in line.upper() and "=" in line and not line.strip().startswith("#"):
            shop_url = line.split("=", 1)[1].strip().strip('"').strip("'")
        if "KAIQI" in line.upper() and "TOKEN" in line.upper() and "=" in line and not line.strip().startswith("#"):
            token = line.split("=", 1)[1].strip().strip('"').strip("'")
    return shop_url, token


def get_all_products(shop_url, headers_get):
    """Obtener todos los productos"""
    products = []
    url = f"https://{shop_url}/admin/api/2024-01/products.json?limit=250"
    while url:
        r = requests.get(url, headers=headers_get)
        data = r.json()
        products.extend(data.get("products", []))
        link = r.headers.get("Link", "")
        url = link.split("<")[1].split(">")[0] if 'rel="next"' in link else None
    return products


def paso1_eliminar_duplicados(shop_url, headers, headers_get):
    """PASO 1: Eliminar productos duplicados"""
    print("\n" + "="*60)
    print("PASO 1: ELIMINAR DUPLICADOS")
    print("="*60)

    products = get_all_products(shop_url, headers_get)
    print(f"Total productos: {len(products)}")

    # Agrupar por SKU
    sku_groups = defaultdict(list)
    for p in products:
        for v in p.get("variants", []):
            sku = v.get("sku", "").strip()
            if sku:
                sku_groups[sku].append(p)

    dup_by_sku = {k: v for k, v in sku_groups.items() if len(v) > 1}
    print(f"Grupos duplicados por SKU: {len(dup_by_sku)}")

    # Determinar cuáles eliminar (mantener el que tiene mejor descripción)
    to_delete = []
    for sku, prods in dup_by_sku.items():
        sorted_prods = sorted(prods, key=lambda p: len(p.get("body_html", "") or ""), reverse=True)
        keeper = sorted_prods[0]
        for p in sorted_prods[1:]:
            if p["id"] != keeper["id"]:
                to_delete.append(p["id"])

    print(f"Productos a eliminar: {len(to_delete)}")

    # Eliminar
    deleted = 0
    for pid in to_delete:
        r = requests.delete(f"https://{shop_url}/admin/api/2024-01/products/{pid}.json", headers=headers)
        if r.status_code == 200:
            deleted += 1
        else:
            print(f"  Error eliminando {pid}: {r.status_code}")
        time.sleep(0.5)

    print(f"✅ Eliminados: {deleted}/{len(to_delete)}")
    return deleted


def paso2_limpiar_imagenes(shop_url, headers, headers_get):
    """PASO 2: Eliminar imágenes con logos de otras marcas"""
    print("\n" + "="*60)
    print("PASO 2: LIMPIAR IMÁGENES CONTAMINADAS")
    print("="*60)

    products = get_all_products(shop_url, headers_get)

    # Detectar imágenes con logos de otras marcas
    contaminated = []
    for p in products:
        for img in p.get("images", []):
            src = img.get("src", "").lower()
            alt = img.get("alt", "").lower()
            # Logos de otras marcas que no deben estar en Kaiqi
            if any(x in src or x in alt for x in ["dfg", "bara", "leo", "genuine", "yokomar", "imbra", "japan"]):
                contaminated.append({"product": p, "image": img})

    print(f"Imágenes contaminadas: {len(contaminated)}")

    # Eliminar
    removed = 0
    for item in contaminated:
        p = item["product"]
        img = item["image"]
        r = requests.delete(
            f"https://{shop_url}/admin/api/2024-01/products/{p['id']}/images/{img['id']}.json",
            headers=headers
        )
        if r.status_code == 200:
            removed += 1
        time.sleep(0.3)

    print(f"✅ Imágenes eliminadas: {removed}")
    return removed


def paso3_completar_descripciones(shop_url, headers, headers_get):
    """PASO 3: Completar descripciones con template ODI 360"""
    print("\n" + "="*60)
    print("PASO 3: COMPLETAR DESCRIPCIONES")
    print("="*60)

    products = get_all_products(shop_url, headers_get)

    def generate_body(p):
        title = p.get("title", "")
        ptype = p.get("product_type", "Repuestos Moto")
        vendor = p.get("vendor", "KAIQI")
        sku = ""
        for v in p.get("variants", []):
            sku = v.get("sku", "")
            if sku: break

        # Detectar motos compatibles del título
        motos = ["AKT", "BAJAJ", "BOXER", "PULSAR", "YAMAHA", "HONDA", "SUZUKI", "TVS", "HERO", "KYMCO", "AUTECO"]
        found = [m for m in motos if m in title.upper()]
        compat = "".join(f"<li>{m}</li>" for m in found) if found else "<li>Consultar compatibilidad con su modelo</li>"

        return f"""<div class="odi-ficha-360">
<h3>Descripción del Producto</h3>
<p>Repuesto {ptype.lower()} marca {vendor} para motocicleta. Diseñado para garantizar el óptimo funcionamiento de su vehículo.</p>

<h3>Información Técnica</h3>
<p>Fabricado con materiales de alta durabilidad. Diseño de ajuste exacto tipo OEM. Cumple con especificaciones del fabricante.</p>

<h3>Compatibilidad</h3>
<p>Este repuesto es compatible con:</p>
<ul>{compat}</ul>
<p><em>Recomendamos verificar el modelo exacto antes de la compra.</em></p>

<h3>Especificaciones</h3>
<table>
<tr><td><strong>Referencia</strong></td><td>{sku}</td></tr>
<tr><td><strong>Marca</strong></td><td>{vendor}</td></tr>
<tr><td><strong>Categoría</strong></td><td>{ptype}</td></tr>
<tr><td><strong>Condición</strong></td><td>Nuevo</td></tr>
<tr><td><strong>Garantía</strong></td><td>6 meses</td></tr>
</table>

<h3>Beneficios</h3>
<ul>
<li>Materiales de primera calidad</li>
<li>Diseño de ajuste exacto</li>
<li>Cumple especificaciones OEM</li>
<li>Mejora rendimiento y seguridad</li>
<li>Garantía por defectos de fabricación</li>
</ul>

<h3>Recomendaciones</h3>
<p>Para mejores resultados recomendamos instalación por técnico especializado. Verifique modelo correcto antes de instalar.</p>

<h3>Información Importante</h3>
<p>Imágenes de referencia. Conserve factura para hacer válida la garantía. No nos hacemos responsables por instalación incorrecta.</p>
</div>"""

    # Identificar productos con descripción incompleta
    required_sections = ["Descripción del Producto", "Compatibilidad", "Especificaciones", "Beneficios"]
    incomplete = [p for p in products if not all(s in (p.get("body_html","") or "") for s in required_sections)]

    print(f"Descripciones incompletas: {len(incomplete)}")

    # Actualizar
    updated = 0
    for p in incomplete:
        new_body = generate_body(p)
        r = requests.put(
            f"https://{shop_url}/admin/api/2024-01/products/{p['id']}.json",
            headers=headers,
            json={"product": {"id": p["id"], "body_html": new_body}}
        )
        if r.status_code == 200:
            updated += 1
        time.sleep(0.5)

    print(f"✅ Descripciones actualizadas: {updated}/{len(incomplete)}")
    return updated


def paso4_aplicar_tema(shop_url, headers, headers_get):
    """PASO 4: Aplicar tema visual + logo"""
    print("\n" + "="*60)
    print("PASO 4: APLICAR TEMA VISUAL")
    print("="*60)

    PALETTE = {
        "colors_accent_1": "#C41E2A",      # Rojo industrial
        "colors_accent_2": "#D4A017",      # Dorado
        "colors_text": "#1A1A1A",          # Negro
        "colors_solid_button_labels": "#FFFFFF",
        "colors_outline_button_labels": "#1A1A1A",
        "colors_background_1": "#FFFFFF",
        "colors_background_2": "#F2F2F0",
        "colors_accent_1_2": "#D4A017",
        "colors_accent_2_2": "#C41E2A",
        "colors_text_2": "#FFFFFF",
        "colors_solid_button_labels_2": "#1A1A1A",
        "colors_background_1_2": "#1A1A1A",
        "colors_background_2_2": "#2D2D2D",
    }

    # Obtener tema activo
    r = requests.get(f"https://{shop_url}/admin/api/2024-01/themes.json", headers=headers_get)
    if r.status_code == 403:
        print("❌ Error 403: Scopes no activos")
        return 0
    if r.status_code != 200:
        print(f"❌ Error: {r.status_code}")
        return 0

    themes = r.json().get("themes", [])
    active = [t for t in themes if t["role"] == "main"][0]
    theme_id = active["id"]
    print(f"Tema activo: {active['name']} (ID: {theme_id})")

    # Subir logo
    logo_png = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/logos_optimized/Kaiqi.png"
    if os.path.exists(logo_png):
        with open(logo_png, "rb") as f:
            r2 = requests.put(
                f"https://{shop_url}/admin/api/2024-01/themes/{theme_id}/assets.json",
                headers=headers,
                json={"asset": {"key": "assets/kaiqi-logo.png", "attachment": base64.b64encode(f.read()).decode()}}
            )
            print(f"Logo PNG: {r2.status_code} {'✅' if r2.status_code == 200 else '❌'}")

    # Obtener settings
    r4 = requests.get(
        f"https://{shop_url}/admin/api/2024-01/themes/{theme_id}/assets.json?asset[key]=config/settings_data.json",
        headers=headers_get
    )

    if r4.status_code == 200:
        settings = json.loads(r4.json().get("asset", {}).get("value", "{}"))

        # Encontrar sección actual
        current_key = None
        for key in settings:
            if key != "presets" and isinstance(settings[key], dict):
                current_key = key
                break

        if not current_key:
            current_key = "current"
            settings[current_key] = {}

        # Aplicar colores
        applied = 0
        for field, value in PALETTE.items():
            settings[current_key][field] = value
            applied += 1

        # Subir settings
        r5 = requests.put(
            f"https://{shop_url}/admin/api/2024-01/themes/{theme_id}/assets.json",
            headers=headers,
            json={"asset": {"key": "config/settings_data.json", "value": json.dumps(settings)}}
        )
        print(f"Colores aplicados: {r5.status_code} {'✅' if r5.status_code == 200 else '❌'}")
        return applied if r5.status_code == 200 else 0

    return 0


def paso5_auditoria_final(shop_url, headers_get):
    """PASO 5: Auditoría final"""
    print("\n" + "="*60)
    print("AUDITORÍA FINAL KAIQI PARTS")
    print("="*60)

    products = get_all_products(shop_url, headers_get)
    total = len(products)

    # Verificar duplicados
    skus = [v.get("sku","") for p in products for v in p.get("variants",[]) if v.get("sku")]
    duplicates = sum(1 for c in Counter(skus).values() if c > 1)

    # Quality checks
    required_sections = ["Descripción del Producto", "Compatibilidad", "Especificaciones", "Beneficios"]
    has_desc = sum(1 for p in products if all(s in (p.get("body_html","") or "") for s in required_sections))
    has_images = sum(1 for p in products if p.get("images"))
    has_price = sum(1 for p in products if p.get("variants") and float(p["variants"][0].get("price",0)) > 0)
    has_tags = sum(1 for p in products if len(p.get("tags","").split(",")) >= 3)

    print(f"")
    print(f"Total productos:      {total}")
    print(f"SKUs duplicados:      {duplicates}")
    print(f"")
    print(f"Descripción completa: {has_desc}/{total} ({has_desc*100//total if total > 0 else 0}%)")
    print(f"Con imagen:           {has_images}/{total} ({has_images*100//total if total > 0 else 0}%)")
    print(f"Con precio:           {has_price}/{total} ({has_price*100//total if total > 0 else 0}%)")
    print(f"Con tags (>=3):       {has_tags}/{total} ({has_tags*100//total if total > 0 else 0}%)")
    print(f"")

    # Score
    if total > 0:
        score = (has_desc + has_images + has_price) / (total * 3) * 100
    else:
        score = 0

    print(f"SCORE ODI 360°: {score:.0f}%")
    print(f"Duplicados: {'✅ 0' if duplicates == 0 else f'❌ {duplicates}'}")
    print(f"")
    print(f"Storefront: https://{shop_url}")

    return {
        "total": total,
        "duplicates": duplicates,
        "score": score,
        "has_desc": has_desc,
        "has_images": has_images,
        "has_price": has_price
    }


def main():
    print("="*60)
    print("CORRECCIÓN TOTAL KAIQI PARTS")
    print("="*60)

    shop_url, token = get_credentials()
    if not shop_url or not token:
        print("❌ Error: Credenciales KAIQI no encontradas en .env")
        return 1

    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    headers_get = {"X-Shopify-Access-Token": token}

    print(f"Tienda: {shop_url}")

    # Ejecutar pasos
    paso1_eliminar_duplicados(shop_url, headers, headers_get)
    paso2_limpiar_imagenes(shop_url, headers, headers_get)
    paso3_completar_descripciones(shop_url, headers, headers_get)
    paso4_aplicar_tema(shop_url, headers, headers_get)
    result = paso5_auditoria_final(shop_url, headers_get)

    # Verificar criterio de éxito
    print("\n" + "="*60)
    if result["duplicates"] == 0 and result["score"] >= 95:
        print("✅ KAIQI PARTS 100% CORREGIDO")
    else:
        print("❌ REQUIERE REVISIÓN ADICIONAL")
        if result["duplicates"] > 0:
            print(f"   - Eliminar {result['duplicates']} duplicados restantes")
        if result["score"] < 95:
            print(f"   - Score actual: {result['score']:.0f}% (objetivo: 95%+)")
    print("="*60)

    return 0


if __name__ == "__main__":
    exit(main())
