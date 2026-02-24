#!/usr/bin/env python3
"""
ODI PDF Industrial Extractor v2
Pass 1 gratis, Pass 2 selectivo, Pass 3 certifica
"""
import os
import re
import json
import hashlib
import statistics
from collections import Counter
from datetime import datetime

import fitz  # PyMuPDF
from PIL import Image

# ============================================================
# THRESHOLDS CALIBRADOS (ARMOTOS 256 páginas)
# ============================================================
PRICE_COLUMN_X_MIN = 420
PRICE_MIN_COP = 200
MEDIAN_AREA_GLOBAL = 4542

SCORE_OVERLAP_MAX = 40
SCORE_FOTO_COLUMN = 25
SCORE_NORMAL_SIZE = 20
SCORE_SQUARE_BONUS = 10
PENALTY_SHOWCASE = -30
PENALTY_MULTIBLOCK = -25
PENALTY_TINY = -15

# ============================================================
# CONFIGURACIÓN POR EMPRESA
# ============================================================
EMPRESA_CONFIGS = {
    "ARMOTOS": {
        "codigo": "ARMOTOS",
        "code_pattern": r"^0[2-5]\d{3}$",
        "code_column_x_max": 120,
        "price_column_x": 420,
        "foto_column": (150, 460),
        "header_y": 70,
        "footer_y": 730,
        "pdf_path": "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Armotos/CATALOGO NOVIEMBRE V01-2025 NF.pdf",
    },
}

# ============================================================
# PASS 1: EXTRACCIÓN POR COORDENADAS
# ============================================================

def parse_price_cop(text_items, y_min, y_max):
    """Parser de precios COP robusto."""
    price_candidates = []

    for ti in text_items:
        if ti["y0"] < y_min - 3 or ti["y0"] > y_max + 3:
            continue
        if ti["x0"] < PRICE_COLUMN_X_MIN:
            continue

        text = ti["text"]

        # Patrón principal: $ seguido de número con puntos de miles
        m = re.search(r'\$\s*([\d]+(?:\.[\d]{3})*)', text)
        if m:
            try:
                val = int(m.group(1).replace(".", ""))
                price_candidates.append({
                    "valor": val,
                    "y": ti["y0"],
                    "raw": text,
                    "suspicious": val < PRICE_MIN_COP
                })
            except:
                pass
            continue

        # Patrón fragmentado: "$4" en una línea, ".980" en la siguiente
        m2 = re.search(r'\$\s*(\d{1,3})$', text)
        if m2:
            base = m2.group(1)
            for ti2 in text_items:
                if abs(ti2["y0"] - ti["y0"]) < 5 and ti2["x0"] > ti["x0"]:
                    m3 = re.search(r'^\.?(\d{3})', ti2["text"])
                    if m3:
                        val = int(base + m3.group(1))
                        price_candidates.append({
                            "valor": val,
                            "y": ti["y0"],
                            "raw": f"${base}.{m3.group(1)}",
                            "suspicious": val < PRICE_MIN_COP
                        })
                        break

        # Patrón sin $: solo número con formato de miles
        m4 = re.match(r'^([\d]+(?:\.[\d]{3})+)$', text)
        if m4:
            try:
                val = int(m4.group(1).replace(".", ""))
                if val >= PRICE_MIN_COP:
                    price_candidates.append({
                        "valor": val,
                        "y": ti["y0"],
                        "raw": text,
                        "suspicious": False
                    })
            except:
                pass

    if not price_candidates:
        return None

    best = min(price_candidates, key=lambda p: p["y"])
    return best


def calculate_page_median_area(page):
    """Calcula el área mediana de imágenes de producto en la página."""
    areas = []
    for img_info in page.get_images(full=True):
        xref = img_info[0]
        try:
            for rect in page.get_image_rects(xref):
                if rect.x0 > 100 and rect.y0 > 70 and rect.width > 20 and rect.height > 20:
                    areas.append(rect.width * rect.height)
        except:
            pass
    return statistics.median(areas) if areas else MEDIAN_AREA_GLOBAL


