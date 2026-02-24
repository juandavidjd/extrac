#!/usr/bin/env python3
"""
ODI Enforcement Engine — Nada pasa sin certificacion.
Orquesta: Productos → QualityStandard → Shopify
"""

import json
import os
import requests
import time
from datetime import datetime, timezone
from collections import Counter

class EnforcementEngine:
    def __init__(self, config):
        self.config = config
        self.empresa = config["empresa"]
        self.shop = config["shopify_shop"]
        self.token = config["shopify_token"]
        self.audit_log = []
        self.stats = {"created": 0, "updated": 0, "errors": 0, "skipped": 0}

    def process(self, products):
        """Procesa productos y sube a Shopify."""
        timestamp = datetime.now(timezone.utc).isoformat()

        print(f"\n{'='*60}")
        print(f"ENFORCEMENT ENGINE — {self.empresa}")
        print(f"Productos: {len(products)}")
        print(f"{'='*60}")

        # Evaluar calidad
        print(f"\n[1/3] EVALUACION DE CALIDAD...")
        import sys
        sys.path.insert(0, '/opt/odi/core')
        from odi_quality_standard import QualityStandard
        catalog_report = QualityStandard.evaluate_catalog(products)
        self._print_report(catalog_report)

        # Subir a Shopify
        print(f"\n[2/3] SUBIENDO A SHOPIFY...")
        for i, product in enumerate(products):
            quality = product.get("_quality", {})
            grade = quality.get("grade", "F")

            if grade == "F":
                self.stats["skipped"] += 1
                self._audit("SKIP", product, "Grado F")
                continue

            status = "active" if grade in ["A+", "A"] else "draft"

            try:
                self._upload_product(product, status)
                if (i + 1) % 100 == 0:
                    print(f"  Procesados: {i+1}/{len(products)}")
            except Exception as e:
                self.stats["errors"] += 1
                self._audit("ERROR", product, str(e)[:100])

        # Guardar audit
        print(f"\n[3/3] GUARDANDO AUDIT LOG...")
        self._save_audit(products, catalog_report, timestamp)

        # Reporte final
        print(f"\n{'='*60}")
        print(f"RESULTADO FINAL")
        print(f"{'='*60}")
        print(f"  Creados:      {self.stats['created']}")
        print(f"  Actualizados: {self.stats['updated']}")
        print(f"  Errores:      {self.stats['errors']}")
        print(f"  Omitidos:     {self.stats['skipped']}")

        return self.stats

    def _upload_product(self, product, status):
        """Sube producto a Shopify via REST API."""
        codigo = product.get("codigo", "")

        shopify_product = self._build_product(product, status)

        headers = {
            "X-Shopify-Access-Token": self.token,
            "Content-Type": "application/json"
        }

        # Crear nuevo producto
        url = f"https://{self.shop}/admin/api/2024-01/products.json"
        resp = requests.post(url, json=shopify_product, headers=headers)

        if resp.status_code in [200, 201]:
            self.stats["created"] += 1
            self._audit("CREATE", product, f"status={status}")
        elif resp.status_code == 429:
            # Rate limited - wait and retry
            time.sleep(2)
            resp = requests.post(url, json=shopify_product, headers=headers)
            if resp.status_code in [200, 201]:
                self.stats["created"] += 1
                self._audit("CREATE", product, f"status={status}")
            else:
                raise Exception(f"POST {resp.status_code}: {resp.text[:100]}")
        else:
            raise Exception(f"POST {resp.status_code}: {resp.text[:100]}")

        # Rate limit - Shopify allows 2 requests per second
        time.sleep(0.5)

    def _build_product(self, product, status):
        """Construye objeto Shopify."""
        codigo = product.get("codigo", "")
        desc = product.get("descripcion", "")
        precio = product.get("precio", 0)
        empaque = product.get("empaque", "X1")
        grade = product.get("_quality", {}).get("grade", "?")
        imagen = product.get("imagen")

        # Titulo con formato
        title = f"{desc}" if desc else f"Producto {codigo}"
        if len(title) > 70:
            title = title[:67] + "..."

        # Handle - lowercase, no spaces
        handle = f"{codigo}-{self.empresa.lower()}"

        # Body HTML (ficha 360)
        body = f"""
<div class="ficha-360">
  <p><strong>Codigo:</strong> {codigo}</p>
  <p><strong>Descripcion:</strong> {desc}</p>
  <p><strong>Empaque:</strong> {empaque or 'X1'}</p>
  <p><strong>Grado ODI:</strong> {grade}</p>
</div>
"""

        shopify_product = {
            "product": {
                "title": title,
                "handle": handle,
                "body_html": body,
                "vendor": self.empresa,
                "product_type": "Repuestos Motos",
                "status": status,
                "tags": f"{self.empresa}, Grade:{grade}, {empaque or 'X1'}",
                "variants": [{
                    "sku": codigo,
                    "price": str(precio) if precio else "0",
                    "inventory_management": "shopify",
                    "inventory_quantity": 10,
                }]
            }
        }

        return shopify_product

    def _audit(self, action, product, detail):
        self.audit_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "codigo": product.get("codigo", "?"),
            "grade": product.get("_quality", {}).get("grade", "?"),
            "detail": detail,
        })

    def _save_audit(self, products, catalog_report, timestamp):
        audit_dir = self.config.get("audit_dir", "/opt/odi/data/audit")
        os.makedirs(audit_dir, exist_ok=True)

        audit = {
            "timestamp": timestamp,
            "empresa": self.empresa,
            "total_products": len(products),
            "catalog_report": catalog_report,
            "stats": self.stats,
            "log": self.audit_log,
        }

        filename = f"{self.empresa}_{timestamp[:10]}_audit.json"
        filepath = os.path.join(audit_dir, filename)

        with open(filepath, "w") as f:
            json.dump(audit, f, indent=2, ensure_ascii=False)

        print(f"  Audit: {filepath}")

    def _print_report(self, report):
        print(f"\n{'='*50}")
        print(f"  {self.empresa} — GRADO {report['catalog_grade']}")
        print(f"{'='*50}")
        print(f"  Total:    {report['total']:>6d}")
        print(f"  A+:       {report['grades'].get('A+', 0):>6d}  (active)")
        print(f"  A:        {report['grades'].get('A', 0):>6d}  (active)")
        print(f"  B:        {report['grades'].get('B', 0):>6d}  (draft)")
        print(f"  C:        {report['grades'].get('C', 0):>6d}  (draft)")
        print(f"  F:        {report['grades'].get('F', 0):>6d}  (skip)")
        print(f"")
        print(f"  A+/A:     {report['a_plus_a_pct']:>3d}%")
        print(f"{'='*50}")
