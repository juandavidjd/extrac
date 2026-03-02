# ODI — Organismo Digital Industrial v25+

## REGLAS CONSTITUCIONALES (LEER SIEMPRE PRIMERO)

### Regla 1: Leer antes de escribir
**ANTES de escribir CUALQUIER código, lee estos archivos:**
- `/opt/odi/core/middleware.py`
- `/opt/odi/core/enforcement_engine.py`
- `/opt/odi/core/ficha_engine.py`

Si no los lees primero, vas a generar scripts sueltos que violan la arquitectura.

### Regla 2: Zero scripts sueltos
**NUNCA crear scripts independientes** tipo `fix_X.py`, `patch_Y.py`, `quick_Z.py`.
Todo cambio a productos Shopify DEBE pasar por Enforcement Engine.
Todo enriquecimiento de fichas DEBE pasar por FichaEngine.
Si no existe la función que necesitas en el engine, REPÓRTALO. No la inventes como script aparte.

**Contexto:** El 22 Feb 2026, un script suelto (PriceRescue) estimó precios y activó 1,688 productos en 5 tiendas antes de ser revertido. Esa es la razón de esta regla.

### Regla 3: Diagnóstico antes de ejecución
Cuando una orden dice "solo diagnóstico" o "solo reportar":
- NO modificar datos en Shopify
- NO crear productos
- NO actualizar campos
- NO ejecutar writes de ningún tipo
- Solo leer, contar, y reportar

### Regla 4: Verificación proactiva
Después de CUALQUIER cambio en Shopify, verificar con curl a la URL pública del storefront.
No basta con que la API responda 200. Si no se ve el cambio en el navegador, no está hecho.

```bash
# Verificación correcta (storefront público)
curl -s "https://DOMINIO.myshopify.com/products/HANDLE" | grep "TEXTO_ESPERADO"

# Verificación insuficiente (solo API)
curl -s -H "X-Shopify-Access-Token: TOKEN" "https://DOMINIO/admin/api/..."
# ↑ Esto solo NO es suficiente
```

### Regla 5: No tocar lo que no te pidieron
Si la orden dice "solo BARA", no toques IMBRA.
Si la orden dice "solo beneficios", no toques títulos.
Si la orden dice "solo diagnóstico", no ejecutes correcciones.
Cada ventana tiene un scope definido. Respétalo.

### Regla 6: Reportar antes de actuar
Si encuentras un problema que no está en la orden, REPÓRTALO.
No lo corrijas por tu cuenta. Juan David decide si se corrige y cuándo.

---

## Proyecto

**Empresa:** LA ROCA MOTOREPUESTOS (NIT: 10.776.560-1) — Pereira, Colombia
**Metodología:** ADSI (Arquitectura, Diseño, Sistemas e Implementación)
**Operador:** Juan David Jiménez
**Modelo de negocio:** Distribuidor híbrido de repuestos de motocicletas asistido por IA
**Marca comercial:** SRM (SomosRepuestosMotos) — ~13,766 SKUs activos, 8 tiendas governed

## Servidor de Producción

- **IP:** 64.23.170.118
- **SO:** Ubuntu 22.04 LTS
- **Proveedor:** DigitalOcean (~$96 USD/mes)
- **RAM:** 16GB, 8 vCPU AMD, 80GB disco + 200GB vol externo
- **Acceso:** SSH root@64.23.170.118
- **Datos pesados:** /mnt/volume_sfo3_01/ (volumen externo)
- **Aplicación:** /opt/odi/
- **Variables de entorno:** /opt/odi/.env
- **Core code:** /opt/odi/core/

### Docker Containers (8+ activos)

| Container | Puerto | Función |
|-----------|--------|---------|
| odi-n8n | 5678 | Workflow engine (WhatsApp, Shopify orders) |
| odi-voice | 7777 | Motor de voz ElevenLabs |
| odi-m62-fitment | 8802 | Motor de compatibilidad motos |
| odi-postgres | 5432 | Base de datos transaccional |
| odi-redis | 6379 | Cache, pub/sub eventos |
| odi-prometheus | 9090 | Métricas |
| odi-grafana | 3000 | Dashboards |

### Servicios systemd (no Docker)

| Servicio | Puerto | Función |
|----------|--------|---------|
| Chat API | 8813 | Cerebro conversacional (LLM + ChromaDB + productos) |
| Gateway | 8815 | API Gateway público |
| ChromaDB | 8000 | Embeddings semánticos |
| Cortex | 8803 | Pipeline de procesamiento |

## API Principal

