# ODI_v6_CORTEX — Patch para Intent Override Gate

**Versión:** 1.0
**Fecha:** 10 Febrero 2026
**Workflow:** ODI_v6_CORTEX
**Ubicación:** https://odi.larocamotorepuestos.com (n8n)

---

## Problema Resuelto

```
ANTES (Bug 8 Feb 2026):
─────────────────────────
Usuario: "Quiero emprender un negocio"
ODI: "Para tu ECO! MANUBRIO HONDA..."  ❌

DESPUÉS (Fix):
─────────────────────────
Usuario: "Quiero emprender un negocio"
ODI: "Entendido. Cambio a modo Emprendimiento.
      ¿Esto es para iniciar desde cero o ya
      tienes una idea definida?"  ✅
```

---

## Arquitectura del Patch

```
┌─────────────────────────────────────────────────────────────────┐
│                    ODI_v6_CORTEX (n8n)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   WhatsApp Webhook                                              │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │         ⚡ INTENT OVERRIDE GATE (NUEVO)                │   │
│   │                                                         │   │
│   │   • Verificar P0 (Urgencia/Seguridad)                  │   │
│   │   • Verificar P3 (Meta-identidad)                      │   │
│   │   • Verificar P1 (Cambio de industria)                 │   │
│   │   • Verificar P2 (Ajuste de contexto)                  │   │
│   │                                                         │   │
│   │   Si override=true → Responder con canonical_response  │   │
│   │   Si override=false → Continuar flujo normal           │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                        │
│        ├── [override=true] → WhatsApp Response (directo)       │
│        │                                                        │
│        └── [override=false] → Intent Classification            │
│                                    │                            │
│                                    ▼                            │
│                              ChromaDB Search                    │
│                                    │                            │
│                                    ▼                            │
│                              GPT-4o Response                    │
│                                    │                            │
│                                    ▼                            │
│                              WhatsApp Response                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementación en n8n

### Paso 1: Agregar Nodo "Code" después del Webhook

**Nombre:** `Intent Override Gate`
**Tipo:** Code (JavaScript)
**Posición:** Inmediatamente después del nodo Webhook de WhatsApp

```javascript
// ============================================================================
// INTENT OVERRIDE GATE — n8n Code Node
// ============================================================================
// Versión: 1.0
// Fecha: 10 Febrero 2026
// DEBE ejecutarse ANTES de cualquier otro procesamiento
// ============================================================================

// Obtener mensaje del usuario
const message = $input.first().json.entry?.[0]?.changes?.[0]?.value?.messages?.[0]?.text?.body || '';
const from = $input.first().json.entry?.[0]?.changes?.[0]?.value?.messages?.[0]?.from || '';

// Contexto actual (obtener de Redis o variable de workflow)
const currentDomain = $input.first().json.current_domain || 'MOTOS';

// ============================================================================
// TRIGGERS (Prioridad: P0 > P3 > P1 > P2)
// ============================================================================

const P0_TRIGGERS = {
  'urgencia': 'SAFETY', 'urgente': 'SAFETY', 'emergencia': 'SAFETY',
  'policía': 'SAFETY', 'policia': 'SAFETY', 'ambulancia': 'SAFETY',
  'auxilio': 'SAFETY', 'socorro': 'SAFETY', 'me robaron': 'SAFETY',
  'me siguen': 'SAFETY', 'peligro': 'SAFETY', 'amenaza': 'SAFETY',
  'me van a': 'SAFETY', 'estoy en peligro': 'SAFETY',
  'dolor fuerte': 'HEALTH_EMERGENCY', 'accidente': 'SAFETY'
};

const P3_TRIGGERS = {
  'tú eres más que eso': 'IDENTITY_RESET', 'tu eres mas que eso': 'IDENTITY_RESET',
  'eres más que eso': 'IDENTITY_RESET', 'eres mas que eso': 'IDENTITY_RESET',
  'deja de ser experto': 'IDENTITY_RESET', 'no solo sabes de': 'IDENTITY_RESET',
  'solo sabes de': 'IDENTITY_CHALLENGE', 'no haces nada': 'IDENTITY_CHALLENGE',
  'no sabes nada': 'IDENTITY_CHALLENGE', 'quién eres': 'IDENTITY_QUERY',
  'quien eres': 'IDENTITY_QUERY'
};

