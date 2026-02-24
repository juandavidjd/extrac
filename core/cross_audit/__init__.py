"""
ODI Cross-Audit Engine v1.0
===========================
"El que genera los datos NUNCA los audita."

Módulo de auditoría cruzada independiente del pipeline.
Lee datos de PostgreSQL + Shopify API real.
Compara contra datos fuente originales.
Evalúa 12 criterios semánticos.
Genera reporte con trazabilidad criptográfica.

Autor: ODI Architecture
Fecha: 2026-02-21
"""

from .engine import CrossAuditEngine
from .criteria import SemanticCriteria
from .reporter import AuditReporter

__all__ = ['CrossAuditEngine', 'SemanticCriteria', 'AuditReporter']
__version__ = '1.0.0'