**Endpoint:** `POST https://api.liveodi.com/odi/chat` (NO /odi/v1/chat)
**Interno desde Docker:** `POST http://172.17.0.1:8813/odi/chat`

Contrato de respuesta:
```json
{
  "response": "texto",
  "productos": [],
  "mode": "commerce|care|build|diagnose|empower|optimize|learn",
  "voice": "ramona|tony",
  "industry": "motos",
  "guardian_color": "verde",
  "from": "DFG MOTOS",
  "follow": "pregunta de seguimiento",
  "company_identity": {}
}
```

## WhatsApp Business API

- **Número:** +57 322 5462101
- **WABA ID:** 1213578830922636
- **Phone Number ID:** 969496722915650
- **Webhook Meta:** https://odi.larocamotorepuestos.com/v1/webhook/whatsapp
- **Pipeline:** Meta → Nginx → n8n (ODI_WHATSAPP_INCOMING_V3) → Chat API :8813 → WhatsApp
- **Token:** en $WHATSAPP_TOKEN (env var de n8n)

### Plantillas de Mensajes

| Nombre | Estado |
|--------|--------|
| hello_world | APROBADO |
| odi_saludo | APROBADO |
| odi_order_confirm_v2 | APROBADO |
| odi_order_status | APROBADO |
| odi_shipping_update | APROBADO |
| odi_contract_approval | APROBADO |

## Inteligencia Artificial

| Proveedor | Servicio | Uso en ODI |
|-----------|----------|------------|
| OpenAI | GPT-4o | Cerebro principal, conversación |
| OpenAI | Embeddings | ChromaDB vectores semánticos |
| OpenAI | Vision | Extracción catálogos PDF |
| Google | Gemini 1.5 Pro | Router semántico, backup |
| ElevenLabs | TTS | Tony (qpjUiwx7YUVAavnmh2sF) + Ramona (ZAQFLZQOmS9ClDGyVg6d) |
| Freepik | Image Gen | Imágenes productos por IA |

**Failover:** Gemini → GPT → Lobotomy

### Voces

- **Tony Maestro:** Voice ID `qpjUiwx7YUVAavnmh2sF` — diagnóstico, ejecución (S0-S4)
- **Ramona Anfitriona:** Voice ID `ZAQFLZQOmS9ClDGyVg6d` — hospitalidad, validación (S4-S6)
- **Container:** odi-voice (puerto 7777), speed 0.85, stability 0.65

## E-Commerce — Shopify (15 Tiendas, 8 Governed)

### Tiendas Governed (activas)

| Tienda | Dominio | Active | Grade | Token env var |
|--------|---------|--------|-------|---------------|
| ARMOTOS | znxx5p-10.myshopify.com | 1,543 | B+ | SHOPIFY_ARMOTOS_TOKEN |
| BARA | 4jqcki-jq.myshopify.com | 908 | A (6/7) | SHOPIFY_BARA_TOKEN |
| DFG | 0se1jt-q1.myshopify.com | 7,445 | F | SHOPIFY_DFG_TOKEN |
| IMBRA | 0i1mdf-gi.myshopify.com | 1,098 | C (4/7) | SHOPIFY_IMBRA_TOKEN |
| KAIQI | u03tqc-0e.myshopify.com | 361 | D | SHOPIFY_KAIQI_TOKEN |
| MCLMOTOS | v023qz-8x.myshopify.com | 249 | D | SHOPIFY_MCLMOTOS_TOKEN |
| VITTON | hxjebc-it.myshopify.com | 1,265 | C | SHOPIFY_VITTON_TOKEN |
| YOKOMAR | u1zmhk-ts.myshopify.com | 1,451 | C (3/7) | SHOPIFY_YOKOMAR_TOKEN |

### Tiendas Legacy/Pendientes

| Tienda | Dominio |
|--------|---------|
| CBI | yrf6hp-f6.myshopify.com |
| DUNA | ygsfhq-fs.myshopify.com |
| JAPAN | 7cy1zd-qz.myshopify.com |
| LEO | h1hywg-pq.myshopify.com |
| OH_IMPORTACIONES | 6fbakq-sj.myshopify.com |
| STORE | 0b6umv-11.myshopify.com |
| VAISAND | z4fpdj-mz.myshopify.com |

## Estándar A+ Universal — 7 Gates

Todo producto en Shopify debe pasar estos 7 gates antes de activarse:

1. **Título** ≤80 chars, descriptivo
2. **Descripción** con ficha ODI (>50 chars, técnica)
3. **Compatibilidad** con motos específicas
4. **Categoría** real (no "Default")
5. **Beneficios** específicos por tipo de pieza (no genéricos)
6. **Imagen** presente y de calidad
7. **Precio** coherente (>200, <500,000 COP)

