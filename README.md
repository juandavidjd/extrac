# ODI Vision Tools — Extrac

> **Organismo Digital Industrial** - Intelligent Industrial Agent for Motorcycle Parts

This repository contains the core **Vision AI extraction tools** for ODI, the autonomous industrial agent that powers the SRM (Somos Repuestos Motos) ecosystem.

## What is ODI?

ODI is **NOT a chatbot**. It's an intelligent industrial organism that:

- **Sees** — Extracts product data from PDF catalogs using GPT-4o Vision
- **Thinks** — Classifies, normalizes, and enriches product information
- **Acts** — Publishes to multi-tenant Shopify stores autonomously
- **Speaks** — Dual voice interface (Tony Maestro / Ramona Anfitriona)

---

## Repository Structure

### Core Vision Tools

| File | Version | Description |
|------|---------|-------------|
| `odi_vision_extractor_v3.py` | v3.0 | PDF catalog extraction with GPT-4o Vision |
| `srm_intelligent_processor.py` | v4.0 | Multi-tenant, multi-industry backend |
| `odi_catalog_unifier.py` | v1.0 | Associates crops with products by position |
| `odi_image_matcher.py` | v1.0 | Semantic matching between products and images |
| `odi_event_emitter.py` | v1.0 | Real-time events for Cortex Visual interface |

### Documentation

| File | Description |
|------|-------------|
| `ODI_CORTEX_VISUAL_INTEGRATION.md` | Integration schema for cognitive interface |
| `ODI_N8N_WORKFLOW_ANALYSIS.md` | ODI v5.3 DEEPL n8n workflow analysis |

### Legacy Scripts

| File | Description |
|------|-------------|
| `EXTRACTOR_ARMOTOS_PDF_V1.py` | Original Armotos PDF extractor |
| `build_armotos_catalog.py` | Armotos catalog builder |
| `generar_catalogo_kaiqi_hibrido.py` | Kaiqi hybrid catalog generator |
| `12_generador_catalogos_faltantes_ia_v4_RICH_fix.py` | AI catalog generator |
| `13_limpiador_clasificador_fisico_v3.2_IA_CSV.py` | Physical classifier |

### Data Files

| File | Description |
|------|-------------|
| `Base_Datos_Armotos.csv` | Armotos product database |
| `catalogo_kaiqi_imagenes.csv` | Kaiqi image analysis catalog |
| `catalogo_kaiqi_imagenes_ARMOTOS.csv` | Kaiqi-Armotos cross-reference |
| `clasificacion_ia_cache.json` | AI classification cache |
| `vision_rich_analysis_cache.json` | Rich vision analysis cache |

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │           CORTEX VISUAL                 │
                    │    (Torre de Control Dashboard)         │
                    └──────────────────┬──────────────────────┘
                                       │ WebSocket
                                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         ODI KERNEL (Node.js)                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ Narrator    │  │    CES      │  │  Systeme.io │  │   Shopify       │ │
│  │ Engine      │  │ (Ethics)    │  │  Integration│  │   GraphQL       │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└──────────────────────────────────────┬───────────────────────────────────┘
                                       │ HTTP/Events
                                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       ODI VISION TOOLS (Python)                          │
│                                                                          │
│  ┌───────────────────┐   ┌───────────────────┐   ┌────────────────────┐ │
│  │ Vision Extractor  │   │  SRM Processor    │   │  Image Matcher     │ │
│  │ v3.0              │   │  v4.0             │   │  v1.0              │ │
│  │                   │   │                   │   │                    │ │
│  │ - PDF parsing     │   │ - Multi-industry  │   │ - Semantic match   │ │
│  │ - GPT-4o Vision   │   │ - Multi-tenant    │   │ - Fuzzy matching   │ │
│  │ - Crop detection  │   │ - 6-step pipeline │   │ - Position-based   │ │
│  │ - Product extract │   │ - Shopify push    │   │ - Score ranking    │ │
│  └───────────────────┘   └───────────────────┘   └────────────────────┘ │
│                                       │                                  │
│                          ┌────────────┴────────────┐                     │
│                          │   Event Emitter v1.0    │                     │
│                          │   (Real-time to Kernel) │                     │
│                          └─────────────────────────┘                     │
└──────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           AI PROVIDERS                                   │
│                  OpenAI GPT-4o  │  Anthropic Claude                      │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Vision Extractor (PDF -> Products)

