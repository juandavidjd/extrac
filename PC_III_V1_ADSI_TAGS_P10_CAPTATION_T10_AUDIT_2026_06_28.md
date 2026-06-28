# PC III V1 · ADSI Tags + P10 Captation + T10 Audit Gate · 2026-06-28

**Estado:** REGISTRADO EN CIRCUITO  
**Carril:** PC III V1 · Tribunal estratégico de producto, captación, browser y misión visual.  
**Relacionado con:** `PC_III_V1_SYSTEME_IO_CAPTATION_HANDOFF_2026_06_28.md`  
**Hito padre:** ODI × Systeme.io · Motor de Captación Inteligente.  
**Regla matriz:** El pipeline produce. Systeme.io capta. ODI gobierna ambos.

---

# 0. Veredicto

Se aprueba la convención universal de tags:

```text
[PROYECTO]_[CATEGORIA]_[VALOR]
```

Ejemplos:

```text
ADSI_ORIGEN_landing_p10
ADSI_IDIOMA_es
P10_TIPO_profesional
P10_STATUS_verificado
T10_EVENTO_miami_junio26
SRM_ACCION_carrito_abandonado
```

La taxonomía de tags queda reconocida como el sistema nervioso del módulo Systeme.io.

Sin tags limpios:

- los funnels se cruzan,
- los correos se disparan mal,
- los referidos no se atribuyen,
- los cursos no segmentan,
- el CRM se ensucia,
- el OptimizationEngine queda ciego.

Por tanto:

```text
No se crea captation.json de producción sin taxonomía aprobada.
No se lanza landing sin tags base.
No se activa workflow sin nomenclatura estable.
```

---

# 1. Convención universal ADSI

## Fórmula

```text
[PROYECTO]_[CATEGORIA]_[VALOR]
```

## Reglas de sintaxis

- Prefijo del proyecto en mayúsculas.
- Categoría en mayúsculas.
- Valor en minúsculas.
- Sin espacios.
- Sin tildes.
- Sin caracteres especiales.
- Usar `_` como separador.
- Valores compuestos en snake_case.
- No crear tags ambiguos.
- No duplicar significado con nombres distintos.

## Ejemplos válidos

```text
ADSI_ORIGEN_whatsapp
ADSI_ORIGEN_landing_p10
ADSI_ORIGEN_referido
ADSI_IDIOMA_es
ADSI_IDIOMA_en
ADSI_ESTADO_prospecto
P10_TIPO_profesional
P10_STATUS_perfil_incompleto
P10_STATUS_verificado
T10_STATUS_miembro
T10_INTERES_cultura
SRM_STATUS_taller
```

## Ejemplos prohibidos

```text
whatsapp
P10 Profesional
p10-verificado
P10_STATUS_Verificado
idioma español
lead nuevo
cliente caliente
```

---

# 2. Tags transversales ADSI

Estos tags aplican a cualquier usuario que ingrese por cualquier puerta del ecosistema.

## ADSI_ORIGEN_[fuente]

Define por dónde entró el usuario al ecosistema.

```text
ADSI_ORIGEN_whatsapp
ADSI_ORIGEN_landing_p10
ADSI_ORIGEN_landing_t10
ADSI_ORIGEN_landing_srm
ADSI_ORIGEN_referido
ADSI_ORIGEN_evento
ADSI_ORIGEN_instagram
ADSI_ORIGEN_facebook
ADSI_ORIGEN_google
ADSI_ORIGEN_manual
```

## ADSI_IDIOMA_[codigo]

Define el idioma de nurture.

```text
ADSI_IDIOMA_es
ADSI_IDIOMA_en
ADSI_IDIOMA_bilingue
```

Regla:

```text
Miami es bilingüe. Esto no es opcional.
```

## ADSI_ESTADO_[nivel]

Marca el nivel de relación comercial o comunitaria.

```text
ADSI_ESTADO_prospecto
ADSI_ESTADO_lead_calificado
ADSI_ESTADO_cliente
ADSI_ESTADO_miembro
ADSI_ESTADO_alumno
ADSI_ESTADO_embajador
ADSI_ESTADO_inactivo
ADSI_ESTADO_reactivacion
```

## ADSI_CONSENT_[estado]

Gobierna consentimiento de comunicaciones.

```text
ADSI_CONSENT_email_ok
ADSI_CONSENT_whatsapp_ok
ADSI_CONSENT_sms_ok
ADSI_CONSENT_marketing_no
ADSI_CONSENT_privacidad_pendiente
```

