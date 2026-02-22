#!/usr/bin/env python3
"""
ODI Shopify Branding Manager - Aplica identidad corporativa a tiendas Shopify.

Configura para cada tienda:
  - Locale del shop (espanol)
  - Logo en el header
  - Colores corporativos
  - Announcement bar (barra superior)
  - Footer en espanol

Uso:
  manager = ShopifyBrandingManager()
  manager.apply_branding("BARA")    # Una tienda
  manager.apply_all()               # Todas las tiendas
"""

import os
import json
import time
import base64
import logging
import requests
from pathlib import Path
from typing import Optional

logger = logging.getLogger("odi.branding")

# Paleta de colores por empresa
COLORES_EMPRESAS = {
    "ARMOTOS":  {"primario": "#E53E3E", "secundario": "#2D3748", "acento": "#ED8936", "fondo": "#FFFFFF"},
    "BARA":     {"primario": "#1B3A5C", "secundario": "#FFFFFF", "acento": "#E8A530", "fondo": "#F5F5F5"},
    "CBI":      {"primario": "#2B6CB0", "secundario": "#EBF8FF", "acento": "#3182CE", "fondo": "#FFFFFF"},
    "DFG":      {"primario": "#276749", "secundario": "#F0FFF4", "acento": "#38A169", "fondo": "#FFFFFF"},
    "DUNA":     {"primario": "#744210", "secundario": "#FFFFF0", "acento": "#D69E2E", "fondo": "#FFFFFF"},
    "IMBRA":    {"primario": "#1A365D", "secundario": "#EBF8FF", "acento": "#2B6CB0", "fondo": "#FFFFFF"},
    "JAPAN":    {"primario": "#9B2C2C", "secundario": "#FFF5F5", "acento": "#E53E3E", "fondo": "#FFFFFF"},
    "KAIQI":    {"primario": "#22543D", "secundario": "#F0FFF4", "acento": "#48BB78", "fondo": "#FFFFFF"},
    "LEO":      {"primario": "#553C9A", "secundario": "#FAF5FF", "acento": "#805AD5", "fondo": "#FFFFFF"},
    "MCLMOTOS": {"primario": "#2A4365", "secundario": "#EBF8FF", "acento": "#4299E1", "fondo": "#FFFFFF"},
    "OH_IMPORTACIONES": {"primario": "#702459", "secundario": "#FFF5F7", "acento": "#D53F8C", "fondo": "#FFFFFF"},
    "STORE":    {"primario": "#1A202C", "secundario": "#F7FAFC", "acento": "#4A5568", "fondo": "#FFFFFF"},
    "VAISAND":  {"primario": "#234E52", "secundario": "#E6FFFA", "acento": "#38B2AC", "fondo": "#FFFFFF"},
    "VITTON":   {"primario": "#1A365D", "secundario": "#FFFFFF", "acento": "#2B6CB0", "fondo": "#FFFFFF"},
    "YOKOMAR":  {"primario": "#7B341E", "secundario": "#FFFAF0", "acento": "#DD6B20", "fondo": "#FFFFFF"},
}

NOMBRES_EMPRESAS = {
    "ARMOTOS": "Armotos - Repuestos de Motos",
    "BARA": "Bara Importaciones - Repuestos de Motos",
    "CBI": "CBI Importaciones",
    "DFG": "DFG Motos Colombia",
    "DUNA": "Duna Importaciones",
    "IMBRA": "Imbra - Repuestos de Motos",
    "JAPAN": "Industrias Japan",
    "KAIQI": "Kaiqi Colombia",
    "LEO": "Industrias Leo",
    "MCLMOTOS": "MCL Motos",
    "OH_IMPORTACIONES": "OH Importaciones",
    "STORE": "Store Repuestos",
    "VAISAND": "Vaisand",
    "VITTON": "Industrias Vitton",
    "YOKOMAR": "Yokomar - Repuestos de Motos",
}


