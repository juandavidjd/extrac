#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tourism Engine — Orquestador de Viabilidad → Plan
===================================================
No busca vuelos por buscar. Busca VIABILIDAD.
Cruza clinical plan con ventanas logísticas, recovery level,
y disponibilidad de providers.

Un solo flujo. Un solo cerebro.
INTENCIÓN → PERFIL → MATCH MULTI-INDUSTRIA → ORQUESTACIÓN → CONVERSIÓN

Versión: 1.0.0 — 13 Feb 2026
"""

import logging
from datetime import date, timedelta
from typing import Optional

from core.industries.turismo.entertainment_adapter import get_entertainment_options
from core.industries.turismo.hospitality_adapter import get_lodging_options
from core.industries.turismo.industry_router import (
    build_clinical_plan,
    detect_secondary_industries,
)
from core.industries.turismo.lead_scoring import calculate_lead_score
from core.industries.turismo.providers.registry import get_flight_provider
from core.industries.turismo.udm_t import (
    BudgetTier,
    Industry,
    LogisticsPlan,
    OrchestrationPlan,
    PlanStatus,
    TourismTransaction,
    TransactionContext,
    UserProfile,
)

logger = logging.getLogger("odi.turismo.engine")


def build_plan(transaction: TourismTransaction) -> TourismTransaction:
    """
    Pipeline completo de orquestación turismo.

    1. Calcular ventanas viables (no vuelo el mismo día de cirugía; respetar recovery)
    2. Llamar providers (flights / lodging / events)
    3. Filtrar entretenimiento por recovery_level
    4. Calcular score inter-industria
    5. Devolver OrchestrationPlan ordenado por valor (mejor fit)

    Reglas:
      - recovery_level HIGH => entretenimiento solo "low impact"
      - Si no hay lodging → plan.status = blocked_lodging
      - Si no hay flights → plan.status = blocked_flights
      - Siempre generar next_actions para humano (Pereira)
    """
    logger.info("Building tourism plan for %s", transaction.transaction_id)

    clinical = transaction.clinical_plan
    logistics = transaction.logistics
    profile = transaction.user_profile
    next_actions = []

    # ── 1. VUELOS ─────────────────────────────────────────────────────────
    flight_provider = get_flight_provider()
    flights = []

    if profile.origin_city:
        # Calcular fecha de llegada: mínimo 1 día antes de la cita
        arrival_target = logistics.arrival_window_start
        if not arrival_target:
            if clinical and clinical.appointment_window_start:
                arrival_target = clinical.appointment_window_start - timedelta(days=1)
            else:
                arrival_target = date.today() + timedelta(days=14)
            logistics.arrival_window_start = arrival_target

        # Calcular fecha de vuelta
        return_target = logistics.departure_window_start
        if not return_target:
            stay = logistics.stay_duration_days
            if clinical:
                min_stay = clinical.recovery_days_max + 2  # recovery + buffer
                stay = max(stay, min_stay)
                logistics.stay_duration_days = stay
            return_target = arrival_target + timedelta(days=stay)
            logistics.departure_window_start = return_target

        origin_code = profile.origin_city.split(",")[0].strip()[:3].upper()
        budget_max = None
        if profile.budget_tier == BudgetTier.ECONOMY:
            budget_max = 400.0
        elif profile.budget_tier == BudgetTier.STANDARD:
            budget_max = 800.0

        flights = flight_provider.search(
            origin=origin_code,
            destination="PEI",
            departure_date=arrival_target,
            return_date=return_target,
            budget_max_usd=budget_max,
        )
        logger.info("Flights: %d options from %s", len(flights), origin_code)
    else:
        next_actions.append("Solicitar ciudad de origen al paciente para buscar vuelos")

    # ── 2. HOSPEDAJE ──────────────────────────────────────────────────────
    lodging = get_lodging_options(
        logistics=logistics,
        clinical_plan=clinical,
        budget_tier=profile.budget_tier,
    )
    logger.info("Lodging: %d options", len(lodging))

    # ── 3. ENTRETENIMIENTO ────────────────────────────────────────────────
    entertainment = get_entertainment_options(
        clinical_plan=clinical,
        logistics=logistics,
    )
    logger.info("Entertainment: %d options", len(entertainment))

    # ── 4. DETERMINAR STATUS ──────────────────────────────────────────────
    status = PlanStatus.DRAFT

    if not flights and profile.origin_city:
        status = PlanStatus.BLOCKED_FLIGHTS
        next_actions.append("Sin vuelos viables. Evaluar fechas alternativas o transporte terrestre.")
    elif not lodging:
        status = PlanStatus.BLOCKED_LODGING
        next_actions.append("Sin hospedaje disponible. Ampliar búsqueda o ajustar fechas.")
    elif flights and lodging:
        status = PlanStatus.VIABLE
    elif not profile.origin_city and lodging:
        status = PlanStatus.DRAFT
        next_actions.append("Plan parcial: hospedaje listo, falta info de vuelos.")

    # Acciones siempre útiles para el humano
    if clinical and not clinical.assigned_doctor_id:
        next_actions.append("Confirmar asignación de doctor con la clínica.")
    if status == PlanStatus.VIABLE:
        next_actions.append("Presentar opciones al paciente para confirmación.")
        next_actions.append("Coordinar transporte aeropuerto → hotel/clínica.")

    # ── 5. CALCULAR ESTIMADO TOTAL ────────────────────────────────────────
    cheapest_flight = min((f.estimated_price_usd for f in flights), default=0)
    cheapest_lodging_total = 0
    if lodging:
        cheapest_lodging_total = lodging[0].price_per_night_usd * logistics.stay_duration_days
    entertainment_total = sum(e.estimated_price_usd for e in entertainment[:3])  # top 3
    total_estimated = round(cheapest_flight + cheapest_lodging_total + entertainment_total, 2)

    # ── 6. ARMAR PLAN ─────────────────────────────────────────────────────
    transaction.orchestration = OrchestrationPlan(
        status=status,
        flight_options=flights,
        lodging_options=lodging,
        entertainment_options=entertainment,
        assigned_provider_ids={
            "flights": flight_provider.name,
            "lodging": "demo_lodging",
            "events": "demo_events",
        },
        total_estimated_value_usd=total_estimated,
        next_actions=next_actions,
        notes=f"Mode: {transaction.mode}. Generated by Tourism Engine v1.0.",
    )

    # ── 7. SCORING ────────────────────────────────────────────────────────
    transaction.lead_score = calculate_lead_score(transaction)

    logger.info(
        "Plan complete: status=%s, total=$%.0f, priority=%s",
        status.value,
        total_estimated,
        transaction.lead_score.priority.value,
    )

    return transaction


def create_full_plan(
    node_id: str,
    procedure_id: str,
    origin_city: Optional[str] = None,
    budget_tier: str = "standard",
    arrival_date: Optional[date] = None,
    stay_days: int = 5,
    lead_id: Optional[str] = None,
) -> TourismTransaction:
    """
    Crear un plan turístico completo desde cero.
    Convenience function que orquesta todo el flujo.
    """
    # 1. Contexto
    context = TransactionContext(
        primary_industry=Industry.SALUD_DENTAL,
        node_id=node_id,
        lead_id=lead_id,
    )
    context.secondary_industries = detect_secondary_industries(context)

    # 2. Perfil
    profile = UserProfile(
        origin_city=origin_city,
        budget_tier=BudgetTier(budget_tier),
    )

    # 3. Plan clínico + asignación
    clinical, assignment = build_clinical_plan(
        procedure_id=procedure_id,
        node_id=node_id,
        preferred_start=arrival_date,
    )

    # 4. Logística
    logistics = LogisticsPlan(
        arrival_window_start=arrival_date,
        stay_duration_days=stay_days,
    )

    # 5. Transacción
    txn = TourismTransaction(
        context=context,
        user_profile=profile,
        clinical_plan=clinical,
        logistics=logistics,
    )

    # 6. Orquestar
    txn = build_plan(txn)

    return txn
