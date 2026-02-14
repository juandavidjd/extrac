#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB Client — Capa de conexión Postgres + Redis para Industria Turismo
=====================================================================
Jerarquía de verdad:
  1. Redis (cache, TTL 300s) — si disponible
  2. Postgres (verdad base) — si disponible
  3. JSON local (fallback demo) — siempre disponible

El router nunca falla: degrada gracefully.

Env vars:
  ODI_PG_HOST, ODI_PG_PORT, ODI_PG_USER, ODI_PG_PASS, ODI_PG_DB
  ODI_REDIS_HOST, ODI_REDIS_PORT

Versión: 1.0.0 — 13 Feb 2026
"""

import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

logger = logging.getLogger("odi.turismo.db")

# ══════════════════════════════════════════════════════════════════════════════
# POSTGRES
# ══════════════════════════════════════════════════════════════════════════════

_pg_pool = None

PG_CONFIG = {
    "host": os.getenv("ODI_PG_HOST", "127.0.0.1"),
    "port": int(os.getenv("ODI_PG_PORT", "5432")),
    "user": os.getenv("ODI_PG_USER", "odi"),
    "password": os.getenv("ODI_PG_PASS", "odi"),
    "dbname": os.getenv("ODI_PG_DB", "odi"),
}


def _get_pg_pool():
    """Lazy init de connection pool Postgres."""
    global _pg_pool
    if _pg_pool is not None:
        return _pg_pool
    try:
        import psycopg2
        from psycopg2 import pool as pg_pool
        _pg_pool = pg_pool.ThreadedConnectionPool(
            minconn=1, maxconn=5, **PG_CONFIG
        )
        logger.info("Postgres pool initialized: %s:%s/%s", PG_CONFIG["host"], PG_CONFIG["port"], PG_CONFIG["dbname"])
        return _pg_pool
    except Exception as e:
        logger.warning("Postgres not available: %s. Falling back to JSON.", e)
        return None


@contextmanager
def pg_connection():
    """Context manager para conexión Postgres del pool."""
    pool = _get_pg_pool()
    if pool is None:
        yield None
        return
    conn = None
    try:
        conn = pool.getconn()
        yield conn
    except Exception as e:
        logger.error("Postgres connection error: %s", e)
        yield None
    finally:
        if conn is not None:
            try:
                pool.putconn(conn)
            except Exception:
                pass


def pg_query(sql: str, params: tuple = None) -> Optional[List[Dict[str, Any]]]:
    """Ejecutar query y devolver lista de dicts. None si Postgres no disponible."""
    with pg_connection() as conn:
        if conn is None:
            return None
        try:
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Postgres query error: %s | SQL: %s", e, sql[:100])
            conn.rollback()
            return None


def pg_execute(sql: str, params: tuple = None) -> bool:
    """Ejecutar statement (INSERT/UPDATE). True si OK."""
    with pg_connection() as conn:
        if conn is None:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                conn.commit()
                return True
        except Exception as e:
            logger.error("Postgres execute error: %s | SQL: %s", e, sql[:100])
            conn.rollback()
            return False


def pg_available() -> bool:
    """Check rápido si Postgres responde."""
    result = pg_query("SELECT 1 AS ok")
    return result is not None and len(result) > 0


# ══════════════════════════════════════════════════════════════════════════════
# REDIS
# ══════════════════════════════════════════════════════════════════════════════

_redis_client = None

REDIS_CONFIG = {
    "host": os.getenv("ODI_REDIS_HOST", "127.0.0.1"),
    "port": int(os.getenv("ODI_REDIS_PORT", "6379")),
    "db": int(os.getenv("ODI_REDIS_DB", "0")),
    "decode_responses": True,
}

# TTL para cache de nodos (5 minutos)
REDIS_NODE_TTL = int(os.getenv("ODI_REDIS_NODE_TTL", "300"))


def _get_redis():
    """Lazy init de cliente Redis."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        _redis_client = redis.Redis(**REDIS_CONFIG)
        _redis_client.ping()
        logger.info("Redis connected: %s:%s", REDIS_CONFIG["host"], REDIS_CONFIG["port"])
        return _redis_client
    except Exception as e:
        logger.warning("Redis not available: %s. Operating without cache.", e)
        return None


def redis_get(key: str) -> Optional[str]:
    """Obtener valor de Redis. None si no disponible."""
    r = _get_redis()
    if r is None:
        return None
    try:
        return r.get(key)
    except Exception as e:
        logger.warning("Redis GET error: %s", e)
        return None


def redis_set(key: str, value: str, ttl: int = REDIS_NODE_TTL) -> bool:
    """Setear valor en Redis con TTL."""
    r = _get_redis()
    if r is None:
        return False
    try:
        r.setex(key, ttl, value)
        return True
    except Exception as e:
        logger.warning("Redis SET error: %s", e)
        return False


def redis_get_json(key: str) -> Optional[Dict]:
    """Obtener JSON de Redis."""
    val = redis_get(key)
    if val is None:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return None


def redis_set_json(key: str, data: Dict, ttl: int = REDIS_NODE_TTL) -> bool:
    """Guardar JSON en Redis."""
    return redis_set(key, json.dumps(data), ttl)


def redis_available() -> bool:
    """Check rápido si Redis responde."""
    r = _get_redis()
    if r is None:
        return False
    try:
        return r.ping()
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# REDIS KEY CONVENTIONS (Contrato ODI)
# ══════════════════════════════════════════════════════════════════════════════
#
# health:node:<node_id>:status      → AVAILABLE|HIGH_LOAD|SATURATED  (TTL 300s)
# health:node:<node_id>:saturation  → float 0.0-1.0                  (TTL 300s)
# health:node:<node_id>:sla_minutes → int                            (TTL 300s)
# health:node:<node_id>:data        → full JSON snapshot             (TTL 300s)
# health:node:<node_id>:last_sync   → epoch timestamp                (TTL 600s)
#

def redis_node_key(node_id: str, field: str) -> str:
    """Generar key Redis para un nodo de salud."""
    return f"health:node:{node_id}:{field}"