class ShopifyBrandingManager:
    """Aplica branding corporativo a tiendas Shopify."""

    LOGOS_DIR = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/logos_optimized"
    BRANDS_DIR = "/opt/odi/data/brands"

    def __init__(self):
        self.stats = {"success": 0, "failed": 0, "skipped": 0}

    def apply_branding(self, empresa_codigo: str) -> dict:
        """
        Aplica branding completo a UNA tienda.
        """
        empresa = empresa_codigo.upper()
        result = {"empresa": empresa, "steps": {}}

        # 1. Cargar configuracion
        brand = self._load_brand(empresa)
        if not brand:
            logger.error(f"X {empresa}: brand.json no encontrado")
            self.stats["failed"] += 1
            result["error"] = "brand.json not found"
            return result

        shop_url = brand.get("shopify", {}).get("shop")
        token = brand.get("shopify", {}).get("token")

        if not shop_url or not token:
            logger.error(f"X {empresa}: credenciales Shopify no encontradas")
            self.stats["failed"] += 1
            result["error"] = "Shopify credentials missing"
            return result

        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        base_url = f"https://{shop_url}/admin/api/2024-01"

        print(f"\n=== {empresa} ===")
        print(f"Shop: {shop_url}")

        # 2. Configurar locale
        result["steps"]["locale"] = self._set_locale(base_url, headers, empresa)
        time.sleep(0.5)

        # 3. Obtener theme activo
        theme_id = self._get_active_theme(base_url, headers)
        if not theme_id:
            logger.error(f"X {empresa}: no se encontro theme activo")
            result["error"] = "No active theme"
            return result
        result["steps"]["theme_id"] = theme_id
        print(f"Theme ID: {theme_id}")

        # 4. Subir logo
        result["steps"]["logo"] = self._upload_logo(base_url, headers, theme_id, empresa)
        time.sleep(0.5)

        # 5. Modificar settings del theme
        result["steps"]["settings"] = self._apply_theme_settings(
            base_url, headers, theme_id, empresa)
        time.sleep(0.5)

        # 6. Verificar traducciones
        result["steps"]["translations"] = self._check_translations(
            base_url, headers, theme_id)

        self.stats["success"] += 1
        print(f"OK {empresa}: branding aplicado")
        return result

    def apply_all(self) -> dict:
        """Aplica branding a TODAS las empresas con brand.json."""
        results = {}
        empresas = self._list_empresas()

        print(f"Aplicando branding a {len(empresas)} tiendas...")

        for empresa in empresas:
            results[empresa] = self.apply_branding(empresa)
            time.sleep(1)

        print(f"\nBranding completado: {self.stats['success']} OK, "
              f"{self.stats['failed']} fallidas, {self.stats['skipped']} omitidas")
        return results

    def _set_locale(self, base_url, headers, empresa) -> str:
        """Configurar locale del shop a espanol."""
        try:
            resp = requests.get(f"{base_url}/shop.json", headers=headers)
            if resp.status_code != 200:
                return f"X Error {resp.status_code}"

            shop = resp.json().get("shop", {})
            current_locale = shop.get("primary_locale", "?")

            if current_locale == "es":
                print(f"  Locale: ya en espanol")
                return "OK ya en es"

            resp = requests.put(
                f"{base_url}/shop.json",
                headers=headers,
                json={"shop": {"primary_locale": "es"}}
            )

            if resp.status_code == 200:
                print(f"  Locale: {current_locale} -> es")
                return f"OK {current_locale} -> es"
            else:
                return f"WARN HTTP {resp.status_code}"

        except Exception as e:
            return f"X {e}"

    def _get_active_theme(self, base_url, headers) -> Optional[int]:
        """Obtener ID del theme activo."""
        try:
            resp = requests.get(f"{base_url}/themes.json", headers=headers)
            if resp.status_code == 200:
                themes = resp.json().get("themes", [])
                for theme in themes:
                    if theme.get("role") == "main":
                        return theme["id"]
        except Exception as e:
            logger.error(f"Error obteniendo themes: {e}")
        return None

    def _upload_logo(self, base_url, headers, theme_id, empresa) -> str:
        """Subir logo como asset del theme."""
        logo_candidates = [
            f"{self.LOGOS_DIR}/{empresa}.png",
            f"{self.LOGOS_DIR}/{empresa.title()}.png",
            f"{self.LOGOS_DIR}/{empresa.lower()}.png",
            f"{self.LOGOS_DIR}/{empresa}_logo.png",
        ]

        logo_path = None
        for candidate in logo_candidates:
            if os.path.exists(candidate):
                logo_path = candidate
                break

        if not logo_path:
            print(f"  Logo: no encontrado (usando nombre texto)")
            return "WARN logo no encontrado"

        try:
            with open(logo_path, "rb") as f:
                logo_data = base64.b64encode(f.read()).decode("utf-8")

            asset_key = "assets/logo.png"
            resp = requests.put(
                f"{base_url}/themes/{theme_id}/assets.json",
                headers=headers,
                json={"asset": {"key": asset_key, "attachment": logo_data}}
            )

            if resp.status_code == 200:
                print(f"  Logo: subido ({os.path.basename(logo_path)})")
                return f"OK {os.path.basename(logo_path)}"
            else:
                return f"WARN HTTP {resp.status_code}"

        except Exception as e:
            return f"X {e}"

    def _apply_theme_settings(self, base_url, headers, theme_id, empresa) -> str:
        """Modificar settings del theme para colores y textos."""
        try:
            # Leer settings actuales
            resp = requests.get(
                f"{base_url}/themes/{theme_id}/assets.json",
                headers=headers,
                params={"asset[key]": "config/settings_data.json"}
            )

            if resp.status_code != 200:
                return f"WARN HTTP {resp.status_code} leyendo settings"

            asset = resp.json().get("asset", {})
            settings_raw = asset.get("value", "{}")
            settings = json.loads(settings_raw)

            current = settings.get("current", settings)

            colores = COLORES_EMPRESAS.get(empresa, COLORES_EMPRESAS["BARA"])
            nombre = NOMBRES_EMPRESAS.get(empresa, empresa)
            announcement = f"Bienvenidos a {nombre}"

            # Colores (Dawn theme keys)
            color_updates = {
                "colors_solid_button_labels": "#FFFFFF",
                "colors_accent_1": colores.get("acento", "#E8A530"),
                "colors_accent_2": colores.get("primario", "#1B3A5C"),
                "colors_text": "#1A1A1A",
                "colors_outline_button_labels": colores.get("primario", "#1B3A5C"),
                "colors_background_1": colores.get("fondo", "#FFFFFF"),
                "colors_background_2": colores.get("secundario", "#F5F5F5"),
            }

            for key, value in color_updates.items():
                if key in current:
                    current[key] = value

            # Announcement bar
            sections = current.get("sections", {})
            for section_id, section in sections.items():
                if section.get("type") == "announcement-bar":
                    blocks = section.get("blocks", {})
                    for block_id, block in blocks.items():
                        if block.get("type") == "announcement":
                            block.setdefault("settings", {})
                            block["settings"]["text"] = announcement
                    break

            # Footer en espanol
            for section_id, section in sections.items():
                if section.get("type") == "footer":
                    section.setdefault("settings", {})
                    section["settings"]["newsletter_heading"] = "Suscribete a nuestro boletin"
                    section["settings"]["newsletter_text"] = "Recibe ofertas exclusivas y novedades en repuestos."
                    break

            # Guardar settings
            settings_str = json.dumps(settings, ensure_ascii=False)

            resp = requests.put(
                f"{base_url}/themes/{theme_id}/assets.json",
                headers=headers,
                json={"asset": {"key": "config/settings_data.json", "value": settings_str}}
            )

            if resp.status_code == 200:
                print(f"  Settings: colores + announcement + footer OK")
                return "OK"
            else:
                return f"WARN HTTP {resp.status_code}"

        except Exception as e:
            return f"X {e}"

    def _check_translations(self, base_url, headers, theme_id) -> str:
        """Verificar locale espanol en theme."""
        try:
            resp = requests.get(
                f"{base_url}/themes/{theme_id}/assets.json",
                headers=headers,
                params={"asset[key]": "locales/es.default.json"}
            )

            if resp.status_code == 200:
                return "OK locale es existe"

            resp = requests.get(
                f"{base_url}/themes/{theme_id}/assets.json",
                headers=headers,
                params={"asset[key]": "locales/es.json"}
            )

            if resp.status_code == 200:
                return "OK locale es.json existe"

            return "WARN locale file no encontrado"

        except Exception as e:
            return f"X {e}"

    def _load_brand(self, empresa: str) -> Optional[dict]:
        """Cargar brand.json de una empresa."""
        paths = [
            Path(f"{self.BRANDS_DIR}/{empresa.lower()}.json"),
            Path(f"{self.BRANDS_DIR}/{empresa}.json"),
        ]
        for path in paths:
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        return None

    def _list_empresas(self) -> list:
        """Listar empresas con brand.json."""
        empresas = []
        brands_path = Path(self.BRANDS_DIR)
        if brands_path.exists():
            for f in brands_path.glob("*.json"):
                empresas.append(f.stem.upper())
        return sorted(empresas)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    manager = ShopifyBrandingManager()

    if len(sys.argv) > 1:
        empresa = sys.argv[1].upper()
        if empresa == "ALL":
            manager.apply_all()
        else:
            result = manager.apply_branding(empresa)
            print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Usage: python odi_shopify_branding.py <EMPRESA|ALL>")
        print("Available:", manager._list_empresas())
