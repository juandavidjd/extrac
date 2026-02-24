"""
Cross-Audit API v1.0
====================
Endpoint HTTP para ejecutar auditorías bajo demanda.
Puerto: 8808 (no colisiona con servicios existentes)
"""

import os
import asyncio
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from .engine import CrossAuditEngine

app = FastAPI(title="ODI Cross-Audit API", version="1.0.0")
engine = CrossAuditEngine()
logger = logging.getLogger('odi.cross_audit.api')


class AuditRequest(BaseModel):
    empresa: str
    auditor: str = 'claude'
    trigger_type: str = 'manual'
    sample_size: int = 30
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    pr_number: Optional[int] = None


class AuditAllRequest(BaseModel):
    auditor: str = 'claude'
    trigger_type: str = 'scheduled'
    sample_size: int = 10


@app.on_event("startup")
async def startup():
    await engine.connect()
    logger.info("Cross-Audit API v1.0 iniciada en :8808")


@app.on_event("shutdown")
async def shutdown():
    await engine.close()


@app.get("/health")
async def health():
    return {
        "service": "odi-cross-audit",
        "version": "1.0.0",
        "status": "operational",
        "principle": "El que genera NUNCA audita"
    }


@app.post("/audit/empresa")
async def audit_empresa(req: AuditRequest):
    """Auditar una empresa específica."""
    try:
        result = await engine.audit_empresa(
            empresa_codigo=req.empresa,
            auditor=req.auditor,
            trigger_type=req.trigger_type,
            sample_size=req.sample_size,
            git_commit=req.git_commit,
            git_branch=req.git_branch,
            pr_number=req.pr_number
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error en auditoría: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit/all")
async def audit_all(req: AuditAllRequest):
    """Auditar TODAS las empresas SRM."""
    try:
        results = await engine.audit_all_empresas(
            auditor=req.auditor,
            trigger_type=req.trigger_type,
            sample_size=req.sample_size
        )
        return {
            "total_empresas": len(results),
            "aprobadas": sum(1 for r in results if r.get('status') == 'approved'),
            "rechazadas": sum(1 for r in results if r.get('status') == 'changes_requested'),
            "errores": sum(1 for r in results if r.get('status') in ('error', 'failed')),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit/health/{empresa}")
async def get_health(empresa: str):
    """Consultar última auditoría de una empresa."""
    async with engine.pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM v_health_por_empresa WHERE empresa = $1
        """, empresa)
        if not row:
            raise HTTPException(status_code=404, detail="Sin auditorías")
        return dict(row)


@app.get("/audit/bugs")
async def get_bugs():
    """Consultar bugs sistémicos activos en todo el ecosistema."""
    async with engine.pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM v_bugs_sistemicos")
        return [dict(r) for r in rows]


@app.get("/audit/history")
async def get_history(limit: int = 20):
    """Historial de auditorías."""
    async with engine.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM v_audit_history LIMIT $1", limit)
        return [dict(r) for r in rows]


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8808)
