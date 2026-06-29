# ÓRDENES CLAUDE CODE · P10/T10 · 12 ENTREGABLES PROMETIDOS

**Regla rectora:** Lo que se propuso es lo que se certifica.  
**Fecha de registro:** 2026-06-29  
**Firma operativa previa:** jdamg-2026-06-17-luz-verde-continua-pcs-v1  
**Alcance:** Profesionales10 + Teveo10, sin desviar a heartbeats internos.

---

# ESTADO DUAL

```text
PRIORIDAD 1 · NERVIO EN PROGRESO
  PR #59 δ-ROOT mergeado.
  PATH α'' PR #57 mergeado.
  Siguiente: RUNTIME_BRIDGE + re-H2.
  H2 exit 0 → first task → NERVE_ALIVE.

PRIORIDAD 2 · P10/T10 12 ENTREGABLES POST-NERVIO
  Mes 3 deuda: mensajería, calificaciones, traducción,
  grupos T10, calendario T10.

  Mes 4 nuevo: embudos, email, referidos, matching,
  pagos visibles, WhatsApp eventos, galería.

SECUENCIA
  Nervio vivo → dispatcher funcional
  → despachar los 12 entregables como tasks reales
  → cada entregable se certifica contra propuesta
  → Martha ve features, no heartbeats.
```

---

# FUENTES DE VERDAD

```text
PROPUESTA_COMERCIAL_P10_T10.docx — cronograma 6 meses.
PROPUESTA_EJECUTIVA_PROFESIONALES10.docx — 4 fases P10.
PROPUESTA_EJECUTIVA_TEVEO10.docx — 5 fases T10.
CONTRATO_SERVICIOS_ADSI_P10_T10_V2.docx — compromisos legales.
```

---

# CRUCE PROPUESTO VS CONSTRUIDO HOY

## Construido · ecosistema listo para absorber

- ChromaDB 201 docs, base para matching.
- Chat API skin P10, base para mensajería.
- 7 gates de verificación, base para calificaciones.
- PAEM BookingOrchestrator, base para calendario.
- Systeme.io cuenta, base para embudos.
- billing.py + Wompi keys, base para pagos.
- WhatsApp Business verificado, base para notificaciones.

## No construido · lo que el cliente espera ver

- Mensajería directa P10, UI chat profesional-cliente.
- Calificaciones bidireccionales, UI + backend + evidencia.
- Traducción bilingüe automática en componentes clave.
- Grupos temáticos T10, lógica + UI.
- Compatibilidad T10, algoritmo de intereses.
- Calendario eventos T10, UI conectada a PAEM.
- Embudos Systeme.io activos.
- Secuencias email configuradas.
- Referidos implementados.
- Pagos conectados de forma visible, medición solo OK pero falta UI.
- Matching inteligente, ChromaDB existe pero falta algoritmo final visible.
- Galería post-evento.

---

# 12 ENTREGABLES · LO QUE SE PROPUSO = LO QUE SE CERTIFICA

## Mes 3 deuda · cerrar ya

1. Mensajería directa P10, chat in-platform.
2. Calificaciones bidireccionales, estrellas + fotos.
3. Traducción bilingüe automática, ES ↔ EN.
4. Grupos temáticos T10, backend + UI.
5. Calendario eventos T10, PAEM wire-up.

## Mes 4 comprometido

6. Embudos Systeme.io activos.
7. Secuencias email automáticas, 5 ES + 5 EN.
8. Referidos P10 + T10, código + límite 3.
9. Matching inteligente, ranking multi-factor.
10. Pagos visibles, medición solo para Martha.
11. Inscripción eventos por WhatsApp.
12. Galería post-evento + referidos T10.

---

# ENTREGABLE 1 · MENSAJERÍA DIRECTA INTELIGENTE P10

## Propuesta dice

- Mensajería directa inteligente entre profesional y cliente.
- Chat API skin P10 como canal de comunicación.

## Existe

- Chat API skin P10 live en odi_chat_api.py.
- Ramona/Tony ya conversan con skin P10.
- WhatsApp Business verificado con templates.

## Falta

- UI de conversación profesional-cliente dentro de P10.
- No es WhatsApp externo; es chat in-platform.
- Cliente busca profesional, lo contacta y conversan dentro de P10.
- Profesional recibe notificación y responde dentro de P10.