const P1_TRIGGERS = {
  'emprender': 'EMPRENDIMIENTO', 'emprendimiento': 'EMPRENDIMIENTO',
  'negocio': 'EMPRENDIMIENTO', 'idea de negocio': 'EMPRENDIMIENTO',
  'quiero emprender': 'EMPRENDIMIENTO', 'tengo una idea': 'EMPRENDIMIENTO',
  'turismo': 'TURISMO', 'viaje': 'TURISMO', 'hotel': 'TURISMO',
  'turismo odontológico': 'TURISMO_SALUD', 'turismo odontologico': 'TURISMO_SALUD',
  'turismo médico': 'TURISMO_SALUD', 'turismo medico': 'TURISMO_SALUD',
  'salud': 'SALUD', 'médico': 'SALUD', 'medico': 'SALUD',
  'clínica': 'SALUD', 'clinica': 'SALUD', 'odontología': 'SALUD',
  'odontologia': 'SALUD', 'belleza': 'BELLEZA', 'estética': 'BELLEZA',
  'abogado': 'LEGAL', 'legal': 'LEGAL', 'educación': 'EDUCACION',
  'educacion': 'EDUCACION', 'curso': 'EDUCACION', 'trabajo': 'TRABAJO',
  'empleo': 'TRABAJO', 'empresa': 'TRABAJO'
};

const P2_TRIGGERS = {
  'no entiendo': 'HELP', 'cómo funciona': 'HELP', 'como funciona': 'HELP',
  'odi ayúdame': 'HELP', 'odi ayudame': 'HELP', 'ayúdame odi': 'HELP',
  'cambia de tema': 'SWITCH', 'otro tema': 'SWITCH', 'basta ya': 'STOP',
  'detente': 'STOP'
};

// ============================================================================
// RESPUESTAS CANÓNICAS
// ============================================================================

const RESPONSES = {
  'SAFETY': `Si estás en peligro inmediato, llama a la línea de emergencias ahora:
🚨 123 - Policía Nacional
🚑 125 - Bomberos
❤️ 106 - Cruz Roja

¿Estás a salvo? ¿En qué ciudad estás?`,

  'HEALTH_EMERGENCY': `Esto suena a una emergencia médica.
🚑 Llama al 125 (Bomberos) o 106 (Cruz Roja) inmediatamente.

¿Hay alguien contigo que pueda ayudar?`,

  'EMPRENDIMIENTO': `Entendido. Cambio a modo Emprendimiento.
¿Esto es para iniciar desde cero o ya tienes una idea definida?`,

  'TURISMO': `Entendido. Cambio a modo Turismo.
¿Buscas planear un viaje o crear un negocio de turismo?`,

  'TURISMO_SALUD': `Entendido. Turismo + Salud es una combinación interesante.
¿Buscas tratamiento dental + viaje, o quieres emprender en este sector?`,

  'SALUD': `Entendido. Cambio a modo Salud.
¿Esto es para una consulta personal o para un proyecto/negocio?`,

  'BELLEZA': `Entendido. Cambio a modo Belleza.
¿Buscas servicios o quieres emprender en este sector?`,

  'LEGAL': `Entendido. Cambio a modo Legal.
¿Necesitas asesoría legal personal o para un negocio?`,

  'EDUCACION': `Entendido. Cambio a modo Educación.
¿Quieres aprender algo específico o crear contenido educativo?`,

  'TRABAJO': `Entendido. Cambio a modo Trabajo.
¿Buscas optimizar tareas en tu empresa o encontrar empleo?`,

  'HELP': `Puedo ayudarte con:
• Tu trabajo (optimizar tareas)
• Tu negocio (crear presencia digital)
• Tus compras (encontrar productos)
• Aprender (academia y cursos)

¿Por dónde quieres empezar?`,

  'SWITCH': `Entendido. Cambio de tema.
¿En qué más puedo ayudarte?`,

  'STOP': `Entendido. Pausa.
Cuando quieras continuar, solo dime.`,

  'IDENTITY_RESET': `Tienes razón. No soy solo de una industria.

Soy ODI. Puedo ayudarte en cualquier área:
emprender, trabajar, comprar, aprender.

¿Qué necesitas hoy?`,

  'IDENTITY_CHALLENGE': `Tienes razón, ese repuesto no corresponde a lo que necesitas.
Déjame entender mejor: ¿qué es lo que realmente buscas?`,

  'IDENTITY_QUERY': `Soy ODI, un organismo digital industrial.
Puedo ayudarte con trabajo, emprendimiento, compras y aprendizaje.

¿Qué necesitas?`
};

