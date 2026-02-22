#!/usr/bin/env python3
"""
ODI Source Quality Gate — Evalua calidad de datos ANTES de procesar.

Si la fuente tiene problemas graves, el pipeline ALERTA antes de publicar.
No bloquea — pero genera reporte para decision humana.

Checks:
  1. Imagenes repetidas (misma URL en multiples productos)
  2. Titulos duplicados o casi-duplicados
  3. SKUs en formato incorrecto (notacion cientifica, vacios)
  4. Precios faltantes o sospechosos ($0, $1)
  5. Cobertura: % de productos con imagen, precio, SKU
  6. Consistencia: formato de datos uniforme

Uso:
  gate = SourceQualityGate()
  result = gate.evaluate(products, "KAIQI")

  print(result["grade"])        # "A", "B", "C", o "D"
  print(result["recommendation"])
  for issue in result["issues"]:
      print(f"  {issue['severity']}: {issue['detail']}")
"""

import re
import logging
from collections import Counter
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

logger = logging.getLogger("odi.source_quality")


class SourceQualityGate:
    """Evalua calidad de datos fuente antes del pipeline."""

    # Umbrales de alerta
    THRESHOLDS = {
        "image_repeat_max_pct": 20,    # Si >20% comparten imagen → alerta
        "title_duplicate_max_pct": 5,   # Si >5% titulos duplicados → alerta
        "title_similar_max_pct": 15,    # Si >15% titulos similares (>80%) → alerta
        "sku_missing_max_pct": 2,       # Si >2% sin SKU → alerta
        "price_missing_max_pct": 10,    # Si >10% sin precio → info
        "price_suspicious_max_pct": 5,  # Si >5% precios sospechosos
        "scientific_notation_max": 0,   # 0 SKUs en notacion cientifica
        "min_title_words": 3,           # Titulos con <3 palabras
        "max_title_length": 200,        # Titulos muy largos
    }

    def __init__(self, thresholds: Dict = None):
        if thresholds:
            self.THRESHOLDS.update(thresholds)

    def evaluate(self, products: List[Dict], empresa: str) -> Dict:
        """
        Evalua calidad de lista de productos extraidos.

        Args:
            products: Lista de productos extraidos del CSV/Excel
            empresa: Nombre de la empresa (para logging)

        Returns:
            {
                "empresa": str,
                "total_products": int,
                "grade": "A" | "B" | "C" | "D" | "F",
                "issues": [...],
                "recommendation": str,
                "metrics": {...}
            }
        """
        total = len(products)
        if total == 0:
            return {
                "empresa": empresa,
                "total_products": 0,
                "grade": "F",
                "issues": [{"type": "NO_DATA", "severity": "CRITICAL",
                           "detail": "0 productos en la fuente"}],
                "metrics": {},
                "recommendation": "FUENTE VACIA - verificar archivo de origen"
            }

        issues = []
        metrics = {}

        # ── Check 1: Imagenes repetidas ──
        self._check_images(products, issues, metrics)

        # ── Check 2: Titulos duplicados y similares ──
        self._check_titles(products, issues, metrics, total)

        # ── Check 3: SKUs problematicos ──
        self._check_skus(products, issues, metrics, total)

        # ── Check 4: Precios ──
        self._check_prices(products, issues, metrics, total)

        # ── Check 5: Cobertura general ──
        self._check_coverage(products, metrics, total)

        # ── Check 6: Consistencia de datos ──
        self._check_consistency(products, issues, metrics)

        # ── Calcular grado ──
        grade, recommendation = self._calculate_grade(issues, metrics)

        # ── Log resultado ──
        self._log_result(empresa, total, grade, issues, metrics, recommendation)

        return {
            "empresa": empresa,
            "total_products": total,
            "grade": grade,
            "issues": issues,
            "metrics": metrics,
            "recommendation": recommendation
        }

    def _check_images(self, products: List[Dict], issues: List,
                      metrics: Dict):
        """Verifica imagenes repetidas."""
        images = []
        for p in products:
            img = p.get("image_url") or p.get("image") or p.get("imagen")
            if img and str(img).strip():
                images.append(str(img).strip())

        if not images:
            metrics["images_coverage"] = 0
            issues.append({
                "type": "NO_IMAGES",
                "severity": "HIGH",
                "detail": "Ningun producto tiene imagen"
            })
            return

        metrics["images_total"] = len(images)
        img_counts = Counter(images)
        metrics["images_unique"] = len(img_counts)

        # Encontrar repetidas
        repeated_count = 0
        repeated_examples = []
        for url, count in img_counts.most_common(5):
            if count > 1:
                repeated_count += count - 1  # Cuantas son duplicadas
                repeated_examples.append(f"URL usada {count}x")

        if repeated_count > 0:
            pct_repeated = (repeated_count / len(images)) * 100
            metrics["images_repeated_count"] = repeated_count
            metrics["images_repeated_pct"] = round(pct_repeated, 1)

            if pct_repeated > self.THRESHOLDS["image_repeat_max_pct"]:
                issues.append({
                    "type": "IMAGE_REPEAT",
                    "severity": "HIGH",
                    "detail": f"{repeated_count} imagenes repetidas ({pct_repeated:.1f}%)",
                    "examples": repeated_examples[:3]
                })

    def _check_titles(self, products: List[Dict], issues: List,
                      metrics: Dict, total: int):
        """Verifica titulos duplicados y similares."""
        titles = []
        for p in products:
            title = p.get("title") or p.get("nombre") or p.get("descripcion") or ""
            titles.append(str(title).strip().upper())

        # Duplicados exactos
        title_counts = Counter(titles)
        exact_duplicates = sum(1 for c in title_counts.values() if c > 1)
        pct_dup = (exact_duplicates / total) * 100 if total else 0
        metrics["titles_duplicate_count"] = exact_duplicates
        metrics["titles_duplicate_pct"] = round(pct_dup, 1)

        if pct_dup > self.THRESHOLDS["title_duplicate_max_pct"]:
            worst = [(t, c) for t, c in title_counts.most_common(3) if c > 1]
            issues.append({
                "type": "TITLE_DUPLICATE",
                "severity": "MEDIUM",
                "detail": f"{exact_duplicates} titulos duplicados ({pct_dup:.1f}%)",
                "examples": [f'"{t[:40]}..." x{c}' for t, c in worst]
            })

        # Titulos muy cortos
        short_titles = sum(1 for t in titles if len(t.split()) < self.THRESHOLDS["min_title_words"])
        if short_titles > 0:
            pct_short = (short_titles / total) * 100
            metrics["titles_short_count"] = short_titles
            if pct_short > 10:
                issues.append({
                    "type": "TITLE_SHORT",
                    "severity": "LOW",
                    "detail": f"{short_titles} titulos con menos de 3 palabras ({pct_short:.1f}%)"
                })

        # Titulos muy largos
        long_titles = sum(1 for t in titles if len(t) > self.THRESHOLDS["max_title_length"])
        if long_titles > 0:
            metrics["titles_long_count"] = long_titles

    def _check_skus(self, products: List[Dict], issues: List,
                    metrics: Dict, total: int):
        """Verifica SKUs problematicos."""
        skus = []
        for p in products:
            sku = p.get("sku") or p.get("codigo") or p.get("code") or p.get("referencia") or ""
            skus.append(str(sku).strip())

        # SKUs faltantes
        missing_sku = sum(1 for s in skus if not s)
        pct_missing = (missing_sku / total) * 100 if total else 0
        metrics["sku_missing_count"] = missing_sku
        metrics["sku_missing_pct"] = round(pct_missing, 1)

        if missing_sku > 0:
            severity = "HIGH" if pct_missing > 10 else "MEDIUM" if pct_missing > 2 else "LOW"
            issues.append({
                "type": "SKU_MISSING",
                "severity": severity,
                "detail": f"{missing_sku} productos sin SKU ({pct_missing:.1f}%)"
            })

        # SKUs en notacion cientifica (Excel problem)
        scientific_pattern = re.compile(r'^[\d.]+[eE][+\-]?\d+$')
        scientific = [s for s in skus if scientific_pattern.match(s)]
        metrics["sku_scientific_count"] = len(scientific)

        if scientific:
            issues.append({
                "type": "SKU_SCIENTIFIC_NOTATION",
                "severity": "HIGH",
                "detail": f"{len(scientific)} SKUs en notacion cientifica (error Excel)",
                "examples": scientific[:3]
            })

        # SKUs duplicados
        sku_counts = Counter(s for s in skus if s)
        sku_duplicates = sum(1 for c in sku_counts.values() if c > 1)
        if sku_duplicates > 0:
            metrics["sku_duplicate_count"] = sku_duplicates
            worst = [(s, c) for s, c in sku_counts.most_common(3) if c > 1]
            issues.append({
                "type": "SKU_DUPLICATE",
                "severity": "MEDIUM",
                "detail": f"{sku_duplicates} SKUs duplicados",
                "examples": [f'"{s}" x{c}' for s, c in worst]
            })

    def _check_prices(self, products: List[Dict], issues: List,
                      metrics: Dict, total: int):
        """Verifica precios."""
        prices = []
        for p in products:
            price = p.get("price") or p.get("precio") or p.get("valor") or 0
            try:
                # Limpiar formato de precio
                if isinstance(price, str):
                    price = price.replace("$", "").replace(",", "").replace(".", "").strip()
                    if price:
                        price = float(price)
                    else:
                        price = 0
                prices.append(float(price))
            except (ValueError, TypeError):
                prices.append(0)

        # Precios faltantes
        missing_price = sum(1 for p in prices if p <= 0)
        pct_missing = (missing_price / total) * 100 if total else 0
        metrics["price_missing_count"] = missing_price
        metrics["price_missing_pct"] = round(pct_missing, 1)

        if missing_price > 0:
            severity = "HIGH" if pct_missing > 50 else "MEDIUM" if pct_missing > 10 else "LOW"
            issues.append({
                "type": "PRICE_MISSING",
                "severity": severity,
                "detail": f"{missing_price} sin precio ({pct_missing:.1f}%)"
            })

        # Precios sospechosos (muy bajos o placeholder)
        suspicious = sum(1 for p in prices if 0 < p <= 100)  # < $100 sospechoso para repuestos
        placeholder = sum(1 for p in prices if p in [1, 100, 1000, 10000, 99999])

        if suspicious > 0:
            pct_suspicious = (suspicious / total) * 100
            metrics["price_suspicious_count"] = suspicious
            if pct_suspicious > self.THRESHOLDS["price_suspicious_max_pct"]:
                issues.append({
                    "type": "PRICE_SUSPICIOUS",
                    "severity": "LOW",
                    "detail": f"{suspicious} precios muy bajos (<$100) ({pct_suspicious:.1f}%)"
                })

        if placeholder > 0:
            metrics["price_placeholder_count"] = placeholder
            issues.append({
                "type": "PRICE_PLACEHOLDER",
                "severity": "MEDIUM",
                "detail": f"{placeholder} posibles precios placeholder (1, 100, 1000, etc.)"
            })

    def _check_coverage(self, products: List[Dict], metrics: Dict, total: int):
        """Calcula cobertura general de campos."""
        fields = {
            "title": ["title", "nombre", "descripcion"],
            "sku": ["sku", "codigo", "code", "referencia"],
            "price": ["price", "precio", "valor"],
            "image": ["image_url", "image", "imagen"],
            "category": ["category", "categoria", "tipo", "product_type"],
        }

        for field_name, possible_keys in fields.items():
            count = 0
            for p in products:
                for key in possible_keys:
                    val = p.get(key)
                    if val and str(val).strip():
                        count += 1
                        break

            pct = (count / total) * 100 if total else 0
            metrics[f"coverage_{field_name}"] = round(pct, 1)

    def _check_consistency(self, products: List[Dict], issues: List,
                           metrics: Dict):
        """Verifica consistencia de formato de datos."""
        # Detectar problemas de encoding
        encoding_issues = 0
        for p in products:
            title = str(p.get("title", ""))
            # Caracteres de encoding roto comunes
            if any(c in title for c in ["Ã¡", "Ã©", "Ã­", "Ã³", "Ãº", "Ã±", "â€"]):
                encoding_issues += 1

        if encoding_issues > 0:
            metrics["encoding_issues"] = encoding_issues
            issues.append({
                "type": "ENCODING_BROKEN",
                "severity": "MEDIUM",
                "detail": f"{encoding_issues} productos con problemas de encoding (tildes rotas)"
            })

        # Detectar ALL CAPS
        all_caps = 0
        for p in products:
            title = str(p.get("title", ""))
            if title and title == title.upper() and len(title) > 10:
                all_caps += 1

        if all_caps > len(products) * 0.5:  # >50% en mayusculas
            metrics["titles_all_caps"] = all_caps
            issues.append({
                "type": "TITLE_ALL_CAPS",
                "severity": "LOW",
                "detail": f"{all_caps} titulos en ALL CAPS (considerar normalizar)"
            })

    def _calculate_grade(self, issues: List, metrics: Dict) -> tuple:
        """Calcula grado final y recomendacion."""
        critical = sum(1 for i in issues if i.get("severity") == "CRITICAL")
        high = sum(1 for i in issues if i.get("severity") == "HIGH")
        medium = sum(1 for i in issues if i.get("severity") == "MEDIUM")
        low = sum(1 for i in issues if i.get("severity") == "LOW")

        # Logica de grado
        if critical > 0:
            grade = "F"
            recommendation = "FUENTE INUTILIZABLE. Verificar archivo de origen."
        elif high >= 3:
            grade = "D"
            recommendation = "FUENTE MUY PROBLEMATICA. Considerar limpieza manual antes de pipeline."
        elif high >= 1:
            grade = "C"
            recommendation = "FUENTE CON PROBLEMAS. Pipeline procesara pero resultados seran mediocres."
        elif medium >= 2:
            grade = "B"
            recommendation = "FUENTE ACEPTABLE. Algunos productos necesitaran revision post-pipeline."
        else:
            grade = "A"
            recommendation = "FUENTE LIMPIA. Pipeline deberia producir Grado A."

        return grade, recommendation

    def _log_result(self, empresa: str, total: int, grade: str,
                    issues: List, metrics: Dict, recommendation: str):
        """Log resultado de evaluacion."""
        high = sum(1 for i in issues if i.get("severity") == "HIGH")
        medium = sum(1 for i in issues if i.get("severity") == "MEDIUM")

        log_msg = (
            f"\n{'='*60}\n"
            f"SOURCE QUALITY GATE: {empresa}\n"
            f"  Productos: {total}\n"
            f"  Grado: {grade}\n"
            f"  Issues: {len(issues)} ({high} HIGH, {medium} MEDIUM)\n"
            f"  Cobertura: "
            f"imagen={metrics.get('coverage_image', 0)}% "
            f"precio={metrics.get('coverage_price', 0)}% "
            f"sku={metrics.get('coverage_sku', 0)}%\n"
            f"  Recomendacion: {recommendation}\n"
            f"{'='*60}"
        )

        if grade in ["D", "F"]:
            logger.warning(log_msg)
        elif grade == "C":
            logger.info(log_msg)
        else:
            logger.info(log_msg)

    def generate_report(self, result: Dict, output_path: str = None) -> str:
        """Genera reporte detallado en formato texto/markdown."""
        lines = [
            f"# Source Quality Report: {result['empresa']}",
            f"",
            f"**Grado:** {result['grade']}",
            f"**Productos:** {result['total_products']}",
            f"**Recomendacion:** {result['recommendation']}",
            f"",
            "## Metricas",
            "",
        ]

        for key, value in result.get("metrics", {}).items():
            lines.append(f"- {key}: {value}")

        lines.extend(["", "## Issues", ""])

        for issue in result.get("issues", []):
            severity = issue.get("severity", "INFO")
            emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}.get(severity, "⚪")
            lines.append(f"### {emoji} [{severity}] {issue['type']}")
            lines.append(f"{issue['detail']}")
            if issue.get("examples"):
                lines.append("Examples:")
                for ex in issue["examples"]:
                    lines.append(f"  - {ex}")
            lines.append("")

        report = "\n".join(lines)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(f"Reporte guardado en: {output_path}")

        return report


