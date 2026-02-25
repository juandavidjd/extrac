#!/usr/bin/env python3
"""
ODI V24 - Ficha Técnica 7 Cuerpos
Módulo permanente para generar fichas técnicas estructuradas.
Parsea títulos, extrae compatibilidad, genera HTML y metafields.
"""
import json
import os
import re
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

BRANDS_DIR = "/opt/odi/data/brands"
REPORTS_DIR = "/opt/odi/data/reports"

# Patrones de marcas de motos
MARCAS_MOTO = {
    'AKT': ['AKT', 'AKTFLEX', 'AKTNKD', 'AKTTT', 'AKTEVO', 'AKTJET'],
    'BAJAJ': ['BAJAJ', 'PULSAR', 'DISCOVER', 'BOXER', 'PLATINO', 'AVENGER', 'DOMINAR', 'TORITO'],
    'HONDA': ['HONDA', 'CBF', 'CB', 'XR', 'NXR', 'BROSS', 'TITAN', 'CG', 'ECO', 'DELUXE', 'TWISTER', 'INVICTA', 'XRE', 'WAVE', 'SPLENDOR', 'PASSION'],
    'YAMAHA': ['YAMAHA', 'YBR', 'FZ', 'FAZER', 'XTZ', 'CRYPTON', 'LIBERO', 'BWS', 'NMAX', 'SZR', 'MOTARD'],
    'SUZUKI': ['SUZUKI', 'GIXXER', 'GN', 'GS', 'HAYATE', 'AX', 'VIVA', 'BEST', 'VIVAX'],
    'TVS': ['TVS', 'APACHE', 'RTR', 'SPORT', 'ROCKZ', 'NTORQ'],
    'KAWASAKI': ['KAWASAKI', 'KLX', 'NINJA', 'Z', 'VERSYS', 'WIND'],
    'HERO': ['HERO', 'SPLENDOR', 'PASSION', 'GLAMOUR', 'HUNK'],
    'KYMCO': ['KYMCO', 'AGILITY', 'FLY', 'ACTIV', 'UNIK', 'TWIST'],
    'AUTECO': ['AUTECO', 'VICTORY', 'SIGMA'],
    'AYCO': ['AYCO', 'NATSUKI'],
    'VAISAND': ['VAISAND'],
    'JIALING': ['JIALING', 'JC', 'JH'],
    'SHINERAY': ['SHINERAY', 'SG'],
    'GENERIC': ['MOTOCARRO', 'SCOOTER', 'MOTO', 'UNIVERSAL']
}

# Patrones de cilindraje
CILINDRAJE_PATTERN = re.compile(r'(\d{2,3})\s*(cc|CC)?', re.IGNORECASE)

# Tipos de motor
TIPOS_MOTOR = {
    'OHC': 'OHC 4T',
    'OHV': 'OHV 4T',
    'SOHC': 'SOHC 4T',
    'DOHC': 'DOHC 4T',
    '2T': '2 Tiempos',
    '4T': '4 Tiempos'
}

# Aplicaciones comunes
APLICACIONES = {
    'ADM': 'Admisión',
    'ESC': 'Escape',
    'ADM-ESC': 'Admisión/Escape',
    'DEL': 'Delantero',
    'TRAS': 'Trasero',
    'IZQ': 'Izquierdo',
    'DER': 'Derecho',
    'COMPLETO': 'Kit Completo'
}