def score_image_candidate(img, block_y_start, block_y_end, page_median_area):
    """Scoring inteligente de candidatos de imagen."""
    score = 0.0
    block_height = block_y_end - block_y_start

    # 1. Overlap vertical con el bloque
    overlap_start = max(img["y0"], block_y_start)
    overlap_end = min(img["y1"], block_y_end)
    overlap = max(0, overlap_end - overlap_start)
    img_height = img["y1"] - img["y0"]

    if img_height > 0:
        overlap_ratio = overlap / img_height
        score += overlap_ratio * SCORE_OVERLAP_MAX

    # 2. En columna FOTO
    if 150 < img["x0"] < 460:
        score += SCORE_FOTO_COLUMN
    elif 100 < img["x0"] < 500:
        score += 10

    # 3. Tamaño relativo a mediana
    if page_median_area > 0:
        size_ratio = img["area"] / page_median_area
        if 0.3 < size_ratio < 2.0:
            score += SCORE_NORMAL_SIZE
        elif 2.0 <= size_ratio < 3.0:
            score -= 10
        elif size_ratio >= 3.0:
            score += PENALTY_SHOWCASE

    # 4. PENALIZACIÓN: cruza múltiples bloques
    if img_height > block_height * 1.3:
        score += PENALTY_MULTIBLOCK

    # 5. PENALIZACIÓN: demasiado pequeña
    if img["area"] < 300:
        score += PENALTY_TINY
    elif img["area"] < 500:
        score -= 10

    # 6. Bonus: cuadrada
    if img["area"] > 500:
        aspect = max(img["width"], img["height"]) / max(min(img["width"], img["height"]), 1)
        if aspect < 2.0:
            score += SCORE_SQUARE_BONUS

    return score


def select_best_image(candidates, block_y_start, block_y_end, page_median_area):
    """Selecciona la mejor imagen para un bloque de producto."""
    if not candidates:
        return None

    scored = []
    for img in candidates:
        s = score_image_candidate(img, block_y_start, block_y_end, page_median_area)
        scored.append((s, img))

    scored.sort(key=lambda x: -x[0])

    best_score, best_img = scored[0]

    if best_score < 0:
        return None

    if len(scored) > 1 and scored[0][0] - scored[1][0] < 5:
        best_img["needs_vision"] = True

    return best_img


# ============================================================
# PASS 3: VALIDATION HARNESS
# ============================================================

def validate_product(product):
    """Certifica un producto individual."""
    issues = []

    if product["precio"] is None:
        issues.append("NO_PRICE")
    elif product.get("precio_suspicious"):
        issues.append("SUSPICIOUS_PRICE")

    if product["imagen"] is None:
        issues.append("NO_IMAGE")
    elif product.get("imagen_invalid"):
        issues.append("INVALID_IMAGE")

    if not product["descripcion"] or len(product["descripcion"]) < 5:
        issues.append("NO_DESCRIPTION")

    if not product["codigo"]:
        issues.append("NO_CODE")

    # Grading - NO_IMAGE es aceptable (páginas sin columna FOTO)
    # Solo cuentan como issues graves: NO_PRICE, NO_DESCRIPTION, NO_CODE
    critical_issues = [i for i in issues if i not in ("NO_IMAGE", "INVALID_IMAGE")]
    
    if not issues:
        return "A+", []
    elif not critical_issues:
        # Solo tiene NO_IMAGE → A (honesto, no hay foto en catálogo)
        return "A", issues
    elif len(critical_issues) == 1 and critical_issues[0] == "NO_PRICE":
        return "B", issues
    elif len(critical_issues) == 1:
        return "B", issues  # Solo un issue crítico → B
    elif len(critical_issues) == 2:
        return "C", issues
    else:
        return "F", issues


