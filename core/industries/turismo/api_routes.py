#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tourism API Routes — Endpoints para integrar en odi-api (8800)
===============================================================
POST /tourism/plan    → Crear plan turístico completo
POST /tourism/assign  → Asignar doctor/nodo por SLA
POST /tourism/score   → Calcular lead scoring inter-industria

No rompe endpoints existentes. Se monta como APIRouter.

Versión: 1.0.0 — 13 Feb 2026
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.industries.turismo.industry_router import (
    build_clinical_plan,
    get_clinic_capacity,
    select_doctor_by_sla,
)
from core.industries.turismo.lead_scoring import calculate_lead_score
from core.industries.turismo.tourism_engine import build_plan, create_full_plan
from core.industries.turismo.udm_t import (
    BudgetTier,
    Industry,
    LeadScore,
    LogisticsPlan,
    PriorityLabel,
    TourismTransaction,
    TransactionContext,
    UserProfile,
)

logger = logging.getLogger("odi.turismo.api")

router = APIRouter(prefix="/tourism", tags=["Turismo Inter-Industria"])


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ══════════════════════════════════════════════════════════════════════════════

class TourismPlanRequest(BaseModel):
    """Request para crear un plan turístico."""
    node_id: str = Field(default="matzu_001", description="Nodo clínico principal")
    procedure_id: str = Field(default="carillas_porcelana", description="ID del procedimiento")
    origin_city: Optional[str] = Field(None, description="Ciudad de origen (ej: Miami, FL)")
    budget_tier: str = Field(default="standard", description="economy | standard | premium")
    arrival_date: Optional[str] = Field(None, description="Fecha de llegada ISO (YYYY-MM-DD)")
    stay_days: int = Field(default=5, ge=1, le=30)
    lead_id: Optional[str] = Field(None, description="ID del lead en CRM")


class TourismPlanResponse(BaseModel):
    """Respuesta con el plan turístico completo."""
    transaction_id: str
    status: str
    mode: str
    priority: str
    summary: Dict[str, Any]
    orchestration: Dict[str, Any]
    lead_score: Dict[str, Any]
    next_actions: List[str]
    saved_to: Optional[str] = None


class AssignRequest(BaseModel):
    """Request para asignar doctor/nodo."""
    node_id: str = Field(default="matzu_001")
    procedure_id: str = Field(default="carillas_porcelana")
    preferred_start: Optional[str] = Field(None, description="Fecha preferida ISO")
    preferred_end: Optional[str] = Field(None, description="Fecha fin preferida ISO")


class AssignResponse(BaseModel):
    """Respuesta de asignación de doctor."""
    assigned_node_id: str
    assigned_doctor_id: str
    sla_deadline_minutes: int
    reason: str
    mode: str
    clinical_plan: Dict[str, Any]


class ScoreRequest(BaseModel):
    """Request para calcular scoring."""
    lead_id: Optional[str] = None
    transaction_id: Optional[str] = None
    node_id: str = Field(default="matzu_001")
    procedure_id: str = Field(default="carillas_porcelana")
    origin_city: Optional[str] = None
    budget_tier: str = Field(default="standard")
    arrival_date: Optional[str] = None


class ScoreResponse(BaseModel):
    """Respuesta del scoring."""
    priority_label: str
    reasons: List[str]
    transaction_id: str


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/plan", response_model=TourismPlanResponse)
async def create_tourism_plan(req: TourismPlanRequest):
    """
    Crear plan turístico completo.
    Orquesta: vuelos + hospedaje + entretenimiento + scoring.
    """
    try:
        arrival = None
        if req.arrival_date:
            arrival = date.fromisoformat(req.arrival_date)

        txn = create_full_plan(
            node_id=req.node_id,
            procedure_id=req.procedure_id,
            origin_city=req.origin_city,
            budget_tier=req.budget_tier,
            arrival_date=arrival,
            stay_days=req.stay_days,
            lead_id=req.lead_id,
        )

        # Persistir
        saved_path = None
        try:
            saved_path = str(txn.save())
        except OSError:
            # En repo local, guardar en data/ local
            try:
                from pathlib import Path
                local_dir = Path(__file__).parent.parent.parent.parent / "data" / "turismo" / "transactions"
                saved_path = str(txn.save(str(local_dir)))
            except OSError as e:
                logger.warning("Could not persist transaction: %s", e)

        return TourismPlanResponse(
            transaction_id=txn.transaction_id,
            status=txn.orchestration.status.value,
            mode=txn.mode,
            priority=txn.lead_score.priority.value if txn.lead_score else "N/A",
            summary=txn.summary(),
            orchestration=txn.orchestration.model_dump(mode="json"),
            lead_score=txn.lead_score.model_dump(mode="json") if txn.lead_score else {},
            next_actions=txn.orchestration.next_actions,
            saved_to=saved_path,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating tourism plan")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post("/assign", response_model=AssignResponse)
async def assign_doctor(req: AssignRequest):
    """
    Asignar doctor/nodo según SLA clínico dinámico.
    Si el nodo principal está saturado, busca alternativa en la red.
    """
    try:
        pref_start = date.fromisoformat(req.preferred_start) if req.preferred_start else None
        pref_end = date.fromisoformat(req.preferred_end) if req.preferred_end else None

        clinical, assignment = build_clinical_plan(
            procedure_id=req.procedure_id,
            node_id=req.node_id,
            preferred_start=pref_start,
            preferred_end=pref_end,
        )

        return AssignResponse(
            assigned_node_id=assignment["assigned_node_id"],
            assigned_doctor_id=assignment["assigned_doctor_id"],
            sla_deadline_minutes=assignment["sla_deadline_minutes"],
            reason=assignment["reason"],
            mode=assignment["mode"],
            clinical_plan=clinical.model_dump(mode="json"),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error assigning doctor")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.post("/score", response_model=ScoreResponse)
async def score_lead(req: ScoreRequest):
    """
    Calcular lead scoring inter-industria.
    Devuelve: ALTA / MEDIA / BAJA + reasons explicativas.
    """
    try:
        arrival = None
        if req.arrival_date:
            arrival = date.fromisoformat(req.arrival_date)

        # Crear transacción mínima para scoring
        txn = create_full_plan(
            node_id=req.node_id,
            procedure_id=req.procedure_id,
            origin_city=req.origin_city,
            budget_tier=req.budget_tier,
            arrival_date=arrival,
            lead_id=req.lead_id,
        )

        score = txn.lead_score

        return ScoreResponse(
            priority_label=score.priority.value if score else "MEDIA",
            reasons=score.reasons if score else ["No score available"],
            transaction_id=txn.transaction_id,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error scoring lead")
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@router.get("/capacity/{node_id}")
async def clinic_capacity(node_id: str):
    """Consultar capacidad/SLA de un nodo clínico."""
    return get_clinic_capacity(node_id)


@router.get("/health")
async def tourism_health():
    """Health check del módulo turismo."""
    return {
        "status": "healthy",
        "service": "odi-turismo",
        "version": "1.0.0",
        "mode": "demo",
        "timestamp": datetime.utcnow().isoformat(),
    }
