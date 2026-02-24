"""
Cross-Audit Engine v1.0
==========================

Orquestador principal. Lee PostgreSQL + Shopify API.
Ejecuta los 12 criterios. Genera findings. Calcula health_score.
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

import asyncpg
import httpx

from .criteria import SemanticCriteria
from .reporter import AuditReporter

logger = logging.getLogger("odi.cross_audit")


class CrossAuditEngine:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "postgresql://odi:odi@172.18.0.8:5432/odi")
        self.pool = None
        self.reporter = AuditReporter()

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.db_url, min_size=2, max_size=5)
        logger.info("Cross-Audit Engine conectado a PostgreSQL")

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def audit_empresa(self, empresa_codigo: str, auditor: str = "claude", trigger_type: str = "manual", sample_size: int = 30, git_commit: str = None, git_branch: str = None, pr_number: int = None) -> Dict:
        async with self.pool.acquire() as conn:
            empresa = await conn.fetchrow("SELECT * FROM empresas WHERE codigo = $1", empresa_codigo)
            if not empresa:
                raise ValueError(f"Empresa {empresa_codigo} no encontrada")
            rules = await self._get_rules(conn, empresa["id"])
            criteria = SemanticCriteria(rules)
            audit_id = await conn.fetchval("INSERT INTO cross_audits (empresa_id, auditor, auditor_model, trigger_type, git_commit, git_branch, pr_number, status) VALUES ($1, $2, $3, $4, $5, $6, $7, 'running') RETURNING id", empresa["id"], auditor, f"{auditor}-v1.0", trigger_type, git_commit, git_branch, pr_number)
            logger.info(f"Auditoria #{audit_id} iniciada para {empresa_codigo}")
            products = await conn.fetch("SELECT p.*, e.brand_color_primary, e.shopify_shop_url, e.shopify_api_password FROM productos p JOIN empresas e ON p.empresa_id = e.id WHERE e.codigo = $1 AND p.shopify_product_id IS NOT NULL ORDER BY RANDOM() LIMIT $2", empresa_codigo, sample_size)
            if not products:
                await self._finalize_audit(conn, audit_id, 0, 0, 0, 0.0, "failed", {})
                return {"status": "failed", "reason": "no_products"}
            total_aprobados = 0
            total_rechazados = 0
            all_findings = []
            shop_url = empresa["shopify_shop_url"]
            token = empresa["shopify_api_password"]
            for product in products:
                try:
                    shopify_data = await self._fetch_shopify_product(shop_url, token, product["shopify_product_id"])
                    if not shopify_data:
                        continue
                    result = criteria.evaluate_all(dict(product), shopify_data)
                    finding_data = {"audit_id": audit_id, "producto_id": product["id"], "titulo_shopify": shopify_data.get("title", ""), "titulo_fuente": product["titulo_raw"], "precio_fuente": float(product["precio_sin_iva"] or 0), "precio_shopify": float(shopify_data.get("variants", [{}])[0].get("price", 0)), **result}
                    await self._insert_finding(conn, finding_data)
                    all_findings.append(finding_data)
                    if result["severity"] == "pass":
                        total_aprobados += 1
                    else:
                        total_rechazados += 1
                except Exception as e:
                    logger.error(f"Error auditando producto {product['id']}: {e}")
                    total_rechazados += 1
            total = total_aprobados + total_rechazados
            health_score = round((total_aprobados / total) * 100, 2) if total > 0 else 0.0
            min_score = rules.get("min_health_score", 80.0)
            status = "approved" if health_score >= min_score else "changes_requested"
            report = self.reporter.generate(empresa_codigo, all_findings, health_score, status)
            hash_input = hashlib.sha256(json.dumps([dict(p) for p in products], default=str).encode()).hexdigest()
            hash_report = hashlib.sha256(json.dumps(report, default=str).encode()).hexdigest()
            await self._finalize_audit(conn, audit_id, total, total_aprobados, total_rechazados, health_score, status, report, hash_input, hash_report)
            logger.info(f"Auditoria #{audit_id} completada: {empresa_codigo} -> {health_score}% ({status})")
            return {"audit_id": audit_id, "empresa": empresa_codigo, "health_score": health_score, "status": status, "total": total, "aprobados": total_aprobados, "rechazados": total_rechazados, "hash_report": hash_report, "report": report}

    async def _fetch_shopify_product(self, shop_url: str, token: str, product_id: int) -> Optional[Dict]:
        url = f"https://{shop_url}/admin/api/2024-01/products/{product_id}.json"
        headers = {"X-Shopify-Access-Token": token}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    return resp.json().get("product", {})
                logger.warning(f"Shopify API {resp.status_code} para {product_id}")
                return None
        except Exception as e:
            logger.error(f"Error Shopify API: {e}")
            return None

    async def _get_rules(self, conn, empresa_id: int) -> Dict:
        row = await conn.fetchrow("SELECT * FROM audit_rules WHERE empresa_id = $1 AND active = true", empresa_id)
        if not row:
            row = await conn.fetchrow("SELECT * FROM audit_rules WHERE empresa_id IS NULL AND active = true")
        if row:
            rules = dict(row)
            for field in ["copypaste_blacklist", "fitment_brand_whitelist"]:
                if isinstance(rules.get(field), str):
                    rules[field] = json.loads(rules[field])
            return rules
        return {}

    async def _insert_finding(self, conn, data: Dict):
        await conn.execute("INSERT INTO audit_findings (audit_id, producto_id, criterio_titulo, criterio_descripcion, criterio_info_tecnica, criterio_compatibilidad, criterio_beneficios, criterio_precio, criterio_stock, criterio_imagen, criterio_sku, criterio_branding, criterio_vendor, criterio_categoria, score, severity, finding_detail, titulo_fuente, titulo_shopify, precio_fuente, precio_shopify, diff_detectado) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22)", data["audit_id"], data["producto_id"], data.get("criterio_titulo"), data.get("criterio_descripcion"), data.get("criterio_info_tecnica"), data.get("criterio_compatibilidad"), data.get("criterio_beneficios"), data.get("criterio_precio"), data.get("criterio_stock"), data.get("criterio_imagen"), data.get("criterio_sku"), data.get("criterio_branding"), data.get("criterio_vendor"), data.get("criterio_categoria"), data.get("score"), data.get("severity"), json.dumps(data.get("finding_detail", {})), data.get("titulo_fuente", ""), data.get("titulo_shopify", ""), data.get("precio_fuente", 0), data.get("precio_shopify", 0), data.get("precio_fuente") != data.get("precio_shopify"))

    async def _finalize_audit(self, conn, audit_id, total, aprobados, rechazados, health_score, status, report, hash_input=None, hash_report=None):
        await conn.execute("UPDATE cross_audits SET total_productos_auditados = $2, total_aprobados = $3, total_rechazados = $4, health_score = $5, status = $6, report_json = $7, hash_input = $8, hash_report = $9, finished_at = CURRENT_TIMESTAMP WHERE id = $1", audit_id, total, aprobados, rechazados, health_score, status, json.dumps(report, default=str), hash_input, hash_report)

    async def audit_all_empresas(self, **kwargs) -> List[Dict]:
        async with self.pool.acquire() as conn:
            empresas = await conn.fetch("SELECT codigo FROM empresas WHERE activa = true AND rama_id = (SELECT id FROM ramas WHERE codigo = 'SRM')")
        results = []
        for emp in empresas:
            try:
                result = await self.audit_empresa(emp["codigo"], **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Error auditando {emp['codigo']}: {e}")
                results.append({"empresa": emp["codigo"], "status": "error", "error": str(e)})
        return results
