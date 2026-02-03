# ODI v5.3 DEEPL - n8n Workflow Analysis

## Overview

This is the **conversational orchestration layer** of ODI implemented in n8n. It handles the complete message lifecycle from ingestion to response, with multilingual support via DeepL.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ODI v5.3 DEEPL WORKFLOW                          │
│                                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌───────┐│
│  │ Webhook  │──▶│Normalizer│──▶│ Detectar │──▶│ DeepL ES │──▶│Intent ││
│  │ Ingest   │   │          │   │ Idioma   │   │          │   │Class. ││
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └───────┘│
│       ▼                                                          │     │
│  WhatsApp                                                        ▼     │
│  API Direct                                              ┌───────────┐ │
│                                                          │    CES    │ │
│                                                          │ Evaluator │ │
│                                                          └─────┬─────┘ │
│                                                                │       │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │       │
│  │ Send WA  │◀──│ DeepL    │◀──│ Response │◀──│ Fitment  │◀──┘       │
│  │ / API    │   │ Original │   │ Format   │   │ M6.2     │           │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘           │
│       │                                              │                │
│       ▼                                              ▼                │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │                    PostgreSQL LEDGER                             ││
│  │          audit_events (ACTION_STARTED, ACTION_COMPLETED)         ││
│  └──────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Workflow Nodes

### 1. Ingestion Layer

#### Webhook Ingest
- **Endpoint**: `POST /webhook/odi-ingest`
- **Accepts**: WhatsApp webhook, Direct API calls

#### Normalizer
Normalizes input from different sources:

```javascript
// WhatsApp format
{
  entry: [{ changes: [{ value: { messages: [...], contacts: [...] } }] }]
}

// API format
{
  text: "mensaje",
  canal: "api",
  user_id: "123"
}

// Output normalizado
{
  odi_event_id: "ODI-LXYZ123",
  canal: "whatsapp" | "api",
  from: "573001234567",
  text: "necesito pastillas de freno para fz 2020",
  contact_name: "Juan",
  timestamp: "2024-01-15T..."
}
```

### 2. Language Layer

#### Detectar Idioma
Simple pattern-based detection:

| Language | Patterns |
|----------|----------|
| **ES** | hola, buenos, tienen, necesito, precio, freno, filtro |
| **EN** | hello, hi, do you have, looking for, brake, filter |
| **PT** | olá, oi, bom dia, vocês, têm, freio, filtro |

Special: Portuguese characters (ã, õ, ç) force PT detection.

#### DeepL → Español
Translates non-Spanish input to Spanish for processing:

```javascript
// Request to DeepL
POST https://api-free.deepl.com/v2/translate
{
  text: ["Hello, do you have brake pads for FZ 2020?"],
  target_lang: "ES"
}

// Result
"Hola, ¿tienen pastillas de freno para FZ 2020?"
```

### 3. Classification Layer

#### Intent Classifier
Classifies user intent and extracts entities:

**Intents:**
| Intent | Triggers |
|--------|----------|
| `SALUDO` | hola, buenos, buenas, hi, hello |
| `FITMENT` | Any automotive entity detected |
| `PRECIO` | precio, cuánto, price, how much |
| `COMPRA` | comprar, quiero, buy, want |
| `ESTADO_PEDIDO` | pedido, orden, order |
| `SOPORTE` | ayuda, problema, help |
| `GENERAL` | Default fallback |

**Entity Extraction:**

```javascript
entities: {
  marca: "YAMAHA",      // 20+ brands supported
  modelo: "FZ",         // 30+ models supported
  year: "2020",         // 1990-2029
  cilindraje: "150",    // XXcc pattern
  repuesto: "pastilla"  // 30+ parts (ES/EN/PT)
}
```

**Fitment Decision:**
```javascript
goToFitment = entities.repuesto || entities.marca || entities.modelo || entities.cilindraje
```

### 4. Governance Layer

#### CES Evaluator
Constitutional Ethics System - simple risk evaluation:

