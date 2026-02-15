#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PAEM API v2.3.0 — Standalone FastAPI app (puerto 8807)
======================================================
Protocolo de Activación Económica Multindustria.

Endpoints:
  GET  /health              → Health check del servicio
  POST /paem/pay/init       → Iniciar checkout Wompi con firma
  POST /webhooks/wompi      → Webhook de eventos Wompi (atómico)
  POST /odi/auth/login      → Login humano (TOTP → JWT)
  POST /odi/override        → Override humano seguro (JWT + TOTP)
  GET  /odi/override/status → Estado del sistema de overrides

Dominio: https://api.adsi.com.co
Puerto interno: 8807
Proxy: Nginx → 127.0.0.1:8807

Versión: 2.3.0 — 15 Feb 2026
  v2.2.1: PAEM v2.2.1 (HOLD + confirm + rate limit)
  v2.3.0: V8.2 Override Humano Seguro (JWT + TOTP + encadenamiento)
"""

import logging
import os
import sys
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Asegurar que los imports de core/ funcionen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, "/opt/odi/core")

from core.industries.turismo.payments_api import router as payments_router

# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("odi.paem.api")


# ══════════════════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="ODI PAEM API",
    description="Protocolo de Activación Económica Multindustria v2.3.0 — Override Humano Seguro",
    version="2.3.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar rutas de pagos
app.include_router(payments_router)


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    """Health check del servicio PAEM."""
    from core.industries.turismo.db.client import pg_available, redis_available

    pg_ok = pg_available()
    redis_ok = redis_available()

    return {
        "ok": True,
        "service": "odi-paem",
        "version": "2.3.0",
        "postgres": pg_ok,
        "redis": redis_ok,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ══════════════════════════════════════════════════════════════════════════════
# V8.2 — OVERRIDE HUMANO SEGURO
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/odi/auth/login")
async def odi_auth_login(request: Request):
    """Login humano — TOTP válido → JWT con TTL corto."""
    from odi_override import obtener_auth

    body = await request.json()
    human_id = body.get("human_id")
    totp_code = body.get("totp_code")

    if not human_id or not totp_code:
        return JSONResponse(status_code=400, content={
            "error": "Campos requeridos: human_id, totp_code"
        })

    auth = obtener_auth()
    valid = await auth.validate_totp(human_id, totp_code)
    if not valid:
        return JSONResponse(status_code=401, content={"error": "Credenciales inválidas"})

    pool = await auth._get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT role, vertical_scope FROM odi_humans WHERE human_id = $1 AND is_active = true",
            human_id
        )
    if not row:
        return JSONResponse(status_code=401, content={"error": "Humano no encontrado"})

    ttl = int(os.getenv("ODI_OVERRIDE_TTL_MINUTES", "10"))
    token = auth.generate_jwt(human_id, row["role"], row["vertical_scope"], ttl)
    logger.info("Auth login: %s (%s)", human_id, row["role"])
    return {"ok": True, "token": token, "role": row["role"], "ttl_minutes": ttl}


@app.post("/odi/override")
async def odi_override(request: Request):
    """Override humano seguro — requiere JWT + TOTP."""
    from odi_override import obtener_override_engine

    engine = obtener_override_engine()

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "JWT requerido"})
    jwt_token = auth_header[7:]

    totp_code = request.headers.get("X-ODI-TOTP", "")
    if not totp_code or len(totp_code) != 6:
        return JSONResponse(status_code=401, content={"error": "TOTP requerido (6 dígitos)"})

    body = await request.json()
    original_event_id = body.get("original_odi_event_id")
    target_decision = body.get("target_decision")
    reason = body.get("reason", "")
    evidence = body.get("evidence", {})

    if not all([original_event_id, target_decision, reason]):
        return JSONResponse(status_code=400, content={
            "error": "Campos requeridos: original_odi_event_id, target_decision, reason"
        })

    success, result = await engine.execute_override(
        jwt_token=jwt_token,
        totp_code=totp_code,
        original_event_id=original_event_id,
        target_decision=target_decision,
        reason=reason,
        evidence=evidence
    )

    if not success:
        return JSONResponse(status_code=403, content={"ok": False, **result})

    return {"ok": True, **result}


@app.get("/odi/override/status")
async def override_status():
    """Estado del sistema de overrides."""
    from odi_override import obtener_override_engine

    try:
        pool = await obtener_override_engine()._get_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM odi_overrides")
            by_decision = await conn.fetch(
                "SELECT decision, count(*) as total FROM odi_overrides GROUP BY decision"
            )
            ultimo = await conn.fetchval("SELECT MAX(timestamp) FROM odi_overrides")
            humans = await conn.fetchval("SELECT COUNT(*) FROM odi_humans WHERE is_active = true")
        return {
            "total_overrides": total,
            "ultimo": ultimo.isoformat() if ultimo else None,
            "por_decision": [dict(r) for r in by_decision],
            "humans_activos": humans,
            "ttl_minutes": int(os.getenv("ODI_OVERRIDE_TTL_MINUTES", "10")),
            "version": "8.2.0"
        }
    except Exception as e:
        return {"error": str(e), "version": "8.2.0"}


# ══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PAEM_API_PORT", "8807"))
    logger.info("Starting PAEM API on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