## ADSI_SEGMENTO_[valor]

Segmento general transversal.

```text
ADSI_SEGMENTO_profesional
ADSI_SEGMENTO_cliente
ADSI_SEGMENTO_taller
ADSI_SEGMENTO_emprendedor
ADSI_SEGMENTO_estudiante
ADSI_SEGMENTO_paciente
ADSI_SEGMENTO_proveedor
ADSI_SEGMENTO_aliado
```

## ADSI_CANAL_[valor]

Canal de relación principal.

```text
ADSI_CANAL_email
ADSI_CANAL_whatsapp
ADSI_CANAL_web
ADSI_CANAL_evento
ADSI_CANAL_crm
```

---

# 3. Tags P10 · Terminal de Inteligencia Profesional

## P10_TIPO_[valor]

```text
P10_TIPO_profesional
P10_TIPO_cliente
P10_TIPO_empresa
P10_TIPO_aliado
```

## P10_STATUS_[valor]

```text
P10_STATUS_registrado
P10_STATUS_perfil_incompleto
P10_STATUS_perfil_completo
P10_STATUS_verificacion_pendiente
P10_STATUS_verificado
P10_STATUS_activo
P10_STATUS_inactivo
P10_STATUS_reactivacion
```

## P10_GUARDIAN_[riesgo]

```text
P10_GUARDIAN_riesgo_bajo
P10_GUARDIAN_riesgo_medio
P10_GUARDIAN_riesgo_alto
P10_GUARDIAN_riesgo_critico
P10_GUARDIAN_oportunidad
P10_GUARDIAN_alerta_activa
```

Regla:

```text
Las alertas no deben generar pánico. Siempre deben incluir acciones concretas.
```

## P10_OLEADA_[numero_estado]

```text
P10_OLEADA_1_conciencia
P10_OLEADA_2_fortalecimiento
P10_OLEADA_3_diversificacion
P10_OLEADA_4_posicionamiento
```

## P10_MUNDO_[valor]

Mundos profesionales para evitar sesgo LinkedIn y evitar volver al sesgo de oficios.

```text
P10_MUNDO_tecnico_operativo
P10_MUNDO_salud_bienestar
P10_MUNDO_legal_cumplimiento
P10_MUNDO_tecnologia_datos
P10_MUNDO_diseno_experiencia
P10_MUNDO_finanzas_estrategia
P10_MUNDO_educacion_formacion
P10_MUNDO_movilidad_mecanica
P10_MUNDO_servicios_hogar
P10_MUNDO_creativos_medios
```

Regla visual:

```text
P10 debe servir igual para quien usa un multímetro que para quien usa un IDE.
```

## P10_ACCION_[valor]

```text
P10_ACCION_completo_formulario
P10_ACCION_inicio_verificacion
P10_ACCION_completo_perfil
P10_ACCION_solicito_revision
P10_ACCION_agendo_llamada
P10_ACCION_descargo_guia
P10_ACCION_abandono_registro
```

## P10_CAPTACION_[valor]

```text
P10_CAPTACION_professional_signup_v1
P10_CAPTACION_client_search_v1
P10_CAPTACION_guardian_test_v1
```

---

# 4. Tags T10 · Radar de Pertenencia

## T10_STATUS_[valor]

```text
T10_STATUS_miembro
T10_STATUS_miembro_verificado
T10_STATUS_miembro_activo
T10_STATUS_miembro_inactivo
T10_STATUS_fundador
T10_STATUS_reactivacion
```

## T10_EVENTO_[nombre]

```text
T10_EVENTO_miami_junio26
T10_EVENTO_wynwood_cena_v1
T10_EVENTO_cultural_miami_v1
```

Regla:

```text
Todo evento real debe dejar memoria relacional.
```

## T10_INTERES_[nicho]

```text
T10_INTERES_networking
T10_INTERES_cultura
T10_INTERES_musica
T10_INTERES_familia
T10_INTERES_emprendimiento
T10_INTERES_bienestar
T10_INTERES_comunidad
T10_INTERES_apoyo
```

## T10_MOMENTO_[valor]

```text
T10_MOMENTO_busco_comunidad
T10_MOMENTO_quiero_conocer_gente
T10_MOMENTO_reubicacion
T10_MOMENTO_emprendiendo
T10_MOMENTO_necesito_apoyo
T10_MOMENTO_busco_eventos
T10_MOMENTO_reconexion
```

