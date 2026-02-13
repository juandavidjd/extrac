#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Industry Router — SLA Clínico Dinámico + Enrutamiento Inter-Industria
======================================================================
Detecta disparadores entre verticales.
Si un lead tiene alta intención en Salud, despierta Turismo + Hospitalidad.
Si Matzu está saturado, busca el siguiente doctor certificado en la red.

Datos:
  - SLA por nodo: /opt/odi/data/turismo/sla/<node_id>.json
  - Red de salud: /opt/odi/data/turismo/network/health_nodes.json

Versión: 1.0.0 — 13 Feb 2026
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
# SLA CLÍNICO DINÁMICO
# ══════════════════════════════════════════════════════════════════════════════

def get_clinic_capacity(node_id: str) -> Dict[str, Any]:
    """
    Lee disponibilidad/cola del nodo clínico.
    Fuentes (en orden de prioridad):
      1. JSON en SLA_DIR/<node_id>.json
      2. Defaults en modo DEMO
    """
    sla_dir = _resolve_sla_dir()
    sla_file = sla_dir / f"{node_id}.json"

    if sla_file.exists():
        try:
            data = json.loads(sla_file.read_text(encoding="utf-8"))
            logger.info("SLA loaded from %s", sla_file)
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read SLA file %s: %s", sla_file, e)

    # Fallback DEMO
    logger.info("[DEMO MODE] Using default SLA for node %s", node_id)
    return {
        "node_id": node_id,
        "mode": "demo",
        "capacity_total": 8,
        "capacity_used": 3,
        "capacity_available": 5,
        "avg_response_minutes": 120,
        "saturated": False,
        "next_available_date": date.today().isoformat(),
        "doctors": [],
        "updated_at": datetime.utcnow().isoformat(),
    }


def _load_health_nodes() -> List[Dict[str, Any]]:
    """Cargar red de nodos de salud."""
    net_dir = _resolve_network_dir()
    nodes_file = net_dir / "health_nodes.json"

    if nodes_file.exists():
        try:
            data = json.loads(nodes_file.read_text(encoding="utf-8"))
            return data.get("nodes", [])
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read health_nodes.json: %s", e)

    logger.info("[DEMO MODE] No health_nodes.json found, using empty network")
    return []


def select_doctor_by_sla(
    node_id: str,
    procedure_id: str,
) -> Dict[str, Any]:
    """
    Seleccionar doctor/clínica que cumpla SLA.
    Si el nodo principal está saturado, busca en la red.

    Returns:
        {
            "assigned_node_id": str,
            "assigned_doctor_id": str,
            "sla_deadline_minutes": int,
            "reason": str,
            "mode": "demo" | "live"
        }
    """
    capacity = get_clinic_capacity(node_id)

    # Si NO está saturado, asignar al nodo principal
    if not capacity.get("saturated", False) and capacity.get("capacity_available", 0) > 0:
        doctors = capacity.get("doctors", [])
        doctor_id = doctors[0]["doctor_id"] if doctors else f"{node_id}_default_doctor"
        return {
            "assigned_node_id": node_id,
            "assigned_doctor_id": doctor_id,
            "sla_deadline_minutes": capacity.get("avg_response_minutes", 120),
            "reason": "primary_node_available",
            "mode": capacity.get("mode", "demo"),
        }

    # Nodo saturado → buscar en red
    logger.warning("Node %s saturated, searching network...", node_id)
    nodes = _load_health_nodes()

    for alt_node in nodes:
        if alt_node.get("node_id") == node_id:
            continue
        if procedure_id not in alt_node.get("procedures", []):
            continue
        if alt_node.get("saturated", True):
            continue
        if not alt_node.get("certified", False):
            continue

        alt_doctors = alt_node.get("doctors", [])
        doctor_id = alt_doctors[0]["doctor_id"] if alt_doctors else f"{alt_node['node_id']}_doctor"
        return {
            "assigned_node_id": alt_node["node_id"],
            "assigned_doctor_id": doctor_id,
            "sla_deadline_minutes": alt_node.get("avg_response_minutes", 180),
            "reason": f"primary_saturated_redirected_to_{alt_node['node_id']}",
            "mode": alt_node.get("mode", "demo"),
        }

    # No hay alternativa → marcar como bloqueado
    return {
        "assigned_node_id": node_id,
        "assigned_doctor_id": "",
        "sla_deadline_minutes": 0,
        "reason": "all_nodes_saturated",
        "mode": capacity.get("mode", "demo"),
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
