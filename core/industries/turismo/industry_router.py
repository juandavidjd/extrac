#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Industry Router — SLA Clínico Dinámico + Enrutamiento Inter-Industria
======================================================================
Jerarquía de verdad (3 niveles):
  1. Redis (cache, TTL 300s) — velocidad
  2. Postgres (verdad base) — fn_odi_failover_candidates, v_odi_health_node_load
  3. JSON local (fallback demo) — siempre disponible

El router NUNCA falla: degrada gracefully.
Industria 5.0: el humano recibe next_actions, no decisiones automáticas.

Versión: 2.0.0 — 13 Feb 2026
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.industries.turismo.db.client import (
    pg_available,
    pg_query,
    redis_available,
    redis_get,
    redis_get_json,
    redis_node_key,
)
from core.industries.turismo.udm_t import (
    ClinicalPlan,
    Industry,
    RecoveryLevel,
    TransactionContext,
)

logger = logging.getLogger("odi.turismo.router")

SLA_DIR = Path("/opt/odi/data/turismo/sla")
NETWORK_DIR = Path("/opt/odi/data/turismo/network")

# Repositorio local (fallback cuando /opt/odi no existe)
_LOCAL_SLA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "turismo" / "sla"
_LOCAL_NETWORK_DIR = Path(__file__).parent.parent.parent.parent / "data" / "turismo" / "network"


def _resolve_sla_dir() -> Path:
    if SLA_DIR.exists():
        return SLA_DIR
    return _LOCAL_SLA_DIR


def _resolve_network_dir() -> Path:
    if NETWORK_DIR.exists():
        return NETWORK_DIR
    return _LOCAL_NETWORK_DIR


# ══════════════════════════════════════════════════════════════════════════════
# PROCEDIMIENTOS CONOCIDOS
# ══════════════════════════════════════════════════════════════════════════════

