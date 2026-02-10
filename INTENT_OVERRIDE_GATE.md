# Intent Override Gate — Prioridades de Intención

**Versión:** 1.0
**Fecha:** 10 Febrero 2026
**Estado:** Constitucional (Anti-Encasillamiento)

---

## Problema Resuelto

```
╔══════════════════════════════════════════════════════════════╗
║  BUG CRÍTICO: Intent Lock (8 Feb 2026, 22:16)               ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Usuario: "Quiero hacer turismo odontológico"               ║
║  ODI: "Para tu ECO! MANUBRIO HONDA..."                      ║
║                                                              ║
║  Usuario: "Llama a la policía urgencia"                     ║
║  ODI: "Para tu ECO! MANUBRIO HONDA..."                      ║
║                                                              ║
║  DIAGNÓSTICO: Intent "motos" bloqueó todas las demás        ║
║               intenciones. ODI quedó en loop.               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Solución: Intent Override Gate

### Principio

> **Ninguna industria puede bloquear intenciones críticas.**
> **ODI siempre puede cambiar de modo.**

---

## Tabla de Prioridades

### Nivel 0 — CRÍTICO (Siempre Override)

| Trigger | Categoría | Acción ODI |
|---------|-----------|------------|
| "urgencia" / "emergencia" / "policía" / "ambulancia" | SEGURIDAD | Mostrar AlertCard + números de emergencia |
| "ayuda" / "auxilio" / "socorro" | SEGURIDAD | Activar Guardian, evaluar contexto |
| "me siento mal" / "estoy perdido" | BIENESTAR | Cambiar a modo apoyo emocional |

### Nivel 1 — ALTO (Override Industria)

| Trigger | Categoría | Acción ODI |
|---------|-----------|------------|
| "emprender" / "negocio" / "idea" / "proyecto" | EMPRENDIMIENTO | Cambiar a modo Emprendedor APO |
| "trabajo" / "empresa" / "empleado" / "jefe" | TRABAJO | Cambiar a modo Empleado APO |
| "turismo" / "viaje" / "hotel" | TURISMO | Cambiar industria a Turismo |
| "salud" / "médico" / "odontología" / "clínica" | SALUD | Cambiar industria a Salud |
| "belleza" / "estética" / "spa" | BELLEZA | Cambiar industria a Belleza |
| "legal" / "abogado" / "contrato" | LEGAL | Cambiar industria a Legal |
| "educación" / "curso" / "academia" | EDUCACIÓN | Cambiar a Academia |

### Nivel 2 — MEDIO (Override Contexto)

| Trigger | Categoría | Acción ODI |
|---------|-----------|------------|
| "no entiendo" / "explica" / "cómo funciona" | AYUDA | Modo explicación |
| "cambia" / "otro tema" / "diferente" | SWITCH | Confirmar cambio de tema |
| "basta" / "para" / "detente" | CONTROL | Pausar flujo actual |

### Nivel 3 — META (Override Total)

| Trigger | Categoría | Acción ODI |
|---------|-----------|------------|
| "tú eres más que eso" | META-INTENT | Reset completo, modo universal |
| "deja de ser experto en X" | META-INTENT | Salir de industria, modo abierto |
| "no solo sabes de X" | META-INTENT | Expandir capacidades visibles |
| "quién eres realmente" | IDENTIDAD | Presentación completa ODI |

---

## Flujo de Override

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   MENSAJE DEL USUARIO                                           │
│          │                                                      │
│          ▼                                                      │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              INTENT OVERRIDE GATE                       │   │
│   │                                                         │   │
│   │   1. ¿Contiene trigger Nivel 0 (CRÍTICO)?              │   │
│   │      → Sí: OVERRIDE INMEDIATO                          │   │
│   │      → No: Continuar                                    │   │
│   │                                                         │   │
│   │   2. ¿Contiene trigger Nivel 1 (ALTO)?                 │   │
│   │      → Sí: CAMBIAR INDUSTRIA/MODO                      │   │
│   │      → No: Continuar                                    │   │
│   │                                                         │   │
│   │   3. ¿Contiene trigger Nivel 2 (MEDIO)?                │   │
│   │      → Sí: AJUSTAR CONTEXTO                            │   │
│   │      → No: Continuar                                    │   │
│   │                                                         │   │
│   │   4. ¿Contiene trigger Nivel 3 (META)?                 │   │
│   │      → Sí: RESET TOTAL                                 │   │
│   │      → No: Procesar con industria actual               │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│          │                                                      │
│          ▼                                                      │
│   RESPUESTA ODI (sin loop de industria)                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Respuestas Obligatorias por Override

### Override Nivel 0 (Seguridad)

```
Usuario: "Llama a la policía urgencia"