def validate_catalog(products):
    """Certifica el catálogo completo."""
    grades = Counter()
    all_issues = Counter()

    for p in products:
        grade, issues = validate_product(p)
        p["grade"] = grade
        p["issues"] = issues
        grades[grade] += 1
        for issue in issues:
            all_issues[issue] += 1

    total = len(products)
    a_plus = grades.get("A+", 0)
    a = grades.get("A", 0)

    catalog_pct = (a_plus + a) * 100 // total if total else 0

    catalog_grade = "A+" if catalog_pct >= 95 else \
                    "A" if catalog_pct >= 85 else \
                    "B" if catalog_pct >= 70 else \
                    "C" if catalog_pct >= 50 else "F"

    # Calculate additional metrics
    with_price = sum(1 for p in products if p["precio"] is not None)
    with_image = sum(1 for p in products if p["imagen"] is not None)

    report = {
        "total": total,
        "grades": dict(grades),
        "catalog_grade": catalog_grade,
        "catalog_a_pct": catalog_pct,
        "issues_summary": dict(all_issues),
        "products_a_plus": a_plus,
        "products_a": a,
        "products_needing_draft": grades.get("B", 0) + grades.get("C", 0) + grades.get("F", 0),
        "with_price": with_price,
        "with_price_pct": round(with_price * 100 / total, 1) if total else 0,
        "with_image": with_image,
        "with_image_pct": round(with_image * 100 / total, 1) if total else 0,
    }

    return report


def print_certification_report(report, empresa):
    """Imprime reporte de certificación estilo ODI."""
    print(f"\n{'='*60}")
    print(f"  CERTIFICACIÓN {empresa} — GRADO {report['catalog_grade']}")
    print(f"{'='*60}")
    print(f"")
    print(f"  Total productos:     {report['total']}")
    print(f"  Con precio:          {report['with_price']} ({report['with_price_pct']}%)")
    print(f"  Con imagen:          {report['with_image']} ({report['with_image_pct']}%)")
    print(f"")
    print(f"  A+ (completo):       {report['grades'].get('A+', 0):>5d}")
    print(f"  A  (sin imagen):     {report['grades'].get('A', 0):>5d}")
    print(f"  B  (sin precio):     {report['grades'].get('B', 0):>5d}")
    print(f"  C  (múltiples gaps): {report['grades'].get('C', 0):>5d}")
    print(f"  F  (inservible):     {report['grades'].get('F', 0):>5d}")
    print(f"")
    print(f"  % A+/A:              {report['catalog_a_pct']}%")
    print(f"  Para Shopify draft:  {report['products_needing_draft']}")
    print(f"")

    if report["issues_summary"]:
        print(f"  Issues:")
        for issue, count in sorted(report["issues_summary"].items(), key=lambda x: -x[1]):
            print(f"    {issue}: {count}")

    if report["catalog_grade"] in ["A+", "A"]:
        print(f"\n  ✅ APROBADO para Shopify")
    else:
        print(f"\n  ⚠️ REQUIERE Pass 2 (Vision AI)")


# ============================================================
# EXTRACTOR PRINCIPAL
# ============================================================

