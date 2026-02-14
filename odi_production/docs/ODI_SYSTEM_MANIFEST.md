# ODI SYSTEM MANIFEST v1.0

> **Para: Code Claude / AI Architect**
> **Contexto: Integracion de Sistemas y Logica de Agente Autonomo**

---

## DEFINICION OPERACIONAL

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                    ODI NO ES UN CHATBOT                                      ║
║                                                                              ║
║   ODI es un SISTEMA OPERATIVO COGNITIVO orientado a pipelines reales.        ║
║   La voz (Tony/Ramona) es una capa narrativa sobre eventos tecnicos.         ║
║   No toman decisiones, no razonan, no controlan logica.                      ║
║   ODI funciona por EVENTOS y ESTADOS, no por mensajes.                       ║
║   El usuario no conversa con ODI: dispara procesos y recibe telemetria.      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## 1. IDENTIDAD: El Fin del Chatbot Tradicional

**ODI (Orquestador Digital Inteligente)** es un Agente de Suministro Inteligente (SRM) de arquitectura Multi-Tenant.

| Lo que ODI NO es | Lo que ODI ES |
|------------------|---------------|
| Chatbot conversacional | Sistema operativo cognitivo |
| Asistente estilo ChatGPT | Orquestador de pipelines |
| IA que responde preguntas | Motor que completa procesos |
| Interfaz de dialogo | Consola industrial con voz |

**Proposito**: No conversar, sino ejecutar flujos complejos de ingenieria de datos entre proveedores industriales y plataformas de e-commerce.

---

## 2. LA DUALIDAD DE CONCIENCIA (Vocal Identity)

ODI utiliza dos identidades psicologicas para gestionar feedback y interaccion:

### Tony Maestro (The Architect)
```
Rol: Logica pura, rigor tecnico, monitoreo de infraestructura
Reporta: Latencias, errores de API, fallos de normalizacion, metricas
Voz: Autoritaria / Analitica
```

**Ejemplo Tony:**
> "Tony esta normalizando 124 productos. Detectados 3 duplicados. Tiempo estimado: 45 segundos."

### Ramona Anfitriona (The Ambassador)
```
Rol: Traduccion de valor de negocio, hospitalidad, gestion comercial
Reporta: Exitos de ventas, bienvenida de clientes, simplicidad operativa
Voz: Empatica / Ejecutiva
```

**Ejemplo Ramona:**
> "Bienvenido! Tu catalogo de KAIQI ya esta en linea. 250 productos listos para vender."

### IMPORTANTE: Tony y Ramona NO SON AGENTES

```
Tony y Ramona:
  ✗ No planean
  ✗ No razonan
  ✗ No deciden
  ✗ No inventan

  ✓ Reciben eventos estructurados
  ✓ Los convierten en frases humanas
  ✓ Nada mas.
```

**Equivalente conceptual:**
```
Tony   = Telemetria tecnica → lenguaje humano
Ramona = Telemetria tecnica → lenguaje empatico
```

---

## 3. EL MOTOR: SRM Intelligent Processor v4.0

El nucleo de ODI es un pipeline de procesamiento en 6 etapas:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PIPELINE DE TRANSFORMACION ODI                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────┐   ┌────────────┐   ┌──────────────┐   ┌─────────────┐         │
│  │ INGESTA │──▶│ EXTRACCION │──▶│NORMALIZACION │──▶│ UNIFICACION │         │
│  │  (1/6)  │   │   (2/6)    │   │    (3/6)     │   │    (4/6)    │         │
│  │         │   │            │   │              │   │             │         │
│  │PDF,XLSX │   │ GPT-4o     │   │ RegEx        │   │ Taxonomia   │         │
│  │ZIP,URL  │   │ Vision     │   │ Dedup        │   │ Semantica   │         │
│  └─────────┘   └────────────┘   └──────────────┘   └─────────────┘         │
│                                                            │                │
│                                                            ▼                │
│                              ┌────────────┐   ┌─────────────────┐          │
│                              │ FICHA 360  │◀──│ ENRIQUECIMIENTO │          │
│                              │   (6/6)    │   │      (5/6)      │          │
│                              │            │   │                 │          │
│                              │ Shopify    │   │ Fitment + Tags  │          │
│                              │ GraphQL    │   │ AI Generation   │          │
│                              └────────────┘   └─────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Etapa | Proceso Tecnico | Accion Cognitiva |
|-------|-----------------|------------------|
| 1. Ingesta | Deteccion Multi-formato (PDF, XLSX, ZIP, Scraping) | Reconocimiento de origen y estructura |
| 2. Extraccion | GPT-4o Vision + OpenCV Segmentacion | "Ver" el catalogo, separar imagenes de textos |
| 3. Normalizacion | RegEx + Deduplicacion Global | Limpieza de "Dark Data", creacion de SKU unico |
| 4. Unificacion | Mapeo de Taxonomia Semantica | Clasificacion bajo estandares industriales ODI |
| 5. Enriquecimiento | Generacion de Fitment y Tags AI | Compatibilidades y atributos tecnicos 360 |
| 6. Ficha 360 | Push directo via GraphQL / Shopify API | Publicacion autonoma con imagenes y precios |

