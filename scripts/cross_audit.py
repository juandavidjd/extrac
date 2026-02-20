#!/usr/bin/env python3
"""
ODI Cross-Audit System v1.0
Sistema de auditoría cruzada para el ecosistema de tiendas Shopify.
Utiliza GPT-4o para análisis inteligente de datos entre tiendas.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

import requests

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constantes
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o"
MAX_TOKENS = 4096


@dataclass
class AuditResult:
    """Resultado de una auditoría individual."""
    store_name: str
    product_count: int
    issues_found: List[Dict[str, Any]]
    recommendations: List[str]
    score: float
    timestamp: str


@dataclass
class CrossAuditReport:
    """Reporte completo de auditoría cruzada."""
    total_stores: int
    total_products: int
    audit_results: List[AuditResult]
    cross_store_issues: List[Dict[str, Any]]
    overall_health_score: float
    generated_at: str


class CrossAuditSystem:
    """Sistema principal de auditoría cruzada ODI."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa el sistema de auditoría.

        Args:
            api_key: OpenAI API key. Si no se proporciona, se lee de OPENAI_API_KEY.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY no encontrada en variables de entorno")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _call_gpt4o(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Realiza llamada a GPT-4o con respuesta en formato JSON.

        Args:
            system_prompt: Instrucciones del sistema.
            user_prompt: Prompt del usuario con datos a analizar.

        Returns:
            Respuesta parseada como diccionario JSON.
        """
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(
                OPENAI_API_URL,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error en llamada a OpenAI: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta JSON: {e}")
            raise

    def audit_store(self, store_name: str, products: List[Dict]) -> AuditResult:
        """
        Audita una tienda individual.

        Args:
            store_name: Nombre de la tienda.
            products: Lista de productos de la tienda.

        Returns:
            Resultado de la auditoría.
        """
        system_prompt = """Eres un experto auditor de catálogos de productos para tiendas Shopify.
Analiza los productos proporcionados y genera un reporte de auditoría en formato JSON con:
- issues_found: lista de problemas encontrados (duplicados, precios inconsistentes, datos faltantes)
- recommendations: lista de recomendaciones de mejora
- score: puntuación de salud del catálogo (0-100)

Responde SOLO con JSON válido."""

        user_prompt = f"""Audita el catálogo de la tienda {store_name}.
Total de productos: {len(products)}
Muestra de productos (primeros 50):
{json.dumps(products[:50], ensure_ascii=False, indent=2)}"""

        result = self._call_gpt4o(system_prompt, user_prompt)

        return AuditResult(
            store_name=store_name,
            product_count=len(products),
            issues_found=result.get("issues_found", []),
            recommendations=result.get("recommendations", []),
            score=result.get("score", 0.0),
            timestamp=datetime.utcnow().isoformat()
        )

    def cross_audit(self, stores_data: Dict[str, List[Dict]]) -> CrossAuditReport:
        """
        Realiza auditoría cruzada entre múltiples tiendas.

        Args:
            stores_data: Diccionario {nombre_tienda: lista_productos}

        Returns:
            Reporte completo de auditoría cruzada.
        """
        logger.info(f"Iniciando Cross-Audit para {len(stores_data)} tiendas")

        audit_results: List[AuditResult] = []
        total_products = 0

        for store_name, products in stores_data.items():
            logger.info(f"Auditando tienda: {store_name} ({len(products)} productos)")
            result = self.audit_store(store_name, products)
            audit_results.append(result)
            total_products += len(products)

        cross_store_issues = self._analyze_cross_store(stores_data)
        overall_score = sum(r.score for r in audit_results) / len(audit_results) if audit_results else 0

        return CrossAuditReport(
            total_stores=len(stores_data),
            total_products=total_products,
            audit_results=audit_results,
            cross_store_issues=cross_store_issues,
            overall_health_score=overall_score,
            generated_at=datetime.utcnow().isoformat()
        )

    def _analyze_cross_store(self, stores_data: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
        """
        Analiza inconsistencias entre tiendas.

        Args:
            stores_data: Datos de todas las tiendas.

        Returns:
            Lista de problemas encontrados entre tiendas.
        """
        system_prompt = """Eres un analista experto en ecosistemas de e-commerce.
Analiza los datos de múltiples tiendas y encuentra:
- Productos duplicados entre tiendas
- Inconsistencias de precios para el mismo SKU
- Oportunidades de optimización cruzada
- Problemas de inventario compartido

Responde con JSON conteniendo:
- cross_store_issues: lista de problemas encontrados con severity (low/medium/high/critical)"""

        summary = {}
        for store, products in stores_data.items():
            skus = [p.get("sku", "") for p in products[:100]]
            summary[store] = {
                "product_count": len(products),
                "sample_skus": skus[:20]
            }

        user_prompt = f"""Analiza las siguientes tiendas para encontrar inconsistencias:
{json.dumps(summary, ensure_ascii=False, indent=2)}"""

        result = self._call_gpt4o(system_prompt, user_prompt)
        return result.get("cross_store_issues", [])

    def save_report(self, report: CrossAuditReport, output_path: str = "audit-report.json"):
        """Guarda el reporte en formato JSON."""
        report_dict = {
            "total_stores": report.total_stores,
            "total_products": report.total_products,
            "audit_results": [asdict(r) for r in report.audit_results],
            "cross_store_issues": report.cross_store_issues,
            "overall_health_score": report.overall_health_score,
            "generated_at": report.generated_at
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        logger.info(f"Reporte guardado en: {output_path}")


def main():
    """Punto de entrada principal."""
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY no configurada")
        sys.exit(1)

    auditor = CrossAuditSystem()

    # Datos de prueba - en producción se cargarían desde /opt/odi/data/orden_maestra_v6/
    test_data = {
        "DFG": [{"sku": "DFG-001", "name": "Filtro aceite", "price": 25000}],
        "ARMOTOS": [{"sku": "ARM-001", "name": "Cadena 428", "price": 45000}],
        "YOKOMAR": [{"sku": "YOK-001", "name": "Kit arrastre", "price": 120000}]
    }

    report = auditor.cross_audit(test_data)
    auditor.save_report(report)

    print(f"Cross-Audit completado: {report.total_stores} tiendas, score: {report.overall_health_score:.1f}")
    return 0 if report.overall_health_score >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
