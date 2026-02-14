# ODI Cortex Visual - Integration Schema

## Architecture Overview

```
                           CORTEX VISUAL (Frontend)
                    ┌─────────────────────────────────────┐
                    │  Neural Orb  │  Terminal Conciencia│
                    │  Action Ctr  │  Visual Cortex      │
                    └───────────────┬─────────────────────┘
                                    │ WebSocket
                                    │ /odi/narrativa
                                    ▼
                    ┌─────────────────────────────────────┐
                    │      ODI Kernel (Node.js/Express)   │
                    │  ├── NarratorEngine (Tony/Ramona)   │
                    │  ├── CES (Constitutional Ethics)    │
                    │  └── SystemeService (Leads)         │
                    └───────────────┬─────────────────────┘
                                    │ HTTP API
                                    │ /odi/vision/*
                                    ▼
              ┌──────────────────────────────────────────────────┐
              │         ODI VISION TOOLS (Python)                │
              │  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
              │  │ Vision      │  │ SRM         │  │ Catalog  │ │
              │  │ Extractor   │  │ Processor   │  │ Unifier  │ │
              │  │ v3.0        │  │ v4.0        │  │ v1.0     │ │
              │  └─────────────┘  └─────────────┘  └──────────┘ │
              │              ▲             ▲            ▲        │
              │              └──────┬──────┴────────────┘        │
              │                     │                            │
              │              ┌──────┴──────┐                     │
              │              │ Image       │                     │
              │              │ Matcher v1.0│                     │
              │              └─────────────┘                     │
              └──────────────────────────────────────────────────┘
                                    │
                                    ▼
              ┌──────────────────────────────────────────────────┐
              │                    AI PROVIDERS                  │
              │         OpenAI GPT-4o  │  Anthropic Claude       │
              └──────────────────────────────────────────────────┘
```

---

## Event Types for NarratorEngine

The following events should be emitted by the Python tools and captured by the NarratorEngine for the Cortex Visual interface:

### Vision Extraction Events

```typescript
// Event Types (extend existing narrator.ts)
type VisionEventType =
  | 'VISION_START'          // Inicio de extraccion de catalogo
  | 'VISION_PAGE_START'     // Procesando una pagina
  | 'VISION_PAGE_COMPLETE'  // Pagina completada
  | 'VISION_CROP_DETECTED'  // Crops de imagen detectados
  | 'VISION_PRODUCT_FOUND'  // Producto extraido
  | 'VISION_ERROR'          // Error en extraccion
  | 'VISION_COMPLETE'       // Extraccion completa
  | 'VISION_CHECKPOINT'     // Checkpoint guardado
```

### SRM Processor Events

```typescript
type SRMEventType =
  | 'SRM_PIPELINE_START'      // Inicio del pipeline 6 pasos
  | 'SRM_INGESTA'             // Paso 1: Ingesta
  | 'SRM_EXTRACCION'          // Paso 2: Extraccion
  | 'SRM_NORMALIZACION'       // Paso 3: Normalizacion
  | 'SRM_UNIFICACION'         // Paso 4: Unificacion
  | 'SRM_ENRIQUECIMIENTO'     // Paso 5: Enriquecimiento
  | 'SRM_FICHA_360'           // Paso 6: Ficha 360
  | 'SRM_INDUSTRY_DETECTED'   // Industria detectada
  | 'SRM_CLIENT_DETECTED'     // Cliente detectado
  | 'SRM_SHOPIFY_PUSH'        // Push a Shopify
  | 'SRM_COMPLETE'            // Pipeline completo
```

### Image Matching Events

```typescript
type MatcherEventType =
  | 'MATCHER_START'           // Inicio matching
  | 'MATCHER_PRODUCT_MATCHED' // Producto asociado a imagen
  | 'MATCHER_NO_MATCH'        // Producto sin match
  | 'MATCHER_COMPLETE'        // Matching completo
```

---

## WebSocket Event Schema

### Event Payload Structure

