#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PAEM API v2.2.1 — Standalone FastAPI app (puerto 8807)
======================================================
Protocolo de Activación Económica Multindustria.

Endpoints:
  GET  /health          → Health check del servicio
  POST /paem/pay/init   → Iniciar checkout Wompi con firma
  POST /webhooks/wompi  → Webhook de eventos Wompi (atómico)

Dominio: https://api.adsi.com.co
Puerto interno: 8807
Proxy: Nginx → 127.0.0.1:8807

Inicio: uvicorn core.industries.turismo.paem_api:app --host 0.0.0.0 --port 8807

Versión: 2.2.1 — 13 Feb 2026
"""

import logging
import os
import sys
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Asegurar que los imports de core/ funcionen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

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
    description="Protocolo de Activación Económica Multindustria v2.2.1 — Metabolismo económico ODI",
    version="2.2.1",
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
        "version": "2.2.1",
        "postgres": pg_ok,
        "redis": redis_ok,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PAEM_API_PORT", "8807"))
    logger.info("Starting PAEM API on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
