# ODI — Organismo Digital Industrial v18.1

## Paradigma

**Industria 5.0 aplicada** — Human-centric, Resiliente, Sostenible, Colaborativa.
ODI no es software. Es infraestructura industrial compartida para pymes colombianas.
Postgres manda. Redis acelera. JSON es fallback. El humano es co-piloto.

## Proyecto

**Empresa:** LA ROCA MOTOREPUESTOS (NIT: 10.776.560-1) — Pereira, Colombia
**Metodología:** ADSI (Arquitectura, Diseño, Sistemas e Implementación)
**Operador:** Juan David Jiménez
**Modelo de negocio:** Distribuidor híbrido de repuestos de motocicletas asistido por IA
**Marca comercial:** SRM (SomosRepuestosMotos) — ~5,750 SKUs, decenas de marcas

## Servidor de Producción

- **IP:** 64.23.170.118
- **SO:** Ubuntu 24 LTS
- **Proveedor:** DigitalOcean (~$24 USD/mes)
- **Acceso:** SSH root@64.23.170.118
- **Datos pesados:** /mnt/volume_sfo3_01/ (volumen externo)
- **Aplicación:** /opt/odi/
- **Variables de entorno:** /opt/odi/.env

### Docker Containers (9 activos)

| Container | Imagen | Puerto | Función |
|-----------|--------|--------|---------|
| odi-n8n | n8nio/n8n:latest | 5678 | Workflow engine (cerebro) |
| odi-voice | odi-odi_voice | 7777 (docker net) | Motor de voz ElevenLabs (Tony + Ramona) |
| odi-m62-fitment | odi-odi_m62_fitment | 8802 | Motor de compatibilidad motos |
| odi-paem-api | odi-paem-api | 8807 | PAEM API v2.3.0 (pagos, turismo, override) |
| odi-chat-api | uvicorn | 8813 | Chat API v1.1 (liveodi.com conversación + TTS) |
| odi-postgres | postgres:15 | 5432 | Base de datos transaccional + n8n |
| odi-redis | redis:alpine | 6379 | Cache, pub/sub eventos |
| odi-prometheus | prom/prometheus | 9090 | Métricas |
| odi-grafana | grafana/grafana | 3000 | Dashboards |

### Bases de Datos

- **PostgreSQL 15:** Datos transaccionales, estado n8n, auditoría cognitiva (odi_decision_logs, odi_user_state)
- **Redis Alpine:** Cache, pub/sub de eventos ODI
- **ChromaDB:** Embeddings semánticos, búsqueda vectorial (`/mnt/volume_sfo3_01/embeddings/kb_embeddings`, collection `odi_ind_motos`: 19,145 docs)

## Dominios y DNS

**Proveedor DNS:** IONOS (1&1)
**Inventario completo:** `IONOS_DOMAINS_INVENTORY.md`

### Dominios Principales

| Dominio | Uso | TLDs Adicionales |
|---------|-----|------------------|
| larocamotorepuestos.com | Negocio principal | .online, .info, .tienda |
| somosrepuestosmotos.com | Marca SRM | — |
| ecosistema-adsi.com | Plataforma ADSI | .tienda, .online, .info |
| liveodi.com | Interfaz ODI / VIVIR | .info, .online, .tienda |
| somosindustriasodi.com | Marca multi-industria | .info, .store, .online |
| cabezasanas.com | Vertical salud | .tienda, .online, .info |
| mis-cubiertas.com | Vertical cubiertas | — |
| matzudentalaesthetics.com | Turismo dental | — |

### DNS Crítico

| Subdominio | Destino | Uso |
|------------|---------|-----|
| odi.larocamotorepuestos.com | A → 64.23.170.118 | Webhook WhatsApp + n8n |
| api.liveodi.com | A → 64.23.170.118 | PAEM API v2.2.1 + WhatsApp API |
| ws.liveodi.com | A → 64.23.170.118 | WebSocket (voz) |
| catrmu.liveodi.com | A → 64.23.170.118 | Landing CATRMU |
| kaiqi.liveodi.com | A → 64.23.170.118 | Tienda Kaiqi |

### CATRMU Live (11 Feb 2026)