```typescript
interface ODIVisionEvent {
  id: string;                      // UUID
  timestamp: Date;
  event_type: string;              // From types above
  source: 'vision' | 'srm' | 'matcher' | 'unifier';
  actor: string;                   // "ODI_VISION" | "SRM_PROCESSOR" | etc.

  // Datos especificos del evento
  data: {
    // Para VISION_PAGE_*
    page_num?: number;
    total_pages?: number;
    products_found?: number;
    crops_detected?: number;

    // Para SRM_*
    pipeline_step?: number;        // 1-6
    pipeline_name?: string;        // "INGESTA", "EXTRACCION", etc.
    industry?: string;
    client?: string;

    // Para productos
    product?: {
      codigo: string;
      nombre: string;
      precio: number;
      categoria: string;
      imagen?: string;
    };

    // Para errores
    error?: string;

    // Progreso general
    progress?: {
      current: number;
      total: number;
      percentage: number;
    };
  };

  // Narrativa para el usuario (generada por NarratorEngine)
  narrativa_humana: string;
  narrator_voice: 'TONY' | 'RAMONA' | 'SISTEMA';

  // Fuentes consultadas (Shadow Indexing)
  shadow_sources: Array<{
    type: 'pdf' | 'api' | 'database' | 'image';
    name: string;
    status: 'consulting' | 'found' | 'not_found';
  }>;
}
```

---

## NarratorEngine Templates for Vision Tools

### Tony (Voz Tecnica)

```typescript
const plantillasTonyVision = {
  VISION_START: "Tony esta iniciando la extraccion del catalogo {pdf_name}. {total_pages} paginas por procesar.",
  VISION_PAGE_START: "Tony esta analizando la pagina {page_num} de {total_pages}. Consultando GPT-4o Vision...",
  VISION_PAGE_COMPLETE: "Pagina {page_num} completada. {products_found} productos extraidos, {crops_detected} imagenes detectadas.",
  VISION_CROP_DETECTED: "Tony detecto {count} regiones de producto en la pagina {page_num}.",
  VISION_PRODUCT_FOUND: "Producto identificado: {codigo} - {nombre}. Categoria: {categoria}. Precio: ${precio}.",
  VISION_CHECKPOINT: "Checkpoint guardado. Progreso: {percentage}% ({current}/{total} paginas).",
  VISION_ERROR: "Error en pagina {page_num}: {error}. Tony intentara continuar con la siguiente.",
  VISION_COMPLETE: "Extraccion completa. {total_products} productos extraidos en {elapsed_time}.",

  SRM_PIPELINE_START: "Tony inicia el pipeline SRM v4.0 para {source_file}.",
  SRM_INGESTA: "Paso 1/6: Tony esta ingiriendo el archivo {filename}. Formato detectado: {format}.",
  SRM_EXTRACCION: "Paso 2/6: Extrayendo datos estructurados del contenido.",
  SRM_NORMALIZACION: "Paso 3/6: Normalizando {count} productos. Eliminando duplicados.",
  SRM_UNIFICACION: "Paso 4/6: Unificando categorias. {categories_count} categorias detectadas.",
  SRM_ENRIQUECIMIENTO: "Paso 5/6: Enriqueciendo productos con tags y metadatos.",
  SRM_FICHA_360: "Paso 6/6: Generando Ficha 360 completa.",
  SRM_INDUSTRY_DETECTED: "Tony detecto industria: {industry_name}. Confianza: {confidence}%.",
  SRM_CLIENT_DETECTED: "Cliente identificado: {client_name}. Tipo: {client_type}.",
  SRM_SHOPIFY_PUSH: "Tony esta publicando {count} productos en Shopify: {shop_url}.",

  MATCHER_START: "Tony inicia el matching semantico. {products_count} productos x {images_count} imagenes.",
  MATCHER_PRODUCT_MATCHED: "Match encontrado: {producto} -> {imagen} (score: {score}%).",
  MATCHER_COMPLETE: "Matching completado. {matched_count}/{total_count} productos con imagen.",
};
```

### Ramona (Voz Hospitalaria)

```typescript
const plantillasRamonaVision = {
  VISION_START: "Vamos a procesar tu catalogo, {usuario}. Dame unos momentos mientras analizo las {total_pages} paginas.",
  VISION_COMPLETE: "Listo, {usuario}! Encontre {total_products} productos en tu catalogo. Ya estan listos para tu tienda.",
  SRM_INDUSTRY_DETECTED: "Detecte que este catalogo es de {industry_name}. Voy a usar las categorias correctas.",
  SRM_CLIENT_DETECTED: "Reconoci a {client_name}! Voy a enviarlo directamente a su tienda.",
  SRM_COMPLETE: "Todo listo, {usuario}. Tu catalogo esta procesado y exportado.",
  VISION_ERROR: "Hubo un pequeno problema en la pagina {page_num}, pero no te preocupes, seguimos adelante.",
};
```

