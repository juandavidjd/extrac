#\!/usr/bin/env python3
"""
ODI V24.1 - Ficha Engine Generico
Motor universal de fichas tecnicas 360.
Empresa hereda via profile.json + brand.json.
"""
import json
import os
import re
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

BRANDS_DIR = Path("/opt/odi/data/brands")
PROFILES_DIR = Path("/opt/odi/data/profiles")
REPORTS_DIR = Path("/opt/odi/data/reports")

MARCAS_MOTO = {
    "AKT": ["AKT", "FLEX", "NKD", "TT", "EVO", "JET", "SIGMA"],
    "BAJAJ": ["BAJAJ", "PULSAR", "DISCOVER", "BOXER", "PLATINO", "NS"],
    "HONDA": ["HONDA", "CBF", "CB", "XR", "BROSS", "TITAN", "CG", "ECO", "WAVE", "C70"],
    "YAMAHA": ["YAMAHA", "YBR", "FZ", "FAZER", "XTZ", "CRYPTON", "LIBERO", "BWS"],
    "SUZUKI": ["SUZUKI", "GIXXER", "GN", "GS", "HAYATE", "AX", "VIVA"],
    "TVS": ["TVS", "APACHE", "RTR"],
    "KYMCO": ["KYMCO", "AGILITY", "ACTIV", "UNIK"],
    "AYCO": ["AYCO"],
    "CERONTE": ["CERONTE"],
    "VAISAND": ["VAISAND"],
    "GY6": ["GY6", "SCOOTER"],
    "GENERIC": ["UNIVERSAL", "MOTOCARRO"]
}

BENEFICIOS_POR_TIPO = {
    "Arbol de Levas": ["Sincronizacion precisa de valvulas", "Acero de alta resistencia", "Perfil optimizado", "Mayor durabilidad"],
    "Biela": ["Conexion piston-ciguenal optima", "Aleacion de alta resistencia", "Balance perfecto", "Reduce vibraciones"],
    "Piston": ["Compresion eficiente", "Aleacion ligera", "Ranuras precisas", "Excelente disipacion de calor"],
    "Anillos": ["Sellado preciso piston-cilindro", "Compresion optima", "Control de aceite", "Resistencia al calor"],
    "Bomba de Aceite": ["Lubricacion constante", "Presion optima", "Engranajes precisos", "Protege el motor"],
    "Cilindro": ["Paredes pulidas", "Enfriamiento eficiente", "Aleacion de alta calidad", "Larga vida util"],
    "Clutch/Embrague": ["Acople suave", "Transmision progresiva", "Materiales premium", "Respuesta inmediata"],
    "Cadena": ["Transmision segura", "Eslabones reforzados", "Lubricacion duradera", "Minimo estiramiento"],
    "Filtro": ["Filtracion superior", "Flujo optimo", "Retencion de particulas", "Proteccion del motor"],
    "CDI": ["Chispa potente", "Curva de encendido optimizada", "Arranque instantaneo", "Proteccion electronica"],
    "Bobina": ["Alto voltaje estable", "Chispa constante", "Materiales aislantes premium", "Arranque confiable"],
    "Rodamiento": ["Giro suave", "Minima friccion", "Sellado antipolvo", "Alta carga soportada"],
    "Banda de Freno": ["Frenado progresivo", "Material premium", "Resistente al calor", "Larga duracion"],
    "Balancin": ["Accionamiento preciso", "Superficie pulida", "Acero endurecido", "Minimo desgaste"],
    "Caja de Cambios": ["Cambios suaves", "Engranajes templados", "Sincronizacion perfecta", "Transmision eficiente"],
    "default": ["Calidad premium", "Compatible OEM", "Facil instalacion", "Garantia de calidad"]
}

CILINDRAJE_PATTERN = re.compile(r"(\d{2,3})\s*(cc|CC)?", re.IGNORECASE)