| Campo | Valor |
|-------|-------|
| URL | https://catrmu.liveodi.com |
| Paleta | Azul (#1e3a5f) → Negro (#0a0a0a) gradiente |
| Tipografía | Exo 2 Medium |
| Secciones | Origen, Gobernanza, Ingeniería |
| Deploy Path | /var/www/catrmu/ |
| Nginx Config | /etc/nginx/sites-available/catrmu |
| Commit | d80f415 (odi-vende repo) |

- **SSL:** Let's Encrypt, auto-renovación hasta mayo 2026
- **Reverse Proxy:** Nginx en servidor

## WhatsApp Business API

- **Número:** +57 322 5462101
- **WABA ID:** 1213578830922636
- **Phone Number ID:** 969496722915650
- **Meta App ID:** 875989111468824
- **Token:** System User permanente (odi-system)
- **Webhook:** https://odi.larocamotorepuestos.com/webhook/odi-ingest
- **Verificación Meta:** Aprobada 3 Feb 2026
- **Pipeline:** Cliente → Meta → HTTPS → Nginx → n8n (ODI_v6_CORTEX) → Cortex → Respuesta → WhatsApp

### Plantillas de Mensajes

| Nombre | Estado |
|--------|--------|
| hello_world | ✅ APROBADO |
| odi_saludo | ✅ APROBADO |
| odi_order_confirm_v2 | ✅ APROBADO |
| odi_order_status | ✅ APROBADO |
| odi_shipping_update | ✅ APROBADO |
| odi_contract_approval | ✅ APROBADO |

### Actores WhatsApp

| wa_id | actor_id | rol | permisos | modo_máximo |
|-------|----------|-----|----------|-------------|
| 573001234567 | ANDRES_VENTAS | VENTAS | SALE_CONFIRM | AUTOMATICO |
| 573009876543 | MARIA_SUPER | SUPERVISION | SALE_CONFIRM, SALE_APPROVE | SUPERVISADO |

## Inteligencia Artificial

| Proveedor | Servicio | Uso en ODI |
|-----------|----------|------------|
| OpenAI | GPT-4o | Cerebro principal, conversación, análisis |
| OpenAI | Embeddings | Vectores semánticos → ChromaDB |
| OpenAI | Vision (GPT-4o) | Extracción de catálogos PDF |
| Google | Gemini 1.5 Pro | Router semántico, backup, multimodal |
| ElevenLabs | TTS | Voz Tony Maestro + Ramona Anfitriona |
| Freepik | Image Gen | Imágenes de productos por IA |

**Failover:** Gemini → GPT → Lobotomy (respuesta mínima sin IA)

### Voces

- **Tony Maestro:** Voice ID `qpjUiwx7YUVAavnmh2sF` — diagnóstico, ejecución (S0-S4)
- **Ramona Anfitriona:** Voice ID `ZAQFLZQOmS9ClDGyVg6d` — hospitalidad, validación (S4-S6)
- **Container:** odi-voice (docker network 172.18.0.6:7777), speed 0.85, stability 0.65, multi-voice (VOICE_MAP)

## E-Commerce — Shopify (15 Tiendas) — 16,681 productos | 100% con precio (15 Feb 2026)

| # | Tienda | Dominio | Productos | Estado |
|---|--------|---------|:---------:|--------|
| 1 | Bara | 4jqcki-jq.myshopify.com | 698 | ✅ Active |
| 2 | Yokomar | u1zmhk-ts.myshopify.com | 1,000 | ✅ Active |
| 3 | Kaiqi | u03tqc-0e.myshopify.com | 138 | ✅ Active |
| 4 | DFG | 0se1jt-q1.myshopify.com | 7,441 | ✅ Active |
| 5 | Duna | ygsfhq-fs.myshopify.com | 1,200 | ✅ Active |
| 6 | Imbra | 0i1mdf-gi.myshopify.com | 1,131 | ✅ Active |
| 7 | Japan | 7cy1zd-qz.myshopify.com | 734 | ✅ Active |
| 8 | Leo | h1hywg-pq.myshopify.com | 120 | ✅ Active |
| 9 | Store | 0b6umv-11.myshopify.com | 66 | ✅ Active |
| 10 | Vaisand | z4fpdj-mz.myshopify.com | 50 | ✅ Active |

**Tienda dev:** somos-moto-repuestos-v95pc.myshopify.com
**Activación:** 14 Feb 2026 — `scripts/activate_all_stores.py` + `scripts/activate_drafts.py`

## Marketing & CRM — Systeme.io

- Academia SRM: 8 cursos, 42 lecciones
- CRM con segmentación de contactos
- Webhooks a n8n: wf_nuevo_usuario, wf_curso_completado
- Email marketing automatizado + membresías por niveles

## Frontend — Vercel Pro ($20/mes)

- Landing ADSI/ODI
- ODI-OS Dashboard (panel cognitivo)
- SRM Tablero (noticias por rol)

## Repositorio

- **GitHub:** juandavidjd/extrac
- **Branch principal:** claude/unify-repository-branches
- **Convención:** Código vía Git, datos pesados vía WinSCP al volumen del servidor

## Auditoría — Google Sheets

- **Proyecto GCP:** ODIPROJECT (gen-lang-client-0753622404)
- **Sheets ID:** 1KK-aUJ...G8aY
- Hojas: AUDITORIA, AUTONOMIA_SKU, RESUMEN
- KPIs: Total Operaciones, Ventas Autónomas, Intervenciones Martha, Índice Autonomía %, Capital Salvaguardado

## Arquitectura de Decisión (Principios Fundacionales)

- **Manifiesto ODI:** `MANIFIESTO_ODI.md` — Ley suprema del organismo
- **Artículo 0:** "ODI existe solo si puede auditar su propia ley"
- **"ODI decide sin hablar, habla solo cuando ya decidió"**
- **"La trazabilidad no depende de la voz"**
- **Triple Solidez:** Validación en 3 capas antes de ejecutar
- **Pulso Cognitivo:** Ciclos de procesamiento autónomo
- **Constitución:** MEO-ODI (Marco Ético), RA-ODI (Reglas Arquitectura), OMA (Ontología Mínima)
- La voz es accesoria, la auditoría es soberana
- Si la voz falla, la operación continúa
- **Componentes Excluidos del Núcleo:** Midjourney, Perplexity (no auditables)

## Flujos n8n Activos

| Flujo | Función |
|-------|---------|
| ODI_v6_CORTEX | Pipeline principal WhatsApp (ingest → intent → cortex → respuesta) — V8.1 integrado |
| ODI_GOBERNANZA_V1 | Gobernanza y control |
| ODI_T007_WhatsApp_v2 | WhatsApp saliente |
| ODI_T007_WhatsApp_Incoming | WhatsApp entrante |
| ODI_v16_9_3_LINUX_CERTIFIED | Flujo certificado Linux |
| ODI_Etapa_3_Autonomía_por_SKU | Autonomía decisional por producto |

## Clientes Piloto

| Cliente | Catálogo | Estado |
|---------|----------|--------|
| Bara Importaciones | 698 productos + 2,553 KB chunks en ChromaDB | ✅ ACTIVA en producción (14 Feb 2026) |
| Yokomar | 1,000 productos normalizados, embeddings generados | Listo para piloto |
| Vaisand | Tienda Shopify configurada | Listo para piloto |
| Industrias Leo | Tienda Shopify configurada | Listo para piloto |

## Intent Override Gate (Febrero 2026)

**Estado:** ✅ INTEGRADO en `/opt/odi/core/odi_core.py`
**Versión:** 1.2
**Tests:** 10/10 PASSED
**Documentación:** `intent_override_gate.py`, `INTENT_OVERRIDE_GATE.md`

### Niveles de Prioridad

| Nivel | Tipo | Ejemplo | Acción |
|-------|------|---------|--------|
| P0 | CRÍTICO/Seguridad | "urgencia", "policía" | Safety flow inmediato |
| P1 | Cambio industria | "emprender", "turismo" | Domain switch |
| P2 | Ajuste contexto | "no entiendo", "para ya" | Context adjust |
| P3 | Meta/Identidad | "quién eres", "eres más que eso" | Full reset |

### Bug Corregido

- **"Para tu ECO"**: ODI ya no responde con repuestos de motos a mensajes de turismo, emprendimiento o urgencias

## ODI V8.1 — Personalidad + Auditoría Cognitiva (14 Feb 2026)

**Estado:** ✅ CERTIFICADO 9/9 tests
**Reporte:** `reports/V81_CERTIFICATION_REPORT.md`
**Principio:** "ODI no solo decide. ODI rinde cuentas."

### Las 4 Dimensiones

| Dimensión | Qué define | Motor |
|-----------|-----------|-------|
| PERSONALIDAD | Quién es ODI (ADN inmutable, 7 genes) | `personalidad/adn.yaml` |
| ESTADO | Cómo se siente ODI (Guardian Layer: verde/amarillo/rojo/negro) | `core/odi_personalidad.py` |
| MODO | Cómo opera ODI (Automático/Supervisado/Custodio) | `core/odi_personalidad.py` |
| CARÁCTER | Cómo responde ODI (calibrado por usuario + industria + intimidad) | `core/odi_personalidad.py` |

### Estructura de Personalidad (`/opt/odi/personalidad/`)

| Archivo | Función |
|---------|---------|
| `adn.yaml` | 7 genes inmutables del organismo |
| `voz.yaml` | Tono, ritmo, reglas de voz |
| `niveles_intimidad.yaml` | 5 niveles: OBSERVADOR → CONOCIDO → CONFIDENTE → CUSTODIO → PUENTE |
| `verticales/p1_transporte.yaml` | Repuestos de motos (SRM) |
| `verticales/p2_salud.yaml` | Dental / Turismo médico (PAEM) |
| `verticales/p3_turismo.yaml` | Experiencias + Turismo médico |
| `verticales/p4_belleza.yaml` | Estética y bienestar |
| `perfiles/arquetipos.yaml` | 5 arquetipos: don_carlos, andres, lucia, dona_martha, diego |
| `guardian/etica.yaml` | Niveles éticos: verde/amarillo/rojo/negro + reglas de cobro |
| `guardian/red_humana.json` | Contactos de emergencia (106, 123, 125, 119) |
| `frases/prohibidas.yaml` | 10 frases chatbot bloqueadas + 3 de imitación |
| `frases/adn_expresado.yaml` | Frases constitucionales de ODI |

### Auditoría Cognitiva Nativa

| Componente | Ubicación | Función |
|------------|-----------|---------|
| Tabla SQL | `odi_decision_logs` (PostgreSQL) | 18 columnas, 7 índices, UUID PK |
| Tabla SQL | `odi_user_state` (PostgreSQL) | 15 columnas, estado persistente por usuario |
| Vista | `odi_audit_resumen` | Resumen por estado_guardian |
| Logger | `core/odi_decision_logger.py` | Async, asyncpg, SHA-256 con timestamp explícito, fallback JSON |
| Hook PAEM | `payments_api.py` v1.2.0 | Guardian evalúa ANTES de checkout Wompi |
| Hook Cortex | `odi_cortex_query.py` v2.1.0 | Guardian evalúa + prompt dinámico en RAG |
| Endpoint | `GET /personalidad/status` (8803) | Diagnóstico 4 dimensiones |
| Endpoint | `GET /audit/status` (8803) | Resumen auditoría desde PostgreSQL |
| Fallback | `/opt/odi/data/audit_fallback/` | JSON si PostgreSQL falla |

### Eventos Auditados

`PAY_INIT_AUTORIZADO`, `PAY_INIT_BLOQUEADO`, `VENTA_AUTORIZADA`, `VENTA_BLOQUEADA`, `ESTADO_CAMBIO_AMARILLO/ROJO/NEGRO`, `EMERGENCIA_ACTIVADA`, `MODO_CAMBIO`, `OVERRIDE_MANUAL`, `PRECIO_ANOMALO`

### Guardian Pre-Wompi (Hook en `/paem/pay/init`)

1. Guardian evalúa estado del usuario/transacción
2. Si estado != verde → 403 `guardian_block` + log `PAY_INIT_BLOQUEADO`
3. Si estado == verde → log `PAY_INIT_AUTORIZADO` + checkout Wompi normal
4. Fail-safe: si V8.1 falla internamente, el flujo existente continúa sin bloqueo

### Cortex Query v2.1.0 (Integración V8.1)

- Prompt dinámico reemplaza prompts estáticos Tony/Ramona (fallback preservado)
- `SemanticRouter.route()` mejorado con `detectar_vertical()` (P1→ind_motos, P2-P4→profesion)
- Guardian evalúa ANTES de generar respuesta RAG (NEGRO→emergencia, ROJO/AMARILLO→log)
- `query_async()` nuevo método async con Guardian + audit logging
- `GET /personalidad/status` — diagnóstico de las 4 dimensiones
- `GET /audit/status` — resumen auditoría desde PostgreSQL

### Hash SHA-256 — Fix de Integridad (14 Feb 2026)

- **Bug:** INSERT usaba `DEFAULT CURRENT_TIMESTAMP` pero hash se calculaba con timestamp Python → mismatch al verificar
- **Fix:** INSERT ahora incluye columna `timestamp` explícitamente con el mismo datetime usado para el hash
- **Resultado:** `verificar_integridad()` retorna `True` para todos los registros post-fix

### Tabla `odi_user_state`

Persiste nivel de intimidad, perfil, historial por usuario. 15 columnas, UUID PK, UNIQUE on usuario_id, CHECK nivel 0-4, trigger auto-update `updated_at`.

### n8n Workflow V8.1 — ODI_v6_CORTEX (14 Feb 2026)

**Archivo:** `odi_production/n8n/ODI_v6_CORTEX.json`
**Backup:** `odi_production/n8n/ODI_v6_CORTEX.v6-backup.json`

4 nodos modificados para integrar personalidad V8.1 en el flujo WhatsApp:

| Nodo | Cambio | Detalle |
|------|--------|---------|
| `cortex-query` | Body actualizado | `voice: "auto"`, `lobe: "auto"`, `usuario_id: $json.from` |
| `format-cortex` | Campos V8.1 extraídos | `guardian_estado`, `odi_event_id` del response Cortex |
| `general-response` | Frases prohibidas eliminadas | Reescrito con voz ODI nativa (sin "¿En qué puedo ayudarte?") |
| `prepare-api` | Objeto guardian en API | `guardian: { estado, odi_event_id }` en respuesta |

- `send-whatsapp` habilitado con credencial `wa-header-auth` (httpHeaderAuth)
- Credencial cifrada en n8n SQLite, token desde `WHATSAPP_TOKEN` env var
- Pipeline E2E verificado: webhook → intent → cortex → WhatsApp → entrega confirmada

### Knowledge Base ChromaDB — Todas las Tiendas (14 Feb 2026)

**Estado:** ✅ 19,145 DOCS EN PRODUCCIÓN
**Collection:** `odi_ind_motos` en ChromaDB
**Path:** `/mnt/volume_sfo3_01/embeddings/kb_embeddings`
**Embedding model:** `text-embedding-3-small` (OpenAI)
**Scripts:** `scripts/activate_bara.py`, `scripts/activate_all_embeddings.py`

| Fuente | Documentos |
|--------|:---------:|
| Manuales/Catálogos (KB chunks) | 2,553 |
| BARA | 698 |
| YOKOMAR | 1,000 |
| KAIQI | 138 |
| DFG | 7,445 |
| DUNA | 1,200 |
| IMBRA | 1,131 |
| JAPAN | 734 |
| LEO | 120 |
| STORE | 66 |
| VAISAND | 50 |
| ARMOTOS | 1,953 |
| CBI | 227 |
| MCLMOTOS | 349 |
| OH_IMPORTACIONES | 1,414 |
| VITTON | 67 |
| **Total** | **19,145** |

Cada producto indexado con: título, SKU, precio COP, sistema, categoría, proveedor, store.
Cada KB chunk indexado con: contenido, source_name, source_path, chunk_id.

Consideraciones de ingesta:
- Batches de 100 docs con 3s pausa entre batches (TPM OpenAI)
- Retry 5x con backoff 20s*attempt en rate limit 429
- Detección automática de stores ya ingestados (skip duplicados)

### Stress Test V8.1 — `/paem/pay/init` (14 Feb 2026)

**Estado:** ✅ PASSED
**Script:** `scripts/stress_v81.py`
**Reporte:** `reports/STRESS_TEST_V81.md`

| Ronda | Requests | Concurrencia | Throughput | P95 | Errores |
|-------|----------|-------------|-----------|-----|---------|
| R1 | 200 | 20 | 919 req/s | 28ms | 0 |
| R2 | 300 | 50 | 924 req/s | 88ms | 0 |

- 500 decision logs insertados en PostgreSQL, 0 perdidos
- 0 locks PostgreSQL detectados durante ejecución
- 10/10 hashes SHA-256 verificados correctamente
- Todos los requests retornaron 404 (pre-Wompi, montos altos → Guardian verde pero producto no existe)

## CASO 001 — Primera Venta Real (10 Feb 2026)

**Estado:** ✅ COMPLETADO
**Pedido:** #ODI-260210034547
**Producto:** 3 x LLANTA 110-70-13 TL V665 SEMIPISTERA YB
**Total:** $123,000 COP
**Canal:** WhatsApp (+57 322 5462101)

### Flujo Validado

1. Usuario solicita "llanta para ECO 100"
2. ODI presenta 5 opciones con precios
3. Usuario selecciona opción 3
4. Usuario confirma cantidad (3 unidades)
5. ODI calcula total y solicita confirmación
6. Pedido generado automáticamente

## ODI V8.2 — Override Humano Seguro (15 Feb 2026)

**Estado:** ✅ CERTIFICADO 4/4 tests (O1-O4)
**Principio:** "ROJO no se edita. ROJO se supera con huella humana."
**Commit:** `c69764c`

### Arquitectura

| Componente | Ubicación | Función |
|------------|-----------|---------|
| Override Engine | `core/odi_override.py` | JWT + TOTP validation, override execution, hash SHA-256 |
| Auth Login | `POST /odi/auth/login` (8807) | TOTP → JWT (TTL 10 min) |
| Override | `POST /odi/override` (8807) | JWT + TOTP → override encadenado |
| Status | `GET /odi/override/status` (8807) | Estado del sistema de overrides |
| Pay Override | `override_event_id` en `/paem/pay/init` | Bypass Guardian con autorización humana |
| Tabla SQL | `odi_humans` (PostgreSQL) | Humanos autorizados (role + TOTP secret) |
| Tabla SQL | `odi_overrides` (PostgreSQL) | Overrides con evidence + hash |
| Vista SQL | `odi_override_audit` | Auditoría de overrides con contexto original |
| Columnas | `prev_event_id`, `event_type` en `odi_decision_logs` | Encadenamiento de eventos |

### Roles y Permisos

| Rol | Override ROJO | Override AMARILLO | Escalar NEGRO | Vertical |
|-----|:---:|:---:|:---:|----------|
| ARQUITECTO | si | si | si | Todas (*) |
| SUPERVISOR | si | si | no | Asignada |
| CUSTODIO | si | si | no | Asignada |

### Reglas Inmutables

- NEGRO **nunca** se convierte en VERDE — solo `ESCALAMIENTO_NEGRO`
- Override crea **nuevo evento** enlazado al original (`prev_event_id`)
- El evento original **nunca se modifica**
- Hash SHA-256 inmutable por override
- JWT expira en 10 min (configurable: `ODI_OVERRIDE_TTL_MINUTES`)
- TOTP secret se muestra **solo una vez** al crear humano

### Decisiones Válidas

`VERDE_OVERRIDE_SUPERVISADO`, `AMARILLO_OVERRIDE_SUPERVISADO`, `ESCALAMIENTO_NEGRO`

### Humanos Registrados

| human_id | Nombre | Rol | Vertical |
|----------|--------|-----|----------|
| JD | Juan David Jiménez | ARQUITECTO | * |

### Tests Certificación

| Test | Descripción | Resultado |
|------|-------------|-----------|
| O1 | Override ROJO → VERDE con chain + hash DB | PASSED |
| O2 | Supervisor fuera de vertical → 403 | PASSED |
| O3 | NEGRO → VERDE → 403 "Solo ESCALAMIENTO" | PASSED |
| O4 | pay/init con override_event_id → no 403 | PASSED |

### Variables de Entorno V8.2

- `ODI_JWT_SECRET` — HMAC-SHA256 key (128 hex chars, nunca en logs)
- `ODI_JWT_ISSUER` — "odi"
- `ODI_OVERRIDE_ENABLED` — "true"
- `ODI_OVERRIDE_TTL_MINUTES` — "10"

## ODI V13 — liveodi.com Chat Conversacional (18 Feb 2026)

**Estado:** ✅ DEPLOYED
**Commit:** `12da68e`
**Principio:** "ODI no se usa. ODI se habita."

### Arquitectura

| Componente | Ubicación | Función |
|------------|-----------|---------|
| Chat API | `core/odi_chat_api.py` v1.1 (puerto 8813) | Backend conversacional FastAPI + Uvicorn |
| Frontend | `frontend/liveodi-chat/` (Vercel) | Next.js 15 + Tailwind CSS 4.0 |
| Nginx | `/etc/nginx/sites-enabled/liveodi` | Proxy api.liveodi.com/odi/chat → 8813 |

### URLs

| URL | Destino |
|-----|---------|
| https://liveodi.com | Frontend Vercel (Next.js) |
| https://api.liveodi.com/odi/chat | Chat API (servidor 8813) |
| https://api.liveodi.com/odi/chat/health | Health check |
| https://api.liveodi.com/odi/chat/speak | TTS endpoint (V13.1) |

### Chat API Endpoints

| Método | Path | Función |
|--------|------|---------|
| POST | `/odi/chat` | Enviar mensaje, recibir respuesta ODI |
| GET | `/odi/chat/health` | Health check |
| POST | `/odi/chat/speak` | TTS — texto a audio MP3 (V13.1) |

### Frontend (Vercel)

- **Proyecto:** liveodi-chat
- **Framework:** Next.js 15.5.12 + Tailwind CSS 4.0
- **Deploy:** Vercel Pro (auto-deploy desde GitHub no configurado, deploy manual con `vercel --prod`)
- **Dominio:** liveodi.com → Vercel
- **Scope:** juan-david-jimenez-sierras-projects

## ODI V13.1 — Voz + Llama + Presencia (18 Feb 2026)

**Estado:** ✅ DEPLOYED (Tests V1-V6 PASSED)
**Principio:** "La presencia se siente antes de hablar."

### Voz ElevenLabs (TTS)

- **Endpoint:** `/odi/chat/speak` (proxy a odi-voice container 172.18.0.6:7777)
- **Selección automática:** `seleccionar_voz()` en odi_chat_api.py
  - Primera interacción → Ramona (hospitalidad)
  - Productos encontrados → Tony (técnico)
  - Keywords precio/stock/envío → Tony
  - Default → Ramona
- **Container odi-voice:** VOICE_MAP con Tony + Ramona, stability 0.65
- **Audio ADITIVO:** Si TTS falla, el texto sigue funcionando (audio_enabled en response)
- **Mute:** Persiste en localStorage (`odi_muted`)

### FlameIndicator (Canvas)

- **Componente:** `components/FlameIndicator.tsx`
- **Técnica:** Canvas puro (sin bibliotecas), requestAnimationFrame
- **Animación:** Respiración sinusoidal (normal), pulso rápido (thinking), rítmico (speaking)
- **Colores:** verde=#10B981, amarillo=#F59E0B, rojo=#EF4444, negro=#6B7280
- **Tamaños:** Landing 120px, Chat header 32px, Empty state 64px

### Frontend V13.1

| Archivo | Cambio |
|---------|--------|
| `lib/useODIVoice.ts` | Hook de audio: fetch /odi/chat/speak → blob → Audio |
| `components/FlameIndicator.tsx` | Canvas llama respiratoria |
| `components/ChatContainer.tsx` | Integra voz, llama, mute toggle |
| `lib/api.ts` | voice + audio_enabled en ChatResponse |
| `app/page.tsx` | FlameIndicator 120px en landing |
| `app/globals.css` | Oculta toolbar Vercel |
| `vercel.json` | cleanUrls |

### Tests V13.1

| Test | Descripción | Resultado |
|------|-------------|-----------|
| V1 | TTS Ramona genera MP3 | ✅ PASSED |
| V2 | TTS Tony genera MP3 | ✅ PASSED |
| V3 | Chat con productos → voice=tony, audio_enabled=true | ✅ PASSED |
| V4 | Primer mensaje → voice=ramona | ✅ PASSED |
| V5 | No toolbar Vercel en producción | ✅ PASSED |
| V6 | Canvas elements presentes en frontend | ✅ PASSED |

## PAEM — Protocolo de Activación Económica Multindustria

**Estado:** v2.3.0 ✅ DEPLOYED (15 Feb 2026)
**Spec completa:** `docs/PAEM_API_v2_2_1_SPEC.md`
**API URL:** https://api.liveodi.com/paem/*
**Pagos:** Wompi (checkout público, COP, amount_in_cents)

### Módulo Turismo (IMPLEMENTADO — core/industries/turismo/)

| Componente | Archivo | Función |
|------------|---------|---------|
| UDM-T | udm_t.py | Objeto canónico universal inter-industria |
| Router 3-tier | industry_router.py | Redis → Postgres → JSON → demo |
| Engine | tourism_engine.py | Orquestador viabilidad → plan |
| Entertainment | entertainment_adapter.py | Terapia de entorno (recovery_level) |
| Hospitality | hospitality_adapter.py | Hospedaje recovery-friendly |
| Lead Scoring | lead_scoring.py | ALTA/MEDIA/BAJA + reasons |
| DB Client | db/client.py | Pool Postgres + Redis (graceful) |
| Sync Job | db/sync_job.py | Postgres → Redis (cron) |
| API Routes | api_routes.py | /tourism/* endpoints |

### Health Census (IMPLEMENTADO — Postgres)

Migraciones en `data/turismo/migrations/`:
- `V001_health_census.sql` — Schema completo (7 tablas + vista + función)
- `V002_seed_demo_data.sql` — 3 nodos, 9 certs, 6 entretenimiento, 4 hospedaje

### PAEM v2.3.0 (✅ DEPLOYED — 15 Feb 2026)

- ✅ HOLD automático de slots clínicos (15 min TTL)
- ✅ POST /paem/confirm con confirmación atómica
- ✅ POST /paem/pay/init — Checkout Wompi + Guardian V8.1 + Override V8.2
- ✅ POST /odi/auth/login — Login humano (TOTP → JWT)
- ✅ POST /odi/override — Override humano seguro (JWT + TOTP)
- ✅ GET /odi/override/status — Estado overrides
- ✅ Rate limiting por IP via Redis
- ✅ Event sourcing (odi_events)
- ✅ Puerto 8807 (odi-paem-api) → https://api.liveodi.com

### Industria 5.0/6.0/7.0

Documentación completa: `docs/ODI_INDUSTRIA_5_0_7_0.md`

## Prioridades (Febrero 2026)

1. ~~**CRÍTICA:** Aprobar 5 plantillas WhatsApp en Meta~~ ✅ COMPLETADO
2. ~~**CRÍTICA:** Intent Override Gate~~ ✅ DEPLOYED
3. ~~**CRÍTICA:** Ejecutar Caso 001 (primera venta real)~~ ✅ COMPLETADO
4. ~~**ALTA:** Activar Turismo Odontológico (segundo vertical)~~ ✅ PAEM v2.0 IMPLEMENTADO
5. ~~**ALTA:** Ejecutar SQL Health Census en servidor + activar API turismo~~ ✅ COMPLETADO
6. ~~**ALTA:** Implementar PAEM v2.2.1 (HOLD + confirm + rate limit)~~ ✅ DEPLOYED 14 Feb 2026
7. ~~**ALTA:** V8.1 Personalidad + Auditoría Cognitiva~~ ✅ CERTIFICADO 9/9 — 14 Feb 2026
8. ~~**ALTA:** Activar BARA en ChromaDB + E2E WhatsApp~~ ✅ 3,251 docs + WhatsApp live — 14 Feb 2026
9. ~~**ALTA:** Stress Test V8.1 /paem/pay/init~~ ✅ 500 req, 0 errores, 10/10 hashes — 14 Feb 2026
10. ~~**ALTA:** Integrar V8.1 en workflow n8n ODI_v6_CORTEX~~ ✅ 4 nodos + WhatsApp creds — 14 Feb 2026
11. ~~**MEDIA:** Activar productos Shopify draft → active~~ ✅ 12,578 productos en 10 tiendas — 14 Feb 2026
12. ~~**MEDIA:** Asignar Voice ID de Ramona en ElevenLabs~~ ✅ ZAQFLZQOmS9ClDGyVg6d — 18 Feb 2026
13. ~~**MEDIA:** Activar todas las tiendas en ChromaDB~~ ✅ 19,145 docs (14 proveedores) — 14 Feb 2026
14. **BAJA:** Configurar Groq como tercer failover IA
15. ~~**ALTA:** V13 — liveodi.com Chat API + Frontend Vercel~~ ✅ DEPLOYED 18 Feb 2026
16. ~~**ALTA:** V13.1 — Voz ElevenLabs + Llama Canvas + Presencia~~ ✅ DEPLOYED 18 Feb 2026

## Convenciones de Código

- **Python:** Scripts de procesamiento, Flask APIs, ChromaDB
- **TypeScript:** Módulos de frontend (Vercel)
- **n8n:** Orquestación de workflows (JSON exportable)
- **Tokens:** Nunca exponer completos. Formato truncado: sk_xxxx...xxxx
- **Credenciales:** Siempre en /opt/odi/.env, nunca en código fuente
- **.env.template:** Versión sanitizada en el repo

## Comandos Útiles del Servidor

```bash
# Estado de containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Logs de n8n
docker logs odi-n8n --tail 50 -f

# Logs de voz
docker logs odi-voice --tail 50 -f

# Reiniciar todo
cd /opt/odi && docker compose down && docker compose up -d

# Test webhook WhatsApp
curl -X POST https://odi.larocamotorepuestos.com/webhook/odi-ingest \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"573001234567","text":{"body":"test"}}]}}]}]}'

# Test voz
curl -X POST http://localhost:7777/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"Operación registrada con éxito","voice":"tony"}'

# Estado SSL
sudo certbot certificates

# Espacio en disco
df -h && docker system df
```