## T10_ACCION_[valor]

```text
T10_ACCION_registro_evento
T10_ACCION_asistio_evento
T10_ACCION_no_asistio_evento
T10_ACCION_invito_referido
T10_ACCION_participo_grupo
T10_ACCION_conexion_guiada
T10_ACCION_post_evento_completado
```

## T10_CAPTACION_[valor]

```text
T10_CAPTACION_first_event_v1
T10_CAPTACION_member_signup_v1
T10_CAPTACION_referral_v1
```

---

# 5. Tags SRM · Motor Comercial

## SRM_STATUS_[valor]

```text
SRM_STATUS_taller
SRM_STATUS_taller_registrado
SRM_STATUS_taller_activo
SRM_STATUS_taller_inactivo
SRM_STATUS_proveedor
SRM_STATUS_cliente_b2c
SRM_STATUS_cliente_b2b
```

## SRM_CURSO_[nombre]

```text
SRM_CURSO_mecanica_desde_cero
SRM_CURSO_taller_digital
SRM_CURSO_diagnostico_electrico
```

## SRM_ACCION_[valor]

```text
SRM_ACCION_carrito_abandonado
SRM_ACCION_solicito_catalogo
SRM_ACCION_descargo_guia
SRM_ACCION_agendo_demo
SRM_ACCION_completo_onboarding
```

## SRM_CAPTACION_[valor]

```text
SRM_CAPTACION_taller_digital_v1
SRM_CAPTACION_curso_mecanica_v1
SRM_CAPTACION_catalogo_demo_v1
```

---

# 6. captation.json mínimo · P10 Professional Signup v1

Nombre operativo:

```text
captation_p10_professional_signup_v1
```

Objetivo:

```text
Captar profesionales fundadores para Profesionales10 antes del lanzamiento completo.
```

Promesa:

```text
No solo publiques tu perfil. Construye una presencia profesional que P10 pueda recomendar, verificar y proyectar.
```

## JSON base

```json
{
  "project": "P10",
  "name": "Profesionales10",
  "version": "captation_p10_professional_signup_v1",
  "systeme_sub_account": "p10",
  "languages": ["es", "en"],
  "primary_goal": "professional_signup",
  "funnel": {
    "id": "p10_professional_signup_v1",
    "pages": [
      "landing",
      "register",
      "verify_interest",
      "welcome"
    ],
    "automation": "wf_p10_professional_onboarding_v1"
  },
  "form_fields": [
    {"name": "first_name", "required": true},
    {"name": "last_name", "required": true},
    {"name": "email", "required": true},
    {"name": "phone", "required": false},
    {"name": "profession", "required": true},
    {"name": "professional_world", "required": true},
    {"name": "city", "required": true},
    {"name": "language_preference", "required": true},
    {"name": "goal", "required": false}
  ],
  "default_tags": [
    "ADSI_ORIGEN_landing_p10",
    "ADSI_ESTADO_prospecto",
    "ADSI_SEGMENTO_profesional",
    "ADSI_CANAL_email",
    "P10_TIPO_profesional",
    "P10_STATUS_registrado",
    "P10_STATUS_perfil_incompleto",
    "P10_CAPTACION_professional_signup_v1"
  ],
  "conditional_tags": {
    "language_preference": {
      "es": "ADSI_IDIOMA_es",
      "en": "ADSI_IDIOMA_en",
      "bilingue": "ADSI_IDIOMA_bilingue"
    },
    "professional_world": {
      "tecnico_operativo": "P10_MUNDO_tecnico_operativo",
      "salud_bienestar": "P10_MUNDO_salud_bienestar",
      "legal_cumplimiento": "P10_MUNDO_legal_cumplimiento",
      "tecnologia_datos": "P10_MUNDO_tecnologia_datos",
      "diseno_experiencia": "P10_MUNDO_diseno_experiencia",
      "finanzas_estrategia": "P10_MUNDO_finanzas_estrategia",
      "educacion_formacion": "P10_MUNDO_educacion_formacion",
      "movilidad_mecanica": "P10_MUNDO_movilidad_mecanica",
      "servicios_hogar": "P10_MUNDO_servicios_hogar",
      "creativos_medios": "P10_MUNDO_creativos_medios"
    }
  },
  "email_sequences": {
    "welcome_professional_es": {
      "emails": 5,
      "days": 7,
      "trigger": "P10_TIPO_profesional + ADSI_IDIOMA_es"
    },
    "welcome_professional_en": {
      "emails": 5,
      "days": 7,
      "trigger": "P10_TIPO_profesional + ADSI_IDIOMA_en"
    },
    "welcome_professional_bilingual": {
      "emails": 5,
      "days": 7,
      "trigger": "P10_TIPO_profesional + ADSI_IDIOMA_bilingue"
    }
  },
  "affiliate": {
    "enabled": true,
    "program": "embajador_p10",
    "commission_pct": 10,
    "cookie_days": 90,
    "badge_name": "Embajador P10"
  },
  "branding": {
    "primary_color": "#060651",
    "accent_color": "#FFC107",
    "background": "#FFFFFF",
    "tone": "profesional, claro, protector, bilingue, productivo"
  }
}
```