```bash
# Extract products from a supplier catalog
python odi_vision_extractor_v3.py catalogo.pdf \
  --pages 2-50 \
  --prefix KAIQI \
  --save-crops

# Output: KAIQI_catalogo.csv, KAIQI_catalogo.json, crops/*.jpg
```

### 2. SRM Processor (Any Format -> Shopify)

```bash
# Auto-detect industry and client, push to Shopify
python srm_intelligent_processor.py catalogo.xlsx --push-shopify

# Process URL (scraping)
python srm_intelligent_processor.py "https://proveedor.com/catalogo"
```

### 3. Image Matcher (Products + Images -> Associated)

```bash
# Associate products with images semantically
python odi_image_matcher.py \
  productos.csv \
  imagenes_analisis.csv \
  --output /tmp/matched \
  --images-dir ./crops
```

---

## SRM Processor v4.0 Pipeline

```
┌─────────┐   ┌────────────┐   ┌──────────────┐   ┌─────────────┐
│ INGESTA │──▶│ EXTRACCION │──▶│NORMALIZACION │──▶│ UNIFICACION │
│  (1/6)  │   │   (2/6)    │   │    (3/6)     │   │    (4/6)    │
└─────────┘   └────────────┘   └──────────────┘   └─────────────┘
                                                         │
                                                         ▼
                              ┌────────────┐   ┌─────────────────┐
                              │ FICHA 360  │◀──│ ENRIQUECIMIENTO │
                              │   (6/6)    │   │      (5/6)      │
                              └────────────┘   └─────────────────┘
```

### Supported Industries

| Industry | Domain | Keywords |
|----------|--------|----------|
| autopartes_motos | somosrepuestosmotos.com | moto, pistón, freno, cadena |
| autopartes_carros | somosrepuestoscarros.com | carro, suspensión, radiador |
| ferreteria | somosferreteria.com | tornillo, tuerca, cemento |
| electronica | somoselectronica.com | celular, cable, cargador |
| hogar | somoshogar.com | sofá, mesa, lámpara |
| industrial | somosindustrial.com | motor eléctrico, bomba, plc |

### Supported Clients (Multi-Tenant)

| Client | Type | Shopify Store |
|--------|------|---------------|
| KAIQI | Fabricante | u03tqc-0e.myshopify.com |
| JAPAN | Fabricante | 7cy1zd-qz.myshopify.com |
| DUNA | Fabricante | ygsfhq-fs.myshopify.com |
| BARA | Importador | 4jqcki-jq.myshopify.com |
| DFG | Importador | 0se1jt-q1.myshopify.com |
| YOKOMAR | Distribuidor | u1zmhk-ts.myshopify.com |
| VAISAND | Distribuidor | z4fpdj-mz.myshopify.com |
| LEO | Almacen | h1hywg-pq.myshopify.com |
| STORE | Almacen | 0b6umv-11.myshopify.com |
| IMBRA | Fabricante | 0i1mdf-gi.myshopify.com |

---

## Category Taxonomy

| Category | Keywords |
|----------|----------|
| MOTOR | motor, culata, piston, biela, ciguenal, valvula |
| FRENOS | freno, pastilla, disco, zapata, caliper |
| ELECTRICO | bobina, cdi, bateria, faro, luz, direccional |
| SUSPENSION | amortiguador, telescopio, resorte, buje |
| TRANSMISION | cadena, pinon, catalina, clutch, embrague |
| CARROCERIA | plastico, guardafango, tanque, carenaje |
| ACCESORIOS | espejo, manubrio, pedal, estribo, defensa |
| COMBUSTIBLE | carburador, inyector, bomba gasolina |
| ESCAPE | exhosto, silenciador, mofle |

