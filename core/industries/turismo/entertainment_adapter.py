#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entertainment Adapter — Terapia de Entorno
============================================
El entretenimiento en ODI no es ocio; es aumento de valor percibido.
Filtra actividades según recovery_level del paciente.

Si el paciente viene por Carillas → cata de café (bajo impacto).
Si viene por Implantes → bloquea actividades de esfuerzo físico.
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from core.industries.turismo.providers.registry import get_events_provider
from core.industries.turismo.udm_t import (
    ClinicalPlan,
    EventOption,
    LogisticsPlan,
    RecoveryLevel,
)

logger = logging.getLogger("odi.turismo.entertainment")


def get_entertainment_options(
    clinical_plan: Optional[ClinicalPlan],
    logistics: LogisticsPlan,
    categories: Optional[List[str]] = None,
    city: str = "Pereira",
) -> List[EventOption]:
    """
    Obtener opciones de entretenimiento filtradas por recovery_level.
    Si no hay plan clínico, permite todo.
    """
    if clinical_plan:
        max_level = clinical_plan.recovery_level
    else:
        max_level = RecoveryLevel.HIGH

    # Calcular fechas disponibles para entretenimiento
    # (después de la cita + días de recuperación mínimos)
    base_date = logistics.arrival_window_start or (date.today() + timedelta(days=14))
    if clinical_plan and clinical_plan.recovery_days_min > 0:
        entertainment_start = base_date + timedelta(days=clinical_plan.recovery_days_min)
    else:
        entertainment_start = base_date + timedelta(days=1)

    stay_days = logistics.stay_duration_days
    entertainment_dates = [
        entertainment_start + timedelta(days=i)
        for i in range(max(stay_days - (clinical_plan.recovery_days_min if clinical_plan else 0), 1))
    ]

    provider = get_events_provider()
    options = provider.search(
        city=city,
        dates=entertainment_dates,
        max_impact_level=max_level,
        categories=categories,
    )

    logger.info(
        "Entertainment: %d options for recovery_level<=%s, dates=%s..%s",
        len(options),
        max_level.value,
        entertainment_dates[0] if entertainment_dates else "N/A",
        entertainment_dates[-1] if entertainment_dates else "N/A",
    )
    return options