// ============================================================================
// FUNCIONES
// ============================================================================

function normalizeText(text) {
  return text.toLowerCase().trim().replace(/[^\w\sáéíóúñü]/g, '');
}

function checkTriggers(text, triggers) {
  const normalized = normalizeText(text);
  const sortedTriggers = Object.keys(triggers).sort((a, b) => b.length - a.length);

  for (const trigger of sortedTriggers) {
    if (normalized.includes(trigger)) {
      return { trigger, category: triggers[trigger] };
    }
  }
  return null;
}

// ============================================================================
// ANÁLISIS
// ============================================================================

const normalizedMessage = normalizeText(message);
let override = false;
let response = '';
let newDomain = currentDomain;
let overrideLevel = 'NONE';
let triggerWord = '';
let category = '';

// P0: Seguridad (máxima prioridad)
let match = checkTriggers(message, P0_TRIGGERS);
if (match) {
  override = true;
  overrideLevel = 'P0_CRITICAL';
  triggerWord = match.trigger;
  category = match.category;
  response = RESPONSES[category] || RESPONSES['SAFETY'];
  newDomain = 'SAFETY';
}

// P3: Meta-identidad (antes de P1)
if (!override) {
  match = checkTriggers(message, P3_TRIGGERS);
  if (match) {
    override = true;
    overrideLevel = 'P3_META';
    triggerWord = match.trigger;
    category = match.category;
    response = RESPONSES[category] || RESPONSES['IDENTITY_RESET'];
    newDomain = 'UNIVERSAL';
  }
}

// P1: Cambio de industria
if (!override) {
  match = checkTriggers(message, P1_TRIGGERS);
  if (match && match.category !== currentDomain) {
    override = true;
    overrideLevel = 'P1_HIGH';
    triggerWord = match.trigger;
    category = match.category;
    response = RESPONSES[category] || `Entendido. Cambio a modo ${category}. ¿Cómo puedo ayudarte?`;
    newDomain = match.category;
  }
}

// P2: Ajuste de contexto
if (!override) {
  match = checkTriggers(message, P2_TRIGGERS);
  if (match) {
    override = true;
    overrideLevel = 'P2_MEDIUM';
    triggerWord = match.trigger;
    category = match.category;
    response = RESPONSES[category] || '¿En qué puedo ayudarte?';
    // No cambia dominio
  }
}

// ============================================================================
// OUTPUT
// ============================================================================

return {
  json: {
    // Datos originales
    original_message: message,
    from: from,

    // Resultado del override
    override: override,
    override_level: overrideLevel,
    trigger_word: triggerWord,
    category: category,

    // Respuesta (si override=true)
    canonical_response: response,

    // Contexto actualizado
    previous_domain: currentDomain,
    current_domain: newDomain,

    // Control de flujo
    continue_normal_flow: !override,

    // Evento para auditoría
    event: {
      timestamp: new Date().toISOString(),
      event_type: 'intent_override_gate',
      override: override,
      override_level: overrideLevel,
      trigger_word: triggerWord,
      category: category,
      from_domain: currentDomain,
      to_domain: newDomain,
      user_id: from,
      input_message: message
    }
  }
};
```

---

### Paso 2: Agregar Nodo "IF" para Bifurcación

**Nombre:** `Check Override`
**Tipo:** IF
**Condición:**
```
{{ $json.override }} equals true
```

**Rama TRUE:** Ir a "WhatsApp Response (Override)"
**Rama FALSE:** Continuar con flujo normal (Intent Classification)

---

### Paso 3: Agregar Nodo "WhatsApp Response (Override)"

**Nombre:** `WhatsApp Response (Override)`
**Tipo:** HTTP Request
**Método:** POST
**URL:** `https://graph.facebook.com/v17.0/{{$env.PHONE_NUMBER_ID}}/messages`

