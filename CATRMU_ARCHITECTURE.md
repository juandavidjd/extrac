# CATRMU — Canal Transversal Multitemático

**Versión:** 1.0
**Fecha:** 11 Febrero 2026
**Estado:** Arquitectura Fundacional

---

## Declaración

> **CATRMU es el contenedor universal de todas las industrias ODI.**
> Un solo sistema, múltiples pieles, lógica compartida.

---

## Jerarquía de Dominios

```
                              catrmu.com
                    Canal Transversal Multitemático
                         "ODI Universal"
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
    ecosistema-adsi.com    liveodi.com    somosindustriasodi.com
      (Plataforma)        (Interfaz)        (Multi-industria)
            │                   │                   │
            └───────────────────┼───────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  TRANSPORTE   │      │    SALUD      │      │ENTRETENIMIENTO│
│    #06B6D4    │      │    #14B8A6    │      │    #EC4899    │
└───────┬───────┘      └───────┬───────┘      └───────┬───────┘
        │                      │                      │
        ▼              ┌───────┼───────┐              ▼
┌───────────────┐      │       │       │      ┌───────────────┐
│somosrepuestos │      ▼       ▼       ▼      │  (pendiente)  │
│  motos.com    │  Matzu   COVER'S  Cabezas   └───────────────┘
│larocamoto...  │  Dental  Bruxismo  Sanas
└───────────────┘
```

---

## Principio Arquitectónico

### Lo que PERMANECE (Core ODI)

| Componente | Versión | Función |
|------------|---------|---------|
| Intent Override Gate | v1.5 | Detección de intención, domain lock |
| Session State | v1.4 | Persistencia de contexto |
| RADAR Orchestrator | v3.0 | 9 disciplinas analíticas |
| LLM Failover | Chain | Gemini → GPT → Groq → Lobotomy |
| ChromaDB | - | Embeddings semánticos |
| n8n CORTEX | v6 | Pipeline WhatsApp |
| Shopify API | - | E-commerce |
| Google Sheets | - | Auditoría |

### Lo que CAMBIA (Skin Layer)

| Elemento | Descripción |
|----------|-------------|
| Colores | Paleta CSS por industria |
| Logo | Branding específico |
| Catálogo | Productos/servicios/procedimientos |
| Respuestas | Canónicas por dominio |
| Triggers P1 | Keywords de industria |
| Voces | ElevenLabs Voice ID |
| Templates | WhatsApp por industria |
| Landing | Contenido HTML/React |

---

## Configuración de Industrias

### TRANSPORTE (SRM)

```yaml
industry: TRANSPORTE
branch: MOTOS
domain: somosrepuestosmotos.com
alias: larocamotorepuestos.com
webhook: odi.larocamotorepuestos.com

colors:
  primary: "#06B6D4"    # Cyan
  secondary: "#10B981"  # Verde
  accent: "#F97316"     # Naranja
  dark: "#0F172A"       # Slate 900
  light: "#F8FAFC"      # Slate 50

catalog:
  type: products
  collection: srm_catalog
  count: 13575

voice:
  primary: "qpjUiwx7YUVAavnmh2sF"  # Tony Maestro
  secondary: null                   # Ramona (pendiente)

triggers:
  - repuesto
  - moto
  - llanta
  - casco
  - aceite
```

### SALUD / Dental (Matzu)

```yaml
industry: SALUD
branch: DENTAL
domain: matzudentalaesthetics.com
alias: null
webhook: null  # Usa odi.larocamotorepuestos.com

colors:
  primary: "#14B8A6"    # Teal
  secondary: "#3B82F6"  # Azul
  accent: "#F59E0B"     # Amber
  dark: "#0F172A"
  light: "#F0FDFA"      # Teal 50

catalog:
  type: procedures
  collection: matzu_procedures
  count: 15

voice:
  primary: null   # Pendiente
  secondary: null

triggers:
  - implante
  - diseño de sonrisa
  - blanqueamiento
  - carillas
  - ortodoncia
  - matzu
```