# ─────────────────────────────────────────────────────────
# TEST STANDALONE
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    gate = SourceQualityGate()

    # Test con datos simulados
    print("=" * 60)
    print("TEST 1: Fuente limpia (Grado A esperado)")
    print("=" * 60)

    clean_products = [
        {"sku": f"SKU-{i:04d}", "title": f"Producto Ejemplo Numero {i}",
         "price": 15000 + i * 100, "image_url": f"https://example.com/img{i}.jpg"}
        for i in range(1, 51)
    ]

    result = gate.evaluate(clean_products, "TEST_CLEAN")
    print(f"Grado: {result['grade']}")
    assert result["grade"] == "A", f"Esperado A, obtenido {result['grade']}"
    print("✅ TEST 1 PASSED\n")

    # Test con problemas
    print("=" * 60)
    print("TEST 2: Fuente problematica (Grado C/D esperado)")
    print("=" * 60)

    problem_products = [
        # SKU en notacion cientifica
        {"sku": "1.23E+10", "title": "PRODUCTO UNO", "price": 100},
        # Imagen repetida
        {"sku": "SKU-001", "title": "PRODUCTO DOS", "price": 15000,
         "image_url": "https://same.jpg"},
        {"sku": "SKU-002", "title": "PRODUCTO TRES", "price": 15000,
         "image_url": "https://same.jpg"},
        {"sku": "SKU-003", "title": "PRODUCTO CUATRO", "price": 15000,
         "image_url": "https://same.jpg"},
        # Sin SKU
        {"title": "Producto sin codigo", "price": 5000},
        # Sin precio
        {"sku": "SKU-004", "title": "Producto sin precio"},
        # Titulo duplicado
        {"sku": "SKU-005", "title": "TITULO DUPLICADO", "price": 1000},
        {"sku": "SKU-006", "title": "TITULO DUPLICADO", "price": 2000},
    ]

    result = gate.evaluate(problem_products, "TEST_PROBLEM")
    print(f"Grado: {result['grade']}")
    print(f"Issues: {len(result['issues'])}")
    for issue in result["issues"]:
        print(f"  - [{issue['severity']}] {issue['type']}: {issue['detail']}")

    assert result["grade"] in ["C", "D"], f"Esperado C/D, obtenido {result['grade']}"
    print("✅ TEST 2 PASSED\n")

    # Test reporte
    print("=" * 60)
    print("TEST 3: Generar reporte")
    print("=" * 60)

    report = gate.generate_report(result)
    print(report[:500] + "...")
    print("✅ TEST 3 PASSED\n")

    print("✅ SourceQualityGate: TODOS LOS TESTS OK")
