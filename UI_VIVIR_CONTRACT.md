# UI VIVIR Contract — Pantalla Única Semi-Permanente

**Versión:** 1.0
**Fecha:** 10 Febrero 2026
**Estado:** Constitucional

---

## Principio Fundamental

> **ODI no es "sitio con scroll". ODI es ENTORNO.**

---

## Arquitectura de Pantalla

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                      VIVIR LIVE SCREEN                          │
│                    (Ventana Permanente)                         │
│                                                                 │
│    ╭─────────────────────────────────────────────────────╮      │
│    │                                                     │      │
│    │     ┌───────────────────┐                           │      │
│    │     │                   │                           │      │
│    │     │   🔥 ODI CORE 🔥  │  ← Llama circular         │      │
│    │     │                   │     Transparente          │      │
│    │     │                   │     Difuminada            │      │
│    │     └───────────────────┘                           │      │
│    │                                                     │      │
│    │     ┌─────────────────────────────────────────┐     │      │
│    │     │         VENTANA EFÍMERA                 │     │      │
│    │     │                                         │     │      │
│    │     │  [Aparece → Muestra → Desvanece]       │     │      │
│    │     │                                         │     │      │
│    │     └─────────────────────────────────────────┘     │      │
│    │                                                     │      │
│    ╰─────────────────────────────────────────────────────╯      │
│                                                                 │
│                    [ESCRITORIO DEL USUARIO]                     │
│                    Visible por transparencia                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tipos de Ventanas

### 1. Ventana Permanente: VIVIR

| Atributo | Valor |
|----------|-------|
| **Nombre** | VIVIR Live Screen |
| **Tipo** | Overlay transparente |
| **Estado** | Siempre visible 24/7 |
| **Motor** | Selenium activo |
| **Transparencia** | 85% (escritorio visible) |
| **Forma** | Llama circular central |

### 2. Ventanas Efímeras

| Atributo | Valor |
|----------|-------|
| **Tipo** | Cards/Panels temporales |
| **Aparición** | Por evento/intención/acción |
| **Duración** | 3-15 segundos (configurable) |
| **Desaparición** | Fade out automático |
| **Registro** | NDJSON audit log |

---

## Catálogo de Cards Efímeras

### IntentCard
**Propósito:** Detectar intención del usuario

```
┌─────────────────────────────────────┐
│  🎯 INTENT DETECTADO               │
├─────────────────────────────────────┤
│                                     │
│  Categoría: EMPRENDIMIENTO          │
│  Industria: TURISMO                 │
│  Confianza: 92%                     │
│                                     │
│  ┌───────────────────────────────┐  │
│  │ ¿Es correcto?  [Sí]  [No]    │  │
│  └───────────────────────────────┘  │
│                                     │
└─────────────────────────────────────┘
Duración: 8 segundos
```

### ActionCard
**Propósito:** Mostrar acción en ejecución

```
┌─────────────────────────────────────┐
│  ⚡ ACCIÓN EN CURSO                │
├─────────────────────────────────────┤
│                                     │
│  Creando Landing Page...            │
│  ████████████░░░░ 75%               │
│                                     │
│  trace_id: abc123                   │
│                                     │
└─────────────────────────────────────┘
Duración: Hasta completar
```

### EvidenceCard
**Propósito:** Mostrar trazas de auditoría

```
┌─────────────────────────────────────┐
│  📋 REGISTRO                       │
├─────────────────────────────────────┤
│                                     │
│  trace_id: f7a8b9c0                 │
│  timestamp: 2026-02-10T22:16:00     │
│  action: domain_switch              │
│  from: motos → turismo              │
│  score: 0.94                        │
│                                     │
└─────────────────────────────────────┘
Duración: 5 segundos
```

### OfferCard
**Propósito:** Mostrar opciones sin encasillar

```
┌─────────────────────────────────────┐
│  💡 OPCIONES DISPONIBLES           │
├─────────────────────────────────────┤
│                                     │
│  • Crear página de tu negocio       │
│  • Explorar industria turismo       │
│  • Conectar con mentores            │
│  • Hablar con Tony                  │
│                                     │
└─────────────────────────────────────┘
Duración: 10 segundos
```