class FichaEngine:
    """Motor generico de fichas tecnicas 360."""

    def __init__(self, empresa: str):
        self.empresa = empresa.upper()
        self.brand_config = self._load_brand()
        self.profile = self._load_profile()
        self.color = self.brand_config.get("color", "#1E88E5")

    def _load_brand(self) -> Dict:
        path = BRANDS_DIR / f"{self.empresa.lower()}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}

    def _load_profile(self) -> Dict:
        path = PROFILES_DIR / f"{self.empresa}.json"
        if not path.exists():
            path = PROFILES_DIR / "_default.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {"prefix_map": {}, "tipos_pieza_keywords": {}}

    def detect_tipo_pieza(self, title: str) -> str:
        title_upper = title.upper()
        keywords = self.profile.get("tipos_pieza_keywords", {})
        for keyword, tipo in keywords.items():
            if keyword in title_upper:
                return tipo
        return "Repuesto de Moto"

    def detect_compatibilidad_by_prefix(self, sku: str) -> Optional[Dict]:
        prefix_map = self.profile.get("prefix_map", {})
        for prefix, data in prefix_map.items():
            if sku.upper().startswith(prefix.upper()):
                return data
        return None

    def detect_marca_from_title(self, title: str) -> Tuple[Optional[str], List[str]]:
        title_upper = title.upper()
        marca = None
        modelos = []
        for brand, keywords in MARCAS_MOTO.items():
            for kw in keywords:
                if kw in title_upper:
                    marca = brand
                    pattern = rf"{kw}\s*(\d{{2,3}}[A-Z]*)"
                    match = re.search(pattern, title_upper)
                    if match:
                        modelos.append(f"{kw} {match.group(1)}")
                    break
            if marca:
                break
        return marca, modelos

    def detect_cilindraje(self, title: str) -> List[str]:
        matches = CILINDRAJE_PATTERN.findall(title)
        cilindrajes = []
        for m in matches:
            cc = int(m[0])
            if 50 <= cc <= 1000:
                cilindrajes.append(f"{cc}cc")
        return list(set(cilindrajes))

    def get_beneficios(self, tipo_pieza: str) -> List[str]:
        return BENEFICIOS_POR_TIPO.get(tipo_pieza, BENEFICIOS_POR_TIPO["default"])

    def generate(self, sku: str, title: str, price: float = None) -> Tuple[str, Dict]:
        """Generar ficha tecnica completa. Returns: (body_html, metafields)"""
        tipo_pieza = self.detect_tipo_pieza(title)
        prefix_data = self.detect_compatibilidad_by_prefix(sku)
        if prefix_data:
            marca = prefix_data.get("marca", "Universal")
            modelos = prefix_data.get("modelos", [])
        else:
            marca, modelos = self.detect_marca_from_title(title)
            if not marca:
                marca = "Universal"
        cilindrajes = self.detect_cilindraje(title)
        beneficios = self.get_beneficios(tipo_pieza)
        html = self._build_html(tipo_pieza, marca, modelos, cilindrajes, beneficios, sku, title, price)
        metafields = {
            "tipo_pieza": tipo_pieza,
            "marca_compatible": marca,
            "modelos": ",".join(modelos) if modelos else "",
            "cilindrajes": ",".join(cilindrajes) if cilindrajes else "",
            "odi_verified": True,
            "ficha_version": "v24.1"
        }
        return html, metafields

    def _build_html(self, tipo_pieza, marca, modelos, cilindrajes, beneficios, sku, title, price=None):
        color = self.color
        compat_items = []
        if marca and marca != "Universal":
            compat_items.append(f"<strong>{marca}</strong>")
        if modelos:
            compat_items.append(", ".join(modelos[:5]))
        if cilindrajes:
            compat_items.append(" / ".join(cilindrajes[:3]))
        compatibilidad = " ".join(compat_items) if compat_items else "Consultar compatibilidad"
        beneficios_html = "".join([f"<li>{b}</li>" for b in beneficios[:4]])
        html = f"""
<div class="odi-ficha-360" style="font-family: Arial, sans-serif; max-width: 800px;">
  <div style="background: linear-gradient(135deg, {color} 0%, {color}dd 100%); color: white; padding: 20px; border-radius: 12px 12px 0 0;">
    <h2 style="margin: 0; font-size: 1.4em;">{tipo_pieza}</h2>
    <p style="margin: 8px 0 0 0; opacity: 0.9;">SKU: {sku}</p>
  </div>
  <div style="background: #f8f9fa; padding: 20px; border-left: 4px solid {color};">
    <h3 style="color: {color}; margin-top: 0;">Especificaciones Tecnicas</h3>
    <table style="width: 100%; border-collapse: collapse;">
      <tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; width: 40%;"><strong>Tipo</strong></td>
          <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{tipo_pieza}</td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Compatibilidad</strong></td>
          <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{compatibilidad}</td></tr>
      <tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Referencia</strong></td>
          <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{sku}</td></tr>
      <tr><td style="padding: 8px;"><strong>Condicion</strong></td>
          <td style="padding: 8px;">Nuevo - Original</td></tr>
    </table>
  </div>
  <div style="padding: 20px; background: white;">
    <h3 style="color: {color}; margin-top: 0;">Beneficios</h3>
    <ul style="padding-left: 20px; line-height: 1.8;">{beneficios_html}</ul>
  </div>
  <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 10px 20px;">
    <strong>Instalacion:</strong> Recomendamos instalacion por tecnico especializado.
  </div>
  <div style="background: {color}; color: white; padding: 12px 20px; border-radius: 0 0 12px 12px; text-align: center;">
    <span style="font-size: 1.1em;">Verificado por ODI</span>
    <span style="opacity: 0.8; margin-left: 15px;">Calidad Garantizada</span>
  </div>
</div>
"""
        return html

    def apply_to_product(self, shop, token, product_id, sku, title, price=None):
        html, metafields = self.generate(sku, title, price)
        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        url = f"https://{shop}/admin/api/2024-10/products/{product_id}.json"
        payload = {"product": {"id": product_id, "body_html": html}}
        try:
            resp = requests.put(url, headers=headers, json=payload, timeout=30)
            return resp.status_code == 200, f"HTTP {resp.status_code}"
        except Exception as e:
            return False, str(e)

    def apply_fichas(self, domain=None, token=None, limit=None, dry_run=False):
        shop_config = self.brand_config.get("shopify", {})
        shop = domain or shop_config.get("shop")
        token = token or shop_config.get("token")
        if not shop or not token:
            return {"error": "missing_credentials"}
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"
        products = self._get_products(shop, token)
        if limit:
            products = products[:limit]
        print(f"[FICHA] {self.empresa}: {len(products)} productos")
        report = {"empresa": self.empresa, "timestamp": datetime.now().isoformat(),
                  "total": len(products), "updated": 0, "failed": 0, "dry_run": dry_run, "details": []}
        for i, p in enumerate(products):
            product_id, sku, title = p["product_id"], p["sku"], p["title"]
            if dry_run:
                html, meta = self.generate(sku, title)
                print(f"  [{i+1}] {sku}: {meta.get('tipo_pieza')} | {meta.get('marca_compatible')}")
                report["details"].append({"sku": sku, "tipo": meta.get("tipo_pieza"), "marca": meta.get("marca_compatible")})
                continue
            success, msg = self.apply_to_product(shop, token, product_id, sku, title)
            if success:
                report["updated"] += 1
                print(f"  [{i+1}/{len(products)}] {sku}: OK")
            else:
                report["failed"] += 1
                print(f"  [{i+1}/{len(products)}] {sku}: FAIL - {msg}")
            time.sleep(0.5)
        report_path = REPORTS_DIR / f"{self.empresa.lower()}_ficha_engine_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n[COMPLETE] Updated: {report['updated']}, Failed: {report['failed']}")
        return report

    def _get_products(self, shop, token):
        headers = {"X-Shopify-Access-Token": token}
        products = []
        url = f"https://{shop}/admin/api/2024-10/products.json"
        params = {"status": "active", "fields": "id,title,variants", "limit": 250}
        while url:
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=60)
                if resp.status_code != 200:
                    break
                data = resp.json()
                for p in data.get("products", []):
                    variant = p.get("variants", [{}])[0]
                    products.append({"product_id": p["id"], "sku": variant.get("sku", ""),
                                   "title": p.get("title", ""), "price": float(variant.get("price", 0) or 0)})
                link = resp.headers.get("Link", "")
                url = None
                params = {}
                if "rel=\"next\"" in link:
                    for part in link.split(","):
                        if "rel=\"next\"" in part:
                            url = part.split(";")[0].strip().strip("<>")
                            break
                time.sleep(0.3)
            except Exception as e:
                print(f"[ERROR] {e}")
                break
        return products


def main():
    import sys
    if len(sys.argv) < 2:
        print("Uso: python odi_ficha_engine.py <EMPRESA> [--dry-run | --apply | --test]")
        sys.exit(1)
    empresa = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--dry-run"
    engine = FichaEngine(empresa)
    if mode == "--apply":
        engine.apply_fichas(dry_run=False)
    elif mode == "--dry-run":
        engine.apply_fichas(dry_run=True, limit=20)
    elif mode == "--test":
        tests = [("GY6-004", "BOMBA DE ACEITE GY6 150CC"), ("MCAY-015", "CILINDRO COMPLETO AYCO 200")]
        for sku, title in tests:
            html, meta = engine.generate(sku, title)
            print(f"{sku}: {meta}")


if __name__ == "__main__":
    main()
