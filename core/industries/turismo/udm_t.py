#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDM-T — Universal Data Model for Tourism (Modelo Canónico)
===========================================================
Objeto universal que viaja por todo el pipeline inter-industria.
Salud, Turismo, Hospitalidad, Entretenimiento y Educación hablan
el mismo idioma a través de este modelo.

Uso:
    from core.industries.turismo.udm_t import TourismTransaction, UserProfile

Versión: 1.0.0 — 13 Feb 2026
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class Industry(str, Enum):
    SALUD_DENTAL = "salud_dental"
    SALUD_CLINICO = "salud_clinico"
    MOTO = "moto"
    TURISMO = "turismo"
    HOSPEDAJE = "hospedaje"
    ENTRETENIMIENTO = "entretenimiento"
    EDUCACION = "educacion"
    TRANSPORTE = "transporte"


class BudgetTier(str, Enum):
    ECONOMY = "economy"
    STANDARD = "standard"
    PREMIUM = "premium"


class RecoveryLevel(str, Enum):
    """Nivel de impacto permitido post-procedimiento."""
    LOW = "low"              # Solo reposo
    MEDIUM_LOW = "medium_low"  # Actividades suaves (cata de café, museo)
    MEDIUM = "medium"        # Actividades moderadas (paseo, gastronomía)
    HIGH = "high"            # Sin restricciones


class PlanStatus(str, Enum):
    DRAFT = "draft"
    VIABLE = "viable"
    BLOCKED_FLIGHTS = "blocked_flights"
    BLOCKED_LODGING = "blocked_lodging"
    BLOCKED_CLINIC = "blocked_clinic"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"


class PriorityLabel(str, Enum):
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAJA = "BAJA"


# ══════════════════════════════════════════════════════════════════════════════
# SUB-MODELOS
# ══════════════════════════════════════════════════════════════════════════════

class TransactionContext(BaseModel):
    """Contexto de la transacción inter-industria."""
    primary_industry: Industry = Industry.SALUD_DENTAL
    secondary_industries: List[Industry] = Field(
        default_factory=lambda: [Industry.TURISMO, Industry.HOSPEDAJE, Industry.ENTRETENIMIENTO]
    )
    node_id: str = Field(..., description="Nodo principal (ej: matzu_001)")
    lead_id: Optional[str] = Field(None, description="ID del lead si existe en CRM")


class UserProfile(BaseModel):
    """Perfil del usuario/paciente."""
    origin_city: Optional[str] = Field(None, description="Ciudad de origen (ej: Miami, FL)")
    origin_country: Optional[str] = Field(None, description="País ISO (ej: US, CO, MX)")
    language: str = Field(default="es", description="Idioma preferido")
    budget_tier: BudgetTier = BudgetTier.STANDARD
    constraints: List[str] = Field(
        default_factory=list,
        description="Restricciones: mobility_low, companion, wheelchair, etc."
    )
    contact_channel: str = Field(default="whatsapp", description="Canal de contacto")


class ClinicalPlan(BaseModel):
    """Plan clínico del procedimiento."""
    procedure_id: str = Field(..., description="ID del procedimiento (ej: carillas_porcelana)")
    procedure_name: str = Field(default="", description="Nombre legible")
    recovery_days_min: int = Field(default=1, ge=0)
    recovery_days_max: int = Field(default=3, ge=0)
    recovery_level: RecoveryLevel = RecoveryLevel.MEDIUM_LOW
    appointment_window_start: Optional[date] = None
    appointment_window_end: Optional[date] = None
    assigned_doctor_id: Optional[str] = None
    assigned_clinic_id: Optional[str] = None


class FlightOption(BaseModel):
    """Opción de vuelo."""
    provider: str = "demo"
    origin_airport: str
    destination_airport: str = Field(default="PEI", description="Matecaña, Pereira")
    departure_date: date
    return_date: Optional[date] = None
    airline: str = ""
    stops: int = 0
    estimated_price_usd: float = 0.0
    currency: str = "USD"
    booking_url: Optional[str] = None
    notes: str = ""


