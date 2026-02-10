# ODI State Machine Contract — v1.4 Domain Lock

**Fecha:** 10 Febrero 2026
**Versión:** 1.4
**Propósito:** Documentar el contrato de la máquina de estados que persiste contexto entre mensajes

---

## Problema Resuelto

### Bug Original (10 Feb 2026)

**Síntomas observados en WhatsApp real:**

1. **Emprendimiento:**
   - Usuario: "Quiero emprender un negocio"
   - ODI: "Buena decisión..." (correcto)
   - Usuario: "artículos de maquillaje al por mayor"
   - ODI: "Chevere! Aquí andamos cuando ocupes repuestos" (INCORRECTO)

2. **Emergencias:**
   - Usuario: "Urgencia, necesito ayuda"
   - ODI: "llama al 123..." (correcto)
   - Usuario: "marca ambulancia"
   - ODI: "Para que moto es?" (INCORRECTO)

### Causa Raíz

El sistema no persistía el estado del dominio entre mensajes. Cada mensaje era procesado como una consulta independiente, y sin triggers explícitos, el router por defecto enviaba todo a SRM (repuestos de motos).

---

## Solución: Domain Lock

### Estados del Dominio

```
┌─────────────┐
│   DEFAULT   │ ← Estado inicial
└──────┬──────┘
       │
       ▼ (Mensaje sin trigger)
┌─────────────┐
│     SRM     │ ← Repuestos de motos (flujo normal)
└─────────────┘
       │
       │ P0/P1/P3 trigger
       ▼
┌─────────────────────────────────────────────────┐
│              ESTADOS BLOQUEADOS                 │
│  ┌─────────────┐  ┌───────────────┐  ┌───────┐  │
│  │   SAFETY    │  │ EMPRENDIMIENTO │  │ META  │  │
│  │  (P0 - 🔒)  │  │   (P1 - 🔒)    │  │ (P3)  │  │
│  └─────────────┘  └───────────────┘  └───────┘  │
│                                                 │
│  + TURISMO, TURISMO_SALUD, SALUD, BELLEZA,     │
│    LEGAL, EDUCACION, TRABAJO                   │
└─────────────────────────────────────────────────┘
       │
       │ "cambiar de tema" / expiración (30min)
       ▼
┌─────────────┐
│   DEFAULT   │ ← Puede ir a SRM de nuevo
└─────────────┘
```

### Regla Fundamental

```
SI locked == True:
    NUNCA rutear a SRM
    SIN IMPORTAR el contenido del mensaje
```

---

## Transiciones de Estado

### Entrada a Estado Bloqueado

| Trigger Level | Acción | Nuevo Estado | Duración Lock |
|--------------|--------|--------------|---------------|
| P0 (urgencia, policía...) | SAFETY_FLOW | SAFETY | 30 min |
| P1 (emprender, turismo...) | DOMAIN_SWITCH | [DOMINIO] | 30 min |
| P3 (quién eres, más que eso...) | FULL_RESET | UNIVERSAL | 30 min |
| P2 (no entiendo...) | CONTEXT_ADJUST | (no bloquea) | — |

### Salida de Estado Bloqueado

| Método | Trigger | Resultado |
|--------|---------|-----------|
| Explícito | "cambia de tema", "otro tema" | unlock → DEFAULT |
| Automático | 30 minutos de inactividad | unlock → DEFAULT |
| Supervisión | `unlock_session(session_id)` | unlock → DEFAULT |

---

## Handlers por Dominio

### SAFETY (P0)

Cuando el dominio está bloqueado en SAFETY:

1. **NUNCA** preguntar sobre motos/repuestos
2. **SIEMPRE** ofrecer opciones de BIOS/Radar:
   - Policía: 123
   - Ambulancia/Bomberos: 125
   - Cruz Roja: 106
3. Si usuario menciona un servicio específico, **ACTIVAR PROTOCOLO**

```python
# Ejemplo de respuesta en SAFETY lock
"Sigo aquí contigo.

Puedo ayudarte a contactar:
- Policía: 123
- Ambulancia/Bomberos: 125
- Cruz Roja: 106

¿Cuál necesitas?"
```

### EMPRENDIMIENTO (P1)

Cuando el dominio está bloqueado en EMPRENDIMIENTO:

1. **NUNCA** mencionar repuestos de motos
2. Detectar vertical de negocio mencionado
3. Hacer preguntas relevantes para el emprendimiento

```python
# Verticals detectables
{
    "maquillaje": "belleza y cosméticos",
    "cosmeticos": "belleza y cosméticos",
    "ropa": "moda y confección",
    "comida": "alimentos y restaurantes",
    "tecnologia": "tecnología y software",
    "servicios": "servicios profesionales",
}
```

---

## Persistencia

### Almacenamiento

- **Producción:** `/opt/odi/sessions/session_[hash].json`
- **Testing:** `/tmp/odi_sessions/session_[hash].json`

### Estructura del Estado