**Enforcement Engine es el ÚNICO gateway a Shopify.** Nada se publica sin pasar por él.

## Dominios y DNS

| Dominio | Uso |
|---------|-----|
| liveodi.com | Frontend principal (Vercel, cycle-nexus-pro) |
| api.liveodi.com | Chat API público |
| larocamotorepuestos.com | Negocio principal |
| odi.larocamotorepuestos.com | Webhooks (WhatsApp, Shopify) |
| somosrepuestosmotos.com | Marca SRM (Vercel) |
| ecosistema-adsi.com | Plataforma ADSI |

## Arquitectura de Archivos Core (Servidor)

```
/opt/odi/core/
├── middleware.py          # OrganismoMiddleware — sistema nervioso central
├── enforcement_engine.py  # Único gateway a Shopify
├── ficha_engine.py        # Generador de fichas técnicas
├── odi_chat_api.py        # Chat API :8813
├── odi_gateway.py         # Gateway :8815
├── governed_stores.json   # Config 8 tiendas governed
└── ...
```

## Arquitectura de Archivos Core (Repositorio)

```
extrac/
├── core/
│   ├── pii_redactor.py        # Redacción PII para logging
│   └── security_guard.py      # Hardening y permisos
├── odi_production/
│   ├── api/main.py            # API unificada ODI v1.0
│   ├── config/odi_config.yaml # Configuración central
│   ├── core/
│   │   ├── odi_pipeline_service.py   # Pipeline 6 etapas
│   │   ├── odi_business_daemon.py    # File watcher auto-trigger
│   │   ├── odi_cortex_query.py       # Router semántico multi-lobe
│   │   ├── odi_event_emitter.py      # Event bus WebSocket
│   │   ├── odi_kb_indexer.py         # Indexador ChromaDB
│   │   ├── odi_kb_query.py           # Búsqueda semántica KB
│   │   └── odi_feedback_loop.py      # Feedback + webhooks
│   ├── extractors/                   # Extractores de datos
│   └── services/                     # Archivos systemd
└── ...
```

## n8n Workflows Activos

| Workflow | Función |
|---------|---------|
| ODI_WHATSAPP_INCOMING_V3 | WhatsApp entrante → Chat API → respuesta |
| ODI_SHOPIFY_ORDER_HANDLER | Órdenes pagadas Shopify |
| ODI_v6_CORTEX_V16 | Pipeline ingest |

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

## Repositorios

- **GitHub:** juandavidjd/odi-vende (main, código core)
- **Legacy:** juandavidjd/extrac
- **Frontend:** cycle-nexus-pro (Vercel)
- **Datos pesados:** vía WinSCP al volumen del servidor

## Frontend — Vercel Pro ($20/mes)

- Landing ADSI/ODI
- ODI-OS Dashboard (panel cognitivo)
- SRM Tablero (noticias por rol)

## Auditoría — Google Sheets

- **Proyecto GCP:** ODIPROJECT (gen-lang-client-0753622404)
- **Sheets ID:** 1KK-aUJ...G8aY
- Hojas: AUDITORIA, AUTONOMIA_SKU, RESUMEN
- KPIs: Total Operaciones, Ventas Autónomas, Intervenciones Martha, Índice Autonomía %, Capital Salvaguardado

## Convenciones de Código

- **Python:** Scripts de procesamiento, Flask/FastAPI APIs, ChromaDB
- **TypeScript:** Módulos de frontend (Vercel)
- **n8n:** Orquestación de workflows (JSON exportable)
- **Tokens:** Nunca exponer completos. Formato truncado: sk_xxxx...xxxx
- **Credenciales:** Siempre en /opt/odi/.env, nunca en código fuente
- **.env.template:** Versión sanitizada en el repo

## Comandos Útiles

```bash
# Estado containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Logs n8n
docker logs odi-n8n --tail 50 -f

# Test Chat API
curl -s -X POST http://localhost:8813/odi/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"filtro aceite Pulsar 200","session_id":"test"}'

# Test WhatsApp webhook
curl -s "https://odi.larocamotorepuestos.com/webhook/whatsapp-incoming?hub.mode=subscribe&hub.verify_token=odi_whatsapp_verify_2026&hub.challenge=test"

# Contar productos tienda
curl -s -H "X-Shopify-Access-Token: TOKEN" \
  "https://DOMINIO.myshopify.com/admin/api/2024-10/products/count.json?status=active"

# Estado SSL
sudo certbot certificates

# Espacio disco
df -h && docker system df
```