class LodgingOption(BaseModel):
    """Opción de hospedaje."""
    provider: str = "demo"
    name: str
    type: str = Field(default="hotel", description="hotel, airbnb, hostal, clinica_hotel")
    location: str = ""
    distance_to_clinic_km: Optional[float] = None
    price_per_night_usd: float = 0.0
    available: bool = True
    recovery_friendly: bool = Field(
        default=True,
        description="Apto para pacientes en recuperación"
    )
    amenities: List[str] = Field(default_factory=list)
    booking_url: Optional[str] = None
    notes: str = ""


class EventOption(BaseModel):
    """Opción de entretenimiento/experiencia."""
    provider: str = "demo"
    name: str
    category: str = Field(default="cultural", description="gastronomia, cultural, naturaleza, wellness")
    impact_level: RecoveryLevel = RecoveryLevel.MEDIUM_LOW
    estimated_duration_hours: float = 2.0
    estimated_price_usd: float = 0.0
    available_dates: List[date] = Field(default_factory=list)
    description: str = ""
    notes: str = ""


class LogisticsPlan(BaseModel):
    """Plan logístico calculado."""
    arrival_window_start: Optional[date] = None
    arrival_window_end: Optional[date] = None
    stay_duration_days: int = Field(default=5, ge=1)
    departure_window_start: Optional[date] = None
    departure_window_end: Optional[date] = None
    transfer_needed: bool = True
    transfer_notes: str = ""


class OrchestrationPlan(BaseModel):
    """Plan orquestado final."""
    status: PlanStatus = PlanStatus.DRAFT
    flight_options: List[FlightOption] = Field(default_factory=list)
    lodging_options: List[LodgingOption] = Field(default_factory=list)
    entertainment_options: List[EventOption] = Field(default_factory=list)
    assigned_provider_ids: Dict[str, str] = Field(default_factory=dict)
    total_estimated_value_usd: float = 0.0
    next_actions: List[str] = Field(
        default_factory=list,
        description="Acciones para el humano en Pereira"
    )
    notes: str = ""


class LeadScore(BaseModel):
    """Score inter-industria del lead."""
    priority: PriorityLabel = PriorityLabel.MEDIA
    score_value: float = Field(default=0.0, ge=0.0, le=1.0, description="Interno, no expuesto al humano")
    reasons: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
# MODELO PRINCIPAL: TourismTransaction
# ══════════════════════════════════════════════════════════════════════════════

class TourismTransaction(BaseModel):
    """
    Objeto canónico UDM-T.
    Viaja por todo el pipeline inter-industria: Salud → Turismo → Hospitalidad → Entretenimiento.
    """
    transaction_id: str = Field(
        default_factory=lambda: f"ODI-PAEM-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    mode: str = Field(default="intel", description="intel | action")

    context: TransactionContext
    user_profile: UserProfile = Field(default_factory=UserProfile)
    clinical_plan: Optional[ClinicalPlan] = None
    logistics: LogisticsPlan = Field(default_factory=LogisticsPlan)
    orchestration: OrchestrationPlan = Field(default_factory=OrchestrationPlan)
    lead_score: Optional[LeadScore] = None

    def save(self, base_dir: str = "/opt/odi/data/turismo/transactions") -> Path:
        """Persistir transacción como JSON."""
        path = Path(base_dir)
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"{self.transaction_id}.json"
        self.updated_at = datetime.utcnow()
        file_path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return file_path

    @classmethod
    def load(cls, transaction_id: str, base_dir: str = "/opt/odi/data/turismo/transactions") -> "TourismTransaction":
        """Cargar transacción desde JSON."""
        file_path = Path(base_dir) / f"{transaction_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Transaction {transaction_id} not found at {file_path}")
        return cls.model_validate_json(file_path.read_text(encoding="utf-8"))

    def summary(self) -> Dict[str, Any]:
        """Resumen legible para humanos."""
        return {
            "id": self.transaction_id,
            "mode": self.mode,
            "industry": self.context.primary_industry.value,
            "node": self.context.node_id,
            "status": self.orchestration.status.value,
            "flights": len(self.orchestration.flight_options),
            "lodging": len(self.orchestration.lodging_options),
            "entertainment": len(self.orchestration.entertainment_options),
            "estimated_total_usd": self.orchestration.total_estimated_value_usd,
            "priority": self.lead_score.priority.value if self.lead_score else "N/A",
            "next_actions": self.orchestration.next_actions,
        }
