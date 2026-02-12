#!/usr/bin/env python3
"""
KAIQI PARTS — Aplicar tema visual profesional
Paleta: Industria motos, sobrio, profesional
Logo monocromático + colores de empaque refinados

Ejecutar en servidor: python3 /opt/odi/scripts/kaiqi-theme-apply.py
"""

import requests
import subprocess
import json
import os
import base64
import time

# ── PALETA KAIQI PARTS ──
# Industria motos: sobrio, profesional, natural
# Logo monocromático + colores de empaque refinados
PALETTE = {
    "primary": "#1A1A1A",       # Negro carbón (logo)
    "accent_1": "#C41E2A",      # Rojo industrial (empaque, sobrio)
    "accent_2": "#D4A017",      # Dorado apagado (empaque, profesional)
    "text": "#1A1A1A",          # Negro para texto
    "text_light": "#FFFFFF",    # Blanco para texto sobre oscuro
    "bg_1": "#FFFFFF",          # Fondo principal limpio
    "bg_2": "#F2F2F0",          # Fondo secundario (gris cálido)
    "dark_bg": "#1A1A1A",       # Fondo oscuro (header/footer)
    "dark_bg_2": "#2D2D2D",     # Fondo oscuro secundario
    "outline": "#4A4A4A",       # Gris acero para bordes
}