---

## REST API Endpoints for Vision Tools

### POST /odi/vision/extract

Inicia extraccion de un catalogo PDF.

```typescript
// Request
{
  pdf_path: string;       // Ruta al PDF
  pages: string;          // "2-50", "all", "1,3,5-10"
  prefix: string;         // Prefijo SKU (default: "CAT")
  dpi?: number;           // Resolucion (default: 150)
  save_crops?: boolean;   // Guardar imagenes recortadas
}

// Response
{
  job_id: string;         // ID del proceso
  status: "started";
  message: string;        // Narrativa de Tony
}
```

### POST /odi/vision/process

Procesa cualquier archivo con SRM Processor.

```typescript
// Request
{
  source: string;         // Ruta o URL
  industry?: string;      // Forzar industria
  client?: string;        // Forzar cliente
  push_shopify?: boolean; // Push automatico
}

// Response
{
  job_id: string;
  status: "started";
  detected_industry?: string;
  detected_client?: string;
}
```

### POST /odi/vision/match

Ejecuta matching semantico imagen-producto.

```typescript
// Request
{
  products_csv: string;
  images_csv: string;
  images_dir?: string;
  threshold?: number;     // 0-1 (default: 0.4)
}

// Response
{
  job_id: string;
  status: "started";
}
```

### GET /odi/vision/status/:job_id

Estado de un proceso en curso.

```typescript
// Response
{
  job_id: string;
  status: "running" | "completed" | "error";
  progress: {
    current: number;
    total: number;
    percentage: number;
  };
  events: ODIVisionEvent[];  // Ultimos N eventos
  result?: {
    products_count: number;
    csv_path: string;
    json_path: string;
  };
}
```

---

## Cortex Visual Components Mapping

### Neural Orb States

| Python Process State | Orb State | Color | Animation |
|---------------------|-----------|-------|-----------|
| Pipeline starting | `thinking` | Blue | Pulse |
| Vision API call | `thinking` | Blue | Pulse fast |
| Processing page | `thinking` | Blue | Rotate |
| Awaiting user (CES) | `waiting_human` | Yellow | Breathe |
| Shopify push | `speaking` | Green | Glow |
| Error/retry | `thinking` | Orange | Blink |
| Complete | `idle` | Cyan | Gentle pulse |

### Terminal de Conciencia Display

```typescript
// Formato de linea en el terminal
interface TerminalLine {
  timestamp: string;      // "14:32:15"
  icon: string;           // "🔍" | "📄" | "✓" | "⚠" | "❌"
  voice: "TONY" | "RAMONA" | "SISTEMA";
  message: string;        // Narrativa humana
  metadata?: {
    page?: number;
    progress?: string;    // "[42/100]"
    product?: string;     // SKU o nombre
  };
}
```

### Shadow Indexing Display

Para cada evento de Vision, mostrar las fuentes siendo consultadas:

```typescript
// Ejemplo de shadow_sources durante extraccion
[
  { type: "pdf", name: "catalogo_kaiqi.pdf", status: "consulting" },
  { type: "api", name: "GPT-4o Vision", status: "consulting" },
  { type: "database", name: "Taxonomia Categorias", status: "found" },
]
```

### Visual Cortex (Image Display)

Cuando se detectan crops o se asocian imagenes:

```typescript
interface VisualCortexState {
  current_image?: string;     // Path or base64
  image_type: "page" | "crop" | "product";
  annotations?: Array<{
    x: number;
    y: number;
    width: number;
    height: number;
    label: string;            // Codigo del producto
  }>;
}
```

---

## Python Integration Points

### Adding Event Emission to Vision Extractor

```python
# En odi_vision_extractor_v3.py, agregar:

import requests

ODI_KERNEL_URL = os.getenv("ODI_KERNEL_URL", "http://localhost:3000")

def emit_event(event_type: str, data: dict):
    """Emite evento al ODI Kernel para Cortex Visual."""
    try:
        payload = {
            "source": "vision",
            "event_type": event_type,
            "actor": "ODI_VISION_v3",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        requests.post(
            f"{ODI_KERNEL_URL}/odi/vision/event",
            json=payload,
            timeout=2
        )
    except:
        pass  # Non-blocking

# Uso en el proceso:
emit_event("VISION_PAGE_START", {
    "page_num": page_num,
    "total_pages": len(pages)
})
```

