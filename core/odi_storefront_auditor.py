"""
odi_storefront_auditor.py — Audita lo que VE el cliente, no lo que dice el API.

Verifica la URL pública de cada tienda para detectar:
- Textos en inglés visibles
- Imágenes que no corresponden al producto
- Beneficios genéricos (copypaste)
- Fichas incompletas

V24.1 - 25 Feb 2026
"""

import requests
import os
import json
import re
from datetime import datetime

# Load environment from .env file
def load_env():
    env_path = "/opt/odi/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key] = val

load_env()

# Configuración de tiendas governed (dominios desde .env como fallback)
GOVERNED_STORES = {
    "ARMOTOS": {"domain": "znxx5p-10.myshopify.com", "public": "znxx5p-10.myshopify.com"},
    "DFG": {"domain": "0se1jt-q1.myshopify.com", "public": "0se1jt-q1.myshopify.com"},
    "VITTON": {"domain": "hxjebc-it.myshopify.com", "public": "hxjebc-it.myshopify.com"},
    "IMBRA": {"domain": "0i1mdf-gi.myshopify.com", "public": "0i1mdf-gi.myshopify.com"},
    "BARA": {"domain": "4jqcki-jq.myshopify.com", "public": "4jqcki-jq.myshopify.com"},
    "KAIQI": {"domain": "u03tqc-0e.myshopify.com", "public": "u03tqc-0e.myshopify.com"},
    "MCLMOTOS": {"domain": "v023qz-8x.myshopify.com", "public": "v023qz-8x.myshopify.com"},
    "YOKOMAR": {"domain": "u1zmhk-ts.myshopify.com", "public": "u1zmhk-ts.myshopify.com"},
}

# Markers de texto en inglés
ENGLISH_MARKERS = [
    "You may also like",
    "Join our email list",
    "Get exclusive deals",
    "Add to cart",
    "Sold out",
    "Continue shopping",
    "View all",
    "Subscribe",
    "Email address",
    "Quick view",
]

# Markers de ficha técnica ODI
FICHA_MARKERS = [
    "Especificaciones",
    "Verificado por ODI",
    "Beneficios",
    "Compatibilidad",
]

# Markers de beneficios genéricos (copypaste)
GENERIC_MARKERS = [
    "Calidad premium",
    "Compatible OEM",
    "Fácil instalación",
    "Garantía de calidad",
    "Repuesto de calidad",
    "Alta durabilidad",
    "Material resistente",
]

