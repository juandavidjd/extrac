#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lead Scoring Inter-Industria v1.0
==================================
Score compuesto:
  Score = w1*semantic_match + w2*sentiment + w3*urgency
        + w4*logistics_feasibility - w5*latency_penalty

Si faltan señales → defaults + reasons explicativas.
Salida para humanos: ALTA / MEDIA / BAJA + reasons (nunca número exacto).

Versión: 1.0.0 — 13 Feb 2026
"""

import logging
from datetime import date, datetime
from typing import List, Optional, Tuple

from core.industries.turismo.udm_t import (
    LeadScore,
    OrchestrationPlan,
    PlanStatus,
    PriorityLabel,
    TourismTransaction,
)

logger = logging.getLogger("odi.turismo.scoring")

# Pesos del scoring
W_SEMANTIC = 0.20
W_SENTIMENT = 0.15
W_URGENCY = 0.25
W_LOGISTICS = 0.25
W_LATENCY_PENALTY = 0.15


def _score_urgency(transaction: TourismTransaction) -> Tuple[float, List[str]]:
    """Evaluar urgencia basada en ventana temporal."""
    reasons = []
    clinical = transaction.clinical_plan
    logistics = transaction.logistics

    if not clinical or not logistics.arrival_window_start:
        return 0.5, ["urgency: sin fecha definida, default medio"]

    days_until = (logistics.arrival_window_start - date.today()).days

    if days_until <= 7:
        return 1.0, [f"urgency: viaje en {days_until} días — MUY URGENTE"]
    elif days_until <= 14:
        return 0.8, [f"urgency: viaje en {days_until} días — urgente"]
    elif days_until <= 30:
        return 0.6, [f"urgency: viaje en {days_until} días — planificado"]
    elif days_until <= 60:
        return 0.4, [f"urgency: viaje en {days_until} días — anticipado"]
    else:
        return 0.2, [f"urgency: viaje en {days_until} días — lejano"]


def _score_logistics_feasibility(transaction: TourismTransaction) -> Tuple[float, List[str]]:
    """Evaluar viabilidad logística del plan."""
    reasons = []
    orch = transaction.orchestration

    if orch.status == PlanStatus.VIABLE:
        score = 1.0
        reasons.append("logistics: plan viable completo")
    elif orch.status == PlanStatus.CONFIRMED:
        score = 1.0
        reasons.append("logistics: plan confirmado")
    elif orch.status == PlanStatus.DRAFT:
        score = 0.5
        reasons.append("logistics: plan en borrador")
    elif orch.status == PlanStatus.BLOCKED_FLIGHTS:
        score = 0.2
        reasons.append("logistics: BLOQUEADO — sin vuelos viables")
    elif orch.status == PlanStatus.BLOCKED_LODGING:
        score = 0.3
        reasons.append("logistics: BLOQUEADO — sin hospedaje disponible")
    elif orch.status == PlanStatus.BLOCKED_CLINIC:
        score = 0.1
        reasons.append("logistics: BLOQUEADO — clínica saturada")
    else:
        score = 0.3
        reasons.append(f"logistics: estado {orch.status.value}")

    # Bonus por tener opciones concretas
    if len(orch.flight_options) > 0:
        score = min(score + 0.1, 1.0)
        reasons.append(f"logistics: {len(orch.flight_options)} vuelos disponibles")
    if len(orch.lodging_options) > 0:
        score = min(score + 0.1, 1.0)
        reasons.append(f"logistics: {len(orch.lodging_options)} hospedajes disponibles")

    return score, reasons


def _score_semantic_match(transaction: TourismTransaction) -> Tuple[float, List[str]]:
    """Evaluar match semántico procedimiento-nodo."""
    reasons = []
    clinical = transaction.clinical_plan

    if not clinical:
        return 0.5, ["semantic: sin procedimiento definido, default medio"]

    # Si tiene doctor asignado → buen match
    if clinical.assigned_doctor_id:
        return 0.9, [f"semantic: doctor asignado ({clinical.assigned_clinic_id})"]
    else:
        return 0.5, ["semantic: sin doctor asignado aún"]


def _score_sentiment(transaction: TourismTransaction) -> Tuple[float, List[str]]:
    """
    Evaluar sentimiento/intención del lead.
    En v1.0 usa heurísticas simples. Futuro: integrar con Radar sentiment_analyzer.
    """
    reasons = []
    profile = transaction.user_profile

    # Budget tier como proxy de intención
    if profile.budget_tier.value == "premium":
        return 0.9, ["sentiment: budget premium — alta intención de compra"]
    elif profile.budget_tier.value == "standard":
        return 0.6, ["sentiment: budget standard"]
    else:
        return 0.4, ["sentiment: budget economy"]


def _score_latency_penalty(transaction: TourismTransaction) -> Tuple[float, List[str]]:
    """Penalización por tiempo transcurrido sin acción."""
    reasons = []
    age_hours = (datetime.utcnow() - transaction.created_at).total_seconds() / 3600

    if age_hours < 1:
        return 0.0, ["latency: lead fresco (<1h)"]
    elif age_hours < 24:
        return 0.2, [f"latency: {age_hours:.0f}h sin acción"]
    elif age_hours < 72:
        return 0.5, [f"latency: {age_hours:.0f}h sin acción — riesgo de enfriamiento"]
    else:
        return 0.8, [f"latency: {age_hours:.0f}h sin acción — lead frío"]


def calculate_lead_score(transaction: TourismTransaction) -> LeadScore:
    """
    Calcular score inter-industria compuesto.
    Devuelve: priority_label (ALTA/MEDIA/BAJA) + reasons.
    NO expone número exacto al humano.
    """
    all_reasons = []

    s_semantic, r = _score_semantic_match(transaction)
    all_reasons.extend(r)

    s_sentiment, r = _score_sentiment(transaction)
    all_reasons.extend(r)

    s_urgency, r = _score_urgency(transaction)
    all_reasons.extend(r)

    s_logistics, r = _score_logistics_feasibility(transaction)
    all_reasons.extend(r)

    s_latency, r = _score_latency_penalty(transaction)
    all_reasons.extend(r)

    # Score compuesto
    score = (
        W_SEMANTIC * s_semantic
        + W_SENTIMENT * s_sentiment
        + W_URGENCY * s_urgency
        + W_LOGISTICS * s_logistics
        - W_LATENCY_PENALTY * s_latency
    )
    score = max(0.0, min(1.0, score))

    # Clasificar
    if score >= 0.7:
        priority = PriorityLabel.ALTA
    elif score >= 0.4:
        priority = PriorityLabel.MEDIA
    else:
        priority = PriorityLabel.BAJA

    logger.info(
        "Lead score for %s: %.2f → %s",
        transaction.transaction_id, score, priority.value,
    )

    return LeadScore(
        priority=priority,
        score_value=round(score, 3),
        reasons=all_reasons,
        timestamp=datetime.utcnow(),
    )