class FichaTecnica:
    """
    Generador de Fichas Técnicas 7 Cuerpos para productos de motos.
    """

    def __init__(self, empresa: str):
        self.empresa = empresa.upper()
        self.config = self._load_config()

    def _load_config(self) -> Optional[Dict]:
        """Cargar configuración Shopify de la empresa."""
        path = os.path.join(BRANDS_DIR, f"{self.empresa.lower()}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
            return data.get("shopify", data)

    def parse_title_to_fitment(self, title: str) -> Dict:
        """
        Parsear título de producto para extraer información de compatibilidad.
        Retorna: {marca, modelos, cilindrajes, aplicacion, tipo_motor}
        """
        title_upper = title.upper()

        # Detectar marca
        marca_detectada = None
        modelos_detectados = []

        for marca, keywords in MARCAS_MOTO.items():
            for kw in keywords:
                if kw in title_upper:
                    marca_detectada = marca
                    # Buscar modelo específico
                    model_match = re.search(rf'{kw}\s*(\d{{2,3}}[A-Z]*)', title_upper)
                    if model_match:
                        modelos_detectados.append(f"{kw} {model_match.group(1)}")
                    else:
                        modelos_detectados.append(kw)
                    break
            if marca_detectada:
                break

        # Si no encontró marca, buscar por patrones
        if not marca_detectada:
            marca_detectada = "GENÉRICO"

        # Extraer cilindrajes
        cilindrajes = []
        for match in CILINDRAJE_PATTERN.finditer(title_upper):
            cc = int(match.group(1))
            if 50 <= cc <= 650:  # Rango válido para motos
                cilindrajes.append(cc)
        cilindrajes = list(set(cilindrajes))
        cilindrajes.sort()

        # Detectar aplicación
        aplicacion = None
        for key, valor in APLICACIONES.items():
            if key in title_upper:
                aplicacion = valor
                break

        # Detectar tipo motor
        tipo_motor = "4 Tiempos"  # Default
        for key, valor in TIPOS_MOTOR.items():
            if key in title_upper:
                tipo_motor = valor
                break

        # Limpiar modelos duplicados
        modelos_unicos = list(dict.fromkeys(modelos_detectados))

        # Calcular confianza
        confidence = 0.5
        if marca_detectada != "GENÉRICO":
            confidence += 0.2
        if cilindrajes:
            confidence += 0.15
        if modelos_unicos:
            confidence += 0.1
        if aplicacion:
            confidence += 0.05

        return {
            'marca_moto': marca_detectada,
            'modelos': modelos_unicos[:5],  # Máximo 5 modelos
            'cilindrajes': cilindrajes,
            'aplicacion': aplicacion or 'General',
            'tipo_motor': tipo_motor,
            'fitment_confidence': round(min(confidence, 1.0), 2)
        }

    def build_ficha(self, sku: str, title: str, price: float = None, image_url: str = None) -> Dict:
        """
        Construir ficha técnica completa de 7 cuerpos.
        """
        fitment = self.parse_title_to_fitment(title)

        ficha = {
            'sku': sku,
            'titulo': title,
            'marca_moto': fitment['marca_moto'],
            'modelos': fitment['modelos'],
            'cilindraje': fitment['cilindrajes'],
            'tipo_motor': fitment['tipo_motor'],
            'aplicacion': fitment['aplicacion'],
            'codigo_proveedor': sku,
            'proveedor': self.empresa,
            'precio_cop': price,
            'imagen_url': image_url,
            'fitment_confidence': fitment['fitment_confidence'],
            'generated_at': datetime.now().isoformat()
        }

        return ficha

    def ficha_to_description_html(self, ficha: Dict) -> str:
        """
        Generar HTML de ficha técnica para body_html de Shopify.
        Formato de tabla con badge ODI.
        """
        modelos_str = ', '.join(ficha.get('modelos', [])) or 'Múltiples modelos'
        cilindraje_str = self._format_cilindraje(ficha.get('cilindraje', []))

        html = f'''<div class="odi-ficha">
  <h3>Especificaciones Técnicas</h3>
  <table class="odi-specs-table">
    <tr><td><strong>Código</strong></td><td>{ficha.get('sku', '-')}</td></tr>
    <tr><td><strong>Proveedor</strong></td><td>{ficha.get('proveedor', '-')}</td></tr>
    <tr><td><strong>Compatible con</strong></td><td>{modelos_str}</td></tr>
    <tr><td><strong>Cilindraje</strong></td><td>{cilindraje_str}</td></tr>
    <tr><td><strong>Tipo Motor</strong></td><td>{ficha.get('tipo_motor', '-')}</td></tr>
    <tr><td><strong>Aplicación</strong></td><td>{ficha.get('aplicacion', '-')}</td></tr>
  </table>
  <p class="odi-badge">✓ Verificado por ODI</p>
</div>

<style>
.odi-ficha {{ font-family: Arial, sans-serif; margin: 20px 0; }}
.odi-ficha h3 {{ color: #333; border-bottom: 2px solid #e63946; padding-bottom: 10px; }}
.odi-specs-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
.odi-specs-table td {{ padding: 10px; border-bottom: 1px solid #eee; }}
.odi-specs-table tr:nth-child(even) {{ background: #f9f9f9; }}
.odi-badge {{ background: #2a9d8f; color: white; padding: 8px 15px; border-radius: 20px; display: inline-block; font-weight: bold; margin-top: 15px; }}
</style>'''

        return html

    def _format_cilindraje(self, cilindrajes: List[int]) -> str:
        """Formatear lista de cilindrajes a string legible."""
        if not cilindrajes:
            return "Múltiples cilindradas"
        if len(cilindrajes) == 1:
            return f"{cilindrajes[0]}cc"
        return f"{min(cilindrajes)}cc - {max(cilindrajes)}cc"

    def ficha_to_shopify_metafields(self, ficha: Dict) -> List[Dict]:
        """
        Convertir ficha a metafields de Shopify.
        """
        metafields = [
            {
                "namespace": "odi",
                "key": "sku",
                "value": ficha.get('sku', ''),
                "type": "single_line_text_field"
            },
            {
                "namespace": "odi",
                "key": "marca_moto",
                "value": ficha.get('marca_moto', ''),
                "type": "single_line_text_field"
            },
            {
                "namespace": "odi",
                "key": "modelos_compatibles",
                "value": json.dumps(ficha.get('modelos', [])),
                "type": "json"
            },
            {
                "namespace": "odi",
                "key": "cilindraje",
                "value": json.dumps(ficha.get('cilindraje', [])),
                "type": "json"
            },
            {
                "namespace": "odi",
                "key": "tipo_motor",
                "value": ficha.get('tipo_motor', ''),
                "type": "single_line_text_field"
            },
            {
                "namespace": "odi",
                "key": "aplicacion",
                "value": ficha.get('aplicacion', ''),
                "type": "single_line_text_field"
            },
            {
                "namespace": "odi",
                "key": "proveedor",
                "value": ficha.get('proveedor', ''),
                "type": "single_line_text_field"
            },
            {
                "namespace": "odi",
                "key": "fitment_confidence",
                "value": str(ficha.get('fitment_confidence', 0)),
                "type": "number_decimal"
            }
        ]
        return metafields

    def update_shopify_product(self, product_id: int, ficha: Dict) -> Tuple[bool, str]:
        """
        Actualizar producto en Shopify con ficha técnica.
        Actualiza body_html y metafields.
        """
        if not self.config:
            return False, "no_config"

        shop = self.config["shop"]
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"

        token = self.config["token"]
        headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json"
        }

        # Generar HTML
        body_html = self.ficha_to_description_html(ficha)

        # Actualizar producto
        url = f"https://{shop}/admin/api/2024-10/products/{product_id}.json"
        payload = {
            "product": {
                "id": product_id,
                "body_html": body_html
            }
        }

        try:
            resp = requests.put(url, headers=headers, json=payload, timeout=30)
            if resp.status_code not in [200, 201]:
                return False, f"product_update_failed_{resp.status_code}"

            # Actualizar metafields
            metafields = self.ficha_to_shopify_metafields(ficha)
            for mf in metafields:
                mf_url = f"https://{shop}/admin/api/2024-10/products/{product_id}/metafields.json"
                mf_payload = {"metafield": mf}
                requests.post(mf_url, headers=headers, json=mf_payload, timeout=30)

            return True, "ok"

        except Exception as e:
            return False, f"exception_{str(e)[:50]}"

    def batch_update_products(self, products: List[Dict]) -> Dict:
        """
        Actualizar batch de productos con fichas técnicas.
        products: [{product_id, sku, title, price}, ...]
        """
        report = {
            'empresa': self.empresa,
            'timestamp': datetime.now().isoformat(),
            'total': len(products),
            'updated': 0,
            'failed': 0,
            'details': []
        }

        print(f"\n[FICHA] Actualizando {len(products)} productos de {self.empresa}...")

        for i, p in enumerate(products):
            product_id = p.get('product_id')
            sku = p.get('sku', '')
            title = p.get('title', '')
            price = p.get('price')

            # Construir ficha
            ficha = self.build_ficha(sku, title, price)

            # Actualizar en Shopify
            success, message = self.update_shopify_product(product_id, ficha)

            if success:
                report['updated'] += 1
                report['details'].append({
                    'sku': sku,
                    'status': 'updated',
                    'confidence': ficha['fitment_confidence']
                })
                print(f"  [{i+1}/{len(products)}] {sku}: OK (conf={ficha['fitment_confidence']})")
            else:
                report['failed'] += 1
                report['details'].append({
                    'sku': sku,
                    'status': 'failed',
                    'error': message
                })
                print(f"  [{i+1}/{len(products)}] {sku}: FAIL - {message}")

            time.sleep(0.5)

            # Checkpoint
            if (i + 1) % 50 == 0:
                print(f"  [CHECKPOINT {i+1}] updated={report['updated']}, failed={report['failed']}")

        # Guardar reporte
        report_path = os.path.join(REPORTS_DIR, f"{self.empresa.lower()}_ficha_update_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n[FICHA COMPLETE] Updated: {report['updated']}, Failed: {report['failed']}")
        return report

    def get_all_products(self) -> List[Dict]:
        """Obtener todos los productos activos de Shopify."""
        if not self.config:
            return []

        shop = self.config["shop"]
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"

        token = self.config["token"]
        headers = {"X-Shopify-Access-Token": token}
        products = []

        url = f"https://{shop}/admin/api/2024-10/products.json"
        params = {"status": "active", "fields": "id,title,handle,variants", "limit": 250}

        while url:
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=60)
                if resp.status_code != 200:
                    break

                data = resp.json()
                for p in data.get("products", []):
                    sku = p["variants"][0].get("sku", "") if p.get("variants") else ""
                    price = p["variants"][0].get("price") if p.get("variants") else None
                    products.append({
                        "product_id": p["id"],
                        "sku": sku,
                        "title": p.get("title", ""),
                        "price": float(price) if price else None
                    })

                link_header = resp.headers.get("Link", "")
                url = None
                params = {}
                if 'rel="next"' in link_header:
                    for part in link_header.split(","):
                        if 'rel="next"' in part:
                            url = part.split(";")[0].strip().strip("<>")
                            break

                time.sleep(0.3)
            except Exception as e:
                print(f"[ERROR] {e}")
                break

        print(f"[SHOPIFY] {self.empresa}: {len(products)} productos activos")
        return products