---

# 7. Copy landing P10 · Español

## Headline

```text
Conecta, crece y protege tu futuro profesional con Profesionales10.
```

## Subtítulo

```text
Registra tu perfil profesional y entra al primer terminal de inteligencia diseñado para ayudarte a ser visible, verificable y recomendado con sentido.
```

## Bloque de valor

```text
Profesionales10 no es otro directorio.
Es una plataforma que organiza tu presencia profesional, entiende tu mundo laboral y te prepara para nuevas oportunidades.
```

## Beneficios

```text
Crea una presencia profesional clara.
Recibe guía para completar y fortalecer tu perfil.
Prepárate para verificación y recomendación.
Conecta con clientes, aliados y oportunidades reales.
Accede a señales que pueden ayudarte a evolucionar tu carrera.
```

## CTA principal

```text
Quiero registrar mi perfil profesional
```

## CTA secundario

```text
Avisarme cuando Profesionales10 abra oficialmente
```

## Microcopy formulario

```text
Te enviaremos los próximos pasos para completar tu perfil. Sin spam. Sin presión. Solo información útil para avanzar.
```

## Cierre

```text
P10 no muestra profesiones. P10 protege trayectorias.
```

---

# 8. Copy landing P10 · English

## Headline

```text
Connect, grow, and protect your professional future with Profesionales10.
```

## Subtitle

```text
Register your professional profile and join a professional intelligence terminal designed to help you become visible, verifiable, and meaningfully recommended.
```

## Value block

```text
Profesionales10 is not another directory.
It organizes your professional presence, understands your career context, and prepares you for better opportunities.
```

## Benefits

```text
Build a clear professional presence.
Get guided steps to complete and strengthen your profile.
Prepare for verification and recommendation.
Connect with clients, allies, and real opportunities.
Receive signals that help you evolve your career.
```

## Primary CTA

```text
I want to register my professional profile
```

## Secondary CTA

```text
Notify me when Profesionales10 officially opens
```

## Form microcopy

```text
We will send you the next steps to complete your profile. No spam. No pressure. Just useful information to move forward.
```

## Closing line

```text
P10 does not just list professions. P10 protects professional journeys.
```

---

# 9. Secuencia inicial de emails · P10 Profesional ES

## Email 1 · Bienvenida

Asunto:

```text
Bienvenido a Profesionales10
```

Objetivo:

```text
Confirmar registro, explicar propósito y preparar el siguiente paso.
```

Mensaje central:

```text
Tu perfil profesional puede ser más que una ficha. Puede convertirse en una presencia clara, verificable y lista para ser recomendada con sentido.
```

CTA:

```text
Completar mi perfil
```

## Email 2 · Perfil claro

Asunto:

```text
Tu perfil debe explicar qué haces y para quién
```

Objetivo:

```text
Ayudar a completar profesión, ciudad, mundo profesional y servicios.
```

CTA:

```text
Actualizar mi información profesional
```

## Email 3 · Verificación

Asunto:

```text
La confianza empieza con una presencia verificable
```

Objetivo:

```text
Introducir verificación sin fricción.
```

CTA:

```text
Preparar mi verificación
```

## Email 4 · Oportunidades

Asunto:

```text
Profesionales10 no solo te muestra, te conecta con oportunidades
```

Objetivo:

```text
Explicar clientes, aliados, sinergias y rutas.
```

CTA:

```text
Ver cómo funciona P10
```

## Email 5 · Guardian Profesional

Asunto:

```text
Tu carrera también necesita señales
```

Objetivo:

