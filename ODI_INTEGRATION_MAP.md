# MAPA DE INTEGRACIONES
## Organismo Digital Industrial
### ODI v17.2 — La Roca Motorepuestos / ADSI
### 5 de febrero de 2026

> Documento confidencial — Uso interno ADSI

---

## 1. Resumen Ejecutivo

Este documento cataloga todas las plataformas, servicios y APIs integradas en el ecosistema ODI (Organismo Digital Industrial) operado por ADSI para La Roca Motorepuestos. El sistema funciona como un distribuidor híbrido asistido por IA para la industria colombiana de repuestos de motocicletas.

El ecosistema comprende **19 plataformas externas**, **7 contenedores Docker**, **10 tiendas Shopify** y **3 dominios activos**, orquestados a través de n8n como cerebro de automatización y conectados mediante WhatsApp Business API como canal principal de comunicación con clientes.

| Categoría | Cantidad | Estado General |
|-----------|----------|----------------|
| Plataformas de IA | 4 | ● ACTIVO |
| Servicios de Voz | 1 | ● ACTIVO |
| Generación de Imágenes | 1 | ● ACTIVO |
| Comunicación (WhatsApp) | 1 | ● OPERATIVO |
| E-Commerce (Shopify) | 10 tiendas | ◐ PARCIAL |
| Marketing/CRM (Systeme.io) | 1 | ● CONFIGURADO |
| Hosting/Deploy (Vercel) | 1 | ● CONFIGURADO |
| Infraestructura (DigitalOcean) | 1 servidor | ● OPERATIVO |
| Dominios (IONOS) | 3 dominios | ● ACTIVO |
| Base de Datos | 3 (Postgres, Redis, ChromaDB) | ● OPERATIVO |
| Monitoreo | 2 (Prometheus, Grafana) | ● OPERATIVO |
| Auditoría (Google Sheets) | 1 | ● ACTIVO |
| Repositorio (GitHub) | 1 | ● ACTIVO |

---

## 2. Inteligencia Artificial

ODI utiliza múltiples modelos de IA con estrategia de failover: Gemini como router semántico principal, GPT-4o como cerebro de análisis y conversación, y OpenAI Embeddings para búsqueda vectorial en ChromaDB.

| Proveedor | Servicio | Uso en ODI | Estado |
|-----------|----------|------------|--------|
| OpenAI | GPT-4o | Cerebro principal, conversación, análisis | ● ACTIVO |
| OpenAI | Embeddings | Vectores semánticos, ChromaDB | ● ACTIVO |
| OpenAI | Vision (GPT-4o) | ODI Vision: extracción de catálogos PDF | ● ACTIVO |
| Google | Gemini 1.5 Pro | Router semántico, backup, multimodal | ● ACTIVO |
| Anthropic | Claude (externo) | Arquitectura, documentos, ética | ● ACTIVO |
| Groq | Llama 3.1 70B | Tareas rápidas, bajo costo | ○ PENDIENTE |

**Estrategia de failover:** Gemini → GPT → Lobotomy (respuesta mínima sin IA).

---

## 3. Voz e Imagen

### 3.1 ElevenLabs — Motor de Voz

Sistema de dualidad vocal: **Tony Maestro** (diagnóstico, ejecución) y **Ramona Anfitriona** (hospitalidad, validación). La voz se selecciona automáticamente según el estado conversacional (S0–S6).

| Componente | Detalle | Estado |
|------------|---------|--------|
| Voice ID (Tony) | qpjUiwx7YUVAavnmh2sF | ● ACTIVO |
| Voice ID (Ramona) | Pendiente asignar | ○ PENDIENTE |
| Container | odi-voice (puerto 7777) | ● OPERATIVO |
| Speed / Stability | 0.85 / 0.65 | ● CONFIGURADO |
| Handoff Tony→Ramona | Automático en S4→S5 | ● ACTIVO |

### 3.2 Freepik — Generación de Imágenes

Genera imágenes de productos por IA para publicación automática en Shopify. Integrado con el motor CES (ético) que valida claims antes de publicar.

| Componente | Detalle | Estado |
|------------|---------|--------|
| Flujo | Prompt → Freepik → CES → Shopify | ● ACTIVO |
| Uso | Imágenes de productos generadas por IA | ● ACTIVO |

---

## 4. WhatsApp Business API

Canal principal de comunicación con clientes. Pipeline bidireccional completo operativo desde el 5 de febrero de 2026. Primer mensaje automático enviado a las 12:26 AM.