## Backend · PC II

1. Endpoint POST /p10/mensajes/enviar.
   - sender_id, receiver_id, mensaje, contexto, servicio_id.
   - Orígenes pre-mutate.
   - Guardian context para detectar contenido sensible.
   - No loguear PII ni contenido de mensaje en texto plano.

2. Endpoint GET /p10/mensajes/:conversacion_id.
   - Retorna historial paginado.
   - Solo accesible con JWT del participante.

3. Endpoint GET /p10/mensajes/bandeja.
   - Lista conversaciones del usuario autenticado.
   - Última actividad, mensajes sin leer y estado.

4. Tabla PG p10_mensajes.
   - id, conversacion_id, sender_id, receiver_id, contenido cifrado o redactado en logs, created_at, leido_at, servicio_id.

5. Notificación WhatsApp al recibir mensaje.
   - Template de nuevo mensaje sobre servicio.
   - Solo si receptor tiene WhatsApp verificado.

## Frontend · PC I

1. ChatWindow en /perfil/:id.
2. Botón Contactar que abre chat.
3. Contacto oculto sin auth.
4. Bandeja de mensajes en /panel.
5. Input de mensaje, envío, timestamp y adjunto de imagen.

## Tests

- Enviar mensaje profesional a cliente.
- Enviar mensaje cliente a profesional.
- Bandeja muestra conversaciones correctas.
- Sin JWT no accede.
- Guardian detecta contenido sensible.
- Notificación WhatsApp disparada.

## Certificación

Martha debe poder abrir un perfil, presionar Contactar, ver conversación, enviar mensaje y ver notificación/bandeja funcional con datos reales o demo controlado honesto.

---

# ENTREGABLE 2 · CALIFICACIONES BIDIRECCIONALES CON EVIDENCIA

## Propuesta dice

- Calificaciones bidireccionales con evidencia fotográfica.
- Profesional califica cliente y cliente califica profesional.
- Evidencia fotográfica del trabajo terminado.

## Existe

- Convenio P10 con fases y seguimiento.
- Portafolio con carga de evidencia.
- badge_nivel autocalculado.

## Falta

- Sistema de calificación post-servicio.
- Ambas partes califican.
- Evidencia fotográfica obligatoria.
- Promedio visible en perfil.

## Backend · PC II

1. Tabla PG p10_calificaciones.
   - id, convenio_id, calificador_id, calificado_id.
   - tipo profesional_a_cliente o cliente_a_profesional.
   - puntuacion 1-5, comentario, evidencia_urls, created_at, verificado_odi.

2. Endpoint POST /p10/calificaciones.
   - Solo después de convenio completado.
   - Evidencia fotográfica mínima de 1 imagen.
   - Ambas partes deben calificar para visibilidad completa.

3. Endpoint GET /p10/profesionales/:id/calificaciones.
   - Promedio, total, desglose por estrellas y últimas 10 calificaciones con evidencia.

4. Actualizar badge_nivel.
   - Promedio >= 4.0 suma señal.
   - 10+ calificaciones suma señal.

5. CES profile gate actualizado.
   - Perfil con calificaciones reales pesa más que perfil sin calificaciones.

## Frontend · PC I

1. CalificacionForm post-convenio.
2. Selector 5 estrellas.
3. Comentario.
4. Upload de fotos obligatorio.
5. CalificacionesDisplay en /perfil/:id.
6. Promedio, número total, galería y comentarios.
7. Badge visual en cards de búsqueda.

## Tests

- Calificar profesional después de convenio.
- Calificar cliente después de convenio.
- Evidencia obligatoria.
- Promedio calcula correctamente.
- Badge actualiza.
- Sin convenio completado no permite calificar.

## Certificación

Martha debe ver una calificación bidireccional completa, con fotos, promedio visible, perfil actualizado y bloqueo si no hay convenio completado.

---

# ENTREGABLE 3 · TRADUCCIÓN BILINGÜE AUTOMÁTICA

## Propuesta dice

- Bilingüe EN/ES con traducción automática integrada.
- Traducción automática en conversaciones.
- El usuario describe lo que busca y el sistema interpreta.