```text
Presentar Guardian Profesional, oleadas y evolución de trayectoria.
```

CTA:

```text
Activar mis próximos pasos
```

---

# 10. Secuencia inicial de emails · P10 Professional EN

## Email 1 · Welcome

Subject:

```text
Welcome to Profesionales10
```

Goal:

```text
Confirm registration, explain purpose, and prepare the next step.
```

Core message:

```text
Your professional profile can be more than a listing. It can become a clear, verifiable presence ready to be meaningfully recommended.
```

CTA:

```text
Complete my profile
```

## Email 2 · Clear profile

Subject:

```text
Your profile should explain what you do and who you help
```

CTA:

```text
Update my professional information
```

## Email 3 · Verification

Subject:

```text
Trust starts with a verifiable presence
```

CTA:

```text
Prepare my verification
```

## Email 4 · Opportunities

Subject:

```text
Profesionales10 does not just display you. It connects you with opportunities.
```

CTA:

```text
See how P10 works
```

## Email 5 · Professional Guardian

Subject:

```text
Your career also needs signals
```

CTA:

```text
Activate my next steps
```

---

# 11. Workflow P10 Professional Signup v1

```text
IF formulario completado
THEN aplicar tags default
THEN aplicar tag idioma
THEN aplicar tag mundo profesional
THEN enviar email bienvenida según idioma
WAIT 24h
IF perfil incompleto
THEN enviar recordatorio completar perfil
WAIT 72h
IF perfil completo
THEN remover P10_STATUS_perfil_incompleto
THEN agregar P10_STATUS_perfil_completo
THEN invitar a verificación
IF verificación iniciada
THEN agregar P10_STATUS_verificacion_pendiente
IF verificación aprobada
THEN agregar P10_STATUS_verificado
THEN agregar P10_STATUS_activo
THEN activar en búsquedas futuras
```

---

# 12. T10 · Auditoría de Realidad permanece bloqueante

Se reafirma el estado del expediente T10:

```text
EXPEDIENTE 002 · TEVEO10
ESTADO: ETAPA 0 · AUDITORÍA DE REALIDAD · TRIBUNAL EN SESIÓN
```

Regla:

```text
Si no hay evidencia de pertenencia, no hay derecho a rediseño.
```

PC III V1 acepta el encargo de auditor forense, pero no emitirá componentes visuales hasta recibir evidencia.

## Evidencia requerida

### 1. Memoria de Afinidad

Entregables:

- estructura de base de datos,
- grupos,
- eventos compartidos,
- ratings,
- conexiones,
- razones de recomendación si existen.

Pregunta:

```text
¿Conectamos por pertenencia o solo por etiquetas?
```

### 2. Fricción de Categoría

Entregables:

- capturas home,
- registro,
- eventos,
- grupos,
- perfil,
- conexión/chat.

Foco:

- detectar lenguaje dating,
- botones match,
- fotos de perfil como mercancía,
- búsqueda genérica,
- señales tipo app social vacía.

### 3. Interacción Orgánica

Entregables:

- usuarios reales,
- conversaciones,
- retornos,
- asistencias,
- referidos,
- actividad recurrente,
- grupos activos.

Pregunta:

```text
¿Hay movimiento humano real o solo datos sembrados?
```

### 4. Memoria Relacional

Entregables:

- historias de eventos,
- qué pasó después,
- quién volvió,
- qué conexión generó valor,
- contenido post-evento,
- señal de continuidad.

## Resultados posibles

```text
PASS · Viable con Pivot
PARTIAL · Pivot a Nicho
FAIL · Pausa Administrativa
```

Regla final:

```text
T10 debe revelar pertenencia real.
```

---

# 13. Decisión de secuencia

La secuencia de ejecución aprobada para Systeme.io queda:

```text
1. Tags ADSI / P10.
2. captation.json mínimo P10.
3. Copy landing P10 ES/EN.
4. Secuencia bienvenida ES/EN.
5. Workflow P10 Professional Signup v1.
6. Landing Systeme.io coming soon P10.
7. Luego T10 First Event v1.
8. Luego SRM Taller Digital v1.
```

---

# 14. Cierre

La convención `[PROYECTO]_[CATEGORIA]_[VALOR]` queda aprobada y registrada.

P10 Professional Signup v1 queda como primera ejecución de CaptationPipeline.

T10 continúa bloqueado a diseño hasta Auditoría de Realidad.

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
