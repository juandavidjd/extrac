# P10/T10 · DUAL SURFACE + HABITAT WIDGETS

**Fecha:** 2026-06-29  
**Estado:** Doctrina técnica aprobada para reescritura de los 12 entregables  
**Alcance:** Profesionales10 + Teveo10  
**Principio:** La web no desaparece técnicamente. Desaparece como carga cognitiva para el humano.

---

# 1. TESIS

La arquitectura correcta no elige entre “web tradicional” y “hábitat”.

Construye una sola lógica operativa, renderizada en dos superficies:

```text
MODO PÚBLICO
  Landing / vitrina / captación.
  Martha puede mostrarlo a socias, profesionales y aliados.
  Aquí existen rutas, páginas y CTAs comprensibles.

MODO HÁBITAT
  Puesto de control del habitante.
  ODI usa P10/T10 como capacidades internas.
  El habitante no navega páginas; decide sobre widgets contextuales.
```

Frase rectora:

```text
El habitante no visita P10.
ODI usa P10 para continuar el flujo del habitante.
```

---

# 2. HONESTIDAD CONTRACTUAL

Martha tiene contrato firmado y espera ver entregables reconocibles:

- mensajería directa;
- calificaciones bidireccionales;
- calendario de eventos;
- matching inteligente;
- pagos visibles;
- referidos;
- embudos;
- emails;
- galerías;
- WhatsApp.

Por tanto, no se puede reemplazar el contrato con lenguaje abstracto de hábitat.

La solución es doble superficie con una sola lógica:

```text
Misma capacidad.
Dos proyecciones.

1. Proyección pública / navegable:
   Martha ve la feature como plataforma.

2. Proyección hábitat / contextual:
   El habitante recibe la feature como widget dentro de su flujo ODI.
```

---

# 3. REGLA DE NO DUPLICACIÓN

No se crean dos sistemas.

```text
NO:
  /buscar construido aparte
  Widget_Matching construido aparte

SÍ:
  MatchingEngine + MatchingWidget
  renderizado como:
    - Página pública /buscar
    - Widget contextual en Puesto de Control
```

La unidad real es la capacidad:

```text
Capability → Widget → Public Projection / Habitat Projection
```

---

# 4. DEPENDENCIA REAL · NERVE_ALIVE

El paradigma hábitat no es un atajo. Depende del nervio.

Sin dispatcher vivo no existe inyección contextual real.

```text
Si NERVE_ALIVE = false:
  se pueden preparar componentes, páginas preview y lógica base.
  no se puede declarar stream contextual vivo.

Si NERVE_ALIVE = true:
  dispatcher puede decidir qué widget inyectar.
  los 12 entregables pueden despacharse como tasks reales.
```

Secuencia vigente:

```text
RUNTIME_BRIDGE
→ re-H2 exit 0
→ first task real
→ NERVE_ALIVE
→ 12 entregables como widgets/capacidades reales
```

---

# 5. NUEVO CONTRATO DE INTERFAZ

La interfaz no debe invitar a hablar. Debe mostrar qué sigue.

Eliminar en modo hábitat:

```text
Hablar con soporte
Centro de ayuda
Preguntas frecuentes
Hablar con asesor
Buscar desde cero
Inbox separado
Review aislada
Calendario navegable como destino
```

Reemplazar por:

```text
Continuar flujo
Autorizar conexión
Resolver bloqueo
Subir evidencia
Confirmar finalización
Revisar opciones encontradas
Separar cupo recomendado
Validar documento
Aprobar convenio
Ver trazabilidad
```

---

# 6. LOS 12 ENTREGABLES COMO CAPACIDADES DUALES

## 1. Matching inteligente

```text
Capacidad:
  MatchingEngine + ChromaDB + reglas de disponibilidad/confianza.

Proyección pública:
  Ruta /buscar con filtros comprensibles.

Proyección hábitat:
  Widget_SugerenciaProfesional.
  ODI muestra 3 opciones procesadas y una acción principal:
  Autorizar conexión.
```

## 2. Mensajería directa

```text
Capacidad:
  Canal seguro entre habitante/profesional/cliente con auditoría ODI.

Proyección pública:
  Bandeja o conversación visible para demostrar feature.

Proyección hábitat:
  Widget_CanalContextual dentro del flujo activo.
  No es inbox; es continuación del hilo ODI.
```

## 3. Calificaciones bidireccionales con evidencia

```text
Capacidad:
  ReviewEngine + evidencia + actualización de reputación.

Proyección pública:
  Vista de calificaciones en perfil y flujo post-servicio.

Proyección hábitat:
  Widget_ResolucionServicio.
  “Servicio completado. Sube evidencia y confirma resultado.”
```

