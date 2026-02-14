#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Events Provider DEMO — Entretenimiento y experiencias en Eje Cafetero.
Filtrado automático por recovery_level del paciente.
"""

from datetime import date, timedelta
from typing import List, Optional

from core.industries.turismo.providers.base import EventsProvider
from core.industries.turismo.udm_t import EventOption, RecoveryLevel

# Orden de severidad para comparación
_LEVEL_ORDER = {
    RecoveryLevel.LOW: 0,
    RecoveryLevel.MEDIUM_LOW: 1,
    RecoveryLevel.MEDIUM: 2,
    RecoveryLevel.HIGH: 3,
}

_DEMO_EVENTS = [
    {
        "name": "Cata de Café de Origen — Hacienda Venecia",
        "category": "gastronomia",
        "impact_level": RecoveryLevel.LOW,
        "duration_hours": 2.5,
        "price_usd": 35.0,
        "description": "Recorrido por finca cafetera con degustación de 5 variedades. Bajo impacto físico.",
    },
    {
        "name": "Visita Museo de Arte de Pereira",
        "category": "cultural",
        "impact_level": RecoveryLevel.LOW,
        "duration_hours": 1.5,
        "price_usd": 8.0,
        "description": "Galería de arte contemporáneo colombiano. Climatizado, accesible.",
    },
    {
        "name": "Recorrido Gastronómico Centro Histórico",
        "category": "gastronomia",
        "impact_level": RecoveryLevel.MEDIUM_LOW,
        "duration_hours": 3.0,
        "price_usd": 45.0,
        "description": "6 paradas culinarias en el centro. Caminata suave de 2km.",
    },
    {
        "name": "Chef Privado — Cena en Finca",
        "category": "gastronomia",
        "impact_level": RecoveryLevel.LOW,
        "duration_hours": 2.0,
        "price_usd": 80.0,
        "description": "Chef prepara cena de 5 tiempos en su alojamiento. Cero esfuerzo.",
    },
    {
        "name": "Termales de Santa Rosa de Cabal",
        "category": "wellness",
        "impact_level": RecoveryLevel.MEDIUM,
        "duration_hours": 4.0,
        "price_usd": 25.0,
        "description": "Aguas termales naturales. Requiere caminata moderada en sendero.",
    },
    {
        "name": "Avistamiento de Aves — Otún Quimbaya",
        "category": "naturaleza",
        "impact_level": RecoveryLevel.MEDIUM,
        "duration_hours": 5.0,
        "price_usd": 40.0,
        "description": "Guía bilingüe, 4km de sendero. Esfuerzo moderado.",
    },
    {
        "name": "Tour Parque del Café",
        "category": "cultural",
        "impact_level": RecoveryLevel.HIGH,
        "duration_hours": 6.0,
        "price_usd": 30.0,
        "description": "Parque temático completo. Incluye atracciones mecánicas. Alto esfuerzo.",
    },
    {
        "name": "Canyoning Río Otún",
        "category": "naturaleza",
        "impact_level": RecoveryLevel.HIGH,
        "duration_hours": 5.0,
        "price_usd": 55.0,
        "description": "Descenso de cascadas. Exige condición física plena.",
    },
]


class DemoEventsProvider(EventsProvider):
    """Provider de eventos DEMO. Experiencias del Eje Cafetero filtradas por recovery."""

    name = "demo_events"
    mode = "intel"

    def search(
        self,
        city: str = "Pereira",
        dates: List[date] = None,
        max_impact_level: RecoveryLevel = RecoveryLevel.MEDIUM,
        categories: Optional[List[str]] = None,
    ) -> List[EventOption]:
        dates = dates or [date.today() + timedelta(days=i) for i in range(14, 19)]
        max_level = _LEVEL_ORDER.get(max_impact_level, 2)

        options = []
        for item in _DEMO_EVENTS:
            item_level = _LEVEL_ORDER.get(item["impact_level"], 3)
            if item_level > max_level:
                continue

            if categories and item["category"] not in categories:
                continue

            opt = EventOption(
                provider=self.name,
                name=item["name"],
                category=item["category"],
                impact_level=item["impact_level"],
                estimated_duration_hours=item["duration_hours"],
                estimated_price_usd=item["price_usd"],
                available_dates=dates,
                description=item["description"],
                notes=f"[DEMO] Apto para recovery level <= {max_impact_level.value}",
            )
            options.append(opt)

        return options

    def is_available(self) -> bool:
        return True
