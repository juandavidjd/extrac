# P10/T10 · CRITERIO DE CERTIFICACIÓN DUAL SURFACE

**Fecha:** 2026-06-29  
**Estado:** Criterio obligatorio para los 12 entregables  
**Alcance:** PC I frontend, PC II backend, PC I V2 certificación, PC I V3 flow governor  
**Regla:** Una capacidad. Dos superficies. Cero duplicación.

---

# 1. RESPUESTA CORTA DEL TRIBUNAL

Sí. Cada entregable P10/T10 debe certificar obligatoriamente:

```text
1. Funcionamiento como feature visible en ruta pública.
2. Funcionamiento como widget autónomo inyectable en Modo Hábitat.
```

Si solo existe como página, no pasa.
Si solo existe como concepto de widget sin ruta visible para Martha, no pasa.

La certificación correcta exige ambas pruebas.

---

# 2. JUSTIFICACIÓN

Martha y sus socias necesitan ver plataforma. El contrato prometió features tangibles.

El ecosistema ODI necesita capacidades reutilizables, no pantallas aisladas.

Por tanto:

```text
La ruta pública certifica la promesa contractual.
El widget contextual certifica la arquitectura de hábitat.
```

---

# 3. REGLA DE CONSTRUCCIÓN FRONTEND

PC I no debe construir páginas como unidad primaria.

Debe construir componentes atómicos:

```text
Capability Component
  ↓
Public Wrapper
  ↓
Habitat Widget Container
```

Ejemplo:

```text
MatchingCapability
  MatchingWidget
    /buscar                → Public Wrapper
    habitat://flow/widget  → Habitat Container
```

---

# 4. MATRIZ DE CERTIFICACIÓN OBLIGATORIA

Cada entregable debe entregar evidencia en 6 capas:

| Capa | Exigencia | PASS |
|---|---|---|
| Backend | Endpoint o servicio responde con datos reales o vacío honesto | No mock no declarado |
| Widget Core | Componente autónomo renderiza con props/contexto | Sin dependencia obligatoria de ruta |
| Public Projection | Ruta visible para Martha | Feature demostrable |
| Habitat Projection | Contenedor inyectable listo para dispatcher | Widget funciona con flow payload |
| Tests | Unit + integration + e2e mínimo | PASS documentado |
| Certificación visual | Browser real o preview controlado | Martha puede verlo |

---

# 5. CRITERIO POR ENTREGABLE

## 1. Matching inteligente

Debe certificar:

```text
Public:
  /buscar muestra resultados ordenados por MatchingEngine.

Habitat:
  Widget_SugerenciaProfesional recibe flow_payload y muestra 3 opciones procesadas.
```

## 2. Mensajería directa

Debe certificar:

```text
Public:
  /mensajes o vista equivalente muestra conversación.

Habitat:
  Widget_CanalContextual se abre dentro de un convenio/flujo activo.
```

## 3. Calificaciones bidireccionales

Debe certificar:

```text
Public:
  Perfil o post-servicio muestra calificación con evidencia.

Habitat:
  Widget_ResolucionServicio solicita evidencia y confirmación al finalizar flujo.
```

## 4. Traducción bilingüe

Debe certificar:

```text
Public:
  Switch ES/EN cambia contenido dinámico.

Habitat:
  Widget_TraduccionContextual traduce mensaje/documento cuando el flujo lo requiere.
```

## 5. Grupos T10

Debe certificar:

```text
Public:
  /grupos muestra grupos y membresía.

Habitat:
  Widget_PertenenciaSugerida aparece por afinidad/ruta.
```

## 6. Calendario T10

Debe certificar:

```text
Public:
  /eventos muestra calendario o lista de eventos.

Habitat:
  Widget_OportunidadEvento permite separar cupo desde flujo activo.
```

## 7. Embudos Systeme.io

Debe certificar:

```text
Public:
  Landing/funnel captura lead y aplica tag.

Habitat:
  Widget_EntradaCaptada muestra lead convertido en flujo vivo.
```

## 8. Secuencia email

Debe certificar:

```text
Public:
  Contacto test entra en secuencia visible en Systeme.io.

Habitat:
  Widget_RecordatorioContextual muestra continuidad asincrónica del flujo.
```

## 9. Referidos

Debe certificar:

```text
Public:
  Código referido visible y tracking de invitado.

Habitat:
  Widget_InvitacionConfiable aparece solo si reputación/flujo lo permite.
```

## 10. Pagos visibles

Debe certificar:

```text
Public:
  Panel Martha muestra cuota, medición y estado.

Habitat:
  Widget_EstadoConvenioPago muestra autorización/bloqueo/cuota dentro del flujo.
```

## 11. WhatsApp eventos

Debe certificar:

```text
Public:
  Flujo de inscripción por WhatsApp demostrable.

Habitat:
  Widget_AccionWhatsAppEvento registra continuidad si el habitante está fuera.
```

## 12. Galería post-evento

Debe certificar:

```text
Public:
  Galería visible del evento.

Habitat:
  Widget_EvidenciaEvento pide/sube evidencia vinculada a memoria y reputación.
```

---

# 6. REGLA DE NERVE_ALIVE

Mientras NERVE_ALIVE no esté certificado:

```text
Permitido:
  construir componentes;
  montar rutas públicas;
  preparar habitat containers;
  usar payloads demo controlados y declarados.

Prohibido:
  declarar inyección contextual viva;
  declarar stream del habitante;
  declarar dispatcher operando widgets;
  inflar datos reales.
```

Después de NERVE_ALIVE:

```text
El dispatcher debe despachar los 12 entregables como tasks reales.
Cada widget debe aceptar payload real del flujo.
Cada public wrapper debe seguir funcionando para auditoría de Martha.
```

---

# 7. ANTI-PATRONES PROHIBIDOS

```text
❌ Página sin widget reutilizable.
❌ Widget sin ruta pública auditable.
❌ Mock no declarado.
❌ Profesionales inventados.
❌ Métricas infladas.
❌ Botones genéricos en modo hábitat: hablar con soporte, FAQ, centro de ayuda.
❌ Doble lógica para public y habitat.
```

---

# 8. DEFINICIÓN DE DONE

Un entregable solo está DONE cuando:

```text
Backend PASS.
Widget Core PASS.
Public Projection PASS.
Habitat Projection PASS.
Tests PASS.
Browser evidence PASS.
Vacío honesto si no hay datos reales.
```

Si falta una de las dos superficies, el estado máximo permitido es:

```text
PARTIAL · no certificable completo.
```

---

# 9. VEREDICTO

El criterio dual queda impuesto.

```text
Martha ve plataforma.
El habitante vive hábitat.
El código es uno.
La proyección es doble.
La certificación exige ambas.
```

**Somos Industrias ODI.**
