# PC III V1 · P10 Professional Signup v1 · Ejecución CaptationPipeline

**Fecha:** 2026-06-28  
**Estado:** APROBADO PARA EJECUCIÓN  
**Hito padre:** ODI × Systeme.io · Motor de Captación Inteligente  
**Campaña:** `captation_p10_professional_signup_v1`  
**Organismo:** P10 · Profesionales10 · Terminal de Inteligencia Profesional  
**Carril:** Captación comercial paralela, sin interferir con Capa 2 ni con auditoría T10.  

---

## 0. Veredicto PC III V1

La decisión queda aprobada:

```text
Activar primero la captación de P10 Profesional.
```

Razón:

P10 ya tiene Misión Visual sellada como Terminal de Inteligencia Profesional. Por tanto, puede recibir captación sin empujar tráfico hacia una promesa vacía.

P10 no capta perfiles para llenar un catálogo.

P10 capta profesionales fundadores para construir una red verificable, útil y protegida por inteligencia profesional.

Frase matriz:

```text
No solo publiques tu perfil. Protege tu trayectoria.
```

---

# 1. Separación de carriles

Este documento registra ejecución de captación P10.

El bloque T10 permanece separado:

```text
T10 sigue en Auditoría de Realidad.
T10 no avanza a diseño hasta demostrar evidencia de pertenencia.
```

La captación P10 puede avanzar en paralelo porque:

- P10 ya tiene tesis validada,
- P10 ya no es directorio muerto,
- P10 v3 tiene arquitectura de valor,
- P10 Profesional alimenta el organismo con oferta inicial,
- P10 puede nutrir a profesionales fundadores sin depender de Capa 2 completa.

---

# 2. Taxonomía de tags para la campaña

Antes de lanzar, estos tags deben existir en Systeme.io.

## Tags de fuente

```text
ADSI_ORIGEN_landing_p10_profesional
```

Uso:

Identifica que el usuario entró por la landing profesional de P10.

## Tags de idioma

```text
ADSI_IDIOMA_es
ADSI_IDIOMA_en
ADSI_IDIOMA_bilingue
```

Uso:

Gobiernan la ruta de nurturing.

## Tags de rol

```text
P10_TIPO_profesional
```

Uso:

Identifica que el contacto ofrece servicios o trayectoria profesional.

## Tags de estado

```text
P10_ESTADO_registro_incompleto
P10_ESTADO_perfil_completo
P10_STATUS_verificado
```

Uso:

- `P10_ESTADO_registro_incompleto`: entró, dejó correo, no completó datos.
- `P10_ESTADO_perfil_completo`: completó datos mínimos para indexación futura.
- `P10_STATUS_verificado`: aprobó protocolo de verificación P10/ODI.

## Nota de consistencia

En documentación previa existía familia `P10_STATUS_*`. Esta campaña introduce `P10_ESTADO_*` para estados operativos de embudo. Recomendación PC III V1:

```text
Mantener ambos solo si tienen función distinta:
P10_ESTADO_* = estado dentro del embudo de captación.
P10_STATUS_* = estado institucional dentro del organismo P10.
```

Si el equipo prefiere máxima simplicidad, unificar en `P10_STATUS_*` antes de producción.

---

# 3. Campos del formulario

El embudo será de dos pasos para proteger conversión.

## Paso 1 · Opt-in rápido

Campos:

```text
nombre
correo_electronico
idioma
```

Objetivo:

Capturar el contacto sin fricción.

## Paso 2 · Onboarding

Campos:

```text
whatsapp_con_codigo_pais
rol_principal
ciudad
```

Ejemplos de rol principal:

```text
abogado
mecanico
desarrollador
contador
medico
disenador
electricista
consultor
agente_seguros
estratega_ia
```

Regla:

No convertir el formulario en interrogatorio. El objetivo es iniciar relación, no completar toda la ficha profesional en el primer contacto.

---

# 4. captation.json · versión ejecutiva

```json
{
  "project": "P10",
  "campaign": "professional_signup_v1",
  "systeme_sub_account": "p10",
  "target_audience": "profesionales_fundadores",
  "funnel_structure": {
    "step_1": "landing_captation",
    "step_2": "thank_you_onboarding",
    "step_3": "verification_instructions"
  },
  "tags_on_entry": [
    "ADSI_ORIGEN_landing_p10_profesional",
    "P10_TIPO_profesional",
    "P10_ESTADO_registro_incompleto"
  ],
  "language_tags": {
    "es": "ADSI_IDIOMA_es",
    "en": "ADSI_IDIOMA_en",
    "bilingue": "ADSI_IDIOMA_bilingue"
  },
  "email_sequences": {
    "es": "seq_p10_welcome_es_v1",
    "en": "seq_p10_welcome_en_v1",
    "bilingue": "seq_p10_welcome_bilingual_v1"
  },
  "automation_rules": [
    "trigger_on_optin",
    "check_profile_completion_24h",
    "route_to_verification"
  ]
}
```

---

# 5. Copy landing · Español

## Titular

```text
No solo publiques tu perfil. Protege tu trayectoria.
```

## Subtítulo

```text
Construye una presencia profesional que P10 pueda analizar, verificar y conectar con oportunidades reales. Únete a la Terminal de Inteligencia Profesional que anticipa el mercado por ti.
```

## CTA principal

```text
Iniciar mi registro profesional gratis
```

## Tres viñetas de valor

### Índice de Exposición

```text
Conoce cómo los cambios del mercado afectan tu rol actual.
```

### Sinergias Estratégicas

```text
Conecta con perfiles que multiplican tu valor.
```

### Rutas de Reconversión

