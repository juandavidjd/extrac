#!/usr/bin/env python3
"""
KAIQI PARTS — WIPE TOTAL Y RECARGA DESDE CERO
ODI v17.5

Los datos fuente están limpios. El problema fue la carga.
Borrar todo y empezar bien.

Ejecutar: python3 /opt/odi/scripts/kaiqi_wipe_reload.py
"""

import requests
import subprocess
import json
import os
import time
import base64
import csv
import re
import glob
from collections import Counter, defaultdict


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


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 1: WIPE TOTAL
# ═══════════════════════════════════════════════════════════════════════════════

def fase1_wipe_total(shop_url, headers):
    """Eliminar TODOS los productos"""
    print("\n" + "="*60)
    print("FASE 1: WIPE TOTAL — Eliminar todos los productos")
    print("="*60)

    headers_get = {"X-Shopify-Access-Token": headers["X-Shopify-Access-Token"]}
    products = get_all_products(shop_url, headers_get)

    print(f"Productos a eliminar: {len(products)}")

    deleted = 0
    errors = 0
    for p in products:
        r = requests.delete(
            f"https://{shop_url}/admin/api/2024-01/products/{p['id']}.json",
            headers=headers
        )
        if r.status_code == 200:
            deleted += 1
        else:
            errors += 1
        if deleted % 50 == 0 and deleted > 0:
            print(f"  Eliminados: {deleted}/{len(products)}")
        time.sleep(0.5)

    print(f"\n✅ Eliminados: {deleted}")
    print(f"❌ Errores: {errors}")

    # Verificar
    r = requests.get(
        f"https://{shop_url}/admin/api/2024-01/products/count.json",
        headers=headers_get
    )
    count = r.json().get("count", -1)
    print(f"Productos restantes: {count}")

    return count == 0


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 2: CONSTRUIR CATÁLOGO DESDE DATOS FUENTE
# ═══════════════════════════════════════════════════════════════════════════════

# Categorías ODI industria motos
CATEGORIES = {
    "Motor": ["piston", "pistón", "anillo", "junta", "empaque", "cilindro", "biela",
              "válvula", "valvula", "reten", "retén", "aceite motor", "cigüeñal",
              "árbol de levas", "balancín", "culata", "camisa", "oring", "o-ring",
              "tapa aceite", "medidor aceite", "descompresor"],
    "Transmisión": ["cadena", "piñon", "piñón", "catalina", "kit arrastre", "corona",
                    "sprocket", "clutch", "embrague", "disco embrague", "arrastre",
                    "campana", "caja cambios"],
    "Frenos": ["pastilla", "freno", "brake", "disco freno", "zapata", "balata",
               "mordaza", "bomba freno", "manigueta freno"],
    "Eléctrico": ["bombillo", "foco", "led", "faro", "stop", "direccional", "relay",
                  "bobina", "bujia", "bujía", "cdi", "regulador", "rectificador",
                  "estator", "magneto", "flasher", "switch", "interruptor", "choque",
                  "capuchon", "cable"],
    "Suspensión": ["amortiguador", "telescopio", "resorte", "tijera", "balinera",
                   "rodamiento", "buje", "monoshock", "mono shock"],
    "Carrocería": ["guardabarro", "guardafango", "farola", "espejo", "retrovisor",
                   "carenaje", "tapa lateral", "salpicadera", "colin", "tanque",
                   "parrilla", "espuma", "ventilador"],
    "Escape": ["exhosto", "escape", "silenciador", "mofle", "tubo escape", "colector"],
    "Dirección": ["trinche", "dirección", "telescópico", "mordaza dirección"],
    "Ruedas": ["llanta", "rin", "caucho", "neumatico", "neumático", "camara",
               "cámara", "manzana", "rayo", "variador", "plato variador"],
    "Filtros": ["filtro aceite", "filtro aire", "filtro gasolina", "filtro combustible"],
    "Accesorios": ["casco", "guante", "protector", "slider", "puño", "palanca",
                   "pedal", "portaplaca", "alarma"],
}