class PdfIndustrialExtractor:
    """Motor de extracción industrial para catálogos PDF."""

    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)

    def process_catalog(self, pdf_path, config):
        """Procesa catálogo con Pass 1 (sin Vision AI)."""
        print(f"\n{'='*60}")
        print(f"PDF INDUSTRIAL EXTRACTOR v2")
        print(f"{'='*60}")
        print(f"PDF: {pdf_path}")
        print(f"Empresa: {config['codigo']}")
        print(f"Inicio: {datetime.now()}")

        doc = fitz.open(pdf_path)
        print(f"Páginas: {len(doc)}")

        # PASS 1
        print(f"\nPASS 1 — Extracción por coordenadas...")
        products = self._pass1_extract(doc, config)
        print(f"  Pass 1: {len(products)} productos extraídos")

        # PASS 3 - Validation
        print(f"\nPASS 3 — Validation Harness...")
        report = validate_catalog(products)
        print_certification_report(report, config["codigo"])

        # Identify products needing Vision
        vision_needed = []
        for p in products:
            reasons = []
            if p["precio"] is None:
                reasons.append("NO_PRICE")
            if p.get("precio_suspicious"):
                reasons.append("SUSPICIOUS_PRICE")
            if p["imagen"] is None:
                reasons.append("NO_IMAGE")
            if p.get("imagen", {}) and isinstance(p.get("imagen"), dict) and p["imagen"].get("needs_vision"):
                reasons.append("AMBIGUOUS_IMAGE")
            if reasons:
                vision_needed.append({
                    "codigo": p["codigo"],
                    "pagina": p["pagina"],
                    "reasons": reasons
                })

        # Save results
        self._save_results(products, report, vision_needed, config)

        doc.close()
        print(f"\nFin: {datetime.now()}")

        return products, report

    def _pass1_extract(self, doc, config):
        """Pass 1: extracción por coordenadas."""
        products = []
        seen_codes = {}
        code_pattern = re.compile(config["code_pattern"])

        for page_num in range(len(doc)):
            page = doc[page_num]
            text_items = self._extract_text_items(page)
            codes = self._detect_codes(text_items, config, code_pattern)

            if not codes:
                continue

            page_median = calculate_page_median_area(page)

            for i, code in enumerate(codes):
                y_start = code["y"]
                y_end = codes[i+1]["y"] - 2 if i < len(codes)-1 else config["footer_y"]

                # Duplicates control
                if code["codigo"] in seen_codes:
                    seen_codes[code["codigo"]] += 1
                else:
                    seen_codes[code["codigo"]] = 1

                # Price
                price_data = parse_price_cop(text_items, y_start, y_end)

                # Description
                desc = self._extract_description(text_items, y_start, y_end, config)

                # Empaque
                empaque = self._extract_empaque(text_items, y_start, y_end)

                # Image
                img_candidates = self._get_image_candidates(page, y_start, y_end)
                best_img = select_best_image(img_candidates, y_start, y_end, page_median)

                img_result = None
                if best_img:
                    img_result = self._extract_image(doc, page, best_img, code["codigo"])

                product = {
                    "codigo": code["codigo"],
                    "descripcion": desc,
                    "precio": price_data["valor"] if price_data else None,
                    "precio_suspicious": price_data["suspicious"] if price_data else False,
                    "precio_raw": price_data["raw"] if price_data else None,
                    "empaque": empaque,
                    "imagen": img_result,
                    "pagina": page_num + 1,
                    "y_start": y_start,
                    "y_end": y_end,
                    "empresa": config["codigo"],
                }

                # FIX C: Precios truncados - les falta ".000" (miles)
                # EXCEPCIÓN: págs 149, 181 (tornillería/fusibles = unitario real)
                PAGES_UNIT_PRICE = {149, 181}
                if product["precio"] and product["precio"] < 200:
                    if product["pagina"] not in PAGES_UNIT_PRICE:
                        product["precio"] = product["precio"] * 1000
                        product["precio_suspicious"] = False

                products.append(product)

            if (page_num + 1) % 50 == 0:
                print(f"  Página {page_num + 1}/{len(doc)}: {len(products)} productos")

        return products

    def _extract_text_items(self, page):
        """Extrae items de texto con coordenadas."""
        items = []
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    items.append({
                        "text": span["text"].strip(),
                        "x0": span["bbox"][0],
                        "y0": span["bbox"][1],
                        "x1": span["bbox"][2],
                        "y1": span["bbox"][3],
                    })

        return items

    def _detect_codes(self, text_items, config, pattern):
        """Detecta códigos de producto en la página."""
        codes = []

        for ti in text_items:
            if ti["x0"] > config["code_column_x_max"]:
                continue
            if ti["y0"] < config["header_y"]:
                continue

            text = ti["text"].strip()
            if pattern.match(text):
                codes.append({
                    "codigo": text,
                    "y": ti["y0"],
                    "x": ti["x0"],
                })

        # Sort by Y position
        codes.sort(key=lambda c: c["y"])
        return codes

    def _extract_description(self, text_items, y_start, y_end, config):
        """Extrae descripción del bloque con concatenación multiline."""
        desc_items = []
        for ti in text_items:
            if ti["y0"] < y_start or ti["y0"] > y_end:
                continue
            # Rango descripción: x: 95-420
            if 95 < ti["x0"] < 420:
                text = ti["text"].strip()
                if text and len(text) > 1:
                    import re as re2
                    if re2.match(r'^(X[0-9]+|PAR|UND|JUEGO|KIT)$', text, re2.I):
                        continue
                    desc_items.append({"text": text, "y": ti["y0"], "x": ti["x0"]})
        
        if not desc_items:
            return ""
        
        desc_items.sort(key=lambda t: (t["y"], t["x"]))
        
        lines = []
        current_line = []
        last_y = None
        
        for item in desc_items:
            if last_y is not None and abs(item["y"] - last_y) < 12:
                current_line.append(item["text"])
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [item["text"]]
            last_y = item["y"]
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return " ".join(lines)

    def _extract_empaque(self, text_items, y_start, y_end):
        """Extrae empaque del bloque."""
        for ti in text_items:
            if ti["y0"] < y_start or ti["y0"] > y_end:
                continue
            text = ti["text"].strip().upper()
            if re.match(r'^X\d+$', text):
                return text
            if text in ["PAR", "UND", "JUEGO", "KIT"]:
                return text
        return None

    def _get_image_candidates(self, page, y_start, y_end):
        """Obtiene candidatos de imagen para un bloque."""
        candidates = []

        for img_info in page.get_images(full=True):
            xref = img_info[0]
            try:
                for rect in page.get_image_rects(xref):
                    # Check if image overlaps with block
                    if rect.y1 < y_start - 20 or rect.y0 > y_end + 20:
                        continue

                    candidates.append({
                        "xref": xref,
                        "x0": rect.x0,
                        "y0": rect.y0,
                        "x1": rect.x1,
                        "y1": rect.y1,
                        "width": rect.width,
                        "height": rect.height,
                        "area": rect.width * rect.height,
                    })
            except:
                pass

        return candidates

    def _extract_image(self, doc, page, img_info, codigo):
        """Extrae y guarda imagen."""
        try:
            xref = img_info["xref"]
            base_image = doc.extract_image(xref)

            if not base_image:
                return None

            img_bytes = base_image["image"]
            ext = base_image["ext"]

            # Save as PNG
            filename = f"{codigo}.png"
            filepath = os.path.join(self.output_dir, "images", filename)

            # Convert to PNG if needed
            from io import BytesIO
            img = Image.open(BytesIO(img_bytes))
            img.save(filepath, "PNG")

            return {
                "path": filepath,
                "filename": filename,
                "width": img_info["width"],
                "height": img_info["height"],
                "size": os.path.getsize(filepath),
                "needs_vision": img_info.get("needs_vision", False),
            }
        except Exception as e:
            return None

    def _save_results(self, products, report, vision_needed, config):
        """Guarda resultados."""
        empresa = config["codigo"].lower()

        # Products JSON
        clean_products = []
        for p in products:
            clean = {
                "codigo": p["codigo"],
                "descripcion": p["descripcion"],
                "precio": p["precio"],
                "empaque": p["empaque"],
                "imagen": p["imagen"]["filename"] if p.get("imagen") else None,
                "pagina": p["pagina"],
                "grade": p.get("grade", "?"),
                "issues": p.get("issues", []),
            }
            clean_products.append(clean)

        products_path = os.path.join(self.output_dir, f"{empresa}_products_v2.json")
        with open(products_path, "w", encoding="utf-8") as f:
            json.dump(clean_products, f, indent=2, ensure_ascii=False)

        # Validation report
        report_path = os.path.join(self.output_dir, f"{empresa}_validation_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Vision needed
        vision_path = os.path.join(self.output_dir, f"{empresa}_vision_needed.json")
        with open(vision_path, "w", encoding="utf-8") as f:
            json.dump(vision_needed, f, indent=2, ensure_ascii=False)

        print(f"\n  Productos: {products_path}")
        print(f"  Reporte: {report_path}")
        print(f"  Vision needed: {vision_path} ({len(vision_needed)} productos)")
        print(f"  Imágenes: {self.output_dir}/images/")


# ============================================================
# MAIN
# ============================================================

def main():
    config = EMPRESA_CONFIGS["ARMOTOS"]
    output_dir = "/opt/odi/data/ARMOTOS"

    extractor = PdfIndustrialExtractor(output_dir)
    products, report = extractor.process_catalog(config["pdf_path"], config)

    return products, report


if __name__ == "__main__":
    main()