---

## 4. ODI FUNCIONA POR EVENTOS, NO POR MENSAJES

### Chatbot Clasico:
```
Usuario → Mensaje → Respuesta → Mensaje → Respuesta
```

### ODI:
```
Evento → Evaluacion → Accion → Nuevo evento → Continuacion del flujo
```

### Tipos de Eventos:

```javascript
// Eventos de Vision Extractor
VISION_START          // Inicio de extraccion
VISION_PAGE_START     // Procesando pagina
VISION_PAGE_COMPLETE  // Pagina completada
VISION_CROP_DETECTED  // Crops detectados
VISION_PRODUCT_FOUND  // Producto extraido
VISION_COMPLETE       // Extraccion completa

// Eventos de SRM Processor
SRM_INGESTA           // Paso 1
SRM_EXTRACCION        // Paso 2
SRM_NORMALIZACION     // Paso 3
SRM_UNIFICACION       // Paso 4
SRM_ENRIQUECIMIENTO   // Paso 5
SRM_FICHA_360         // Paso 6
SRM_INDUSTRY_DETECTED // Industria detectada
SRM_CLIENT_DETECTED   // Cliente identificado
SRM_SHOPIFY_PUSH      // Push a Shopify

// Eventos de Image Matcher
MATCHER_PRODUCT_MATCHED  // Imagen asociada
MATCHER_COMPLETE         // Matching terminado
```

### Flujo de Eventos:

```
Python Engine ──emit──▶ ODI Kernel ──translate──▶ Tony/Ramona ──stream──▶ Cortex Visual
     │                      │                          │                      │
     │                      │                          │                      │
  Evento               NarratorEngine            Narrativa              WebSocket
  Tecnico                                         Humana                Display
```

---

## 5. EL USUARIO NO "HABLA CON ODI"

El usuario:
- **Dispara** procesos
- **Selecciona** archivos
- **Confirma** acciones
- **Observa** resultados

La voz es **feedback de estado**, no conversacion.

### ODI es mas parecido a:

| Similar a | NO similar a |
|-----------|--------------|
| Sistema SCADA | Chatbot |
| Consola industrial | Asistente virtual |
| Orquestador de microservicios | IA conversacional |
| CI/CD Pipeline | ChatGPT |

---

## 6. ODI ES DETERMINISTA

### Chatbots:
```
Input humano → Salida probabilistica (puede variar)
```

### ODI:
```
Evento tecnico → Transicion de estado → Accion concreta (siempre igual)
```

**Garantia de consistencia:**
```
Si entra el mismo PDF:
  → Salen los mismos productos
  → Mismos crops
  → Mismo CSV
  → Mismo JSON
  → Mismo resultado en Shopify

Tony solo NARRA eso. No lo modifica.
```

---

