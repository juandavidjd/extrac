"""
Industria Turismo — PAEM (Protocolo de Activación Económica Multindustria)
==========================================================================
Convierte intención clínica en itinerario económico completo.

Componentes:
  - udm_t.py                 : Modelo de datos universal turismo (UDM-T)
  - industry_router.py       : Router inter-industria + SLA clínico dinámico
  - tourism_engine.py        : Orquestador de viabilidad → plan
  - entertainment_adapter.py : Filtro entretenimiento por recovery_level
  - hospitality_adapter.py   : Adapter hoteles/Airbnb/hostales
  - lead_scoring.py          : Scoring inter-industria compuesto
  - api_routes.py            : Endpoints FastAPI (/tourism/*)

Providers (pluggable):
  - providers/base.py        : Interfaces abstractas
  - providers/flights_demo.py: Demo sin API keys
  - providers/lodging_demo.py: Demo sin API keys
  - providers/events_demo.py : Demo sin API keys
  - providers/registry.py    : Selección de provider por ENV

Modos:
  A) INTEL MODE  — Sin keys, sin reservas: sugerencias y estimaciones.
  B) ACTION MODE — Con keys de provider: prebooking / reservas reales.
"""

__version__ = "1.0.0"