def main():
    # Credenciales
    env = subprocess.check_output(["cat", "/opt/odi/.env"]).decode()
    shop_url = token = ""
    for line in env.split("\n"):
        if "KAIQI" in line.upper() and "SHOP" in line.upper() and "=" in line and not line.strip().startswith("#"):
            shop_url = line.split("=", 1)[1].strip().strip('"').strip("'")
        if "KAIQI" in line.upper() and "TOKEN" in line.upper() and "=" in line and not line.strip().startswith("#"):
            token = line.split("=", 1)[1].strip().strip('"').strip("'")

    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    headers_get = {"X-Shopify-Access-Token": token}

    print("=== PALETA KAIQI PARTS (Industria Motos) ===")
    for k, v in PALETTE.items():
        print(f"  {k}: {v}")

    # ── 1. OBTENER TEMA ACTIVO ──
    print("\n=== CONECTANDO A SHOPIFY ===")
    r = requests.get(f"https://{shop_url}/admin/api/2024-01/themes.json", headers=headers_get)
    print(f"Themes API: {r.status_code}")

    if r.status_code == 403:
        print("❌ Aún sin scope. ¿Publicaste la nueva versión de ODI Manager?")
        print("   1. Click 'Publicar' en dev.shopify.com")
        print("   2. Ir a la tienda → Apps → ODI Manager → Reinstalar")
        print("   3. Si el token cambió, actualizar /opt/odi/.env")
        return 1

    if r.status_code != 200:
        print(f"Error: {r.status_code} {r.text[:200]}")
        return 1

    themes = r.json().get("themes", [])
    active = [t for t in themes if t["role"] == "main"][0]
    theme_id = active["id"]
    print(f"Tema activo: {active['name']} (ID: {theme_id})")

    # ── 2. SUBIR LOGO ──
    print("\n=== SUBIENDO LOGO ===")
    logo_png = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/logos_optimized/Kaiqi.png"
    logo_svg = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/logos_optimized/Kaiqi.svg"

    logo_png_url = ""

    # Subir PNG
    if os.path.exists(logo_png):
        with open(logo_png, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        r2 = requests.put(
            f"https://{shop_url}/admin/api/2024-01/themes/{theme_id}/assets.json",
            headers=headers,
            json={"asset": {"key": "assets/kaiqi-logo.png", "attachment": logo_b64}}
        )
        print(f"Logo PNG: {r2.status_code} {'✅' if r2.status_code == 200 else '❌'}")
        if r2.status_code == 200:
            logo_png_url = r2.json().get("asset", {}).get("public_url", "")
            print(f"  URL: {logo_png_url}")
    else:
        print(f"Logo PNG no encontrado: {logo_png}")

    # Subir SVG
    if os.path.exists(logo_svg):
        with open(logo_svg, "r") as f:
            svg_content = f.read()
        r3 = requests.put(
            f"https://{shop_url}/admin/api/2024-01/themes/{theme_id}/assets.json",
            headers=headers,
            json={"asset": {"key": "assets/kaiqi-logo.svg", "value": svg_content}}
        )
        print(f"Logo SVG: {r3.status_code} {'✅' if r3.status_code == 200 else '❌'}")
    else:
        print(f"Logo SVG no encontrado: {logo_svg}")

    # ── 3. OBTENER Y MODIFICAR SETTINGS ──
    print("\n=== MODIFICANDO TEMA ===")
    r4 = requests.get(
        f"https://{shop_url}/admin/api/2024-01/themes/{theme_id}/assets.json?asset[key]=config/settings_data.json",
        headers=headers_get
    )
    if r4.status_code != 200:
        print(f"Error obteniendo settings: {r4.status_code}")
        return 1

    settings_raw = r4.json().get("asset", {}).get("value", "{}")
    settings = json.loads(settings_raw)

    # Encontrar sección actual
    current = None
    current_key = None
    for key in settings:
        if key != "presets" and isinstance(settings[key], dict):
            current = settings[key]
            current_key = key
            break

    if not current:
        current = settings.get("current", {})
        current_key = "current"

    print(f"Settings key: {current_key}")
    print(f"Campos disponibles: {len(current)}")

    # Listar campos de color existentes para debug
    color_fields = sorted([k for k in current.keys() if "color" in k.lower()])
    print(f"Campos de color encontrados: {len(color_fields)}")
    for cf in color_fields:
        print(f"  {cf}: {current[cf]}")

    # ── 4. APLICAR COLORES (adaptado a estructura Horizon) ──
    # Esquema 1 (secciones claras - mayoría de la tienda)
    scheme1_mapping = {
        "colors_accent_1": PALETTE["accent_1"],         # Rojo industrial
        "colors_accent_2": PALETTE["accent_2"],          # Dorado apagado
        "colors_text": PALETTE["text"],                  # Negro
        "colors_solid_button_labels": PALETTE["text_light"],  # Blanco en botones
        "colors_outline_button_labels": PALETTE["text"],      # Negro en bordes
        "colors_background_1": PALETTE["bg_1"],          # Blanco
        "colors_background_2": PALETTE["bg_2"],          # Gris cálido
    }

    # Esquema 2 (secciones oscuras - header, footer, destacados)
    scheme2_mapping = {
        "colors_accent_1_2": PALETTE["accent_2"],        # Dorado en oscuro
        "colors_accent_2_2": PALETTE["accent_1"],        # Rojo en oscuro
        "colors_text_2": PALETTE["text_light"],           # Blanco
        "colors_solid_button_labels_2": PALETTE["dark_bg"],  # Negro en botones
        "colors_outline_button_labels_2": PALETTE["text_light"],
        "colors_background_1_2": PALETTE["dark_bg"],     # Negro carbón
        "colors_background_2_2": PALETTE["dark_bg_2"],   # Gris oscuro
    }

    # Combinar
    all_mappings = {**scheme1_mapping, **scheme2_mapping}

    applied = 0
    for field, value in all_mappings.items():
        old = current.get(field, "NO EXISTE")
        current[field] = value
        if old != value:
            print(f"  {field}: {old} → {value}")
            applied += 1

    # Buscar y actualizar campos de logo si existen
    logo_fields = [k for k in current.keys() if "logo" in k.lower()]
    print(f"\nCampos de logo: {logo_fields}")
    for lf in logo_fields:
        if "width" in lf.lower():
            current[lf] = 200  # Ancho razonable
        elif isinstance(current[lf], str) and ("shopify" in current[lf].lower() or not current[lf]):
            if logo_png_url:
                current[lf] = logo_png_url
                print(f"  {lf} → {logo_png_url}")

    # Buscar campo de tipo de letra / fuentes
    font_fields = [k for k in current.keys() if "font" in k.lower() or "type" in k.lower()]
    print(f"\nCampos de fuente: {font_fields[:10]}")

    print(f"\n=== RESUMEN: {applied} campos actualizados ===")

    # ── 5. SUBIR SETTINGS ACTUALIZADO ──
    settings[current_key] = current
    r5 = requests.put(
        f"https://{shop_url}/admin/api/2024-01/themes/{theme_id}/assets.json",
        headers=headers,
        json={"asset": {"key": "config/settings_data.json", "value": json.dumps(settings)}}
    )
    print(f"\nSubir settings: {r5.status_code}")

    if r5.status_code == 200:
        print("✅ TEMA APLICADO EXITOSAMENTE")
    else:
        print(f"❌ Error: {r5.text[:300]}")

    # ── 6. VERIFICAR ──
    print(f"\n{'='*50}")
    print(f"VERIFICAR RESULTADO:")
    print(f"  Storefront: https://{shop_url}")
    print(f"  Admin temas: https://admin.shopify.com/store/{shop_url.split('.')[0]}/themes")
    print(f"  Editar tema: https://admin.shopify.com/store/{shop_url.split('.')[0]}/themes/{theme_id}/editor")

    return 0

if __name__ == "__main__":
    exit(main())
