import re
import json
from typing import Dict, Any, Optional, List
from decimal import Decimal


class SemanticCriteria:
    def __init__(self, rules):
        self.rules = rules
        self.copypaste_blacklist = rules.get("copypaste_blacklist", [])
        self.fitment_whitelist = rules.get("fitment_brand_whitelist", [])
        self.min_price = Decimal(str(rules.get("min_price_cop", 100)))
        self.max_price = Decimal(str(rules.get("max_price_cop", 50000000)))

    def evaluate_all(self, product, shopify_data, source_data=None):
        results = {
            "criterio_titulo": self._eval_titulo(product, shopify_data),
            "criterio_descripcion": self._eval_descripcion(product, shopify_data),
            "criterio_info_tecnica": self._eval_info_tecnica(product, shopify_data),
            "criterio_compatibilidad": self._eval_compatibilidad(product, shopify_data),
            "criterio_beneficios": self._eval_beneficios(product, shopify_data),
            "criterio_precio": self._eval_precio(product, shopify_data),
            "criterio_stock": self._eval_stock(shopify_data),
            "criterio_imagen": self._eval_imagen(product, shopify_data),
            "criterio_sku": self._eval_sku(shopify_data),
            "criterio_branding": self._eval_branding(product, shopify_data),
            "criterio_vendor": self._eval_vendor(product, shopify_data),
            "criterio_categoria": self._eval_categoria(product, shopify_data),
        }
        scores = [v for v in results.values() if isinstance(v, int)]
        total = sum(scores)
        results["score"] = round((total / len(scores)) * 100, 2) if scores else 0.0
        if results["score"] >= 90:
            results["severity"] = "pass"
        elif results["score"] >= 70:
            results["severity"] = "warning"
        elif results["score"] >= 50:
            results["severity"] = "critical"
        else:
            results["severity"] = "blocker"
        results["finding_detail"] = self._build_detail(results, product, shopify_data)
        return results

    def _eval_titulo(self, product, shopify):
        title = shopify.get("title", "")
        if not title:
            return 0
        if title == title.upper() and len(title) > 10:
            return 0
        titulo_raw = product.get("titulo_raw", "")
        if title.lower().startswith("empaque") and "empaque" not in str(titulo_raw).lower():
            return 0
        if len(title.split()) < 3:
            return 0
        return 1

    def _eval_descripcion(self, product, shopify):
        body = shopify.get("body_html", "") or ""
        if len(body.strip()) < 50:
            return 0
        body_lower = body.lower()
        copypaste_count = sum(1 for phrase in self.copypaste_blacklist if phrase.lower() in body_lower)
        if copypaste_count >= 2:
            return 0
        return 1

    def _eval_info_tecnica(self, product, shopify):
        body = shopify.get("body_html", "") or ""
        body_lower = body.lower()
        
        # V22.1: Accept any structured ficha-360 as VALID
        # The criterion catches products with NO info, not products with generic info
        has_ficha_360 = "ficha-360" in body_lower or "ficha_360" in body_lower
        has_structured = ("<h2>" in body or "<h3>" in body) and len(body) > 200
        
        # Technical indicators (any industry)
        tech_indicators = [
            # Measurements
            "mm", "cm", "pulgadas", "litros", "kg", "lb", "psi", "bar", "nm",
            # Properties
            "material:", "medida:", "capacidad", "altura", "peso:", "voltaje:",
            "diametro:", "ancho:", "largo:", "alto:", "potencia", "torque",
            # Certifications
            "certificacion", "dot", "ece", "iso", "api",
            # Descriptive
            "profesional", "industrial", "reforzado", "templado"
        ]
        has_tech = any(ind in body_lower for ind in tech_indicators)
        
        # PASS if: ficha-360 structure OR structured HTML with content OR tech indicators
        if has_ficha_360 or has_structured or has_tech:
            return 1
        return 0

    def _eval_compatibilidad(self, product, shopify):
        body = shopify.get("body_html", "") or ""
        title = shopify.get("title", "").lower()
        body_lower = body.lower()
        
        # V22.1: Compatibility section exists is enough
        # The criterion catches CONTRADICTIONS, not missing info
        
        # Workshop items always pass (they dont need moto compatibility)
        workshop_keywords = ["mesa", "elevadora", "gato", "compresor", "herramienta", 
                            "llave", "torquimetro", "extractor", "grasa", "casco", "guante", "chaleco"]
        if any(kw in title for kw in workshop_keywords):
            return 1
        
        # FAIL only if: title has specific brand BUT body says "Universal"
        has_model_in_title = any(brand.lower() in title for brand in self.fitment_whitelist)
        says_universal = "universal" in body_lower and "compatibilidad" in body_lower
        if has_model_in_title and says_universal:
            return 0
        
        # PASS if: has compatibilidad section OR has ficha-360 structure
        has_compat_section = "compatibilidad" in body_lower
        has_ficha = "ficha-360" in body_lower
        if has_compat_section or has_ficha:
            return 1
        
        # Generic parts without specific compatibility: PASS (not a contradiction)
        return 1

    def _eval_beneficios(self, product, shopify):
        body = shopify.get("body_html", "") or ""
        default_benefits = ["durabilidad garantizada", "ajuste exacto", "facil instalacion"]
        if all(b in body.lower() for b in default_benefits):
            return 0
        return 1

    def _eval_precio(self, product, shopify):
        variants = shopify.get("variants", [])
        if not variants:
            return 0
        price = Decimal(str(variants[0].get("price", "0")))
        if price <= Decimal("1.00") or price == Decimal("1000.00"):
            return 0
        if price < self.min_price or price > self.max_price:
            return 0
        return 1

    def _eval_stock(self, shopify):
        variants = shopify.get("variants", [])
        if not variants:
            return 0
        v = variants[0]
        qty = v.get("inventory_quantity", 0)
        policy = v.get("inventory_policy", "deny")
        mgmt = v.get("inventory_management", None)
        if qty <= 0 and policy == "deny" and mgmt == "shopify":
            return 0
        return 1

    def _eval_imagen(self, product, shopify):
        images = shopify.get("images", [])
        if not images:
            return 0
        for img in images:
            src = img.get("src", "")
            if "freepik" in src.lower() or "ai_gen" in src.lower():
                return 0
        return 1

    def _eval_sku(self, shopify):
        variants = shopify.get("variants", [])
        if not variants:
            return 0
        sku = variants[0].get("sku", "")
        if not sku or sku == "None" or sku == "null":
            return 0
        return 1

    def _eval_branding(self, product, shopify):
        body = shopify.get("body_html", "") or ""
        # Verificar que tiene estructura de ficha ODI
        if "ficha-360" in body.lower() or "ficha_360" in body.lower():
            return 1
        # O tiene cualquier div estructurado
        if "<div" in body and "</div>" in body:
            return 1
        # O tiene secciones HTML
        if "<h2>" in body or "<h3>" in body or "<table" in body:
            return 1
        # Body vacío o sin estructura = fail
        if len(body.strip()) < 100:
            return 0
        return 1

    def _eval_vendor(self, product, shopify):
        vendor = shopify.get("vendor", "")
        ptype = shopify.get("product_type", "")
        if not vendor or vendor.lower() in ["", "default", "none"]:
            return 0
        if not ptype or ptype.lower() in ["", "default", "none"]:
            return 0
        return 1

    def _eval_categoria(self, product, shopify):
        ptype = shopify.get("product_type", "")
        title = shopify.get("title", "")
        freno_keywords = ["banda", "freno", "brake", "pastilla"]
        is_freno = any(kw in title.lower() for kw in freno_keywords)
        if is_freno and ptype.lower() == "empaque":
            return 0
        if not ptype:
            return 0
        return 1

    def _build_detail(self, results, product, shopify):
        detail = {}
        criteria_names = {
            "criterio_titulo": "Titulo",
            "criterio_descripcion": "Descripcion",
            "criterio_info_tecnica": "Info Tecnica",
            "criterio_compatibilidad": "Compatibilidad",
            "criterio_beneficios": "Beneficios",
            "criterio_precio": "Precio",
            "criterio_stock": "Stock",
            "criterio_imagen": "Imagen",
            "criterio_sku": "SKU",
            "criterio_branding": "Branding",
            "criterio_vendor": "Vendor/Type",
            "criterio_categoria": "Categoria",
        }
        for key, name in criteria_names.items():
            if results.get(key) == 0:
                detail[name] = "FALLA - verificar manualmente"
        return detail
