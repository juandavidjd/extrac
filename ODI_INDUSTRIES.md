# ODI — Arquitectura de Industrias v1.0

**Fecha:** 10 Febrero 2026
**Propósito:** Documentar la estructura de industrias y ramas del ecosistema ODI

---

## Jerarquía de Industrias

```
ODI (Organismo Digital Industrial)
│
├── INDUSTRIA TRANSPORTE
│   └── Rama: MOTOS (SRM)
│       ├── somosrepuestosmotos.com
│       ├── larocamotorepuestos.com (.online, .info, .tienda)
│       └── 13,575 SKUs / 10 tiendas Shopify
│
├── INDUSTRIA SALUD
│   ├── Rama: DENTAL
│   │   ├── matzudentalaesthetics.com
│   │   ├── mis-cubiertas.com
│   │   ├── Matzu Clínica Odontológica
│   │   └── COVER'S Laboratorio (bruxismo)
│   │
│   └── Rama: CAPILAR
│       ├── cabezasanas.com (.tienda, .online, .info)
│       └── Especialistas dermatólogos tricólogos
│
├── INDUSTRIA TURISMO ← PAEM v1.0 (13 Feb 2026)
│   ├── Tourism Engine (orquestador viabilidad)
│   ├── Providers: Vuelos, Hospedaje, Eventos (pluggable)
│   ├── SLA Clínico Dinámico (industry_router)
│   ├── Lead Scoring Inter-Industria
│   └── liveodi.com (.info, .online, .tienda)
│
└── INDUSTRIA ENTRETENIMIENTO ← Integrada como adapter
    ├── Filtro por recovery_level del paciente
    ├── Experiencias Eje Cafetero (gastronomía, cultural, wellness)
    └── Terapia de Entorno (entretenimiento ≠ ocio)
```

---

## Datos en Servidor (DigitalOcean)

| Industria | Rama | Ruta en Servidor | Descripción |
|-----------|------|------------------|-------------|
| Salud | Dental | `/mnt/volume_sfo3_01/matzu` | Clínica Odontológica |
| Salud | Dental | `/mnt/volume_sfo3_01/COVER'S` | Laboratorio bruxismo |
| Salud | Capilar | `/mnt/volume_sfo3_01/Cabezas Sanas` | Tricología |
| Transporte | Motos | `/mnt/volume_sfo3_01/yokomar`, etc. | Catálogos proveedores |

---

## Mapeo de Dominios a Estados

| Dominio | DomainState | P-Level | TTL |
|---------|-------------|---------|-----|
| SRM (motos) | `SRM` | Default | - |
| Emprendimiento | `EMPRENDIMIENTO` | P1 | 30min |
| Turismo | `TURISMO` | P1 | 30min |
| Turismo Dental | `TURISMO_SALUD` | P1 | 30min |
| Salud General | `SALUD` | P1 | 30min |
| Belleza | `BELLEZA` | P1 | 30min |
| Emergencias | `SAFETY` | P0 | ∞ |
| Identidad | `UNIVERSAL` | P3 | 30min |

---

## Triggers por Industria

### INDUSTRIA SALUD — Rama DENTAL

```python
P1_DENTAL_TRIGGERS = {
    # Turismo odontológico
    "turismo odontológico": "TURISMO_SALUD",
    "turismo odontologico": "TURISMO_SALUD",
    "turismo dental": "TURISMO_SALUD",
    "viaje dental": "TURISMO_SALUD",
    "tratamiento dental en": "TURISMO_SALUD",

    # Procedimientos
    "implante": "TURISMO_SALUD",
    "implantes": "TURISMO_SALUD",
    "implantes dentales": "TURISMO_SALUD",
    "diseño de sonrisa": "TURISMO_SALUD",
    "carillas": "TURISMO_SALUD",
    "blanqueamiento": "TURISMO_SALUD",
    "blanqueamiento dental": "TURISMO_SALUD",
    "ortodoncia": "TURISMO_SALUD",
    "brackets": "TURISMO_SALUD",
    "invisalign": "TURISMO_SALUD",
    "corona dental": "TURISMO_SALUD",
    "endodoncia": "TURISMO_SALUD",
    "extracción": "TURISMO_SALUD",
    "prótesis dental": "TURISMO_SALUD",

    # Bruxismo (COVER'S)
    "bruxismo": "TURISMO_SALUD",
    "rechinar dientes": "TURISMO_SALUD",
    "guarda oclusal": "TURISMO_SALUD",
    "placa de bruxismo": "TURISMO_SALUD",
    "protector dental": "TURISMO_SALUD",

    # Matzu específico
    "matzu": "TURISMO_SALUD",
    "clínica dental medellín": "TURISMO_SALUD",
    "dentista medellín": "TURISMO_SALUD",
}
```