## Existe

- 63 categorías bilingües ES/EN.
- Frontend con switch ES/EN.
- ChromaDB indexado en ambos idiomas.

## Falta

- Traducción automática de componentes dinámicos.
- Perfiles traducidos.
- Mensajes traducidos automáticamente.
- Resultados en idioma del usuario.

## Backend · PC II

1. Helper core/odi_translator.py.
   - translate(text, from_lang, to_lang).
   - DeepL API si está disponible.
   - Cache por hash de texto.
   - Fallback a texto original si API falla.

2. Endpoints traducidos.
   - GET /p10/profesionales/:id?lang=en.
   - GET /p10/buscar?q=plumber&lang=en.
   - Descripción profesional traducida al vuelo.
   - Categorías ya bilingües no se retraducen.

3. Mensajería bilingüe.
   - Si sender ES y receiver EN, mostrar mensaje traducido con nota.
   - Texto original disponible al expandir.

## Frontend · PC I

1. Switch idioma ES/EN persistente en localStorage.
2. Componentes dinámicos respetan idioma.
3. Perfiles en idioma del visitante.
4. Búsqueda acepta queries en ambos idiomas.
5. Nota Traducido automáticamente cuando aplique.

## Tests

- Buscar plumber devuelve resultados relevantes equivalentes a plomero.
- Perfil ES cambia a EN.
- Mensaje ES a EN traducido con nota.
- Cache evita doble llamada.

## Certificación

Martha debe poder cambiar idioma y ver perfil, búsqueda y mensaje traducidos sin placeholders ni textos fijos hardcodeados.

---

# ENTREGABLE 4 · GRUPOS TEMÁTICOS T10

## Propuesta dice

- Grupos temáticos funcionales: viajes, lectura, deportes, crecimiento personal, cocina y otros.
- Actividad real.

## Existe

- Frontend T10 con grupos demo.
- Estructura visual de grupos en carruseles.

## Falta

- Backend de grupos.
- Crear, unirse, publicar y gestionar.
- Membresía por grupo.
- Posts, comentarios, compartir.
- Moderación básica.

## Backend · PC II

1. Tabla PG t10_grupos.
   - id, nombre, descripcion, categoria, creador_id, imagen_url, miembros_count, privado, created_at, activo.

2. Tabla PG t10_grupo_miembros.
   - grupo_id, miembro_id, rol, joined_at, estado.

3. Tabla PG t10_grupo_posts.
   - id, grupo_id, autor_id, contenido, imagen_url, created_at, likes_count.

4. Endpoints.
   - POST /t10/grupos.
   - POST /t10/grupos/:id/unirse.
   - POST /t10/grupos/:id/posts.
   - GET /t10/grupos.
   - GET /t10/grupos/:id.
   - GET /t10/grupos/:id/miembros.

5. Categorías seed.
   - Viajes, Lectura, Deportes, Crecimiento personal, Cocina, Música, Arte, Tecnología, Emprendimiento, Bienestar.

## Frontend · PC I

1. /grupos con lista por categoría.
2. /grupos/:id con detalle, posts y miembros.
3. Botón Unirme con verificación.
4. Crear grupo con formulario.
5. Publicar texto + imagen opcional.
6. Carrusel grupos populares en inicio T10.

## Tests

- Crear grupo.
- Unirse a grupo verificado.
- Publicar post.
- Listar por categoría.
- Grupo privado solo muestra posts a miembros.

## Certificación

Martha debe ver grupo real creado, usuario unido, post publicado y visibilidad diferenciada para grupo privado.

---

# ENTREGABLE 5 · CALENDARIO EVENTOS T10 + PAEM

## Propuesta dice

- Calendario de eventos presenciales y virtuales integrado.
- Registro a eventos con un click.
- Recordatorio automático por WhatsApp.
- Galería post-evento.

## Existe

- PAEM BookingOrchestrator con adapters.
- Frontend T10 con fichas demo.
- Convenio multi-actor.
- WhatsApp Business con templates.

## Falta

- Wire-up frontend T10 a PAEM backend.
- Calendario visual real.
- Inscripción real.
- Recordatorio WhatsApp pre-evento.
- Galería post-evento con fotos.

## Backend · PC II