PROCEDURES = {
    "carillas_porcelana": {
        "name": "Carillas de Porcelana",
        "recovery_days_min": 1,
        "recovery_days_max": 3,
        "recovery_level": RecoveryLevel.MEDIUM_LOW,
        "sessions": 2,
        "industry": Industry.SALUD_DENTAL,
    },
    "implantes_dentales": {
        "name": "Implantes Dentales",
        "recovery_days_min": 3,
        "recovery_days_max": 7,
        "recovery_level": RecoveryLevel.LOW,
        "sessions": 3,
        "industry": Industry.SALUD_DENTAL,
    },
    "diseno_sonrisa": {
        "name": "Diseño de Sonrisa Completo",
        "recovery_days_min": 2,
        "recovery_days_max": 5,
        "recovery_level": RecoveryLevel.MEDIUM_LOW,
        "sessions": 3,
        "industry": Industry.SALUD_DENTAL,
    },
    "blanqueamiento": {
        "name": "Blanqueamiento Dental",
        "recovery_days_min": 0,
        "recovery_days_max": 1,
        "recovery_level": RecoveryLevel.MEDIUM,
        "sessions": 1,
        "industry": Industry.SALUD_DENTAL,
    },
    "ortodoncia_express": {
        "name": "Ortodoncia Express (alineadores)",
        "recovery_days_min": 0,
        "recovery_days_max": 1,
        "recovery_level": RecoveryLevel.HIGH,
        "sessions": 2,
        "industry": Industry.SALUD_DENTAL,
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1: REDIS (velocidad)
# ══════════════════════════════════════════════════════════════════════════════

def _get_node_from_redis(node_id: str) -> Optional[Dict[str, Any]]:
    """Leer nodo desde Redis cache."""
    data = redis_get_json(redis_node_key(node_id, "data"))
    if data:
        logger.debug("Node %s loaded from Redis", node_id)
        return data

    # Intentar fields individuales
    status = redis_get(redis_node_key(node_id, "status"))
    if status:
        saturation_str = redis_get(redis_node_key(node_id, "saturation")) or "0.0"
        sla_str = redis_get(redis_node_key(node_id, "sla_minutes")) or "30"
        return {
            "node_id": node_id,
            "load_status": status,
            "saturation": float(saturation_str),
            "sla_response_minutes": int(sla_str),
            "source": "redis",
        }

    return None


# ══════════════════════════════════════════════════════════════════════════════
# TIER 2: POSTGRES (verdad base)
# ══════════════════════════════════════════════════════════════════════════════

def _get_node_from_postgres(node_id: str) -> Optional[Dict[str, Any]]:
    """Leer nodo desde Postgres via v_odi_health_node_load."""
    rows = pg_query(
        "SELECT * FROM v_odi_health_node_load WHERE node_id = %s",
        (node_id,),
    )
    if rows and len(rows) > 0:
        row = rows[0]
        row["source"] = "postgres"
        logger.debug("Node %s loaded from Postgres", node_id)
        return row
    return None


def _get_failover_from_postgres(
    city: str, procedure_id: str, exclude_node: str = ""
) -> List[Dict[str, Any]]:
    """Usar fn_odi_failover_candidates de Postgres."""
    rows = pg_query(
        "SELECT * FROM fn_odi_failover_candidates(%s, %s, TRUE)",
        (city, procedure_id),
    )
    if rows:
        return [r for r in rows if r.get("node_id") != exclude_node]
    return []


# ══════════════════════════════════════════════════════════════════════════════
# TIER 3: JSON LOCAL (fallback demo)
# ══════════════════════════════════════════════════════════════════════════════

def _get_node_from_json(node_id: str) -> Optional[Dict[str, Any]]:
    """Leer nodo desde JSON local."""
    sla_dir = _resolve_sla_dir()
    sla_file = sla_dir / f"{node_id}.json"

    if sla_file.exists():
        try:
            data = json.loads(sla_file.read_text(encoding="utf-8"))
            data["source"] = "json"
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read SLA file %s: %s", sla_file, e)

    return None


def _get_failover_from_json(procedure_id: str, exclude_node: str = "") -> List[Dict[str, Any]]:
    """Leer red de nodos desde JSON."""
    net_dir = _resolve_network_dir()
    nodes_file = net_dir / "health_nodes.json"

    if not nodes_file.exists():
        return []

    try:
        data = json.loads(nodes_file.read_text(encoding="utf-8"))
        nodes = data.get("nodes", [])
        result = []
        for n in nodes:
            if n.get("node_id") == exclude_node:
                continue
            if procedure_id not in n.get("procedures", []):
                continue
            if n.get("saturated", True):
                continue
            if not n.get("certified", False):
                continue
            result.append(n)
        return result
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read health_nodes.json: %s", e)
        return []


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — 3-Tier Resolution
# ══════════════════════════════════════════════════════════════════════════════

def get_clinic_capacity(node_id: str) -> Dict[str, Any]:
    """
    Lee disponibilidad/cola del nodo clínico.
    Jerarquía: Redis → Postgres → JSON → Demo defaults.
    """
    # Tier 1: Redis
    data = _get_node_from_redis(node_id)
    if data:
        return _normalize_capacity(data, node_id)

    # Tier 2: Postgres
    data = _get_node_from_postgres(node_id)
    if data:
        return _normalize_capacity(data, node_id)

    # Tier 3: JSON
    data = _get_node_from_json(node_id)
    if data:
        return _normalize_capacity(data, node_id)

    # Fallback absoluto: DEMO
    logger.info("[DEMO MODE] No data source available for node %s", node_id)
    return {
        "node_id": node_id,
        "mode": "demo",
        "source": "fallback",
        "capacity_total": 8,
        "capacity_used": 3,
        "capacity_available": 5,
        "avg_response_minutes": 120,
        "saturated": False,
        "load_status": "AVAILABLE",
        "next_available_date": date.today().isoformat(),
        "doctors": [],
        "updated_at": datetime.utcnow().isoformat(),
    }


def _normalize_capacity(data: Dict[str, Any], node_id: str) -> Dict[str, Any]:
    """Normalizar datos de diferentes fuentes a formato uniforme."""
    source = data.get("source", "unknown")

    # Postgres/Redis format (v_odi_health_node_load)
    if "load_status" in data:
        saturated = data.get("load_status") == "SATURATED"
        cap_total = data.get("weekly_capacity", 8)
        cap_used = data.get("weekly_booked", 0)
        return {
            "node_id": node_id,
            "mode": "live" if source in ("postgres", "redis") else "demo",
            "source": source,
            "capacity_total": cap_total,
            "capacity_used": cap_used,
            "capacity_available": max(cap_total - cap_used, 0),
            "avg_response_minutes": data.get("sla_response_minutes", 120),
            "saturated": saturated,
            "load_status": data.get("load_status", "AVAILABLE"),
            "clinic_name": data.get("clinic_name", ""),
            "doctor_name": data.get("doctor_name", ""),
            "certification_level": data.get("certification_level", ""),
            "doctors": [],
            "updated_at": str(data.get("updated_at", datetime.utcnow().isoformat())),
        }

    # JSON format (legacy)
    return {
        "node_id": node_id,
        "mode": data.get("mode", "demo"),
        "source": source,
        "capacity_total": data.get("capacity_total", 8),
        "capacity_used": data.get("capacity_used", 3),
        "capacity_available": data.get("capacity_available", 5),
        "avg_response_minutes": data.get("avg_response_minutes", 120),
        "saturated": data.get("saturated", False),
        "load_status": "SATURATED" if data.get("saturated") else "AVAILABLE",
        "doctors": data.get("doctors", []),
        "updated_at": data.get("updated_at", datetime.utcnow().isoformat()),
    }


def select_doctor_by_sla(
    node_id: str,
    procedure_id: str,
) -> Dict[str, Any]:
    """
    Seleccionar doctor/clínica que cumpla SLA.
    Si nodo primario saturado → failover via Postgres → JSON.

    Returns:
        {
            "assigned_node_id": str,
            "assigned_doctor_id": str,
            "sla_deadline_minutes": int,
            "reason": str,
            "mode": str,
            "source": str,
        }
    """
    capacity = get_clinic_capacity(node_id)

    # Si NO está saturado, asignar al nodo principal
    if not capacity.get("saturated", False) and capacity.get("capacity_available", 0) > 0:
        doctors = capacity.get("doctors", [])
        doctor_id = doctors[0]["doctor_id"] if doctors else capacity.get("doctor_name", f"{node_id}_doctor")
        return {
            "assigned_node_id": node_id,
            "assigned_doctor_id": doctor_id,
            "sla_deadline_minutes": capacity.get("avg_response_minutes", 120),
            "reason": "primary_node_available",
            "mode": capacity.get("mode", "demo"),
            "source": capacity.get("source", "unknown"),
        }

    # Nodo saturado → buscar failover
    logger.warning("Node %s saturated (source=%s), searching failover...",
                    node_id, capacity.get("source", "?"))

    # Tier 2: Postgres failover function
    city = capacity.get("city", "Pereira")
    if not city:
        # Intentar sacar city de Postgres
        node_data = _get_node_from_postgres(node_id)
        city = node_data.get("city", "Pereira") if node_data else "Pereira"

    pg_candidates = _get_failover_from_postgres(city, procedure_id, exclude_node=node_id)
    if pg_candidates:
        best = pg_candidates[0]  # Ya ordenado por saturation ASC, cert DESC
        return {
            "assigned_node_id": best["node_id"],
            "assigned_doctor_id": best.get("doctor_name", f"{best['node_id']}_doctor"),
            "sla_deadline_minutes": best.get("sla_response_minutes", 180),
            "reason": f"primary_saturated_failover_to_{best['node_id']}",
            "mode": "live",
            "source": "postgres_failover",
            "certification_level": best.get("certification_level", ""),
            "certification_weight": best.get("certification_weight", 0),
        }

    # Tier 3: JSON fallover
    json_candidates = _get_failover_from_json(procedure_id, exclude_node=node_id)
    if json_candidates:
        alt = json_candidates[0]
        alt_doctors = alt.get("doctors", [])
        doctor_id = alt_doctors[0]["doctor_id"] if alt_doctors else f"{alt['node_id']}_doctor"
        return {
            "assigned_node_id": alt["node_id"],
            "assigned_doctor_id": doctor_id,
            "sla_deadline_minutes": alt.get("avg_response_minutes", 180),
            "reason": f"primary_saturated_failover_to_{alt['node_id']}",
            "mode": alt.get("mode", "demo"),
            "source": "json_failover",
        }

    # Sin alternativa → bloqueado
    return {
        "assigned_node_id": node_id,
        "assigned_doctor_id": "",
        "sla_deadline_minutes": 0,
        "reason": "all_nodes_saturated",
        "mode": capacity.get("mode", "demo"),
        "source": capacity.get("source", "unknown"),
    }


def build_clinical_plan(
    procedure_id: str,
    node_id: str,
    preferred_start: Optional[date] = None,
    preferred_end: Optional[date] = None,
) -> Tuple[ClinicalPlan, Dict[str, Any]]:
    """
    Construir plan clínico + asignación de doctor.
    Returns: (ClinicalPlan, assignment_info)
    """
    proc = PROCEDURES.get(procedure_id)
    if proc is None:
        raise ValueError(f"Unknown procedure: {procedure_id}. Known: {list(PROCEDURES.keys())}")

    assignment = select_doctor_by_sla(node_id, procedure_id)

    plan = ClinicalPlan(
        procedure_id=procedure_id,
        procedure_name=proc["name"],
        recovery_days_min=proc["recovery_days_min"],
        recovery_days_max=proc["recovery_days_max"],
        recovery_level=proc["recovery_level"],
        appointment_window_start=preferred_start,
        appointment_window_end=preferred_end,
        assigned_doctor_id=assignment["assigned_doctor_id"],
        assigned_clinic_id=assignment["assigned_node_id"],
    )

    return plan, assignment


def detect_secondary_industries(context: TransactionContext) -> List[Industry]:
    """Detectar qué industrias secundarias activar según el contexto."""
    secondaries = []

    if context.primary_industry in (Industry.SALUD_DENTAL, Industry.SALUD_CLINICO):
        secondaries.extend([
            Industry.TURISMO,
            Industry.HOSPEDAJE,
            Industry.ENTRETENIMIENTO,
        ])
        # Si hay nodos educativos, también Educación
        net_dir = _resolve_network_dir()
        edu_file = net_dir / "education_certifiers.json"
        if edu_file.exists():
            secondaries.append(Industry.EDUCACION)

    return secondaries


def data_source_status() -> Dict[str, Any]:
    """Diagnóstico: qué fuentes de datos están disponibles."""
    return {
        "redis": redis_available(),
        "postgres": pg_available(),
        "json_sla_dir": _resolve_sla_dir().exists(),
        "json_network_dir": _resolve_network_dir().exists(),
        "timestamp": datetime.utcnow().isoformat(),
    }