### INDUSTRIA SALUD — Rama CAPILAR

```python
P1_CAPILAR_TRIGGERS = {
    "cabeza sana": "SALUD",
    "cabezas sanas": "SALUD",
    "caída del cabello": "SALUD",
    "alopecia": "SALUD",
    "tricología": "SALUD",
    "tricologo": "SALUD",
    "tricólogo": "SALUD",
    "dermatólogo capilar": "SALUD",
    "tratamiento capilar": "SALUD",
    "injerto capilar": "SALUD",
    "trasplante de cabello": "SALUD",
    "minoxidil": "SALUD",
    "finasteride": "SALUD",
}
```

---

## Servicios por Rama

### Matzu Clínica Odontológica

| Servicio | Categoría | Rango Precio (COP) |
|----------|-----------|-------------------|
| Diseño de Sonrisa | Estética | $3M - $15M |
| Implante Unitario | Rehabilitación | $2.5M - $4M |
| Blanqueamiento | Estética | $400K - $800K |
| Carillas (x unidad) | Estética | $800K - $1.5M |
| Ortodoncia Brackets | Ortodoncia | $3M - $6M |
| Invisalign | Ortodoncia | $8M - $15M |
| Corona Cerámica | Rehabilitación | $800K - $1.2M |
| Endodoncia | Tratamiento | $300K - $600K |

### COVER'S Laboratorio (Bruxismo)

| Servicio | Descripción | Rango Precio (COP) |
|----------|-------------|-------------------|
| Guarda Oclusal Básica | Acrílico termocurado | $150K - $300K |
| Guarda Premium | Material importado | $400K - $600K |
| Evaluación Bruxismo | Diagnóstico completo | $100K - $200K |

### Cabezas Sanas (Tricología)

| Servicio | Descripción | Rango Precio (COP) |
|----------|-------------|-------------------|
| Consulta Tricológica | Evaluación capilar | $150K - $250K |
| Tratamiento PRP | Plasma rico en plaquetas | $400K - $800K |
| Microinjerto | Por sesión | $2M - $5M |

---

## Ubicaciones

| Marca | Ciudad | País |
|-------|--------|------|
| Matzu Dental | Medellín | Colombia |
| COVER'S | Medellín | Colombia |
| Cabezas Sanas | Pereira | Colombia |
| La Roca Motorepuestos | Pereira | Colombia |

---

## Contactos de Coordinación

| Marca | WhatsApp | Rol |
|-------|----------|-----|
| ODI Principal | +57 322 5462101 | Gateway unificado |
| (Pendiente) | - | Coordinación Matzu |
| (Pendiente) | - | Coordinación COVER'S |
| (Pendiente) | - | Coordinación Cabezas Sanas |

---

## Flujo de Activación P2 (Salud/Dental)

```
Usuario: "Quiero turismo odontológico"
         │
         ▼
    ┌─────────────┐
    │ Gate Check  │ → P1 trigger "turismo odontológico"
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │ Domain Lock │ → TURISMO_SALUD (30min)
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │ Handler P2  │ → Intake estructurado
    └─────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ 1. ¿Qué procedimiento te interesa?   │
    │ 2. ¿En qué ciudad te gustaría?       │
    │ 3. ¿Cuándo planeas viajar?           │
    │ 4. ¿Presupuesto aproximado?          │
    └──────────────────────────────────────┘
         │
         ▼
    ┌─────────────┐
    │ Hand-off    │ → Coordinador humano o cita
    └─────────────┘
```