### SALUD / Bruxismo (COVER'S)

```yaml
industry: SALUD
branch: BRUXISMO
domain: mis-cubiertas.com
alias: null

colors:
  primary: "#8B5CF6"    # Violeta
  secondary: "#06B6D4"  # Cyan
  accent: "#10B981"     # Verde
  dark: "#1E1B4B"       # Indigo 950
  light: "#F5F3FF"      # Violet 50

catalog:
  type: products
  collection: covers_products
  count: 8

triggers:
  - bruxismo
  - guarda oclusal
  - protector dental
  - rechinar dientes
  - covers
```

### SALUD / Capilar (Cabezas Sanas)

```yaml
industry: SALUD
branch: CAPILAR
domain: cabezasanas.com
alias: null

colors:
  primary: "#F59E0B"    # Amber
  secondary: "#10B981"  # Verde
  accent: "#06B6D4"     # Cyan
  dark: "#1C1917"       # Stone 900
  light: "#FFFBEB"      # Amber 50

catalog:
  type: treatments
  collection: cabezas_treatments
  count: 12

triggers:
  - alopecia
  - caída del cabello
  - tricología
  - injerto capilar
  - cabezas sanas
```

### CATRMU (Universal)

```yaml
industry: UNIVERSAL
branch: ALL
domain: catrmu.com
alias: null

colors:
  primary: "#EC4899"    # Pink
  secondary: "#8B5CF6"  # Violeta
  accent: "#06B6D4"     # Cyan
  dark: "#0F0F23"       # Custom dark
  light: "#FDF2F8"      # Pink 50

catalog:
  type: all
  collection: catrmu_universal
  count: dynamic

triggers:
  # Detecta automáticamente y rutea a industria
```

---

## Flujo de Routing

```
Usuario envía mensaje
        │
        ▼
┌───────────────────┐
│ Intent Override   │
│ Gate v1.5         │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐     ┌─────────────────┐
│ ¿Trigger P0?      │────▶│ SAFETY (siempre)│
└─────────┬─────────┘     └─────────────────┘
          │ No
          ▼
┌───────────────────┐     ┌─────────────────┐
│ ¿Session locked?  │────▶│ Usa skin actual │
└─────────┬─────────┘     └─────────────────┘
          │ No
          ▼
┌───────────────────┐
│ Detectar industria│
│ por triggers P1   │
└─────────┬─────────┘
          │
    ┌─────┴─────┬─────────┬─────────┐
    ▼           ▼         ▼         ▼
TRANSPORTE   SALUD    BELLEZA   DEFAULT
    │           │         │         │
    ▼           ▼         ▼         ▼
 Cargar      Cargar   Cargar    Cargar
 skin SRM    skin     skin      skin
             Matzu/   industria CATRMU
             COVER'S
```

---

## Archivos de Producción

| Archivo | Ubicación | Función |
|---------|-----------|---------|
| `industry_skins.py` | `/opt/odi/core/` | Configuración de skins |
| `skin_loader.py` | `/opt/odi/core/` | Cargador dinámico |
| `domain_router.py` | `/opt/odi/core/` | Router por dominio |
| `catrmu_config.json` | `/opt/odi/config/` | Config universal |

---

## DNS Requerido (IONOS)

| Dominio | Tipo | Destino | Estado |
|---------|------|---------|--------|
| catrmu.com | A | 64.23.170.118 | PENDIENTE |
| catrmu.com | CNAME www | catrmu.com | PENDIENTE |
| *.catrmu.com | A | 64.23.170.118 | PENDIENTE (wildcard) |

---

## Próximos Pasos

1. [x] Crear `CATRMU_ARCHITECTURE.md`
2. [x] Crear `industry_skins.py`
3. [ ] Deploy a `/opt/odi/core/`
4. [ ] Crear `skin_loader.py`
5. [ ] Configurar DNS catrmu.com
6. [ ] Test de routing por industria
7. [ ] Conectar dominios existentes

---

*"Una lógica, infinitas industrias."*
