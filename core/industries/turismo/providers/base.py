#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provider Interfaces — Contratos para conectores externos
=========================================================
Cada provider es un sensor que ODI consulta.
INTEL MODE: estimaciones sin reservas. ACTION MODE: prebooking real.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional

from core.industries.turismo.udm_t import (
    EventOption,
    FlightOption,
    LodgingOption,
    RecoveryLevel,
)


class FlightSearchCriteria(Dict):
    """Criterios de búsqueda de vuelos."""
    pass


class LodgingSearchCriteria(Dict):
    """Criterios de búsqueda de hospedaje."""
    pass


class EventSearchCriteria(Dict):
    """Criterios de búsqueda de eventos."""
    pass


class FlightProvider(ABC):
    """Interfaz para proveedores de vuelos."""

    name: str = "base"
    mode: str = "intel"  # intel | action

    @abstractmethod
    def search(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None,
        budget_max_usd: Optional[float] = None,
    ) -> List[FlightOption]:
        """Buscar opciones de vuelo."""
        ...

    def is_available(self) -> bool:
        """Verificar si el provider está operativo."""
        return True


class LodgingProvider(ABC):
    """Interfaz para proveedores de hospedaje."""

    name: str = "base"
    mode: str = "intel"

    @abstractmethod
    def search(
        self,
        city: str,
        checkin: date,
        checkout: date,
        recovery_friendly: bool = True,
        budget_max_usd: Optional[float] = None,
    ) -> List[LodgingOption]:
        """Buscar opciones de hospedaje."""
        ...

    def is_available(self) -> bool:
        return True


class EventsProvider(ABC):
    """Interfaz para proveedores de eventos/entretenimiento."""

    name: str = "base"
    mode: str = "intel"

    @abstractmethod
    def search(
        self,
        city: str,
        dates: List[date],
        max_impact_level: RecoveryLevel = RecoveryLevel.MEDIUM,
        categories: Optional[List[str]] = None,
    ) -> List[EventOption]:
        """Buscar opciones de entretenimiento filtradas por recovery_level."""
        ...

    def is_available(self) -> bool:
        return True