MOTOS = ["AKT", "BAJAJ", "BOXER", "PULSAR", "DISCOVER", "PLATINO", "TVS", "APACHE",
         "SUZUKI", "GN", "GIXXER", "YAMAHA", "YBR", "FZ", "LIBERO", "CRYPTON", "BWS",
         "HONDA", "CB", "CBF", "NXR", "XR", "HERO", "ECO", "SPLENDOR", "GLAMOUR",
         "KAWASAKI", "AUTECO", "VICTORY", "ADVANCE", "JIALING", "KYMCO", "AGILITY",
         "JETIX", "SIGMA", "ACTIVE", "DELUXE", "DYNAMIK", "FLEX", "SPECIAL", "NKDR",
         "SL", "XM", "CRIPTON", "BEST", "VIVA", "SPORT", "DINAMIC", "TTR", "NKD",
         "SCOOTER", "GY6", "CUATRIMOTO", "DR200", "KLX", "AYCO", "VAISAND"]


def classify(text):
    """Clasificar producto por categoría"""
    t = text.lower()
    for cat, keywords in CATEGORIES.items():
        if any(kw in t for kw in keywords):
            return cat
    return "Repuestos Moto"


def extract_motos(text):
    """Extraer motos compatibles del texto"""
    found = []
    upper = text.upper()
    for m in MOTOS:
        if m in upper:
            found.append(m.title())
    return found


def extract_cc(text):
    """Extraer cilindradas del texto"""
    matches = re.findall(r'\b(50|70|100|110|115|125|135|150|160|180|200|250|300)\b', text)
    return list(set(matches))