**Body:**
```json
{
  "messaging_product": "whatsapp",
  "to": "{{ $json.from }}",
  "type": "text",
  "text": {
    "body": "{{ $json.canonical_response }}"
  }
}
```

---

### Paso 4: Agregar Nodo "NDJSON Audit"

**Nombre:** `Audit Override Event`
**Tipo:** Function
**Código:**

```javascript
// Escribir evento al log NDJSON
const event = $input.first().json.event;

// Aquí puedes enviar a:
// - Archivo local (/var/log/odi/audit.ndjson)
// - Redis pub/sub
// - WebSocket para dashboard
// - Google Sheets

// Por ahora, retornamos el evento para logging
console.log(JSON.stringify(event));

return { json: event };
```

---

## Diagrama de Flujo Actualizado

```
┌─────────────────┐
│ WhatsApp        │
│ Webhook         │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              INTENT OVERRIDE GATE                       │
│                                                         │
│  P0: Urgencia/Seguridad    → override=true, SAFETY     │
│  P3: Meta-identidad        → override=true, UNIVERSAL  │
│  P1: Cambio industria      → override=true, NEW_DOMAIN │
│  P2: Ajuste contexto       → override=true, HELP/STOP  │
│  NONE: Sin match           → override=false            │
└─────────────────────────────────────────────────────────┘
         │
         ├───── [override=true] ─────────────────┐
         │                                       │
         ▼                                       ▼
┌─────────────────┐                    ┌─────────────────┐
│ Intent          │                    │ WhatsApp        │
│ Classification  │                    │ Response        │
│ (ChromaDB)      │                    │ (canonical)     │
└────────┬────────┘                    └────────┬────────┘
         │                                       │
         ▼                                       ▼
┌─────────────────┐                    ┌─────────────────┐
│ GPT-4o          │                    │ NDJSON Audit    │
│ Response        │                    │ (event log)     │
└────────┬────────┘                    └─────────────────┘
         │
         ▼
┌─────────────────┐
│ WhatsApp        │
│ Response        │
└─────────────────┘
```

---

## Verificación Post-Deploy

### Tests a ejecutar:

```bash
# Test 1: Mensaje normal de motos (NO debe hacer override)
curl -X POST https://odi.larocamotorepuestos.com/webhook/odi-ingest \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"573001234567","text":{"body":"Busco piñon para AKT 125"}}]}}]}]}'

# Test 2: Emprendimiento (DEBE hacer override)
curl -X POST https://odi.larocamotorepuestos.com/webhook/odi-ingest \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"573001234567","text":{"body":"Quiero emprender un negocio"}}]}}]}]}'

# Test 3: Urgencia (DEBE hacer override P0)
curl -X POST https://odi.larocamotorepuestos.com/webhook/odi-ingest \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"573001234567","text":{"body":"Llama a la policia urgencia"}}]}}]}]}'

# Test 4: Meta-identidad (DEBE hacer override P3)
curl -X POST https://odi.larocamotorepuestos.com/webhook/odi-ingest \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"573001234567","text":{"body":"Deja de ser un experto en motos. Tú eres más que eso."}}]}}]}]}'
```

---

## Checklist de Deploy

- [ ] Backup de ODI_v6_CORTEX actual
- [ ] Agregar nodo "Intent Override Gate"
- [ ] Agregar nodo "Check Override" (IF)
- [ ] Agregar nodo "WhatsApp Response (Override)"
- [ ] Agregar nodo "Audit Override Event"
- [ ] Conectar flujo correctamente
- [ ] Ejecutar tests de verificación
- [ ] Monitorear logs por 24 horas
- [ ] Verificar dashboard /supervision

---

*"ODI responde por intención, no por industria."*