```javascript
// Current rules
if (intent === 'COMPRA' && amount > 200000) {
  return { action: 'AWAIT_HUMAN', risk: 'HIGH', reason: 'Monto supera umbral' };
}
return { action: 'PROCEED', risk: 'LOW' };
```

#### Ledger Ingest / Ledger Response
Writes to PostgreSQL audit_events with:

```sql
INSERT INTO audit_events (
  event_id,        -- 'ODI-LXYZ123'
  event_type,      -- 'ACTION_STARTED' | 'ACTION_COMPLETED'
  category,        -- 'ACTION' | 'RESPONSE'
  user_id,         -- Phone/user ID
  action_type,     -- Intent
  risk_level,      -- 'LOW' | 'HIGH'
  metadata,        -- JSON with full context
  event_hash       -- SHA256 for immutability
)
```

### 5. Fitment Layer

#### Consultar M6.2
Queries the fitment service:

```javascript
POST http://odi-m62-fitment:8802/fitment/query
{
  q: "pastillas de freno para fz 2020"
}

// Response
{
  query_id: "FIT-123",
  results: [
    {
      title: "Pastillas Freno Delantero FZ 150",
      price: 45000,
      price_formatted: "$45,000",
      compatibility: "FZ 150/250 2018-2024",
      client: "KAIQI"
    },
    // ... more results
  ]
}
```

#### Formatear Fitment
Formats results for user:

```
Encontré 5 opciones.

MEJOR OPCIÓN:
Pastillas Freno Delantero FZ 150
Precio: $45,000
Compatible: FZ 150/250 2018-2024
Proveedor: KAIQI

Hay 4 opciones más disponibles.
```

### 6. Response Layer

#### Response General
Handles non-fitment intents:

| Intent | Response |
|--------|----------|
| SALUDO | ¡Hola {name}! 👋 Soy ODI, tu asistente de repuestos... |
| PRECIO | Para darte precios necesito saber: ¿qué repuesto...? |
| COMPRA | Excelente, quieres hacer una compra... |
| ESTADO_PEDIDO | Para consultar tu pedido necesito el número... |
| SOPORTE | Entiendo que tienes un inconveniente... |
| GENERAL | Soy ODI, especialista en repuestos de motos... |

#### DeepL → Idioma Original
Translates response back to user's language:

```javascript
POST https://api-free.deepl.com/v2/translate
{
  text: ["Encontré 5 opciones..."],
  target_lang: "EN"  // or "PT"
}
```

### 7. Delivery Layer

#### Send WA (disabled)
WhatsApp Cloud API delivery:

```javascript
POST https://graph.facebook.com/v18.0/{phone_number_id}/messages
{
  messaging_product: "whatsapp",
  to: "573001234567",
  type: "text",
  text: { body: "Found 5 options..." }
}
```

#### OK API
JSON response for API channel:

```javascript
{
  status: "ok",
  event_id: "ODI-LXYZ123",
  intent: "FITMENT",
  detected_lang: "EN",
  translated: true,
  ledger_sequence: "42",
  fitment_query_id: "FIT-123",
  fitment_count: 5,
  entities: { marca: "YAMAHA", modelo: "FZ", year: "2020" },
  best_option: { title: "...", price: 45000 },
  response: "Found 5 options...",
  response_es: "Encontré 5 opciones..."
}
```

---

## Supported Brands & Models

### Marcas (20+)
```
YAMAHA, HONDA, SUZUKI, KAWASAKI, BAJAJ, PULSAR, KTM, TVS,
AKT, HERO, AUTECO, VICTORY, KYMCO, SYM, PIAGGIO, VESPA,
BENELLI, ROYAL ENFIELD, CFMOTO, ZONTES
```

### Modelos (30+)
```
FZ, MT, R15, R3, R6, R1, NMAX, BWS, XTZ, YBR, FAZER, CRYPTON,
CB, CBR, CRF, NINJA, DUKE, DOMINAR, NS, RS, DISCOVER, BOXER,
PLATINO, CT100, GIXXER, GSXR, AGILITY
```