1. Conectar T10 a PAEM.
   - POST /t10/eventos → PAEM booking/create.
   - POST /t10/eventos/:id/inscribirse → PAEM booking/confirm.
   - GET /t10/eventos → listado filtrado por T10.
   - GET /t10/eventos/:id → detalle con asistentes.

2. Tabla PG t10_eventos si no usa PAEM directo.
   - id, titulo, descripcion, fecha, hora, lugar_id, organizador_id, capacidad, inscritos_count, tipo, estado, galeria_urls.

3. Tabla PG t10_inscripciones.
   - evento_id, miembro_id, fecha_inscripcion, asistio, calificacion_evento.

4. Recordatorio WhatsApp 24h antes.

5. Galería post-evento.
   - POST /t10/eventos/:id/galeria.
   - Solo organizador y asistentes.
   - Generar contenido para redes.

## Frontend · PC I

1. /eventos calendario mes/semana/lista.
2. /eventos/:id ficha real.
3. Botón Inscribirme con verificación.
4. Contador asistentes en tiempo real.
5. Post-evento: galería + calificación.
6. /crear para organizador verificado.

## Tests

- Crear evento futuro.
- Inscribirse.
- Recordatorio 24h disparado.
- Galería con fotos.
- Evento pasado cambia a finalizado.
- Calificación post-evento.

## Certificación

Martha debe ver evento creado, inscripción real, calendario visible, contador actualizado y recordatorio/galería certificados.

---

# ENTREGABLE 6 · EMBUDOS CAPTACIÓN SYSTEME.IO

## Propuesta dice

- Embudos de captación para profesionales y clientes.
- Systeme.io como canal; ODI como centro.

## Existe

- Cuenta Systeme.io en dry-run.
- Landing profesionales10.online captura leads.
- Lead Habitat V1 live.

## Falta

- Embudos activos con páginas secuenciales.
- Segmentación profesional vs cliente.
- Embudo profesional de 3 páginas.
- Embudo cliente de 2 páginas.

## Ejecución

1. Activar cuenta Systeme.io.
2. Crear embudo profesional.
   - Dolor: profesional hispano necesita visibilidad.
   - Solución: perfil verificado conecta con clientes.
   - Registro: formulario que redirige a P10.

3. Crear embudo cliente.
   - Necesidad: buscar servicio profesional.
   - Acción: búsqueda directa que redirige a P10.

4. Tags base.
   - profesional_p10.
   - cliente_p10.
   - lead_t10.

5. Cada lead llega a Lead Habitat + PG.

## Frontera

- Configuración Systeme.io: arquitecto con credenciales.
- Contenido páginas: Manuela + Martha.

## Certificación

Martha debe ver embudo publicado, formulario funcional, tag aplicado, lead registrado y redirección correcta hacia profesionales10.online.

---

# ENTREGABLE 7 · SECUENCIAS EMAIL AUTOMÁTICAS

## Propuesta dice

- Secuencias email automáticas de bienvenida.
- 5 correos ES + 5 correos EN.

## Existe

- Correos IONOS configurados.
- 5 correos ES diseñados en Mes 1.

## Falta

- Configurar en Systeme.io como automatización.
- 5 correos EN.
- Trigger registro → secuencia automática.
- Segmentación profesional, cliente y T10.

## Ejecución

1. Traducir 5 correos ES a EN.
2. Configurar en Systeme.io.
   - tag profesional_p10 → secuencia profesional.
   - tag cliente_p10 → secuencia cliente.
   - tag lead_t10 → secuencia T10.

3. Cadencia.
   - Día 0, día 2, día 5, día 10, día 15.

4. Contenido.
   - Bienvenida + qué es P10.
   - Cómo funciona la verificación.
   - Completa tu perfil.
   - Testimonios cuando existan.
   - Habla con ODI.

## Certificación

Martha debe ver contacto test entrar, recibir tag, secuencia activada y al menos el primer correo enviado/pendiente en Systeme.io.

---

# ENTREGABLE 8 · PROGRAMA REFERIDOS P10 + T10

## Propuesta dice

- Sistema de referidos controlado.
- Cada miembro verificado invita hasta 3 personas.
- Responsabilidad compartida.

## Falta