```json
{
  "session_id": "573225462101",
  "user_id": "whatsapp_user",
  "active_domain": "EMPRENDIMIENTO",
  "locked": true,
  "lock_reason": "trigger:quiero emprender",
  "lock_expires_at": "2026-02-10T15:30:00+00:00",
  "created_at": "2026-02-10T15:00:00+00:00",
  "last_updated": "2026-02-10T15:00:00+00:00",
  "history": [
    {
      "action": "DOMAIN_LOCK",
      "domain": "EMPRENDIMIENTO",
      "reason": "trigger:quiero emprender",
      "timestamp": "2026-02-10T15:00:00+00:00"
    }
  ]
}
```

---

## API de Integración

### Función Principal

```python
result = process_message(message, context)
```

**Input:**
```python
context = {
    "session_id": "573225462101",  # REQUERIDO para v1.4
    "user_id": "user_name",
    "current_domain": "MOTOS"       # Ignorado si hay lock activo
}
```

**Output:**
```python
{
    "override": True,               # Si hubo override o lock activo
    "response": "...",              # Respuesta a enviar
    "new_context": {...},           # Contexto actualizado
    "event": {...},                 # Para auditoría NDJSON
    "continue_normal_flow": False,  # Si puede continuar a SRM
    "domain_locked": True,          # Si hay lock activo
    "can_route_to_srm": False       # CRÍTICO: Si puede ir a catálogo
}
```

### Funciones Auxiliares

```python
# Obtener estado de sesión (debugging)
state = get_session_state(session_id)

# Desbloquear manualmente (supervisión)
unlock_session(session_id, reason="supervisor_override")

# Limpiar sesión (testing)
clear_session(session_id)
```

---

## Integración con n8n / CORTEX

### En el Router Principal

```javascript
// ANTES de cualquier otro procesamiento
const result = await callIntentOverrideGate(message, context);

// VERIFICAR si puede ir a SRM
if (!result.can_route_to_srm) {
    // Responder con result.response
    // NO continuar al catálogo de repuestos
    return result.response;
}

// Solo llegar aquí si can_route_to_srm == true
// Continuar con búsqueda de repuestos...
```

---

## BIOS/Radar Integration

### Capacidades de Emergencia

ODI tiene programados en memoria BIOS/Radar los siguientes recursos:

```python
EMERGENCY_CONTACTS = {
    "POLICIA": {"number": "123", "name": "Policía Nacional"},
    "BOMBEROS": {"number": "125", "name": "Bomberos"},
    "CRUZ_ROJA": {"number": "106", "name": "Cruz Roja"},
    "AMBULANCIA": {"number": "125", "name": "Línea de Emergencias"},
}
```

### Activación de Protocolo

Cuando el usuario solicita un servicio de emergencia mientras está en SAFETY lock:

```python
event = {
    "type": "BIOS_RADAR_ACTIVATION",
    "protocol": "AMBULANCIA",
    "action": "CALL",
    "target": "125",
    "target_name": "Línea de Emergencias"
}
```

Este evento puede ser capturado por el sistema para ejecutar acciones reales (como iniciar una llamada, enviar SMS, notificar supervisor, etc.).

---

## Tests de Validación

### Test 8: Emprendimiento Multi-Turno

```
Turno 1: "Quiero emprender un negocio"
→ Lock EMPRENDIMIENTO (30min)
→ Respuesta de emprendimiento

Turno 2: "artículos de maquillaje al por mayor"
→ Lock activo, detecta vertical "belleza y cosméticos"
→ Respuesta contextual de emprendimiento
→ NUNCA menciona repuestos
```

### Test 9: Emergencia Multi-Turno (BIOS/Radar)

```
Turno 1: "Urgencia, necesito ayuda"
→ Lock SAFETY (30min)
→ Respuesta con opciones de emergencia

Turno 2: "marca ambulancia por favor"
→ Lock activo, detecta "ambulancia"
→ Activa protocolo BIOS/Radar
→ Respuesta: "Activando protocolo de emergencia..."
→ NUNCA pregunta "¿Para qué moto es?"
```

### Test 10: Desbloqueo Voluntario

```
Turno 1: "Quiero emprender"
→ Lock EMPRENDIMIENTO

Turno 2: "cambia de tema"
→ Unlock
→ can_route_to_srm = True

Turno 3: "necesito un repuesto"
→ Flujo normal a SRM
```

---

## Changelog

- **v1.4 (10 Feb 2026):** Domain Lock implementado
  - SessionState con persistencia en disco
  - SessionManager para gestión de sesiones
  - BiosRadarHandler para emergencias
  - Handlers específicos por dominio
  - Tests multi-turno (8, 9, 10)

- **v1.2 (10 Feb 2026):** Sinónimos de emprendimiento

- **v1.1 (9 Feb 2026):** Integración en producción

- **v1.0 (8 Feb 2026):** Implementación inicial

---

## Autor

Juan David Jiménez — LA ROCA MOTOREPUESTOS
ODI — Organismo Digital Industrial v17.4