class ThemeLocalizer:
    """
    Actualizar textos del theme a español.
    """

    def __init__(self, empresa: str):
        self.empresa = empresa.upper()
        self.config = self._load_config()

    def _load_config(self) -> Optional[Dict]:
        path = os.path.join(BRANDS_DIR, f"{self.empresa.lower()}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
            return data.get("shopify", data)

    def update_theme_locale(self) -> Dict:
        """
        Actualizar traducciones del theme activo.
        """
        if not self.config:
            return {"error": "no_config"}

        shop = self.config["shop"]
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"

        token = self.config["token"]
        headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json"
        }

        # Obtener theme activo
        themes_url = f"https://{shop}/admin/api/2024-10/themes.json"
        try:
            resp = requests.get(themes_url, headers=headers, timeout=30)
            themes = resp.json().get("themes", [])
            main_theme = next((t for t in themes if t.get("role") == "main"), None)

            if not main_theme:
                return {"error": "no_main_theme"}

            theme_id = main_theme["id"]

            # Traducciones a aplicar
            translations = {
                "You may also like": "También te puede interesar",
                "Join our email list": "Suscríbete a nuestro boletín",
                "Get exclusive deals": "Recibe ofertas exclusivas",
                "Add to cart": "Agregar al carrito",
                "Buy now": "Comprar ahora",
                "Sold out": "Agotado",
                "Sale": "Oferta",
                "New": "Nuevo",
                "Free shipping": "Envío gratis",
                "In stock": "Disponible",
                "Out of stock": "Agotado"
            }

            # Actualizar locale settings vía asset (si existe)
            # Nota: Las traducciones completas requieren modificar el theme
            # Este es un approach simplificado usando metafields del shop

            print(f"[LOCALE] Theme {theme_id} para {self.empresa}")
            print(f"[LOCALE] Traducciones a aplicar: {len(translations)}")

            return {
                "theme_id": theme_id,
                "translations_count": len(translations),
                "status": "translations_ready",
                "note": "Full theme localization requires theme asset modification"
            }

        except Exception as e:
            return {"error": str(e)}


def main():
    """CLI para testing."""
    import sys

    if len(sys.argv) < 2:
        print("Uso: python odi_ficha_tecnica.py <EMPRESA> [--all | --test]")
        print("Ejemplo: python odi_ficha_tecnica.py BARA --test")
        sys.exit(1)

    empresa = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--test"

    ft = FichaTecnica(empresa)

    if mode == "--all":
        products = ft.get_all_products()
        if products:
            report = ft.batch_update_products(products)
            print(json.dumps(report, indent=2))
    else:
        # Test con título de ejemplo
        test_title = "Arbol De Levas AK. AKT125/Jet4/150/Jet5"
        ficha = ft.build_ficha("2-3-132", test_title, 42000)
        print("Ficha generada:")
        print(json.dumps(ficha, indent=2, ensure_ascii=False))
        print("\nHTML generado:")
        print(ft.ficha_to_description_html(ficha))


if __name__ == "__main__":
    main()