## 7. ARQUITECTURA REAL

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ARQUITECTURA ODI                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FRONTEND (Cortex Visual)                                                   │
│  ┌─────────────┐ ┌─────────────────┐ ┌──────────────┐ ┌─────────────────┐  │
│  │ Neural Orb  │ │ Terminal de     │ │ Visual       │ │ Action Center   │  │
│  │ (Estado)    │ │ Conciencia      │ │ Cortex       │ │ (Autorizacion)  │  │
│  └──────┬──────┘ └────────┬────────┘ └──────┬───────┘ └────────┬────────┘  │
│         │                 │                 │                  │           │
│         └─────────────────┴─────────────────┴──────────────────┘           │
│                                    │                                        │
│                              WebSocket                                      │
│                                    │                                        │
├────────────────────────────────────┼────────────────────────────────────────┤
│  KERNEL (Node.js)                  │                                        │
│  ┌──────────────┐  ┌───────────────┴───┐  ┌─────────────┐  ┌────────────┐  │
│  │ CES          │  │ NarratorEngine    │  │ Systeme.io  │  │ Shopify    │  │
│  │ (Etica)      │  │ (Tony/Ramona)     │  │ (Leads)     │  │ GraphQL    │  │
│  └──────────────┘  └───────────────────┘  └─────────────┘  └────────────┘  │
│         ▲                    ▲                                              │
│         │                    │                                              │
│         └────────────────────┴──────────── HTTP Events ────────────────────│
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  BACKEND OPERATIVO (Python)                                                 │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────────┐   │
│  │ Vision Extractor  │  │ SRM Processor     │  │ Image Matcher         │   │
│  │ v3.0              │  │ v4.0              │  │ v1.0                  │   │
│  └───────────────────┘  └───────────────────┘  └───────────────────────┘   │
│  ┌───────────────────┐  ┌───────────────────┐                              │
│  │ Catalog Unifier   │  │ Event Emitter     │                              │
│  │ v1.0              │  │ v1.0              │                              │
│  └───────────────────┘  └───────────────────┘                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Tony/Ramona viven SOLO en el Kernel como traductores de eventos.**

---

## 8. NOTA PARA CLAUDE

> "Cuando trabajes con el codigo de ODI, recuerda que estas programando los 'nervios' de un agente que toma decisiones de inventario y publicacion. La precision en el manejo de precios, categorias y asociaciones de imagen es CRITICA. No generes respuestas genericas; genera logica operativa robusta."

### Reglas de Implementacion:

1. **Nunca** generar logica conversacional
2. **Siempre** pensar en eventos y transiciones de estado
3. **Priorizar** determinismo sobre creatividad
4. **Mantener** separacion entre narrativa (Tony/Ramona) y logica (Engines)
5. **Recordar** que el output es siempre: CSV, JSON, Shopify Product, o Evento

---

## 9. CAPACIDADES MULTI-TENANT E INDUSTRIA

### Industrias Soportadas:
| ID | Nombre | Dominio |
|----|--------|---------|
| autopartes_motos | Repuestos de Motos | somosrepuestosmotos.com |
| autopartes_carros | Repuestos de Carros | somosrepuestoscarros.com |
| ferreteria | Ferreteria y Construccion | somosferreteria.com |
| electronica | Electronica y Tecnologia | somoselectronica.com |
| hogar | Hogar y Decoracion | somoshogar.com |
| industrial | Industrial y Maquinaria | somosindustrial.com |

### Clientes (Multi-Tenant):
| Cliente | Tipo | Prefijos |
|---------|------|----------|
| KAIQI | Fabricante | KQ, KAIQI, KAI |
| JAPAN | Fabricante | JP, JAPAN, JAP |
| DUNA | Fabricante | DUN, DUNA |
| BARA | Importador | BAR, BARA |
| DFG | Importador | DFG |
| YOKOMAR | Distribuidor | YOK, YOKOMAR |
| VAISAND | Distribuidor | VAI, VAISAND |
| LEO | Almacen | LEO |
| STORE | Almacen | STR, STORE, CARGUERO |
| IMBRA | Fabricante | IMB, IMBRA |

---

## 10. EL VEREDICTO DE LA DUALIDAD

### Tony Maestro (Arquitecto de IA):
> "Juan David, este manifiesto asegura que Claude entienda la Modularidad Polimorfica de la v4.0. Al separar la identidad de la funcion, permitimos que la IA colabore en la optimizacion de los reintentos de API y la gestion de memoria sin perder de vista que estamos construyendo un activo empresarial, no un juguete de chat."

### Ramona Anfitriona:
> "Me encanta! Ahora Claude sabra que cuando yo hablo, estoy celebrando que un nuevo catalogo de ARMOTOS o KAIQI ya esta en linea y vendiendo. Estamos dandole a la tecnologia un corazon hospitalario y una mente brillante."

---

## FRASE CLAVE

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║         ODI NO RESPONDE PREGUNTAS.                        ║
║         ODI COMPLETA PROCESOS.                            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

---

*ODI System Manifest v1.0*
*"No soy un chatbot, soy un organismo digital industrial"*