```text
Descubre qué habilidad aprender antes de que sea obligatorio.
```

## Microcopy de confianza

```text
Profesionales10 no es un directorio más. Es un terminal diseñado para ayudarte a construir una presencia profesional verificable, útil y preparada para nuevas oportunidades.
```

## Cierre

```text
P10 no muestra profesiones. P10 protege trayectorias.
```

---

# 6. Landing copy · English

## Headline

```text
Don't just publish your profile. Protect your career trajectory.
```

## Subtitle

```text
Build a professional presence that P10 can analyze, verify, and connect with real opportunities. Join the Professional Intelligence Terminal that anticipates the market for you.
```

## Main CTA

```text
Start my professional registration for free
```

## Three value bullets

### Exposure Index

```text
Understand how market shifts affect your current role.
```

### Strategic Synergies

```text
Connect with profiles that multiply your value.
```

### Reconversion Routes

```text
Discover what skill to learn before it becomes mandatory.
```

## Trust microcopy

```text
Profesionales10 is not another directory. It is a terminal designed to help you build a verifiable, useful, opportunity-ready professional presence.
```

## Closing

```text
P10 does not just list professions. P10 protects professional journeys.
```

---

# 7. Secuencia de bienvenida · 5 correos

Objetivo:

```text
Educar al profesional en la filosofía Guardian y empujarlo a completar perfil y avanzar hacia verificación.
```

No vender primero. Nutrir, orientar y activar.

## Email 1 · Día 0 · El fin del directorio

Propósito:

Dar bienvenida y explicar que P10 es terminal de inteligencia, no vitrina estática.

CTA:

```text
Completa tu rol principal
```

Mensaje central:

```text
Tu perfil no debe quedarse quieto. Debe explicar quién eres, qué sabes resolver y cómo P10 puede ayudarte a ser encontrado con sentido.
```

## Email 2 · Día 1 · Índice de Exposición

Propósito:

Educar sobre automatización, mercado y cambios que afectan todas las profesiones.

CTA:

```text
Ingresa tus datos para calcular tu índice
```

Mensaje central:

```text
Cada profesión vive cambios. P10 te ayuda a verlos antes de que te sorprendan.
```

## Email 3 · Día 3 · El poder de la sinergia

Propósito:

Mostrar que el crecimiento profesional no ocurre en aislamiento.

CTA:

```text
Conecta con un aliado
```

Ejemplos:

```text
Técnico en motos + especialista en diagnóstico IA.
Diseñador de interiores + experto en domótica.
Contador + automatizador financiero.
Abogado + consultor legaltech.
```

## Email 4 · Día 5 · La insignia verde

Propósito:

Explicar por qué la verificación aumenta confianza.

CTA:

```text
Inicia tu proceso de verificación
```

Mensaje central:

```text
La confianza no se improvisa. Se construye con información clara, evidencia y presencia verificable.
```

## Email 5 · Día 7 · Tu primera alerta de mercado

Propósito:

Demostrar valor con una señal real del ecosistema.

CTA:

```text
Actualiza tu mapa de oleadas
```

Mensaje central:

```text
P10 no espera a que el mercado te golpee. Te ayuda a leer señales y preparar el siguiente movimiento.
```

---

# 8. Workflow de automatización

## Trigger

```text
Usuario completa Paso 1 Opt-in.
```

## Acción inmediata

```text
Asignar ADSI_ORIGEN_landing_p10_profesional.
Asignar P10_TIPO_profesional.
Asignar P10_ESTADO_registro_incompleto.
Asignar idioma: ADSI_IDIOMA_es o ADSI_IDIOMA_en.
Suscribir a secuencia ES o EN según idioma.
```

## Delay 24 horas

Condición:

```text
¿El usuario completó Paso 2 Onboarding?
```

Si sí:

```text
Remover P10_ESTADO_registro_incompleto.
Agregar P10_ESTADO_perfil_completo.
Continuar hacia verificación.
```

Si no:

```text
Enviar recordatorio:
Tu terminal de inteligencia está pausada. Faltan 2 datos para activar tu perfil.
```

## Delay 7 días

Condición:

```text
¿Tiene P10_STATUS_verificado?
```

Si sí:

```text
Finalizar workflow inicial.
Mover a Segmento Activo.
```

Si no:

```text
Enviar invitación formal al proceso de verificación.
```

---

# 9. Criterios de aceptación

La campaña está lista para configuración manual en Systeme.io si:

- Los tags base existen.
- Landing ES/EN está cargada.
- Paso 1 captura nombre, email e idioma.
- Paso 2 captura WhatsApp, rol principal y ciudad.
- Secuencia ES/EN está creada.
- Workflow 24h funciona.
- Workflow 7 días funciona.
- Test contact pasa sin tags duplicados ni secuencia incorrecta.

---

# 10. Próxima orden técnica recomendada

Crear orden para operador/Claude Code o equipo Systeme.io:

```text
ORDEN DE CONFIGURACIÓN · SYSTEME.IO · P10 PROFESSIONAL SIGNUP V1
```

Alcance:

- Crear tags.
- Crear funnel.
- Cargar copy ES/EN.
- Crear formulario 2 pasos.
- Crear secuencia bienvenida ES/EN.
- Crear workflow 24h y 7 días.
- Probar con contacto test.
- Entregar evidencia browser.

No construir API todavía.

Primero configuración manual/semiautomática.
Luego conector.
Después CaptationPipeline completo.

---

# 11. Cierre

```text
El pipeline produce.
Systeme.io capta.
ODI gobierna ambos.
```

```text
P10 protege trayectorias.
T10 revela pertenencia.
Somos Industrias ODI.
```
