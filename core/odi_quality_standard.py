#!/usr/bin/env python3
"""
ODI A+ Minimum Quality Standard
Política del organismo. No se negocia.
7 Gates de certificación.
"""

from collections import Counter

class QualityStandard:
    VERSION = "1.0"
    
    GATES = [
        "titulo_especifico",
        "descripcion_real",
        "compatibilidad_estructurada",
        "categoria_catrmu",
        "beneficios_por_categoria",
        "imagen_real",
        "precio_verificado",
    ]
    
    @staticmethod
    def evaluate(product: dict) -> dict:
        results = {}
        issues = []
        
        # Gate 1: Título específico
        title = product.get("title", product.get("descripcion", ""))
        generic_titles = ["repuesto", "producto", "artículo", "item", "pieza"]
        is_generic = any(g in str(title).lower() for g in generic_titles) and len(str(title)) < 30
        results["titulo_especifico"] = not is_generic and len(str(title)) > 5
        if not results["titulo_especifico"]:
            issues.append("TITULO_GENERICO")
        
        # Gate 2: Descripción real
        desc = product.get("description", product.get("descripcion", ""))
        has_real_desc = len(str(desc)) > 15
        results["descripcion_real"] = has_real_desc
        if not results["descripcion_real"]:
            issues.append("DESCRIPCION_GENERICA")
        
        # Gate 3: Compatibilidad (opcional para A)
        compat = product.get("compatibilidad", product.get("compatibility", []))
        results["compatibilidad_estructurada"] = bool(compat) and compat != ["Universal"]
        if not results["compatibilidad_estructurada"]:
            issues.append("SIN_COMPATIBILIDAD")
        
        # Gate 4: Categoría CATRMU
        cat = product.get("categoria", product.get("product_type", product.get("sistema", "")))
        results["categoria_catrmu"] = bool(cat) and str(cat).lower() not in ["default", "", "sin categoría"]
        if not results["categoria_catrmu"]:
            issues.append("SIN_CATEGORIA")
        
        # Gate 5: Beneficios por categoría
        benefits = product.get("beneficios", product.get("benefits", ""))
        results["beneficios_por_categoria"] = len(str(benefits)) > 20
        if not results["beneficios_por_categoria"]:
            issues.append("BENEFICIOS_GENERICOS")
        
        # Gate 6: Imagen real (opcional para A)
        img = product.get("imagen", product.get("image", product.get("imagen_hd")))
        results["imagen_real"] = bool(img) and "placeholder" not in str(img).lower()
        if not results["imagen_real"]:
            issues.append("SIN_IMAGEN")
        
        # Gate 7: Precio verificado
        price = product.get("precio", product.get("price", 0))
        try:
            price = float(price) if price else 0
        except:
            price = 0
        results["precio_verificado"] = 200 <= price <= 5000000
        if not results["precio_verificado"]:
            issues.append("PRECIO_INVALIDO")
        
        # Scoring
        score = sum(1 for v in results.values() if v)
        
        # Grading - adaptar a Pass 1 (sin beneficios ni compatibilidad completa)
        critical_issues = [i for i in issues if i not in ("SIN_IMAGEN", "SIN_COMPATIBILIDAD", "BENEFICIOS_GENERICOS", "SIN_CATEGORIA")]
        
        if not critical_issues:
            if score >= 5:
                grade = "A+"
            else:
                grade = "A"
        elif len(critical_issues) == 1:
            grade = "B"
        elif len(critical_issues) == 2:
            grade = "C"
        else:
            grade = "F"
        
        return {
            "grade": grade,
            "score": score,
            "max_score": 7,
            "gates": results,
            "issues": issues,
            "shopify_status": "active" if grade in ["A+", "A"] else "draft",
        }
    
    @staticmethod
    def evaluate_catalog(products: list) -> dict:
        grades = Counter()
        all_issues = Counter()
        
        for p in products:
            result = QualityStandard.evaluate(p)
            p["_quality"] = result
            grades[result["grade"]] += 1
            for issue in result["issues"]:
                all_issues[issue] += 1
        
        total = len(products)
        a_plus = grades.get("A+", 0)
        a = grades.get("A", 0)
        catalog_pct = (a_plus + a) * 100 // total if total else 0
        
        catalog_grade = (
            "A+" if catalog_pct >= 95 else
            "A"  if catalog_pct >= 85 else
            "B"  if catalog_pct >= 70 else
            "C"  if catalog_pct >= 50 else
            "F"
        )
        
        return {
            "total": total,
            "grades": dict(grades),
            "catalog_grade": catalog_grade,
            "a_plus_a_pct": catalog_pct,
            "issues": dict(all_issues),
            "publishable": grades.get("A+", 0) + grades.get("A", 0),
            "draft": grades.get("B", 0) + grades.get("C", 0),
            "rejected": grades.get("F", 0),
        }


if __name__ == "__main__":
    # Test
    test_product = {
        "codigo": "04417",
        "descripcion": "GUARDAPOLVO UNIVERSAL (LENGÜETA)",
        "precio": 2250,
        "imagen": "04417.png",
    }
    result = QualityStandard.evaluate(test_product)
    print(f"Test product: {result}")
