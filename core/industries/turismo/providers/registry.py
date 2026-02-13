#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provider Registry — Selección de providers por variable de entorno.
Si falta ENV o el provider requiere key ausente → fallback a DEMO + warning.
"""

import logging
import os
from typing import Dict, Type

from core.industries.turismo.providers.base import (
    EventsProvider,
    FlightProvider,
    LodgingProvider,
)
from core.industries.turismo.providers.events_demo import DemoEventsProvider
from core.industries.turismo.providers.flights_demo import DemoFlightProvider
from core.industries.turismo.providers.lodging_demo import DemoLodgingProvider

logger = logging.getLogger("odi.turismo.registry")

# Registros de providers disponibles
_FLIGHT_PROVIDERS: Dict[str, Type[FlightProvider]] = {
    "demo": DemoFlightProvider,
}

_LODGING_PROVIDERS: Dict[str, Type[LodgingProvider]] = {
    "demo": DemoLodgingProvider,
}

_EVENTS_PROVIDERS: Dict[str, Type[EventsProvider]] = {
    "demo": DemoEventsProvider,
}


def get_flight_provider() -> FlightProvider:
    """Obtener provider de vuelos según ODI_FLIGHTS_PROVIDER env."""
    name = os.getenv("ODI_FLIGHTS_PROVIDER", "demo").lower()
    cls = _FLIGHT_PROVIDERS.get(name)
    if cls is None:
        logger.warning("Flight provider '%s' not found, falling back to demo", name)
        cls = DemoFlightProvider
    provider = cls()
    if not provider.is_available():
        logger.warning("Flight provider '%s' not available, falling back to demo", name)
        return DemoFlightProvider()
    return provider


def get_lodging_provider() -> LodgingProvider:
    """Obtener provider de hospedaje según ODI_LODGING_PROVIDER env."""
    name = os.getenv("ODI_LODGING_PROVIDER", "demo").lower()
    cls = _LODGING_PROVIDERS.get(name)
    if cls is None:
        logger.warning("Lodging provider '%s' not found, falling back to demo", name)
        cls = DemoLodgingProvider
    provider = cls()
    if not provider.is_available():
        logger.warning("Lodging provider '%s' not available, falling back to demo", name)
        return DemoLodgingProvider()
    return provider


def get_events_provider() -> EventsProvider:
    """Obtener provider de eventos según ODI_EVENTS_PROVIDER env."""
    name = os.getenv("ODI_EVENTS_PROVIDER", "demo").lower()
    cls = _EVENTS_PROVIDERS.get(name)
    if cls is None:
        logger.warning("Events provider '%s' not found, falling back to demo", name)
        cls = DemoEventsProvider
    provider = cls()
    if not provider.is_available():
        logger.warning("Events provider '%s' not available, falling back to demo", name)
        return DemoEventsProvider()
    return provider


def register_flight_provider(name: str, cls: Type[FlightProvider]) -> None:
    """Registrar un provider de vuelos adicional."""
    _FLIGHT_PROVIDERS[name.lower()] = cls


def register_lodging_provider(name: str, cls: Type[LodgingProvider]) -> None:
    """Registrar un provider de hospedaje adicional."""
    _LODGING_PROVIDERS[name.lower()] = cls


def register_events_provider(name: str, cls: Type[EventsProvider]) -> None:
    """Registrar un provider de eventos adicional."""
    _EVENTS_PROVIDERS[name.lower()] = cls
