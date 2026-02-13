#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lodging Provider DEMO — Hospedaje simulado para Pereira, Colombia.
Incluye hoteles, Airbnb y hospedaje médico (recovery-friendly).
"""

from datetime import date, timedelta
from typing import List, Optional

from core.industries.turismo.providers.base import LodgingProvider
from core.industries.turismo.udm_t import LodgingOption

_DEMO_LODGING = [
    {
        "name": "Hotel Movich Pereira",
        "type": "hotel",
        "location": "Centro, Pereira",
        "distance_to_clinic_km": 1.2,
        "price_per_night_usd": 85.0,
        "recovery_friendly": True,
        "amenities": ["wifi", "room_service", "parking", "breakfast"],
    },
    {
        "name": "Sonesta Hotel Pereira",
        "type": "hotel",
        "location": "Pinares, Pereira",
        "distance_to_clinic_km": 2.5,
        "price_per_night_usd": 110.0,
        "recovery_friendly": True,
        "amenities": ["wifi", "spa", "pool", "gym", "breakfast", "airport_shuttle"],
    },
    {
        "name": "Apartamento Recuperación Centro",
        "type": "airbnb",
        "location": "Centro, Pereira",
        "distance_to_clinic_km": 0.8,
        "price_per_night_usd": 45.0,
        "recovery_friendly": True,
        "amenities": ["wifi", "kitchen", "washer", "quiet_zone"],
    },
    {
        "name": "Finca Cafetera El Descanso",
        "type": "airbnb",
        "location": "Cerritos, Pereira",
        "distance_to_clinic_km": 12.0,
        "price_per_night_usd": 65.0,
        "recovery_friendly": True,
        "amenities": ["wifi", "nature", "private_chef_available", "pool"],
    },
    {
        "name": "Hostal Viajero Eje Cafetero",
        "type": "hostal",
        "location": "Universidad, Pereira",
        "distance_to_clinic_km": 3.0,
        "price_per_night_usd": 22.0,
        "recovery_friendly": False,
        "amenities": ["wifi", "shared_kitchen", "social_area"],
    },
]


class DemoLodgingProvider(LodgingProvider):
    """Provider de hospedaje DEMO. Datos simulados de Pereira."""

    name = "demo_lodging"
    mode = "intel"

    def search(
        self,
        city: str = "Pereira",
        checkin: date = None,
        checkout: date = None,
        recovery_friendly: bool = True,
        budget_max_usd: Optional[float] = None,
    ) -> List[LodgingOption]:
        checkin = checkin or (date.today() + timedelta(days=14))
        checkout = checkout or (checkin + timedelta(days=5))
        nights = max((checkout - checkin).days, 1)

        options = []
        for item in _DEMO_LODGING:
            if recovery_friendly and not item["recovery_friendly"]:
                continue

            total_price = item["price_per_night_usd"] * nights
            if budget_max_usd and total_price > budget_max_usd:
                continue

            opt = LodgingOption(
                provider=self.name,
                name=item["name"],
                type=item["type"],
                location=item["location"],
                distance_to_clinic_km=item["distance_to_clinic_km"],
                price_per_night_usd=item["price_per_night_usd"],
                available=True,
                recovery_friendly=item["recovery_friendly"],
                amenities=item["amenities"],
                notes=f"[DEMO] {nights} noches = ${total_price:.0f} USD total",
            )
            options.append(opt)

        return options

    def is_available(self) -> bool:
        return True