- Código por usuario verificado.
- Límite 3 invitaciones.
- Tracking invitador-invitado.
- Notificación si referido es reportado.

## Backend · PC II

1. Campo referido_code en p10_profesionales y t10_miembros.
   - Auto-generado al verificarse.
   - 6 caracteres alfanuméricos.
   - Único.

2. Campo referido_por en registro.
   - Vincula por código.
   - Límite de 3.

3. Endpoint GET /p10/referidos/mi-codigo.
4. Endpoint GET /p10/referidos/mis-referidos.
5. Mismo patrón para T10.
6. Lógica de reporte.
   - Referido reportado/suspendido notifica al invitador.
   - 2+ referidos reportados activan revisión del invitador.

## Frontend · PC I

1. Perfil propio muestra código.
2. Botón compartir enlace.
3. Campo opcional de código en registro.
4. Panel de mis referidos y estado.

## Tests

- Generar código al verificarse.
- Registro con código válido vincula.
- Código inválido no bloquea.
- Límite 3 respetado.
- Reporte dispara notificación.

## Certificación

Martha debe ver un usuario verificado con código, un referido creado y el límite funcionando.

---

# ENTREGABLE 9 · MATCHING INTELIGENTE

## Propuesta dice

- Matching inteligente por zona, disponibilidad y calificaciones.
- El usuario describe lo que busca y el sistema interpreta.

## Existe

- ChromaDB 201 docs con búsqueda semántica.
- 63 categorías bilingües.
- P10MatchingEngine live/base.

## Falta

- Algoritmo de ranking combinando relevancia semántica, proximidad, calificación, disponibilidad y badge.
- Sugerencias proactivas.

## Backend · PC II

1. Actualizar P10MatchingEngine.search.

```text
score_final = semantic * 0.30
            + proximity * 0.25
            + rating * 0.25
            + badge * 0.10
            + availability * 0.10
```

2. Normalizar cada factor 0-1.
3. Retornar top 10 rankeados.
4. Endpoint GET /p10/sugerencias?lat=X&lng=Y.
5. Endpoint GET /p10/profesionales/:id/disponibilidad.

## Frontend · PC I

1. /buscar ordenado por matching score.
2. Indicador visual de match.
3. Sección Sugeridos para ti si hay ubicación.

## Tests

- Query con ubicación prioriza cercanos.
- Query con calificación prioriza mejores ratings.
- Sin ubicación prioriza badge + rating.
- Sugerencias sin query devuelven cercanos verificados.

## Certificación

Martha debe ver resultados ordenados por lógica real y explicación visual del match, no orden hardcodeado.

---

# ENTREGABLE 10 · PASARELA PAGOS VISIBLE

## Propuesta dice

- Procesador de pagos integrado.
- Comisión solo por resultado: 5% cuando servicio se conecta.
- Cuota de prestación de servicios como lenguaje legal adecuado.

## Existe

- billing.py con score, comisión, ledger y endpoints base.
- Wompi keys en config.
- config_billing.yaml.
- medicion_solo true.

## Falta

- UI visible para Martha.
- Flujo servicio completado → cuota calculada → visible en panel.
- No activar cobro real todavía.

## Backend · PC II

1. Endpoint GET /p10/billing/resumen.
   - Servicios conectados este mes.
   - Cuota estimada por servicio.
   - Total estimado.
   - Estado medicion_solo.

2. Endpoint GET /p10/billing/historial.
   - Servicio, fecha, profesional, cliente, monto, cuota.

## Frontend · PC I

1. Panel Martha, sección Cuotas de prestación.
2. Servicios conectados, cuota estimada total.
3. Mensaje: sistema en modo medición, cobro automático próximamente.
4. Tabla detalle.

## Nota soberana

medicion_solo = true permanece. No se activa cobro real sin firma soberana.

## Certificación

Martha debe ver panel de cuotas con datos reales o demo controlado honesto y estado de medición claramente visible.

---

# ENTREGABLE 11 · INSCRIPCIÓN EVENTOS POR WHATSAPP

## Propuesta dice

- Inscripción a eventos por mensajería WhatsApp.
- Recordatorio automático.

## Conecta con

- Entregable 5 calendario T10.
- WhatsApp Business.

## Falta