### AlertCard
**Propósito:** Seguridad/Guardian/Urgencias

```
┌─────────────────────────────────────┐
│  🚨 ALERTA GUARDIAN                │
├─────────────────────────────────────┤
│                                     │
│  Detecté urgencia en tu mensaje.    │
│                                     │
│  Línea 123: Policía Nacional        │
│  Línea 106: Cruz Roja               │
│                                     │
│  ¿Necesitas que conecte?            │
│                                     │
└─────────────────────────────────────┘
Duración: 30 segundos (prioridad máxima)
```

---

## Ciclo de Vida de Card Efímera

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   EVENTO                                                        │
│      │                                                          │
│      ▼                                                          │
│   ┌─────────┐                                                   │
│   │ CREAR   │  → Generar card según tipo                       │
│   └────┬────┘                                                   │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────┐                                                   │
│   │ MOSTRAR │  → Fade in (300ms)                               │
│   └────┬────┘                                                   │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────┐                                                   │
│   │ ESPERAR │  → Tiempo configurado (3-30s)                    │
│   └────┬────┘                                                   │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────┐                                                   │
│   │ OCULTAR │  → Fade out (500ms)                              │
│   └────┬────┘                                                   │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────┐                                                   │
│   │ AUDITAR │  → Escribir NDJSON log                           │
│   └─────────┘                                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tiempos por Tipo de Card

| Card | Duración | Prioridad | Interrupción |
|------|----------|-----------|--------------|
| IntentCard | 8s | Media | Sí, por AlertCard |
| ActionCard | Hasta completar | Alta | No |
| EvidenceCard | 5s | Baja | Sí |
| OfferCard | 10s | Media | Sí |
| AlertCard | 30s | Máxima | No |

---

## Colores de Estado (Llama Central)

| Estado | Color | Hex | Trigger |
|--------|-------|-----|---------|
| **Escuchando** | Cyan | `#00d4ff` | Usuario habla |
| **Procesando** | Amarillo | `#ffcc00` | ODI piensa |
| **Respondiendo** | Verde | `#00ff88` | ODI actúa |
| **Alerta** | Naranja | `#ff8800` | Atención requerida |
| **Urgencia** | Rojo pulsante | `#ff4444` | Guardian activado |
| **Standby** | Gris tenue | `#333333` | Sin actividad |

---

## Eventos NDJSON

Cada card genera registro de auditoría:

```json
{
  "trace_id": "f7a8b9c0-1234-5678-abcd-ef0123456789",
  "timestamp": "2026-02-10T22:16:00.000-05:00",
  "event_type": "card_shown",
  "card_type": "IntentCard",
  "duration_ms": 8000,
  "content": {
    "category": "EMPRENDIMIENTO",
    "industry": "TURISMO",
    "confidence": 0.92
  },
  "user_action": "confirmed",
  "guardian_status": "green"
}
```

---

## Interacción por Voz

| Acción | Trigger de Voz |
|--------|----------------|
| Confirmar card | "Sí" / "Correcto" / "Ok" |
| Rechazar card | "No" / "Incorrecto" / "Cambiar" |
| Cerrar card | "Cerrar" / "Listo" / "Siguiente" |
| Pedir ayuda | "Ayuda" / "Qué es esto" |
| Urgencia | "Urgente" / "Emergencia" / "Policía" |

---

## Plataformas Soportadas

| OS | Implementación |
|----|----------------|
| **Windows** | Overlay nativo + Selenium |
| **macOS** | Overlay nativo + Selenium |
| **Android** | Floating window service |
| **iOS** | Widget + Notification extension |

---

## Selenium Bridge

```python
# Configuración base VIVIR
VIVIR_CONFIG = {
    "mode": "overlay",
    "transparency": 0.85,
    "always_on_top": True,
    "headless_when_hidden": True,
    "blur_background": True,
    "position": "center",
    "shape": "circular_flame",
    "animation_fps": 30
}
```

---

## Regla de Oro

> **La interfaz no "habla" por industria.**
> **La interfaz MUESTRA lo que ODI está haciendo.**

ODI piensa. VIVIR muestra. El usuario observa y actúa.

---

*"Una sola pantalla viva. Todo lo demás es efímero."*