| Componente | Detalle | Estado |
|------------|---------|--------|
| Número | +57 322 5462101 | ● OPERATIVO |
| Cuenta | La Roca Motorepuestos | ● ACTIVO |
| WABA ID | 1213578830922636 | ● ACTIVO |
| Phone Number ID | 969496722915650 | ● ACTIVO |
| Meta App ID | 875989111468824 | ● ACTIVO |
| Token | System User (permanente, odi-system) | ● ACTIVO |
| Webhook URL | https://odi.larocamotorepuestos.com/webhook/odi-ingest | ● OPERATIVO |
| SSL | Let's Encrypt (auto-renovación) | ● ACTIVO |
| Verificación Meta | Aprobada (3 Feb 2026) | ● ACTIVO |
| Método de pago | VISA *5177 | ● CONFIGURADO |

### 4.1 Plantillas de Mensajes

| Nombre | Categoría | Estado |
|--------|-----------|--------|
| odi_saludo | Utilidad | ◐ EN REVISIÓN |
| odi_order_confirm_v2 | Utilidad | ◐ EN REVISIÓN |
| odi_order_status | Utilidad | ◐ EN REVISIÓN |
| odi_shipping_update | Utilidad | ◐ EN REVISIÓN |
| odi_contract_approval | Utilidad | ◐ EN REVISIÓN |
| hello_world | Utilidad | ● ACTIVO |

**Pipeline:** WhatsApp → Meta → HTTPS → Nginx → n8n (ODI_v6_CORTEX) → Cortex → Respuesta → WhatsApp

---

## 5. E-Commerce — Shopify (10 Tiendas)

Arquitectura multi-tenant con 10 tiendas Shopify, cada una representando un proveedor/marca del ecosistema SRM. Productos actualmente en estado draft, pendientes de activación para Caso 001.

| # | Tienda | Dominio Shopify | Estado |
|---|--------|-----------------|--------|
| 1 | Bara | 4jqcki-jq.myshopify.com | ● CONFIGURADO |
| 2 | Yokomar | u1zmhk-ts.myshopify.com | ● CONFIGURADO |
| 3 | Kaiqi | u03tqc-0e.myshopify.com | ● CONFIGURADO |
| 4 | DFG | 0se1jt-q1.myshopify.com | ● CONFIGURADO |
| 5 | Duna | ygsfhq-fs.myshopify.com | ● CONFIGURADO |
| 6 | Imbra | 0i1mdf-gi.myshopify.com | ● CONFIGURADO |
| 7 | Japan | 7cy1zd-qz.myshopify.com | ● CONFIGURADO |
| 8 | Leo | h1hywg-pq.myshopify.com | ● CONFIGURADO |
| 9 | Store | 0b6umv-11.myshopify.com | ● CONFIGURADO |
| 10 | Vaisand | z4fpdj-mz.myshopify.com | ● CONFIGURADO |

**Tienda principal de desarrollo:** somos-moto-repuestos-v95pc.myshopify.com

---

## 6. Marketing & CRM — Systeme.io

Plataforma de academia, CRM y automatización de marketing para el ecosistema SRM. Conectada a n8n mediante webhooks para sincronizar eventos de usuarios, cursos completados y ventas.

| Componente | Detalle | Estado |
|------------|---------|--------|
| Academia SRM | 8 cursos, 42 lecciones | ● CONFIGURADO |
| CRM | Gestión de contactos y segmentación | ● CONFIGURADO |
| Webhooks → n8n | wf_nuevo_usuario, wf_curso_completado | ● CONFIGURADO |
| Campañas | Email marketing automatizado | ● CONFIGURADO |
| Membresías | Acceso por niveles a contenido SRM | ● CONFIGURADO |

---

## 7. Hosting, Deploy & Dominios

### 7.1 DigitalOcean — Servidor Principal

| Componente | Detalle | Estado |
|------------|---------|--------|
| IP | 64.23.170.118 | ● OPERATIVO |
| SO | Ubuntu 24 LTS | ● ACTIVO |
| Costo | ~$24 USD/mes | ● ACTIVO |
| Docker Containers | 7 servicios activos | ● OPERATIVO |
| Nginx | Reverse proxy + SSL | ● OPERATIVO |
| n8n | Puerto 5678 (workflow engine) | ● OPERATIVO |

### 7.2 Contenedores Docker

| Container | Imagen | Estado |
|-----------|--------|--------|
| odi-n8n | n8nio/n8n:latest (puerto 5678) | ● OPERATIVO |
| odi-voice | odi-odi_voice (puerto 7777) | ● OPERATIVO |
| odi-m62-fitment | odi-odi_m62_fitment (puerto 8802) | ● OPERATIVO |
| odi-postgres | postgres:15 | ● OPERATIVO |
| odi-redis | redis:alpine | ● OPERATIVO |
| odi-prometheus | prom/prometheus | ● OPERATIVO |
| odi-grafana | grafana/grafana | ● OPERATIVO |

### 7.3 Vercel — Frontend & Landing

| Componente | Detalle | Estado |
|------------|---------|--------|
| Plan | Pro ($20/mes) | ● ACTIVO |
| Landing ADSI/ODI | Página principal | ● CONFIGURADO |
| ODI-OS Dashboard | Panel cognitivo | ● CONFIGURADO |
| SRM Tablero | Noticias por rol | ● CONFIGURADO |
| Deploy API | Programmatic deploys via REST | ● CONFIGURADO |

