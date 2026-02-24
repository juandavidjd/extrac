"""
Audit Reporter v1.0
===================
Genera reportes estructurados con recomendaciones.
"""

import json
from datetime import datetime
from typing import Dict, List, Any


class AuditReporter:
    """Generador de reportes de auditoria."""

    def generate(self, empresa: str, findings: List[Dict],
                 health_score: float, status: str) -> Dict:
        """Generar reporte completo."""
        # Conteo de fallas por criterio
        criteria_stats = {}
        for f in findings:
            for key in [k for k in f.keys() if k.startswith("criterio_")]:
                if key not in criteria_stats:
                    criteria_stats[key] = {"pass": 0, "fail": 0}
                if f[key] == 1:
                    criteria_stats[key]["pass"] += 1
                elif f[key] == 0:
                    criteria_stats[key]["fail"] += 1

        # Top 3 problemas
        problems_sorted = sorted(
            [(k, v["fail"]) for k, v in criteria_stats.items()],
            key=lambda x: x[1], reverse=True
        )
        top_problems = problems_sorted[:3]

        # Blockers (productos con score < 50)
        blockers = [f for f in findings if f.get("severity") == "blocker"]

        return {
            "empresa": empresa,
            "health_score": health_score,
            "status": status,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_auditados": len(findings),
                "aprobados": sum(1 for f in findings if f.get("severity") == "pass"),
                "warnings": sum(1 for f in findings if f.get("severity") == "warning"),
                "critical": sum(1 for f in findings if f.get("severity") == "critical"),
                "blockers": len(blockers),
            },
            "criteria_stats": criteria_stats,
            "top_problems": [
                {"criterio": k.replace("criterio_", ""), "fallas": v}
                for k, v in top_problems
            ],
            "blocker_products": [
                {"producto_id": b["producto_id"],
                 "titulo": b.get("titulo_shopify", ""),
                 "score": b.get("score", 0)}
                for b in blockers[:10]
            ],
            "recommendation": self._recommend(health_score, top_problems),
        }

    def _recommend(self, score: float, top_problems: list) -> str:
        if score >= 90:
            return "APROBADA. Tienda lista para Caso 001."
        elif score >= 70:
            return (f"CORREGIR {len(top_problems)} problemas principales "
                    f"antes de produccion.")
        elif score >= 50:
            return "REQUIERE re-procesamiento por pipeline corregido."
        else:
            return "BLOQUEADA. Pipeline debe repararse antes de re-auditar."