- Evento publicado → WhatsApp notifica seguidores.
- Usuario responde SI o me inscribo.
- Inscripción automática.
- Confirmación y recordatorio 24h antes.

## Backend · PC II

1. Al crear evento, broadcast WhatsApp a seguidores con opt-in.
2. Template: nuevo evento con fecha, lugar y respuesta SI.
3. Webhook WhatsApp interpreta SI / sí / me inscribo.
4. Ejecuta inscripción automática.
5. Confirmación WhatsApp.
6. Cron 24h pre-evento.

## Frontera

- Templates Meta aprobados.
- Broadcasting requiere opt-in.

## Certificación

Martha debe ver respuesta WhatsApp transformada en inscripción real y recordatorio programado o disparado en ambiente controlado.

---

# ENTREGABLE 12 · GALERÍA POST-EVENTO + REFERIDOS T10

## Propuesta dice

- Galería post-evento que genera contenido para redes.
- Sistema de referidos T10.

## Conecta con

- Entregable 5 eventos.
- Entregable 8 referidos.

## Backend · PC II

1. POST /t10/eventos/:id/galeria.
   - Upload múltiples fotos.
   - Solo organizador + asistentes verificados.
   - Thumbnails automáticos.

2. GET /t10/eventos/:id/galeria.
   - Grid de fotos.
   - Metadata: quién subió, fecha, likes.

3. Referidos T10.
   - Código por miembro verificado.
   - Límite 3.
   - Tracking invitador-invitado.

## Frontend · PC I

1. Post-evento: Comparte tus fotos.
2. Grid galería con lightbox.
3. Botón compartir en redes.
4. Referidos T10 usando patrón P10 adaptado.

## Certificación

Martha debe ver evento finalizado con fotos reales/demo controlado, galería visible, enlace compartible y código de referido T10 operativo.

---

# CARRILES POR PC

```text
PC II · BACKEND
  Todos los endpoints, tablas y lógica de negocio.
  Mensajería, calificaciones, traducción, grupos,
  calendario PAEM, referidos, matching, billing UI,
  WhatsApp integración y galería.

PC I · FRONTEND
  Todas las pantallas, componentes y flujos UI.
  Chat, estrellas, switch idioma, grupos UI,
  calendario visual, referidos UI, matching display,
  Panel Martha billing y galería grid.

PC I V2 · CERTIFICACIÓN
  SONAR cards mostrando estado real por entregable.
  Certificación visual cuando funcione end-to-end.

PC I V3 · FLOW GOVERNOR
  Monitorear avance de las 12 tareas.
  Detectar mock o hardcode.
  Mantener cola limpia.
  No abrir frentes fuera de estos 12.
```

---

# ORDEN DE EJECUCIÓN

## Bloque A · Mes 3 deuda · semana 1

1. Mensajería directa P10.
2. Calendario eventos T10 + PAEM.

## Bloque B · Mes 3 deuda · semana 2

3. Calificaciones bidireccionales.
4. Grupos temáticos T10.
5. Traducción bilingüe.

## Bloque C · Mes 4 · semana 3

6. Matching inteligente.
7. Referidos P10 + T10.
8. Pagos visibles, medicion_solo.

## Bloque D · Mes 4 · semana 4

9. Embudos Systeme.io.
10. Secuencias email.
11. Inscripción WhatsApp.
12. Galería post-evento.

---

# REGLA DE CERTIFICACIÓN

Cada entregable se certifica cuando:

1. Backend endpoint responde con datos reales, no mock.
2. Frontend muestra el resultado, no placeholder.
3. Test verifica el flujo end-to-end.
4. Martha puede verlo en su panel o en la plataforma.

Si un entregable no tiene persona real todavía:

```text
Vacío honesto + funcionalidad probada con demo controlado.
No inventar profesionales fake.
No inflar números.
No declarar piloto sin personas.
```

---

# VEREDICTO

El nervio se cierra primero. Después el dispatcher despacha estos 12 entregables como tasks reales del organismo. La prueba de vida no es una task canary read_only. La prueba de vida son 12 features prometidas, construidas, visibles y certificadas contra la propuesta.

```text
Lo que se propuso es lo que se certifica.
Martha ve features, no heartbeats.
```

**Somos Industrias ODI.**