### 7.4 IONOS — Dominios

| Dominio | Uso | Estado |
|---------|-----|--------|
| larocamotorepuestos.com | Negocio principal + subdominio odi.* | ● ACTIVO |
| ecosistema-adsi.com | Plataforma ADSI | ● ACTIVO |
| somosrepuestosmotos.com | Marca comercial SRM | ● ACTIVO |

**DNS:** `odi.larocamotorepuestos.com` → 64.23.170.118 (registro A, TTL 5min)

---

## 8. Datos, Auditoría & Repositorio

### 8.1 Google Cloud / Sheets

| Componente | Detalle | Estado |
|------------|---------|--------|
| Proyecto GCP | ODIPROJECT (gen-lang-client-0753622404) | ● ACTIVO |
| Google Sheets | Auditoría ODI | ● ACTIVO |
| Generative Language API | Habilitada para Gemini | ● ACTIVO |

### 8.2 Bases de Datos

| Motor | Uso | Estado |
|-------|-----|--------|
| PostgreSQL 15 | Datos transaccionales, n8n | ● OPERATIVO |
| Redis Alpine | Cache, pub/sub eventos | ● OPERATIVO |
| ChromaDB | Embeddings, búsqueda semántica | ● ACTIVO |

### 8.3 GitHub

| Componente | Detalle | Estado |
|------------|---------|--------|
| Repositorio | juandavidjd/extrac | ● ACTIVO |
| Último commit | e8ff135 - Complete WhatsApp pipeline | ● ACTIVO |
| Branch principal | claude/unify-repository-branches | ● ACTIVO |

---

## 9. Arquitectura de Flujo

El siguiente diagrama muestra el flujo completo de datos entre todas las plataformas integradas:

### Pipeline Principal (WhatsApp)
```
Cliente (WhatsApp) → Meta Cloud API → HTTPS (odi.larocamotorepuestos.com)
→ Nginx (SSL termination) → n8n ODI_v6_CORTEX (webhook)
→ Intent Detection (SALUDO/FITMENT/PRECIO/VISUAL)
→ Cortex (Gemini/GPT) → Respuesta → WhatsApp API → Cliente
```

### Pipeline Visual (Generación de productos)
```
Usuario: "Quiero tenis deportivos a 400 mil"
→ IntentClassifier (visual_generate) → LLM (prompt en inglés)
→ Freepik API (imagen) → CES Engine (validación ética)
→ Shopify API (publicación) → Confirmación al usuario
```

### Pipeline Academia (Systeme.io)
```
Systeme.io (registro/curso) → Webhook → n8n
→ ODI Pipelines (segmentación) → CRM + Notificaciones
```

---

## 10. Seguridad & Credenciales

Todas las credenciales se almacenan en `/opt/odi/.env` en el servidor y en `.env.template` (sanitizado) en el repositorio. Los tokens nunca se exponen en código fuente.

| Credencial | Tipo | Expiración | Estado |
|------------|------|------------|--------|
| WhatsApp Token | System User (permanente) | No expira | ● ACTIVO |
| OpenAI API Key | Project key | Sin expiración fija | ● ACTIVO |
| Gemini API Key | GCP API Key | Sin expiración fija | ● ACTIVO |
| ElevenLabs API Key | Secret key | Sin expiración fija | ● ACTIVO |
| Freepik API Key | API key | Sin expiración fija | ● ACTIVO |
| Systeme.io API Key | API key | Sin expiración fija | ● ACTIVO |
| Shopify Tokens (x10) | Access tokens | Sin expiración fija | ● ACTIVO |
| SSL Certificate | Let's Encrypt | 6 May 2026 (auto-renueva) | ● ACTIVO |
| ODI Secure Token | Custom auth | N/A | ● ACTIVO |

> **REGLA ODI:** Nunca exponer tokens completos en documentos. Usar formato truncado: `sk_xxxx...xxxx`

---

## 11. Próximas Acciones

| Acción | Prioridad | Estado |
|--------|-----------|--------|
| Aprobar 5 plantillas WhatsApp (Meta) | Crítica | ◐ EN REVISIÓN |
| Activar productos Shopify (draft → active) | Alta | ○ PENDIENTE |
| Ejecutar Caso 001 (primera venta real) | Alta | ○ PENDIENTE |
| Asignar Voice ID de Ramona en ElevenLabs | Media | ○ PENDIENTE |
| Configurar Groq como tercer failover de IA | Baja | ○ PENDIENTE |
| Comprar dominio dedicado ODI (odi.dev o similar) | Media | ○ PENDIENTE |

---

*Generado: 5 de febrero de 2026*
*Versión: ODI v17.2*
