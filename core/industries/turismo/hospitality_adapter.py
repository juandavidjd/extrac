#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hospitality Adapter — Coordinación de hospedaje
=================================================
Busca hospedaje recovery-friendly cerca de la clínica asignada.
Si hotel lleno, ODI mueve fechas o sugiere alternativas.
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from core.industries.turismo.providers.registry import get_lodging_provider
from core.industries.turismo.udm_t import (
    BudgetTier,
    ClinicalPlan,
    LodgingOption,
    LogisticsPlan,
)

logger = logging.getLogger("odi.turismo.hospitality")

# Presupuesto máximo por noche según tier
_BUDGET_LIMITS = {
    BudgetTier.ECONOMY: 50.0,
    BudgetTier.STANDARD: 120.0,
    BudgetTier.PREMIUM: 500.0,
}


def get_lodging_options(
    logistics: LogisticsPlan,
    clinical_plan: Optional[ClinicalPlan],
    budget_tier: BudgetTier = BudgetTier.STANDARD,
    city: str = "Pereira",
) -> List[LodgingOption]:
    """
    Obtener opciones de hospedaje filtradas por recuperación y presupuesto.
    """
    checkin = logistics.arrival_window_start or (date.today() + timedelta(days=14))
    checkout = checkin + timedelta(days=logistics.stay_duration_days)

    recovery_friendly = True
    if clinical_plan and clinical_plan.recovery_days_min == 0:
        recovery_friendly = False  # Procedimiento sin recuperación, cualquier hospedaje

    budget_max = _BUDGET_LIMITS.get(budget_tier)
    if budget_max:
        budget_max = budget_max * logistics.stay_duration_days

    provider = get_lodging_provider()
    options = provider.search(
        city=city,
        checkin=checkin,
        checkout=checkout,
        recovery_friendly=recovery_friendly,
        budget_max_usd=budget_max,
    )

    # Ordenar por distancia a clínica (más cerca primero)
    options.sort(key=lambda x: x.distance_to_clinic_km or 999)

    logger.info(
        "Hospitality: %d options, recovery_friendly=%s, budget_tier=%s",
        len(options),
        recovery_friendly,
        budget_tier.value,
    )
    return options
