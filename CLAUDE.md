# ODI — Organismo Digital Industrial v17.5

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

### Docker Containers (7 activos)

| Container | Imagen | Puerto | Función |
|-----------|--------|--------|---------|
| odi-n8n | n8nio/n8n:latest | 5678 | Workflow engine (cerebro) |
| odi-voice | odi-odi_voice | 7777 | Motor de voz ElevenLabs |
| odi-m62-fitment | odi-odi_m62_fitment | 8802 | Motor de compatibilidad motos |
| odi-postgres | postgres:15 | 5432 | Base de datos transaccional + n8n |
| odi-redis | redis:alpine | 6379 | Cache, pub/sub eventos |
| odi-prometheus | prom/prometheus | 9090 | Métricas |
| odi-grafana | grafana/grafana | 3000 | Dashboards |

### Bases de Datos

- **PostgreSQL 15:** Datos transaccionales, estado n8n
- **Redis Alpine:** Cache, pub/sub de eventos ODI
- **ChromaDB:** Embeddings semánticos, búsqueda vectorial (en /opt/odi/)

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
- **Ramona Anfitriona:** Pendiente asignar Voice ID — hospitalidad, validación (S4-S6)
- **Container:** odi-voice (puerto 7777), speed 0.85, stability 0.65

## E-Commerce — Shopify (10 Tiendas)

| # | Tienda | Dominio |
|---|--------|---------|
| 1 | Bara | 4jqcki-jq.myshopify.com |
| 2 | Yokomar | u1zmhk-ts.myshopify.com |
| 3 | Kaiqi | u03tqc-0e.myshopify.com |
| 4 | DFG | 0se1jt-q1.myshopify.com |
| 5 | Duna | ygsfhq-fs.myshopify.com |
| 6 | Imbra | 0i1mdf-gi.myshopify.com |
| 7 | Japan | 7cy1zd-qz.myshopify.com |
| 8 | Leo | h1hywg-pq.myshopify.com |
| 9 | Store | 0b6umv-11.myshopify.com |
| 10 | Vaisand | z4fpdj-mz.myshopify.com |

**Tienda dev:** somos-moto-repuestos-v95pc.myshopify.com
**Estado productos:** DRAFT (pendiente activar para Caso 001)

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
| ODI_v6_CORTEX | Pipeline principal WhatsApp (ingest → intent → cortex → respuesta) |
| ODI_GOBERNANZA_V1 | Gobernanza y control |
| ODI_T007_WhatsApp_v2 | WhatsApp saliente |
| ODI_T007_WhatsApp_Incoming | WhatsApp entrante |
| ODI_v16_9_3_LINUX_CERTIFIED | Flujo certificado Linux |
| ODI_Etapa_3_Autonomía_por_SKU | Autonomía decisional por producto |

## Clientes Piloto

| Cliente | Catálogo | Estado |
|---------|----------|--------|
| Bara Importaciones | Tienda Shopify configurada | Listo para piloto |
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

## Prioridades (Febrero 2026)

1. ~~**CRÍTICA:** Aprobar 5 plantillas WhatsApp en Meta~~ ✅ COMPLETADO
2. ~~**CRÍTICA:** Intent Override Gate~~ ✅ DEPLOYED
3. ~~**CRÍTICA:** Ejecutar Caso 001 (primera venta real)~~ ✅ COMPLETADO
4. **ALTA:** Activar Turismo Odontológico (segundo vertical)
5. **MEDIA:** Activar productos Shopify draft → active
6. **MEDIA:** Asignar Voice ID de Ramona en ElevenLabs
7. **BAJA:** Configurar Groq como tercer failover IA

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