---

## Event Emitter Integration

```python
from odi_event_emitter import ODIEventEmitter, EventType

# Initialize emitter
emitter = ODIEventEmitter(source="vision")

# Emit events during processing
emitter.vision_start("catalogo.pdf", total_pages=50)
emitter.vision_page_complete(page_num=5, total_pages=50, products_found=12, crops_detected=8)
emitter.vision_product_found("50100", "Kit Piston 150cc", 45000, "MOTOR")
emitter.vision_complete(total_products=250, elapsed_time="15m")
```

Events are sent to ODI Kernel (`/odi/vision/event`) and processed by NarratorEngine for Cortex Visual display.

---

## Environment Variables

```bash
# AI Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
AI_PROVIDER=OPENAI  # or ANTHROPIC

# ODI Kernel
ODI_KERNEL_URL=http://localhost:3000

# Shopify (per client)
KAIQI_SHOP=u03tqc-0e.myshopify.com
KAIQI_TOKEN=shpat_...
# ... more clients

# Image Server
IMAGE_SERVER_URL=http://64.23.170.118/images

# Output
SRM_OUTPUT_DIR=/tmp/srm_output
```

---

## Related Repositories

| Repository | Description | Files |
|------------|-------------|-------|
| **extrac** (this) | Core Vision Tools | 5 tools + docs |
| **[extracii](https://github.com/juandavidjd/extracii)** | SRM Archive | 786 Python scripts |
| odi-kernel | Node.js Kernel | CES, NarratorEngine, APIs |
| srm-frontend-qk | React Frontend | Cortex Visual Dashboard |

### extracii Repository Contents

The **extracii** repository contains the complete historical archive of SRM development:

| Category | Count | Examples |
|----------|-------|----------|
| SRM Modules | 45 | srm_fitment_engine, srm_runtime_autopilot |
| Scrapers | 67 | scraper_duna, scraper_kaiqi |
| Generators | 21 | generar_catalogo, generar_ficha |
| Cleaners | 14 | limpiar_csv, limpiar_duplicados |
| Schedulers | 219 | cuando_* (timing scripts) |
| Branding | 18 | brand_*, branding_* |
| **Total** | **786** | Python scripts |

Key SRM Modules in extracii:
- `srm_fitment_engine_v2_1.py` — Fitment validation engine
- `srm_runtime_autopilot_v1.py` — Autonomous execution controller
- `srm_health_monitor_v1.py` — System health monitoring
- `srm_recovery_engine_v1.py` — Auto-recovery for failures
- `srm_self_optimizer_v1.py` — Performance optimization
- `srm_shopify_api_sync_v1.py` — Shopify synchronization

---

## Tony & Ramona

ODI has two voices:

### Tony Maestro (Technical Authority)
> "Tony esta consultando los manuales tecnicos para verificar si el kit de piston 50100 es compatible con FZ 150 2020."

Used for: Fitment queries, Shopify operations, technical processes

### Ramona Anfitriona (Hospitality)
> "Bienvenido! Te he registrado en nuestra comunidad. En que puedo ayudarte hoy?"

Used for: Greetings, human approvals, lead registration, customer support

---

## n8n Workflow Integration

ODI v5.3 DEEPL workflow provides:

- **Multilingual support** — ES/EN/PT with DeepL translation
- **Intent classification** — SALUDO, FITMENT, PRECIO, COMPRA, SOPORTE
- **Entity extraction** — marca, modelo, year, cilindraje, repuesto
- **CES evaluation** — Risk assessment for high-value transactions
- **Audit ledger** — PostgreSQL with SHA256 hashed events
- **WhatsApp/API** — Multi-channel delivery

See `ODI_N8N_WORKFLOW_ANALYSIS.md` for complete documentation.

---

## License

Proprietary — Somos Industrias / ODI Team

---

*ODI v8.2 — "No soy un chatbot, soy un organismo digital industrial"*