### Adding Event Emission to SRM Processor

```python
# En srm_intelligent_processor.py, agregar:

def emit_event(event_type: str, data: dict):
    """Emite evento al ODI Kernel."""
    try:
        payload = {
            "source": "srm",
            "event_type": event_type,
            "actor": "SRM_PROCESSOR_v4",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        requests.post(
            f"{ODI_KERNEL_URL}/odi/vision/event",
            json=payload,
            timeout=2
        )
    except:
        pass

# En el pipeline:
def _ingest(self, source: str):
    emit_event("SRM_INGESTA", {
        "filename": os.path.basename(source),
        "format": detect_file_type(source)
    })
    # ... resto del codigo
```

---

## Environment Variables

```bash
# ODI Kernel
ODI_KERNEL_URL=http://localhost:3000

# AI Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
AI_PROVIDER=OPENAI  # or ANTHROPIC

# Shopify (por cliente)
KAIQI_SHOP=u03tqc-0e.myshopify.com
KAIQI_TOKEN=***REMOVED***...
JAPAN_SHOP=7cy1zd-qz.myshopify.com
JAPAN_TOKEN=***REMOVED***...
# ... mas clientes

# Image Server
IMAGE_SERVER_URL=http://64.23.170.118/images

# Processing
SRM_OUTPUT_DIR=/tmp/srm_output
SRM_TEMP_DIR=/tmp/srm_temp
```

---

## Multi-Tenant Client Configuration

```typescript
// Clientes configurados en SRM Processor v4.0
const CLIENTS = {
  autopartes_motos: {
    KAIQI: { shop: "u03tqc-0e.myshopify.com", type: "fabricante" },
    JAPAN: { shop: "7cy1zd-qz.myshopify.com", type: "fabricante" },
    DUNA: { shop: "ygsfhq-fs.myshopify.com", type: "fabricante" },
    BARA: { shop: "4jqcki-jq.myshopify.com", type: "importador" },
    DFG: { shop: "0se1jt-q1.myshopify.com", type: "importador" },
    YOKOMAR: { shop: "u1zmhk-ts.myshopify.com", type: "distribuidor" },
    VAISAND: { shop: "z4fpdj-mz.myshopify.com", type: "distribuidor" },
    LEO: { shop: "h1hywg-pq.myshopify.com", type: "almacen" },
    STORE: { shop: "0b6umv-11.myshopify.com", type: "almacen" },
    IMBRA: { shop: "0i1mdf-gi.myshopify.com", type: "fabricante" },
  }
};
```

---

## Category Taxonomy

Categorias estandar usadas por todos los tools:

| Categoria | Keywords |
|-----------|----------|
| MOTOR | motor, culata, piston, biela, ciguenal, valvula, cilindro, aro, anillo |
| FRENOS | freno, pastilla, disco, zapata, caliper, bomba freno, manigueta |
| ELECTRICO | bobina, cdi, bateria, faro, luz, bombillo, direccional, regulador |
| SUSPENSION | amortiguador, telescopio, resorte, buje, rodamiento |
| TRANSMISION | cadena, pinon, catalina, clutch, embrague, variador, correa |
| CARROCERIA | plastico, guardafango, tanque, tapa, carenaje, asiento |
| ACCESORIOS | espejo, manubrio, pedal, estribo, defensa, parrilla |
| HERRAMIENTAS | llave, extractor, dado, banco |
| LUJOS | cromado, emblema, calcomania, adhesivo |
| COMBUSTIBLE | carburador, inyector, bomba gasolina, filtro |
| ESCAPE | exhosto, silenciador, mofle, tubo escape |
| OTROS | default |

---

## Summary

This integration schema enables the **Cortex Visual** frontend to receive real-time updates from the **ODI Vision Tools** through the **ODI Kernel**. The NarratorEngine translates technical processing events into human-readable narratives using Tony's technical voice and Ramona's hospitality voice.

Key integration points:
1. Python tools emit events via HTTP POST to ODI Kernel
2. ODI Kernel processes events through NarratorEngine
3. Cortex Visual receives narrated events via WebSocket
4. Neural Orb, Terminal, and Visual Cortex update accordingly

---

*Document Version: 1.0*
*Generated: 2026-01-31*
*For: ODI Kernel + Cortex Visual Integration*