## 4. Traducción bilingüe automática

```text
Capacidad:
  TranslationLayer + cache + contexto de interlocutor.

Proyección pública:
  Switch ES/EN y contenido traducido.

Proyección hábitat:
  Widget_TraduccionContextual.
  ODI traduce solo cuando el flujo lo exige.
```

## 5. Grupos temáticos T10

```text
Capacidad:
  Pertenencia, afinidad y grupos por contexto.

Proyección pública:
  Ruta /grupos para demostrar comunidad.

Proyección hábitat:
  Widget_PertenenciaSugerida.
  “Este grupo suma a tu ruta actual.”
```

## 6. Calendario eventos T10

```text
Capacidad:
  EventEngine + PAEM + disponibilidad + recordatorios.

Proyección pública:
  Calendario de eventos navegable.

Proyección hábitat:
  Widget_OportunidadEvento.
  “Este encuentro coincide con tu ruta. ¿Separo cupo?”
```

## 7. Embudos Systeme.io

```text
Capacidad:
  CaptationPipeline + tags + Lead Habitat.

Proyección pública:
  Landing/funnel visible para captación.

Proyección hábitat:
  Widget_EntradaCaptada.
  El lead aparece como flujo vivo, no como contacto muerto.
```

## 8. Secuencias email automáticas

```text
Capacidad:
  Continuidad asincrónica del flujo.

Proyección pública:
  Secuencia de emails demostrable para Martha.

Proyección hábitat:
  Widget_RecordatorioContextual.
  Email no reemplaza hábitat; extiende continuidad cuando el habitante sale.
```

## 9. Referidos P10/T10

```text
Capacidad:
  Extensión controlada de confianza.

Proyección pública:
  Código de referido y panel simple.

Proyección hábitat:
  Widget_InvitacionConfiable.
  ODI sugiere invitar solo cuando el flujo y la reputación lo permiten.
```

## 10. Pagos visibles

```text
Capacidad:
  BillingState + Wompi + medición solo + convenio.

Proyección pública:
  Panel de cuotas/pagos visible para Martha.

Proyección hábitat:
  Widget_EstadoConvenioPago.
  “Cuota pendiente / medición / autorización / bloqueo.”
```

## 11. WhatsApp eventos

```text
Capacidad:
  WhatsApp asíncrono + opt-in + inscripción/recordatorio.

Proyección pública:
  Flujo de inscripción por WhatsApp demostrable.

Proyección hábitat:
  Widget_AccionWhatsAppEvento.
  WhatsApp no es destino; es extensión del flujo cuando el habitante está fuera.
```

## 12. Galería post-evento

```text
Capacidad:
  Evidencia visual + memoria + reputación + contenido.

Proyección pública:
  Galería del evento.

Proyección hábitat:
  Widget_EvidenciaEvento.
  ODI pide evidencia y la vincula a reputación, memoria y continuidad.
```

---

# 7. ARQUITECTURA FRONTEND

El frontend no debe ser solo SPA tradicional.

Debe tener dos capas:

```text
Public Shell
  Rutas demostrables.
  Vitrina para Martha, socias, profesionales y aliados.

Habitat Shell
  Stream de widgets contextuales.
  El Dispatcher decide qué aparece según el estado del flujo.
```

Contrato técnico:

```ts
interface HabitatWidget {
  widget_id: string;
  capability: string;
  project: 'P10' | 'T10' | 'SRM' | 'CATRMU' | string;
  flow_id: string;
  habitante_id: string;
  state: 'suggested' | 'pending' | 'blocked' | 'ready' | 'completed';
  priority: number;
  title: string;
  summary: string;
  evidence: EvidenceRef[];
  actions: WidgetAction[];
  audit_ref: string;
  expires_at?: string;
}
```

---

# 8. REGLA PARA MARTHA Y SOCIAS

Martha debe poder ver features.

```text
No se le muestra “el dispatcher respira”.
Se le muestra:
  búsqueda funcionando,
  convenio visible,
  mensajería visible,
  calendario visible,
  calificación visible,
  pago visible.
```

Pero internamente esas features deben nacer como widgets/capacidades reutilizables, no como páginas aisladas.

---

# 9. VEREDICTO

La especificación anterior de los 12 entregables queda como base contractual histórica.

Esta especificación se convierte en la capa de ejecución arquitectónica:

```text
Lo prometido se conserva.
La forma de ejecución evoluciona.
Martha ve plataforma.
El habitante vive hábitat.
ODI usa las capacidades.
El humano decide solo lo necesario.
```

**Somos Industrias ODI.**
