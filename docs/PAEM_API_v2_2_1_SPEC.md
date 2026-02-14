# PAEM API v2.2.1 — Especificación Técnica

**Estado:** SPEC (pendiente implementar)
**Fecha:** 13 Feb 2026
**Equipos:** API Team + Orchestration Team + Calendar Team
**Puerto objetivo:** 8807 (odi-paem-api)

---

## Resumen

PAEM v2.2.1 integra HOLD automático de slots clínicos con confirmación
atómica de reservas. El flujo completo:

```
Lead → /paem → route_calendar (HOLD) → tourism_engine → READY_FOR_CONFIRMATION
Humano confirma → /paem/confirm → fn_odi_confirm_booking → CONFIRMED
```

---

## Endpoints

### GET /health

```json
{"ok": true, "service": "odi-paem", "version": "2.2.1"}
```

### POST /paem

Ejecuta flujo PAEM completo: routing + HOLD + cotización turismo.

**Request:**

```json
{
  "transaction_id": "ODI-PAEM-2026-DEMO-HOLD-01",
  "lead_id": "WA:+57-3000000000",
  "procedure_id": "implantes",
  "primary_node_id": "HLT-PER-MATZU-001",
  "origin_city": "Bogotá",
  "recovery_profile": "medium",
  "accepts_international": true
}
```

**Response (READY_FOR_CONFIRMATION):**

```json
{
  "ok": true,
  "data": {
    "transaction_id": "ODI-PAEM-2026-DEMO-HOLD-01",
    "status": "READY_FOR_CONFIRMATION",
    "assignment_id": "...",
    "assigned_node_id": "HLT-PER-MATZU-001",
    "city": "Pereira",
    "procedure_id": "implantes",
    "booking_hold": {
      "booking_id": "BKG-...",
      "hold_expires_at": "2026-02-13T15:30:00Z"
    },
    "slot_options": [...],
    "logistics": {...},
    "total_estimated_cost": 3450.00
  }
}
```

### POST /paem/confirm

Confirma una reserva con HOLD activo.

**Request:**

```json
{
  "transaction_id": "ODI-PAEM-2026-DEMO-HOLD-01",
  "booking_id": "BKG-DEVUELTO-POR-PAEM"
}
```

**Response:**

```json
{
  "ok": true,
  "data": {
    "transaction_id": "...",
    "booking_id": "...",
    "status": "CONFIRMED"
  }
}
```

---

## Servicios Internos

### 1. industry_router_v2_2_calendar.py

`route_calendar()` — Router con calendario integrado:

- Lee nodo primario (Redis → Postgres → JSON)
- Evalúa saturación y SLA
- Si nodo disponible: genera slot_options con lookahead (14 días por defecto)
- Primer slot compatible → HOLD automático (15 min por defecto)
- Si saturado → failover multi-ciudad → mismo flujo de slots
- Retorna: `assigned_node_id`, `assignment_id`, `slot_options`, `hold`

### 2. paem_orchestrator_v2_2_1.py

`execute_paem_flow_v221()` — Orquestador:

1. Llama `route_calendar()` → obtiene slot reservado con HOLD
2. Pasa fecha real del slot a `tourism_engine()` → vuelos, hospedaje, entretenimiento
3. Arma `final_package` con booking_id + hold_expires_at
4. Registra evento `PAEM.READY_FOR_CONFIRMATION` en `odi_events`
5. Retorna payload completo al endpoint

### 3. tourism_engine.py (ajuste v2.2.1)

Acepta `appointment_start_ts` y `appointment_end_ts` del slot reservado.
Los transporta en el resultado para que n8n los muestre y futuros providers de vuelos los usen.

---

## Postgres — Funciones Nuevas Requeridas

### fn_odi_confirm_booking(booking_id TEXT)

```sql
-- Cambia estado del booking de HOLD a CONFIRMED
-- Valida que el hold no haya expirado
-- Returns: (ok BOOLEAN, error TEXT)
```

### Tabla: odi_events (event sourcing)

```sql
CREATE TABLE IF NOT EXISTS odi_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,      -- PAEM.READY_FOR_CONFIRMATION, PAEM.BOOKING_CONFIRMED
    transaction_id TEXT,
    assignment_id TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### Tabla: odi_bookings (slots + HOLD)

```sql
-- Gestión de slots con estado:
-- AVAILABLE → HOLD → CONFIRMED | EXPIRED
-- hold_expires_at: timestamp de expiración automática
```

---

## Rate Limiting

- Por IP, bucket por minuto
- Redis INCR con TTL 70s
- Default: 30 requests/minuto
- HTTP 429 si excede

---

## Variables de Entorno

```
ODI_PG_DSN=dbname=odi user=postgres password=postgres host=odi-postgres port=5432
ODI_REDIS_URL=redis://odi-redis:6379/0
ODI_RATE_LIMIT_PER_MIN=30
ODI_HOLD_MINUTES=15
ODI_SLOTS_LOOKAHEAD_DAYS=14
ODI_SLOTS_LIMIT=3
```

---

## Docker Compose (servicio nuevo)

```yaml
odi-paem-api:
  image: odi-paem-api:latest
  port: 8807
  environment:
    ODI_PG_DSN: "dbname=odi user=postgres password=postgres host=odi-postgres port=5432"
    ODI_REDIS_URL: "redis://odi-redis:6379/0"
    ODI_RATE_LIMIT_PER_MIN: "30"
    ODI_HOLD_MINUTES: "15"
    ODI_SLOTS_LOOKAHEAD_DAYS: "14"
    ODI_SLOTS_LIMIT: "3"
```

---

## Flujo de Eventos Auditables

```
PAEM.ROUTING_STARTED     → Lead entra al router
PAEM.SLOT_HOLD_CREATED   → Slot reservado con TTL
PAEM.LOGISTICS_QUOTED    → Tourism engine cotizó
PAEM.READY_FOR_CONFIRMATION → Paquete listo para humano
PAEM.BOOKING_CONFIRMED   → Humano confirmó
PAEM.HOLD_EXPIRED        → HOLD expiró sin confirmación
```

---

## Pruebas (curl)

```bash
# 1) Ejecutar PAEM completo
curl -X POST http://localhost:8807/paem \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "ODI-PAEM-2026-DEMO-HOLD-01",
    "lead_id": "WA:+57-3000000000",
    "procedure_id": "implantes",
    "primary_node_id": "HLT-PER-MATZU-001",
    "origin_city": "Bogotá",
    "recovery_profile": "medium",
    "accepts_international": true
  }'

# 2) Confirmar booking
curl -X POST http://localhost:8807/paem/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "ODI-PAEM-2026-DEMO-HOLD-01",
    "booking_id": "BKG-REEMPLAZA-CON-EL-DEVUELTO"
  }'
```

---

## Métricas de Conversión

Con este flujo se puede medir:

| Métrica | Evento |
|---------|--------|
| HOLDs creados | `PAEM.SLOT_HOLD_CREATED` |
| Confirmados | `PAEM.BOOKING_CONFIRMED` |
| Expirados | `PAEM.HOLD_EXPIRED` |
| Tasa Hold→Confirm | `CONFIRMED / (CONFIRMED + EXPIRED)` |

---

## Evolución Pendiente

- `/paem/confirm` con `option_slot_id` para switch hold (paciente elige slot 2 o 3)
- `odi_assignments` tabla formal (lead→node persistente)
- Cron de expiración automática de HOLDs
- Webhook a n8n en cada transición de estado