### Repuestos (30+)
```
Español: pastilla, freno, filtro, aceite, cadena, piñon, kit,
         llanta, bateria, faro, espejo, cable, clutch, embrague,
         suspension, amortiguador, rodamiento, empaque, piston,
         biela, cigueñal, carburador, bujia, bobina

English: brake, pad, filter, oil, chain, tire, battery, mirror

Portuguese: freio, filtro, corrente, óleo
```

---

## Integration with Cortex Visual

To connect this workflow with the Cortex Visual interface:

### Events to Emit

```typescript
// On message received (after Normalizer)
emitEvent('INGEST_RECEIVED', {
  event_id: odi_event_id,
  canal: canal,
  from: from,
  detected_lang: detected_lang
});

// On intent classified
emitEvent('INTENT_CLASSIFIED', {
  intent: intent,
  entities: entities,
  goToFitment: goToFitment
});

// On CES evaluation
emitEvent('CES_EVALUATED', {
  action: ces.action,
  risk: ces.risk
});

// On fitment query
emitEvent('FITMENT_QUERY', {
  query_id: fitment_query_id,
  count: fitment_count
});

// On response sent
emitEvent('RESPONSE_SENT', {
  channel: canal,
  translated: response_translated
});
```

### HTTP Request Node Addition

Add after each key step:

```javascript
// HTTP Request to ODI Kernel
POST http://localhost:3000/odi/vision/event
{
  source: "n8n",
  event_type: "INGEST_RECEIVED",
  actor: "ODI_N8N_v5.3",
  data: { ... }
}
```

---

## Environment Configuration

```bash
# DeepL API
DEEPL_API_KEY=6076c331-11ca-4934-a1fa-b6ca05d56686

# Fitment Service
FITMENT_URL=http://odi-m62-fitment:8802

# PostgreSQL (Ledger)
POSTGRES_HOST=...
POSTGRES_DB=...

# WhatsApp Cloud API
WHATSAPP_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...

# Facebook Graph API
FB_GRAPH_VERSION=v18.0
```

---

## Database Schema

```sql
CREATE TABLE audit_events (
  id SERIAL PRIMARY KEY,
  event_id VARCHAR(50) UNIQUE,
  sequence_num BIGSERIAL,
  event_type VARCHAR(50),
  category VARCHAR(50),
  user_id VARCHAR(100),
  action_type VARCHAR(50),
  target_type VARCHAR(50),
  target_id VARCHAR(100),
  risk_level VARCHAR(20),
  metadata JSONB,
  event_hash VARCHAR(64),
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Workflow Statistics

| Metric | Value |
|--------|-------|
| Total Nodes | 26 |
| Webhook Endpoints | 1 |
| HTTP Requests | 4 (DeepL x2, Fitment, WhatsApp) |
| Database Operations | 2 (Ledger Ingest, Ledger Response) |
| Code Nodes | 9 |
| Conditional Nodes | 5 |
| Merge Nodes | 6 |

---

## Tony/Ramona Voice Mapping

For NarratorEngine integration:

| Event | Voice | Narrative Template |
|-------|-------|-------------------|
| INGEST_RECEIVED | SISTEMA | "Mensaje recibido de {canal}: {from}" |
| INTENT_CLASSIFIED (FITMENT) | TONY | "Tony detectó consulta de fitment: {marca} {modelo} {repuesto}" |
| INTENT_CLASSIFIED (SALUDO) | RAMONA | "Ramona recibe saludo de {contact_name}" |
| CES_AWAIT_HUMAN | RAMONA | "Un momento, necesito autorización para esta operación" |
| FITMENT_QUERY | TONY | "Tony consultando base de fitment... {count} resultados" |
| RESPONSE_SENT | RAMONA | "Respuesta enviada a {contact_name} via {canal}" |

---

*Document Version: 1.0*
*Workflow Version: ODI_v5.3_DEEPL*
*Generated: 2026-01-31*