ODI: "Entendido. Esto es una emergencia.

     🚨 Línea 123 - Policía Nacional
     🚑 Línea 125 - Bomberos
     ❤️ Línea 106 - Cruz Roja

     ¿Necesitas que conecte alguna línea?"
```

### Override Nivel 1 (Cambio de Industria)

```
Usuario: "Quiero hacer turismo odontológico"

ODI: "Interesante. Turismo odontológico combina salud + viajes.

     ¿Ya tienes clínicas aliadas o empezamos desde cero?
     ¿Esto es para emprender o para un viaje personal?"
```

### Override Nivel 2 (Contexto)

```
Usuario: "No entiendo cómo funciona"

ODI: "Te explico. ODI puede ayudarte con:

     • Tu trabajo (optimizar tareas)
     • Tu negocio (crear presencia digital)
     • Tus compras (encontrar productos)

     ¿Por dónde quieres empezar?"
```

### Override Nivel 3 (Meta)

```
Usuario: "Tú eres más que eso"

ODI: "Tienes razón. No soy solo de motos.

     Soy ODI. Puedo ayudarte en cualquier industria:
     emprender, trabajar, comprar, aprender.

     ¿Qué necesitas hoy?"
```

---

## Eventos NDJSON para Override

```json
{
  "trace_id": "override-001",
  "timestamp": "2026-02-10T22:16:00.000-05:00",
  "event_type": "intent_override",
  "override_level": 1,
  "trigger_word": "turismo",
  "previous_industry": "motos",
  "new_industry": "turismo",
  "previous_mode": "producto_search",
  "new_mode": "emprendimiento_guide",
  "user_message": "Quiero hacer turismo odontológico",
  "guardian_status": "green"
}
```

---

## Anti-Patrones Prohibidos

### ❌ NUNCA hacer esto:

```
Usuario: "Tengo una idea de negocio"
ODI: "Para tu ECO! MANUBRIO HONDA..."  ← PROHIBIDO

Usuario: "Quiero emprender"
ODI: "Chevere! Cuando ocupes repuestos..."  ← PROHIBIDO

Usuario: "Deja de hablar de motos"
ODI: "Para tu ECO! MANUBRIO..."  ← PROHIBIDO
```

### ✅ SIEMPRE hacer esto:

```
Usuario: "Tengo una idea de negocio"
ODI: "Cuéntame más. ¿De qué industria es tu idea?"

Usuario: "Quiero emprender"
ODI: "Perfecto. ¿Ya tienes definido qué tipo de negocio?"

Usuario: "Deja de hablar de motos"
ODI: "Entendido. Cambio de tema. ¿En qué más puedo ayudarte?"
```

---

## Implementación en n8n (ODI_v6_CORTEX)

### Nodo: Intent Override Check

```javascript
// Antes de procesar industria, verificar overrides
const message = $json.message.toLowerCase();

const LEVEL_0 = ['urgencia', 'emergencia', 'policía', 'ambulancia', 'ayuda', 'socorro'];
const LEVEL_1 = ['emprender', 'negocio', 'proyecto', 'turismo', 'salud', 'belleza'];
const LEVEL_3 = ['eres más que', 'deja de ser experto', 'no solo sabes'];

// Nivel 0: Override inmediato
for (const trigger of LEVEL_0) {
  if (message.includes(trigger)) {
    return { override: true, level: 0, action: 'EMERGENCY' };
  }
}

// Nivel 1: Cambio de industria
for (const trigger of LEVEL_1) {
  if (message.includes(trigger)) {
    return { override: true, level: 1, action: 'INDUSTRY_SWITCH' };
  }
}

// Nivel 3: Reset total
for (const trigger of LEVEL_3) {
  if (message.includes(trigger)) {
    return { override: true, level: 3, action: 'FULL_RESET' };
  }
}

return { override: false };
```

---

## Checklist de Validación

- [ ] Intent Override Gate implementado en ODI_v6_CORTEX
- [ ] Nivel 0 (Seguridad) funciona con cualquier industria activa
- [ ] Nivel 1 (Industria) cambia correctamente el contexto
- [ ] Nivel 3 (Meta) hace reset completo
- [ ] NDJSON registra todos los overrides
- [ ] AlertCard aparece en VIVIR para emergencias
- [ ] No hay loops de industria posibles

---

## Regla Constitucional

> **ODI responde por intención, no por industria.**
> **Ningún contexto previo puede bloquear un intent válido.**

---

*"ODI escucha. ODI entiende. ODI cambia."*
