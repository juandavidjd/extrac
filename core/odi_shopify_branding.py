#!/usr/bin/env python3
"""
ODI V22.2 Shopify Branding Module
Applies corporate branding to Shopify stores:
- Locale: es (Spanish)
- Corporate colors via metafields
- Announcement bar
- Spanish footer
"""
import json
import os
import requests
import time
from typing import Dict, Optional, List

BRANDS_DIR = "/opt/odi/data/brands"
IDENTIDAD_DIR = "/opt/odi/data/identidad"


def get_shop_config(empresa: str) -> Optional[Dict]:
    """Get Shopify credentials for a store."""
    path = os.path.join(BRANDS_DIR, f"{empresa.lower()}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
        return data.get("shopify", data)


def get_brand_identity(empresa: str) -> Optional[Dict]:
    """Get brand identity (colors, logo, etc)."""
    path = os.path.join(IDENTIDAD_DIR, empresa.upper(), "brand.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def shopify_request(config: Dict, method: str, endpoint: str, data: Dict = None) -> Dict:
    """Make a Shopify API request."""
    shop = config["shop"]
    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"

    url = f"https://{shop}/admin/api/2024-01/{endpoint}"
    headers = {
        "X-Shopify-Access-Token": config["token"],
        "Content-Type": "application/json"
    }

    if method == "GET":
        resp = requests.get(url, headers=headers, timeout=30)
    elif method == "PUT":
        resp = requests.put(url, headers=headers, json=data, timeout=30)
    elif method == "POST":
        resp = requests.post(url, headers=headers, json=data, timeout=30)
    else:
        raise ValueError(f"Unknown method: {method}")

    return {"status": resp.status_code, "data": resp.json() if resp.text else {}}


def get_shop_info(config: Dict) -> Dict:
    """Get current shop information."""
    result = shopify_request(config, "GET", "shop.json")
    return result.get("data", {}).get("shop", {})


def update_shop_locale(config: Dict) -> Dict:
    """Update shop to Spanish locale."""
    # Note: Primary locale is set in shop settings, but we can set metafields
    result = shopify_request(config, "PUT", "shop.json", {
        "shop": {
            "primary_locale": "es"
        }
    })
    return result


def set_shop_metafield(config: Dict, namespace: str, key: str, value: str, value_type: str = "single_line_text_field") -> Dict:
    """Set a shop-level metafield."""
    result = shopify_request(config, "POST", "metafields.json", {
        "metafield": {
            "namespace": namespace,
            "key": key,
            "value": value,
            "type": value_type,
            "owner_resource": "shop"
        }
    })
    return result


def get_themes(config: Dict) -> List[Dict]:
    """Get all themes."""
    result = shopify_request(config, "GET", "themes.json")
    return result.get("data", {}).get("themes", [])


def get_main_theme(config: Dict) -> Optional[Dict]:
    """Get the main/active theme."""
    themes = get_themes(config)
    for theme in themes:
        if theme.get("role") == "main":
            return theme
    return themes[0] if themes else None


def update_theme_settings(config: Dict, theme_id: int, settings: Dict) -> Dict:
    """Update theme settings via settings_data.json asset."""
    # First get current settings
    result = shopify_request(config, "GET", f"themes/{theme_id}/assets.json?asset[key]=config/settings_data.json")

    if result["status"] != 200:
        return {"error": "Could not get theme settings", "status": result["status"]}

    try:
        current_settings = json.loads(result["data"]["asset"]["value"])
    except:
        current_settings = {"current": {}}

    # Merge new settings
    if "current" not in current_settings:
        current_settings["current"] = {}

    current_settings["current"].update(settings)

    # Update settings
    result = shopify_request(config, "PUT", f"themes/{theme_id}/assets.json", {
        "asset": {
            "key": "config/settings_data.json",
            "value": json.dumps(current_settings, ensure_ascii=False)
        }
    })

    return result


def create_announcement_bar_content(brand: Dict) -> str:
    """Create Spanish announcement bar text."""
    nombre = brand.get("nombre_comercial", brand.get("nombre", ""))
    return f"Bienvenido a {nombre} - Envios a toda Colombia - WhatsApp para pedidos"


def create_footer_content(brand: Dict) -> Dict:
    """Create Spanish footer content."""
    nombre = brand.get("nombre_comercial", brand.get("nombre", ""))
    return {
        "footer_copyright": f"© 2026 {nombre}. Todos los derechos reservados.",
        "footer_payment_text": "Pagos seguros con todas las tarjetas",
        "footer_shipping_text": "Envios a toda Colombia"
    }


def apply_branding(empresa: str, dry_run: bool = False) -> Dict:
    """Apply full branding to a Shopify store."""
    results = {
        "empresa": empresa,
        "steps": [],
        "success": True
    }

    # Get configs
    config = get_shop_config(empresa)
    if not config:
        return {"empresa": empresa, "error": "Shopify config not found", "success": False}

    brand = get_brand_identity(empresa)
    if not brand:
        return {"empresa": empresa, "error": "Brand identity not found", "success": False}

    # 1. Get shop info
    shop_info = get_shop_info(config)
    results["shop_name"] = shop_info.get("name", "Unknown")
    results["current_locale"] = shop_info.get("primary_locale", "unknown")

    if dry_run:
        results["dry_run"] = True
        results["would_apply"] = {
            "locale": "es",
            "colors": brand.get("colores", {}),
            "announcement": create_announcement_bar_content(brand),
            "footer": create_footer_content(brand)
        }
        return results

    # 2. Set metafields for branding
    colores = brand.get("colores", {})

    # Color primario
    if colores.get("primario"):
        r = set_shop_metafield(config, "branding", "color_primario", colores["primario"])
        results["steps"].append({
            "action": "metafield_color_primario",
            "status": r["status"],
            "value": colores["primario"]
        })
        time.sleep(0.5)

    # Color secundario
    if colores.get("secundario"):
        r = set_shop_metafield(config, "branding", "color_secundario", colores["secundario"])
        results["steps"].append({
            "action": "metafield_color_secundario",
            "status": r["status"],
            "value": colores["secundario"]
        })
        time.sleep(0.5)

    # Color acento
    if colores.get("acento"):
        r = set_shop_metafield(config, "branding", "color_acento", colores["acento"])
        results["steps"].append({
            "action": "metafield_color_acento",
            "status": r["status"],
            "value": colores["acento"]
        })
        time.sleep(0.5)

    # 3. Announcement bar text
    announcement = create_announcement_bar_content(brand)
    r = set_shop_metafield(config, "branding", "announcement_text", announcement)
    results["steps"].append({
        "action": "metafield_announcement",
        "status": r["status"],
        "value": announcement[:50] + "..."
    })
    time.sleep(0.5)

    # 4. Footer content
    footer = create_footer_content(brand)
    for key, value in footer.items():
        r = set_shop_metafield(config, "branding", key, value)
        results["steps"].append({
            "action": f"metafield_{key}",
            "status": r["status"]
        })
        time.sleep(0.3)

    # 5. Try to update theme settings
    theme = get_main_theme(config)
    if theme:
        results["theme"] = theme.get("name", "Unknown")
        results["theme_id"] = theme.get("id")

        # Try to update color scheme in theme
        theme_settings = {}
        if colores.get("primario"):
            theme_settings["colors_accent_1"] = colores["primario"]
        if colores.get("secundario"):
            theme_settings["colors_accent_2"] = colores["secundario"]

        if theme_settings:
            r = update_theme_settings(config, theme["id"], theme_settings)
            results["steps"].append({
                "action": "theme_colors",
                "status": r.get("status", "attempted")
            })

    # Check overall success
    errors = [s for s in results["steps"] if s.get("status", 200) >= 400]
    results["success"] = len(errors) == 0
    results["errors"] = len(errors)

    return results


def apply_branding_all(dry_run: bool = False) -> Dict:
    """Apply branding to all 15 stores."""
    empresas = [
        "ARMOTOS", "BARA", "CBI", "DFG", "DUNA", "IMBRA", "JAPAN",
        "KAIQI", "LEO", "MCLMOTOS", "OH_IMPORTACIONES", "STORE",
        "VAISAND", "VITTON", "YOKOMAR"
    ]

    results = {"stores": {}, "success": 0, "failed": 0}

    for empresa in empresas:
        print(f"Processing {empresa}...")
        r = apply_branding(empresa, dry_run)
        results["stores"][empresa] = r

        if r.get("success"):
            results["success"] += 1
        else:
            results["failed"] += 1

        time.sleep(1)  # Rate limit between stores

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 odi_shopify_branding.py test EMPRESA     # Dry run")
        print("  python3 odi_shopify_branding.py apply EMPRESA    # Apply to one")
        print("  python3 odi_shopify_branding.py apply-all        # Apply to all 15")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "test" and len(sys.argv) > 2:
        empresa = sys.argv[2].upper()
        result = apply_branding(empresa, dry_run=True)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "apply" and len(sys.argv) > 2:
        empresa = sys.argv[2].upper()
        result = apply_branding(empresa, dry_run=False)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "apply-all":
        result = apply_branding_all(dry_run=False)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