### Flujo PAEM v1.0 (Automatizado, 13 Feb 2026)

```
Lead: "Viajo en 20 días a Pereira para implantes"
         │
         ▼
    ┌──────────────────────┐
    │ Industry Router      │ → Detecta Salud+Turismo+Hospedaje
    └──────────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ SLA Clínico Dinámico │ → Matzu saturado? → Red alternativa
    └──────────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ Tourism Engine       │ → Vuelos + Hospedaje + Entretenimiento
    └──────────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ Lead Scoring         │ → ALTA/MEDIA/BAJA + reasons
    └──────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ OrchestrationPlan con next_actions   │
    │ → Presentar opciones al paciente     │
    │ → Coordinar transporte               │
    │ → Persistir transacción UDM-T        │
    └──────────────────────────────────────┘
```

---

## Módulo Industria Turismo — PAEM v1.0 (13 Feb 2026)

**Protocolo de Activación Económica Multindustria.**
Convierte intención clínica en itinerario económico completo.
Es inter-industria: Salud → Turismo → Hospitalidad → Entretenimiento → Educación.

### Arquitectura

```
core/industries/turismo/
├── udm_t.py                  # UDM-T: modelo canónico universal
├── industry_router.py        # SLA clínico dinámico + routing inter-industria
├── tourism_engine.py         # Orquestador viabilidad → plan
├── entertainment_adapter.py  # Terapia de entorno (filtro por recovery_level)
├── hospitality_adapter.py    # Hospedaje recovery-friendly
├── lead_scoring.py           # Scoring inter-industria compuesto
├── api_routes.py             # Endpoints /tourism/*
└── providers/
    ├── base.py               # Interfaces: FlightProvider, LodgingProvider, EventsProvider
    ├── flights_demo.py       # Demo: rutas hacia PEI (Matecaña)
    ├── lodging_demo.py       # Demo: hoteles/Airbnb en Pereira
    ├── events_demo.py        # Demo: experiencias Eje Cafetero
    └── registry.py           # Selección por ENV (ODI_FLIGHTS_PROVIDER, etc.)
```

### Endpoints (Puerto 8800)

| Método | Ruta | Función |
|--------|------|---------|
| POST | /tourism/plan | Crear plan turístico completo |
| POST | /tourism/assign | Asignar doctor/nodo por SLA |
| POST | /tourism/score | Calcular lead scoring inter-industria |
| GET | /tourism/capacity/{node_id} | Consultar SLA clínica |
| GET | /tourism/health | Health check módulo turismo |

### Modos

- **INTEL MODE** (default): Sin API keys, sugerencias y estimaciones demo.
- **ACTION MODE**: Con keys de provider, prebooking / reservas reales.

### Variables de Entorno

```
ODI_FLIGHTS_PROVIDER=demo    # demo | (futuro: amadeus, skyscanner)
ODI_LODGING_PROVIDER=demo    # demo | (futuro: booking, airbnb_api)
ODI_EVENTS_PROVIDER=demo     # demo | (futuro: viator, local_api)
```

### Lead Scoring

```
Score = 0.20·semantic + 0.15·sentiment + 0.25·urgency
      + 0.25·logistics - 0.15·latency_penalty
```
Salida: ALTA / MEDIA / BAJA + reasons (nunca número exacto al humano).

### Red de Nodos

```
data/turismo/
├── sla/matzu_001.json                  # SLA clínico de Matzu
├── network/health_nodes.json           # Red de doctores/clínicas
├── network/hospitality_partners.json   # Aliados hospedaje
├── network/education_certifiers.json   # Certificadores educativos
└── transactions/                       # Transacciones UDM-T persistidas
```

---

## Changelog

- **v1.1 (13 Feb 2026):** Módulo Industria Turismo PAEM v1.0 — SLA dinámico, lead scoring, providers pluggable, modo demo E2E
- **v1.0 (10 Feb 2026):** Estructura inicial de industrias