class StorefrontAuditor:
    def __init__(self):
        self.results = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_url(self, url, timeout=15):
        """Fetch URL content with error handling."""
        try:
            r = self.session.get(url, timeout=timeout, allow_redirects=True)
            return r.text if r.status_code == 200 else None
        except Exception as e:
            return None

    def check_english_markers(self, html):
        """Check for English text markers in HTML."""
        if not html:
            return {"found": [], "count": 0}

        found = []
        html_lower = html.lower()
        for marker in ENGLISH_MARKERS:
            if marker.lower() in html_lower:
                found.append(marker)

        return {"found": found, "count": len(found)}

    def check_ficha_markers(self, html):
        """Check for ODI ficha técnica markers."""
        if not html:
            return {"found": [], "missing": FICHA_MARKERS[:], "has_ficha": False}

        found = []
        html_lower = html.lower()
        for marker in FICHA_MARKERS:
            if marker.lower() in html_lower:
                found.append(marker)

        missing = [m for m in FICHA_MARKERS if m not in found]
        has_ficha = len(found) >= 2

        return {"found": found, "missing": missing, "has_ficha": has_ficha}

    def check_generic_markers(self, html):
        """Check for generic/copypaste benefit markers."""
        if not html:
            return {"found": [], "count": 0, "is_generic": False}

        found = []
        html_lower = html.lower()
        for marker in GENERIC_MARKERS:
            if marker.lower() in html_lower:
                found.append(marker)

        is_generic = len(found) >= 2

        return {"found": found, "count": len(found), "is_generic": is_generic}

    def get_token_and_domain(self, empresa):
        """Get token and domain for a store, trying multiple naming conventions."""
        # Try SHOPIFY_X_TOKEN first, then X_TOKEN
        token = os.getenv(f"SHOPIFY_{empresa}_TOKEN") or os.getenv(f"{empresa}_TOKEN")
        # Try X_SHOP for domain override
        domain = os.getenv(f"{empresa}_SHOP")
        if not domain:
            config = GOVERNED_STORES.get(empresa)
            domain = config["domain"] if config else None
        return token, domain

    def get_product_urls(self, empresa):
        """Get sample product URLs via API."""
        config = GOVERNED_STORES.get(empresa)
        if not config:
            return []

        token, domain = self.get_token_and_domain(empresa)
        if not domain:
            domain = config["domain"]

        if not token:
            return []

        try:
            headers = {'X-Shopify-Access-Token': token, 'Content-Type': 'application/json'}
            url = f"https://{domain}/admin/api/2024-10/products.json?status=active&limit=5"
            r = requests.get(url, headers=headers, timeout=15)

            if r.status_code == 200:
                products = r.json().get('products', [])
                public_domain = config.get("public", domain)
                urls = []
                for p in products:
                    handle = p.get('handle', '')
                    if handle:
                        urls.append({
                            "url": f"https://{public_domain}/products/{handle}",
                            "sku": p['variants'][0].get('sku', 'N/A') if p.get('variants') else 'N/A',
                            "has_image": len(p.get('images', [])) > 0
                        })
                return urls
        except Exception as e:
            pass

        return []

    def count_images_api(self, empresa):
        """Count products with/without images via API."""
        config = GOVERNED_STORES.get(empresa)
        if not config:
            return {"with_image": 0, "without_image": 0, "total": 0}

        token, domain = self.get_token_and_domain(empresa)
        if not domain:
            domain = config["domain"]

        if not token:
            return {"with_image": 0, "without_image": 0, "total": 0}

        try:
            headers = {'X-Shopify-Access-Token': token, 'Content-Type': 'application/json'}

            r = requests.get(f"https://{domain}/admin/api/2024-10/products/count.json?status=active",
                           headers=headers, timeout=15)
            total = r.json().get('count', 0) if r.status_code == 200 else 0

            r = requests.get(f"https://{domain}/admin/api/2024-10/products.json?status=active&limit=50",
                           headers=headers, timeout=15)

            with_image = 0
            if r.status_code == 200:
                products = r.json().get('products', [])
                for p in products:
                    if len(p.get('images', [])) > 0:
                        with_image += 1

                if len(products) > 0:
                    ratio = with_image / len(products)
                    estimated_with = int(total * ratio)
                    return {
                        "with_image": estimated_with,
                        "without_image": total - estimated_with,
                        "total": total,
                        "sample_size": len(products)
                    }

            return {"with_image": 0, "without_image": total, "total": total}
        except Exception as e:
            return {"with_image": 0, "without_image": 0, "total": 0, "error": str(e)}

    def audit_store(self, empresa):
        """Full audit of a single store."""
        print(f"\n[AUDIT] {empresa}...")

        config = GOVERNED_STORES.get(empresa)
        if not config:
            return {"error": f"Store {empresa} not configured"}

        result = {
            "empresa": empresa,
            "domain": config.get("public", config["domain"]),
            "timestamp": datetime.now().isoformat(),
            "homepage": {},
            "products": [],
            "images": {},
            "summary": {}
        }

        public_domain = config.get("public", config["domain"])

        # 1. Audit homepage
        print(f"  Fetching homepage...")
        homepage_url = f"https://{public_domain}"
        homepage_html = self.fetch_url(homepage_url)

        if homepage_html:
            result["homepage"]["url"] = homepage_url
            result["homepage"]["english"] = self.check_english_markers(homepage_html)
            result["homepage"]["fetched"] = True
        else:
            result["homepage"]["fetched"] = False
            result["homepage"]["english"] = {"found": [], "count": -1}

        # 2. Audit sample products
        print(f"  Getting product URLs...")
        product_urls = self.get_product_urls(empresa)

        english_in_products = 0
        ficha_found = 0
        generic_found = 0

        for i, prod in enumerate(product_urls[:3]):
            print(f"  Fetching product {i+1}: {prod['sku']}...")
            html = self.fetch_url(prod["url"])

            prod_result = {
                "url": prod["url"],
                "sku": prod["sku"],
                "has_image_api": prod["has_image"]
            }

            if html:
                eng = self.check_english_markers(html)
                ficha = self.check_ficha_markers(html)
                generic = self.check_generic_markers(html)

                prod_result["english"] = eng
                prod_result["ficha"] = ficha
                prod_result["generic"] = generic

                if eng["count"] > 0:
                    english_in_products += 1
                if ficha["has_ficha"]:
                    ficha_found += 1
                if generic["is_generic"]:
                    generic_found += 1
            else:
                prod_result["fetch_error"] = True

            result["products"].append(prod_result)

        # 3. Image audit via API
        print(f"  Counting images...")
        result["images"] = self.count_images_api(empresa)

        # 4. Generate summary
        total_products_checked = len(result["products"])
        homepage_english = result["homepage"].get("english", {}).get("count", 0)

        english_score = "FAIL" if homepage_english > 0 else "PASS"
        ficha_score = "PASS" if ficha_found >= (total_products_checked * 0.5) else "FAIL"
        benefits_score = "FAIL" if generic_found >= (total_products_checked * 0.5) else "PASS"

        img_total = result["images"].get("total", 1)
        img_with = result["images"].get("with_image", 0)
        img_pct = (img_with / img_total * 100) if img_total > 0 else 0
        img_score = "PASS" if img_pct >= 50 else "FAIL"

        scores = [english_score, ficha_score, benefits_score, img_score]
        fails = scores.count("FAIL")

        if fails == 0:
            grade = "A"
        elif fails == 1:
            grade = "B"
        elif fails == 2:
            grade = "C"
        elif fails == 3:
            grade = "D"
        else:
            grade = "F"

        result["summary"] = {
            "english_homepage": homepage_english,
            "english_score": english_score,
            "ficha_ratio": f"{ficha_found}/{total_products_checked}",
            "ficha_score": ficha_score,
            "generic_ratio": f"{generic_found}/{total_products_checked}",
            "benefits_score": benefits_score,
            "images_pct": f"{img_pct:.0f}%",
            "images_ratio": f"{img_with}/{img_total}",
            "images_score": img_score,
            "grade": grade
        }

        print(f"  Grade: {grade}")

        self.results[empresa] = result
        return result

    def audit_all(self):
        """Audit all governed stores."""
        print("=" * 60)
        print("AUDITORIA STOREFRONT - 8 TIENDAS GOVERNED")
        print("=" * 60)

        for empresa in GOVERNED_STORES.keys():
            self.audit_store(empresa)

        return self.results

    def print_report(self):
        """Print consolidated report."""
        print("\n" + "=" * 80)
        print("REPORTE CONSOLIDADO - AUDITORIA STOREFRONT")
        print("=" * 80)

        print(f"\n{'Tienda':<12} {'Ingles':<12} {'Ficha':<10} {'Beneficios':<12} {'Imagenes':<15} {'Score':<6}")
        print("-" * 70)

        for empresa, data in self.results.items():
            if "error" in data:
                print(f"{empresa:<12} ERROR: {data['error']}")
                continue

            s = data.get("summary", {})

            eng_count = s.get("english_homepage", 0)
            eng_disp = f"{eng_count} fail" if eng_count > 0 else "OK"

            ficha_disp = "OK" if s.get("ficha_score") == "PASS" else "FAIL"

            ben_score = s.get("benefits_score", "?")
            ben_disp = "generic" if ben_score == "FAIL" else "especif"

            img_disp = s.get("images_ratio", "?")

            grade = s.get("grade", "?")

            print(f"{empresa:<12} {eng_disp:<12} {ficha_disp:<10} {ben_disp:<12} {img_disp:<15} {grade:<6}")

        print("\n" + "-" * 70)
        print("GAPS COMUNES:")

        english_fail = sum(1 for d in self.results.values()
                         if d.get("summary", {}).get("english_score") == "FAIL")
        if english_fail > 0:
            print(f"- FIX_LOCALE: {english_fail}/8 tiendas con textos en ingles")

        for empresa, data in self.results.items():
            s = data.get("summary", {})
            if s.get("images_score") == "FAIL":
                img = data.get("images", {})
                print(f"- {empresa}: {s.get('images_pct', '?')} imagenes ({img.get('with_image', 0)}/{img.get('total', 0)})")
            if s.get("benefits_score") == "FAIL":
                print(f"- {empresa}: beneficios genericos detectados")

        print("\n" + "=" * 80)


def main():
    """Run full audit."""
    auditor = StorefrontAuditor()
    auditor.audit_all()
    auditor.print_report()

    report_path = "/opt/odi/data/reports/storefront_audit_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(auditor.results, f, indent=2, default=str)
    print(f"\nReporte JSON guardado en: {report_path}")


if __name__ == "__main__":
    main()
