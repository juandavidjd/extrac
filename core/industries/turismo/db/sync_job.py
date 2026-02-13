#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync Job — Postgres → Redis (Health Census Cache)
===================================================
Lee v_odi_health_node_load de Postgres y actualiza keys Redis.
Opcionalmente inserta snapshot en odi_health_capacity_log.

Diseñado para ejecutarse como cron job o dentro del loop de odi-api.

Contrato de keys Redis:
  health:node:<node_id>:status      → AVAILABLE|HIGH_LOAD|SATURATED
  health:node:<node_id>:saturation  → float
  health:node:<node_id>:sla_minutes → int
  health:node:<node_id>:data        → JSON completo
  health:node:<node_id>:last_sync   → epoch

Versión: 1.0.0 — 13 Feb 2026
"""

import json
import logging
import time
from datetime import date, datetime
from typing import Dict, List, Optional

from core.industries.turismo.db.client import (
    REDIS_NODE_TTL,
    pg_available,
    pg_execute,
    pg_query,
    redis_available,
    redis_node_key,
    redis_set,
    redis_set_json,
)

logger = logging.getLogger("odi.turismo.sync")


def sync_nodes_to_redis() -> Dict[str, any]:
    """
    Sincronizar vista v_odi_health_node_load → Redis.
    Returns: resumen de la sincronización.
    """
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "pg_available": False,
        "redis_available": False,
        "nodes_synced": 0,
        "errors": [],
    }

    if not pg_available():
        result["errors"].append("Postgres not available")
        logger.warning("Sync aborted: Postgres not available")
        return result
    result["pg_available"] = True

    if not redis_available():
        result["errors"].append("Redis not available")
        logger.warning("Sync aborted: Redis not available")
        return result
    result["redis_available"] = True

    # Leer estado de carga desde Postgres
    rows = pg_query("SELECT * FROM v_odi_health_node_load WHERE is_active = TRUE")
    if rows is None:
        result["errors"].append("Failed to query v_odi_health_node_load")
        return result

    epoch = str(int(time.time()))

    for row in rows:
        node_id = row["node_id"]
        try:
            # Status
            redis_set(
                redis_node_key(node_id, "status"),
                row.get("load_status", "AVAILABLE"),
                REDIS_NODE_TTL,
            )

            # Saturation
            redis_set(
                redis_node_key(node_id, "saturation"),
                str(row.get("saturation", 0.0)),
                REDIS_NODE_TTL,
            )

            # SLA
            redis_set(
                redis_node_key(node_id, "sla_minutes"),
                str(row.get("sla_response_minutes", 30)),
                REDIS_NODE_TTL,
            )

            # Full data JSON (serializar tipos especiales)
            clean_row = {}
            for k, v in row.items():
                if isinstance(v, (datetime, date)):
                    clean_row[k] = v.isoformat()
                elif isinstance(v, list):
                    clean_row[k] = v
                else:
                    clean_row[k] = v
            redis_set_json(
                redis_node_key(node_id, "data"),
                clean_row,
                REDIS_NODE_TTL,
            )

            # Last sync timestamp (TTL más largo)
            redis_set(
                redis_node_key(node_id, "last_sync"),
                epoch,
                REDIS_NODE_TTL * 2,
            )

            result["nodes_synced"] += 1

        except Exception as e:
            err = f"Error syncing {node_id}: {e}"
            result["errors"].append(err)
            logger.error(err)

    logger.info("Sync complete: %d nodes synced", result["nodes_synced"])
    return result


def log_weekly_capacity() -> int:
    """
    Insertar snapshot semanal en odi_health_capacity_log.
    Ejecutar una vez por semana (o por día si quieres granularidad).
    Returns: número de filas insertadas/actualizadas.
    """
    if not pg_available():
        logger.warning("Capacity log aborted: Postgres not available")
        return 0

    sql = """
    INSERT INTO odi_health_capacity_log (node_id, week_start, capacity, booked, source)
    SELECT
        node_id,
        DATE_TRUNC('week', CURRENT_DATE)::DATE,
        weekly_capacity,
        weekly_booked,
        'sync'
    FROM odi_health_nodes
    WHERE is_active = TRUE
    ON CONFLICT ON CONSTRAINT ux_capacity_node_week
    DO UPDATE SET
        booked = EXCLUDED.booked,
        source = 'sync_update'
    """

    if pg_execute(sql):
        rows = pg_query(
            "SELECT COUNT(*) as cnt FROM odi_health_capacity_log WHERE week_start = DATE_TRUNC('week', CURRENT_DATE)::DATE"
        )
        count = rows[0]["cnt"] if rows else 0
        logger.info("Capacity log: %d rows for current week", count)
        return count
    return 0


def full_sync() -> Dict[str, any]:
    """Sync completo: Redis + capacity log."""
    sync_result = sync_nodes_to_redis()
    log_count = log_weekly_capacity()
    sync_result["capacity_log_rows"] = log_count
    return sync_result


# ═══════════════════════════════════════════════════════════════════════════════
# CLI — ejecutar directamente: python -m core.industries.turismo.db.sync_job
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    result = full_sync()
    print(json.dumps(result, indent=2, default=str))