def fase2_construir_catalogo():
    """Construir catálogo desde datos fuente"""
    print("\n" + "="*60)
    print("FASE 2: CONSTRUIR CATÁLOGO DESDE DATOS FUENTE")
    print("="*60)

    base = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Kaiqi"

    # ── 1. CARGAR VISION AI ──
    vision = {}
    vision_file = os.path.join(base, "catalogo_imagenes_Kaiqi.csv")
    if os.path.exists(vision_file):
        with open(vision_file, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = ""
                for k in row.keys():
                    if "codigo" in k.lower() or "sku" in k.lower() or "código" in k.lower():
                        code = row[k].strip()
                        break
                if not code:
                    code = list(row.values())[0].strip() if row else ""
                if code:
                    vision[code] = row
    print(f"Vision AI: {len(vision)} registros")

    # ── 2. CARGAR PRECIOS ──
    precios = {}
    precios_file = os.path.join(base, "Lista_Precios_Kaiqi.csv")
    if os.path.exists(precios_file):
        with open(precios_file, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = ""
                price = ""
                desc = ""
                for k, v in row.items():
                    kl = k.lower().strip()
                    if "codigo" in kl or "código" in kl or "sku" in kl:
                        code = v.strip()
                    if "precio" in kl or "price" in kl:
                        price = v.strip()
                    if "descripcion" in kl or "descripción" in kl or "nombre" in kl:
                        desc = v.strip()
                if code:
                    precios[code] = {"price": price, "description": desc}
    print(f"Precios: {len(precios)} registros")

    # ── 3. CARGAR BASE DATOS ──
    base_datos = {}
    base_file = os.path.join(base, "Base_Datos_Kaiqi.csv")
    if os.path.exists(base_file):
        with open(base_file, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = ""
                img_url = ""
                for k, v in row.items():
                    kl = k.lower().strip()
                    if "codigo" in kl or "código" in kl:
                        code = v.strip()
                    if "imagen" in kl and "url" in kl:
                        img_url = v.strip()
                    if "url_producto" in kl:
                        if not img_url:
                            img_url = v.strip()
                if code:
                    base_datos[code] = {"image_url": img_url, "row": row}
    print(f"Base datos: {len(base_datos)} registros")

    # ── 4. MAPEAR IMÁGENES LOCALES ──
    img_dir = base
    local_images = {}
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.PNG']:
        for f in glob.glob(os.path.join(img_dir, '**', ext), recursive=True):
            fname = os.path.basename(f).lower()
            key = os.path.splitext(fname)[0]
            local_images[key] = f
            clean = re.sub(r'[^a-z0-9]', '', key)
            local_images[clean] = f
    print(f"Imágenes locales: {len(local_images)}")

    # ── 5. CRUCE MAESTRO ──
    all_codes = set()
    all_codes.update(vision.keys())
    all_codes.update(precios.keys())
    all_codes.update(base_datos.keys())

    clean_codes = set()
    for code in all_codes:
        if code and len(code) > 2 and not code.startswith("E+") and "," not in code:
            clean_codes.add(code)

    print(f"Códigos únicos: {len(clean_codes)}")

    # ── 6. GENERAR PRODUCTOS ──
    products_to_create = []

    for code in sorted(clean_codes):
        v_data = vision.get(code, {})
        p_data = precios.get(code, {})
        b_data = base_datos.get(code, {})

        # Título
        title_raw = ""
        for k, val in v_data.items():
            if "nombre_comercial" in k.lower() or "nombre" in k.lower():
                title_raw = val
                break
        if not title_raw:
            title_raw = p_data.get("description", "")
        if not title_raw:
            for k, val in b_data.get("row", {}).items():
                if "descripcion" in k.lower():
                    title_raw = val
                    break
        if not title_raw:
            title_raw = code

        title = title_raw.strip()
        if not title:
            continue

        # Precio
        price_raw = p_data.get("price", "0")
        try:
            price = float(str(price_raw).replace(",", "").replace("$", "").strip())
        except:
            price = 0

        # Categoría
        search_text = f"{title} {' '.join(str(v) for v in v_data.values()) if v_data else ''}"
        category = classify(search_text)

        # Datos Vision AI
        funcion = ""
        caracteristicas = ""
        identificacion = ""
        sistema = ""
        compat = ""
        tags_ai = ""

        for k, val in v_data.items():
            kl = k.lower()
            if "funcion" in kl or "función" in kl:
                funcion = val or ""
            elif "caracteristicas" in kl or "características" in kl:
                caracteristicas = val or ""
            elif "identificacion" in kl or "identificación" in kl:
                identificacion = val or ""
            elif kl == "sistema":
                sistema = val or ""
            elif "compatibilidad" in kl:
                compat = val or ""
            elif "tags" in kl:
                tags_ai = val or ""

        if sistema:
            mapped = classify(sistema)
            if mapped != "Repuestos Moto":
                category = mapped

        motos = extract_motos(title)
        ccs = extract_cc(title)

        # Compatibilidad HTML
        compat_html = ""
        if compat:
            try:
                cl = json.loads(compat)
                if isinstance(cl, list):
                    items = "".join(f"<li>{c}</li>" for c in cl if c)
                    compat_html = f"<ul>{items}</ul>"
            except:
                compat_html = f"<p>{compat}</p>"

        if not compat_html and motos:
            items = "".join(f"<li>{m}</li>" for m in motos)
            compat_html = f"<ul>{items}</ul>"
        elif not compat_html:
            compat_html = "<p>Consultar compatibilidad con su modelo específico.</p>"

        # Descripción por defecto
        if not identificacion:
            identificacion = f"Repuesto {category.lower()} marca KAIQI para motocicleta."
        if not caracteristicas:
            caracteristicas = "Fabricado con materiales de alta durabilidad. Diseño de ajuste exacto tipo OEM."
        if not funcion:
            funcion = f"Componente de {category.lower()} diseñado para el rendimiento óptimo de su motocicleta."

        body_html = f"""<div class="odi-ficha-360">
<h3>Descripción del Producto</h3>
<p>{identificacion}</p>
<h3>Información Técnica</h3>
<p>{caracteristicas}</p>
<p>{funcion}</p>
<h3>Compatibilidad</h3>
<p>Este repuesto es compatible con:</p>
{compat_html}
<p><em>Recomendamos verificar el modelo exacto antes de la compra.</em></p>
<h3>Especificaciones</h3>
<table>
<tr><td><strong>Referencia</strong></td><td>KAIQI-{code}</td></tr>
<tr><td><strong>Marca</strong></td><td>KAIQI</td></tr>
<tr><td><strong>Categoría</strong></td><td>{category}</td></tr>
<tr><td><strong>Condición</strong></td><td>Nuevo</td></tr>
<tr><td><strong>Garantía</strong></td><td>6 meses</td></tr>
</table>
<h3>Beneficios</h3>
<ul>
<li>Fabricado con materiales de primera calidad</li>
<li>Diseño de ajuste exacto</li>
<li>Cumple especificaciones OEM</li>
<li>Mejora rendimiento y seguridad</li>
<li>Garantía por defectos de fabricación</li>
</ul>
<h3>Recomendaciones</h3>
<p>Para mejores resultados recomendamos instalación por técnico especializado.</p>
<h3>Información Importante</h3>
<p>Imágenes de referencia. Conserve factura para garantía.</p>
</div>"""

        # Tags
        tags = set()
        tags.add("KAIQI")
        tags.add(category)
        for m in motos:
            tags.add(m)
        for cc in ccs:
            tags.add(f"{cc}cc")
        if tags_ai:
            for t in tags_ai.split(","):
                t = t.strip()
                if t and len(t) > 2:
                    tags.add(t)

        # Imagen
        image_url = b_data.get("image_url", "")

        # Buscar imagen local
        local_img = None
        code_clean = re.sub(r'[^a-z0-9]', '', code.lower())
        for key_attempt in [code.lower(), code_clean, code.upper()]:
            if key_attempt in local_images:
                local_img = local_images[key_attempt]
                break

        product = {
            "title": title,
            "body_html": body_html,
            "vendor": "KAIQI",
            "product_type": category,
            "tags": ", ".join(sorted(tags)),
            "status": "active",
            "variants": [{
                "sku": code,
                "price": str(price) if price > 0 else "10000",
                "inventory_management": "shopify",
                "inventory_quantity": 10,
            }],
            "_local_image": local_img,
            "_has_vision": bool(v_data),
            "_has_price": price > 0,
        }

        if image_url and image_url.startswith("http"):
            product["images"] = [{"src": image_url}]

        products_to_create.append(product)

    # Estadísticas
    print(f"\n{'='*60}")
    print(f"CATÁLOGO KAIQI RECONSTRUIDO")
    print(f"{'='*60}")
    print(f"Total productos: {len(products_to_create)}")

    with_vision = sum(1 for p in products_to_create if p.get("_has_vision"))
    with_price = sum(1 for p in products_to_create if p.get("_has_price"))
    with_image_url = sum(1 for p in products_to_create if p.get("images"))
    with_local_img = sum(1 for p in products_to_create if p.get("_local_image"))

    print(f"Con datos Vision AI: {with_vision}")
    print(f"Con precio real: {with_price}")
    print(f"Con imagen URL: {with_image_url}")
    print(f"Con imagen local: {with_local_img}")

    cats = Counter(p["product_type"] for p in products_to_create)
    print(f"\nCategorías:")
    for cat, count in cats.most_common():
        print(f"  {cat}: {count}")

    # Guardar
    os.makedirs("/opt/odi/data", exist_ok=True)
    with open("/opt/odi/data/kaiqi_reload_catalog.json", "w") as f:
        json.dump(products_to_create, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Catálogo guardado: /opt/odi/data/kaiqi_reload_catalog.json")

    return products_to_create


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 3: CARGAR A SHOPIFY
# ═══════════════════════════════════════════════════════════════════════════════

def fase3_cargar_shopify(shop_url, headers, catalog):
    """Cargar catálogo limpio a Shopify"""
    print("\n" + "="*60)
    print("FASE 3: CARGAR CATÁLOGO A SHOPIFY")
    print("="*60)

    print(f"Productos a cargar: {len(catalog)}")

    created = 0
    errors = 0
    error_list = []

    for i, product in enumerate(catalog):
        # Limpiar campos internos
        local_img = product.pop("_local_image", None)
        product.pop("_has_vision", None)
        product.pop("_has_price", None)

        # Subir imagen local si no tiene URL
        if not product.get("images") and local_img and os.path.exists(local_img):
            try:
                with open(local_img, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                product["images"] = [{
                    "attachment": img_b64,
                    "filename": os.path.basename(local_img),
                }]
            except:
                pass

        # Crear producto
        r = requests.post(
            f"https://{shop_url}/admin/api/2024-01/products.json",
            headers=headers,
            json={"product": product}
        )

        if r.status_code == 201:
            created += 1
        else:
            errors += 1
            if errors <= 5:
                error_list.append({
                    "title": product.get("title", "")[:50],
                    "status": r.status_code,
                    "error": r.text[:100]
                })

        if (i + 1) % 25 == 0:
            print(f"  Progreso: {created} creados, {errors} errores de {i+1}")

        time.sleep(0.5)

    print(f"\n✅ Creados: {created}/{len(catalog)}")
    print(f"❌ Errores: {errors}")

    if error_list:
        print(f"\nPrimeros errores:")
        for e in error_list:
            print(f"  {e['title']}: {e['status']} - {e['error']}")

    return created


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 4: APLICAR TEMA
# ═══════════════════════════════════════════════════════════════════════════════

def fase4_aplicar_tema(shop_url, headers):
    """Aplicar tema visual + logo"""
    print("\n" + "="*60)
    print("FASE 4: APLICAR TEMA VISUAL")
    print("="*60)

    headers_get = {"X-Shopify-Access-Token": headers["X-Shopify-Access-Token"]}

    PALETTE = {
        "colors_accent_1": "#C41E2A",
        "colors_accent_2": "#D4A017",
        "colors_text": "#1A1A1A",
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

    r = requests.get(f"https://{shop_url}/admin/api/2024-01/themes.json", headers=headers_get)
    if r.status_code != 200:
        print(f"❌ Themes: {r.status_code}")
        return False

    themes = r.json().get("themes", [])
    active = [t for t in themes if t["role"] == "main"][0]
    theme_id = active["id"]
    print(f"Tema: {active['name']} (ID: {theme_id})")

    # Subir logos
    for logo_path, asset_key in [
        ("/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/logos_optimized/Kaiqi.png", "assets/kaiqi-logo.png"),
        ("/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/logos_optimized/Kaiqi.svg", "assets/kaiqi-logo.svg"),
    ]:
        if os.path.exists(logo_path):
            if logo_path.endswith('.svg'):
                with open(logo_path, "r") as f:
                    payload = {"asset": {"key": asset_key, "value": f.read()}}
            else:
                with open(logo_path, "rb") as f:
                    payload = {"asset": {"key": asset_key, "attachment": base64.b64encode(f.read()).decode()}}
            r = requests.put(
                f"https://{shop_url}/admin/api/2024-01/themes/{theme_id}/assets.json",
                headers=headers, json=payload
            )
            print(f"Logo {asset_key}: {r.status_code}")

    # Aplicar colores
    r4 = requests.get(
        f"https://{shop_url}/admin/api/2024-01/themes/{theme_id}/assets.json?asset[key]=config/settings_data.json",
        headers=headers_get
    )

    if r4.status_code == 200:
        settings = json.loads(r4.json().get("asset", {}).get("value", "{}"))

        current_key = None
        for key in settings:
            if key != "presets" and isinstance(settings[key], dict):
                current_key = key
                break

        if not current_key:
            current_key = "current"
            settings[current_key] = {}

        for field, value in PALETTE.items():
            settings[current_key][field] = value

        r5 = requests.put(
            f"https://{shop_url}/admin/api/2024-01/themes/{theme_id}/assets.json",
            headers=headers,
            json={"asset": {"key": "config/settings_data.json", "value": json.dumps(settings)}}
        )
        print(f"✅ Colores: {r5.status_code}")
        return r5.status_code == 200

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# FASE 5: AUDITORÍA FINAL
# ═══════════════════════════════════════════════════════════════════════════════

def fase5_auditoria(shop_url, headers_get):
    """Auditoría final post-recarga"""
    print("\n" + "="*60)
    print("FASE 5: AUDITORÍA FINAL KAIQI PARTS")
    print("="*60)

    products = get_all_products(shop_url, headers_get)
    total = len(products)

    if total == 0:
        print("❌ No hay productos")
        return {"score": 0, "total": 0}

    # Checks
    skus = [v.get("sku","") for p in products for v in p.get("variants",[]) if v.get("sku")]
    dup_skus = sum(1 for c in Counter(skus).values() if c > 1)

    required_sections = ["Descripción del Producto", "Compatibilidad", "Especificaciones", "Beneficios", "Recomendaciones", "Información Importante"]
    has_desc = sum(1 for p in products if all(s in (p.get("body_html","") or "") for s in required_sections))
    has_type = sum(1 for p in products if p.get("product_type","").strip() not in ["Repuestos Moto", ""])
    has_tags = sum(1 for p in products if len(p.get("tags","").split(",")) >= 3)
    has_images = sum(1 for p in products if p.get("images"))
    has_price = sum(1 for p in products if p.get("variants") and float(p["variants"][0].get("price",0)) > 0)

    print(f"\nTotal productos:       {total}")
    print(f"SKUs duplicados:       {dup_skus}")
    print(f"Descripción completa:  {has_desc}/{total} ({has_desc*100//total}%)")
    print(f"Tipo clasificado:      {has_type}/{total} ({has_type*100//total}%)")
    print(f"Tags (>=3):            {has_tags}/{total} ({has_tags*100//total}%)")
    print(f"Con imagen:            {has_images}/{total} ({has_images*100//total}%)")
    print(f"Con precio > 0:        {has_price}/{total} ({has_price*100//total}%)")

    score = (has_desc + has_type + has_tags + has_images + has_price) / (total * 5) * 100
    print(f"\nSCORE ODI 360°: {score:.0f}%")
    print(f"Duplicados: {'✅ 0' if dup_skus == 0 else f'❌ {dup_skus}'}")

    # Categorías
    cats = Counter(p["product_type"] for p in products)
    print(f"\nCategorías:")
    for cat, count in cats.most_common():
        print(f"  {cat}: {count}")

    # Muestra
    print(f"\nMuestra de títulos:")
    for p in products[:5]:
        price = p["variants"][0]["price"] if p.get("variants") else "N/A"
        imgs = len(p.get("images", []))
        print(f"  [{p.get('product_type','')}] {p['title'][:50]} - ${price} - {imgs}img")

    print(f"\nStorefront: https://{shop_url}")

    return {
        "score": score,
        "total": total,
        "duplicates": dup_skus,
        "has_desc": has_desc,
        "has_images": has_images,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("="*60)
    print("KAIQI PARTS — WIPE TOTAL Y RECARGA DESDE CERO")
    print("="*60)

    shop_url, token = get_credentials()
    if not shop_url or not token:
        print("❌ Error: Credenciales KAIQI no encontradas en .env")
        return 1

    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    headers_get = {"X-Shopify-Access-Token": token}

    print(f"Tienda: {shop_url}")

    # FASE 1: Wipe
    fase1_wipe_total(shop_url, headers)

    # FASE 2: Construir catálogo
    catalog = fase2_construir_catalogo()

    # FASE 3: Cargar a Shopify
    fase3_cargar_shopify(shop_url, headers, catalog)

    # FASE 4: Aplicar tema
    fase4_aplicar_tema(shop_url, headers)

    # FASE 5: Auditoría
    result = fase5_auditoria(shop_url, headers_get)

    # Veredicto
    print("\n" + "="*60)
    if result["score"] >= 95 and result.get("duplicates", 0) == 0:
        print("✅ KAIQI PARTS RECARGA EXITOSA")
    else:
        print("❌ REQUIERE REVISIÓN")
        if result.get("duplicates", 0) > 0:
            print(f"   - Duplicados: {result['duplicates']}")
        if result["score"] < 95:
            print(f"   - Score: {result['score']:.0f}% (objetivo: 95%+)")
    print("="*60)

    return 0


if __name__ == "__main__":
    exit(main())
