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

## Módulo Industria Turismo — PAEM v2.0 (13 Feb 2026)

**Protocolo de Activación Económica Multindustria — Industria 5.0**
Convierte intención clínica en itinerario económico completo.
Es inter-industria: Salud → Turismo → Hospitalidad → Entretenimiento → Educación.
Paradigma: Postgres manda, Redis acelera, JSON es fallback. El humano es co-piloto.

### Arquitectura

```
core/industries/turismo/
├── udm_t.py                  # UDM-T: modelo canónico universal
├── industry_router.py        # SLA 3-tier: Redis → Postgres → JSON
├── tourism_engine.py         # Orquestador viabilidad → plan
├── entertainment_adapter.py  # Terapia de entorno (filtro por recovery_level)
├── hospitality_adapter.py    # Hospedaje recovery-friendly
├── lead_scoring.py           # Scoring inter-industria compuesto
├── api_routes.py             # Endpoints /tourism/*
├── db/
│   ├── client.py             # Conexión Postgres + Redis (graceful fallback)
│   └── sync_job.py           # Sync Postgres → Redis (cron / manual)
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
| POST | /tourism/sync | Disparar sync Postgres → Redis manual |
| GET | /tourism/capacity/{node_id} | Consultar SLA clínica |
| GET | /tourism/datasources | Estado de fuentes (Redis/PG/JSON) |
| GET | /tourism/health | Health check + modo actual |

### Modos

- **INTEL MODE** (default): Sin API keys, sugerencias y estimaciones demo.
- **ACTION MODE**: Con keys de provider, prebooking / reservas reales.

### Variables de Entorno

```
# Providers
ODI_FLIGHTS_PROVIDER=demo    # demo | (futuro: amadeus, skyscanner)
ODI_LODGING_PROVIDER=demo    # demo | (futuro: booking, airbnb_api)
ODI_EVENTS_PROVIDER=demo     # demo | (futuro: viator, local_api)

# Postgres (verdad base)
ODI_PG_HOST=127.0.0.1
ODI_PG_PORT=5432
ODI_PG_USER=odi
ODI_PG_PASS=odi
ODI_PG_DB=odi

# Redis (cache)
ODI_REDIS_HOST=127.0.0.1
ODI_REDIS_PORT=6379
ODI_REDIS_NODE_TTL=300       # TTL cache de nodos en segundos
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
├── transactions/                       # Transacciones UDM-T persistidas
└── migrations/
    ├── V001_health_census.sql          # Schema Postgres completo
    └── V002_seed_demo_data.sql         # Datos demo (3 nodos, 9 certs, 6 entretenimiento, 4 hospedaje)
```

### Jerarquía de Verdad (3 Niveles)

```
┌─────────────────────┐
│ 1. REDIS            │ ← Cache, TTL 300s, velocidad
│    health:node:*    │
├─────────────────────┤
│ 2. POSTGRES         │ ← Verdad base, auditable
│    odi_health_nodes │
│    v_odi_health..   │
│    fn_odi_failover  │
├─────────────────────┤
│ 3. JSON LOCAL       │ ← Fallback demo, siempre disponible
│    data/turismo/*   │
└─────────────────────┘
```

### Redis Key Conventions

```
health:node:<node_id>:status      → AVAILABLE|HIGH_LOAD|SATURATED  (TTL 300s)
health:node:<node_id>:saturation  → float 0.0-1.0                  (TTL 300s)
health:node:<node_id>:sla_minutes → int                            (TTL 300s)
health:node:<node_id>:data        → full JSON snapshot             (TTL 300s)
health:node:<node_id>:last_sync   → epoch                          (TTL 600s)
```

### Tablas Postgres (Health Census v1)

| Tabla | Función |
|-------|---------|
| `odi_health_nodes` | Nodos clínicos (capacidad, SLA, certificación) |
| `odi_health_certifications` | Certificaciones por procedimiento |
| `odi_health_capacity_log` | Log semanal auditable |
| `odi_entertainment_partners` | Partners entretenimiento |
| `odi_hospitality_partners` | Partners hospedaje |
| `odi_certification_weights` | Pesos para scoring |
| `v_odi_health_node_load` | Vista: estado de carga calculado |
| `fn_odi_failover_candidates()` | Función: candidatos failover |

---

## Changelog

- **v2.0 (13 Feb 2026):** Health Census Postgres + Redis sync + Router 3-tier + migraciones SQL + seed data
- **v1.1 (13 Feb 2026):** Módulo Industria Turismo PAEM v1.0 — SLA dinámico, lead scoring, providers pluggable, modo demo E2E
- **v1.0 (10 Feb 2026):** Estructura inicial de industrias
