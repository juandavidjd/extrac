#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flight Provider DEMO — Resultados mock coherentes para pruebas end-to-end.
No requiere API keys. Simula rutas reales hacia Pereira (PEI).
"""

from datetime import date, timedelta
from typing import List, Optional

from core.industries.turismo.providers.base import FlightProvider
from core.industries.turismo.udm_t import FlightOption

# Rutas demo realistas hacia Pereira
_DEMO_ROUTES = {
    "MIA": {"airline": "Avianca", "stops": 1, "base_price": 380.0, "hub": "BOG"},
    "JFK": {"airline": "LATAM", "stops": 1, "base_price": 450.0, "hub": "BOG"},
    "MEX": {"airline": "Avianca", "stops": 1, "base_price": 320.0, "hub": "BOG"},
    "GRU": {"airline": "LATAM", "stops": 1, "base_price": 520.0, "hub": "BOG"},
    "PTY": {"airline": "Copa Airlines", "stops": 1, "base_price": 290.0, "hub": "BOG"},
    "BOG": {"airline": "Avianca", "stops": 0, "base_price": 85.0, "hub": ""},
    "MDE": {"airline": "EasyFly", "stops": 0, "base_price": 65.0, "hub": ""},
    "CLO": {"airline": "Avianca", "stops": 0, "base_price": 55.0, "hub": ""},
    "CTG": {"airline": "LATAM", "stops": 0, "base_price": 120.0, "hub": ""},
    "DEFAULT": {"airline": "Avianca", "stops": 1, "base_price": 400.0, "hub": "BOG"},
}


class DemoFlightProvider(FlightProvider):
    """Provider de vuelos DEMO. Datos simulados, sin API externa."""

    name = "demo_flights"
    mode = "intel"

    def search(
        self,
        origin: str,
        destination: str = "PEI",
        departure_date: date = None,
        return_date: Optional[date] = None,
        budget_max_usd: Optional[float] = None,
    ) -> List[FlightOption]:
        departure_date = departure_date or (date.today() + timedelta(days=14))
        origin_code = origin.upper()[:3]
        route = _DEMO_ROUTES.get(origin_code, _DEMO_ROUTES["DEFAULT"])

        options = []
        # Generar 3 opciones con variación de precio/horario
        for i, (price_mult, label) in enumerate([
            (1.0, "Mañana"),
            (0.85, "Tarde (promo)"),
            (1.15, "Noche"),
        ]):
            price = round(route["base_price"] * price_mult, 2)
            if budget_max_usd and price > budget_max_usd:
                continue

            opt = FlightOption(
                provider=self.name,
                origin_airport=origin_code,
                destination_airport=destination,
                departure_date=departure_date,
                return_date=return_date,
                airline=route["airline"],
                stops=route["stops"],
                estimated_price_usd=price,
                currency="USD",
                notes=f"[DEMO] Vuelo {label} vía {route['hub'] or 'directo'}",
            )
            options.append(opt)

        return options

    def is_available(self) -> bool:
        return True
