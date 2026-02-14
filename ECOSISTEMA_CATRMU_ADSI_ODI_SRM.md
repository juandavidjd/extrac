# ECOSISTEMA CATRMU-ADSI-ODI-SRM

**Versión:** 1.0
**Fecha:** 11 Febrero 2026
**Estado:** Arquitectura Unificada

---

## Declaración Fundacional

> **CATRMU** contiene a **ADSI**, que implementa a **ODI**, que opera en **SRM** y otras industrias.
>
> Es una arquitectura de muñecas rusas: cada capa contiene y habilita a la siguiente.

---

## Jerarquía del Ecosistema

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              CATRMU                                           ║
║                    Canal Transversal Multitemático                            ║
║                      "Todo ODI en un solo punto"                              ║
║                          catrmu.com                                           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────┐    ║
║   │                            ADSI                                      │    ║
║   │            Arquitectura, Diseño, Sistemas e Implementación           │    ║
║   │                     ecosistema-adsi.com                              │    ║
║   │                                                                       │    ║
║   │   ┌─────────────────────────────────────────────────────────────┐   │    ║
║   │   │                         ODI                                  │   │    ║
║   │   │              Organismo Digital Industrial                    │   │    ║
║   │   │         liveodi.com / somosindustriasodi.com                │   │    ║
║   │   │                                                              │   │    ║
║   │   │   ┌───────────┐  ┌───────────┐  ┌───────────┐              │   │    ║
║   │   │   │TRANSPORTE │  │   SALUD   │  │  ENTRETEN │              │   │    ║
║   │   │   │           │  │           │  │           │              │   │    ║
║   │   │   │  ┌─────┐  │  │ ┌───────┐ │  │ ┌───────┐ │              │   │    ║
║   │   │   │  │ SRM │  │  │ │ Matzu │ │  │ │Turismo│ │              │   │    ║
║   │   │   │  └─────┘  │  │ ├───────┤ │  │ └───────┘ │              │   │    ║
║   │   │   │           │  │ │COVER'S│ │  │           │              │   │    ║
║   │   │   │           │  │ ├───────┤ │  │           │              │   │    ║
║   │   │   │           │  │ │Cabezas│ │  │           │              │   │    ║
║   │   │   └───────────┘  └─┴───────┴─┘  └───────────┘              │   │    ║
║   │   │                                                              │   │    ║
║   │   └─────────────────────────────────────────────────────────────┘   │    ║
║   │                                                                       │    ║
║   └─────────────────────────────────────────────────────────────────────┘    ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Definiciones

### CATRMU — Canal Transversal Multitemático
- **Qué es:** Punto de entrada universal a todas las industrias ODI
- **Dominio:** catrmu.com (+3 TLDs)
- **Función:** Routing inteligente a la industria correcta
- **Analogía:** El lobby de un edificio corporativo

### ADSI — Arquitectura, Diseño, Sistemas e Implementación
- **Qué es:** Metodología y plataforma de implementación
- **Dominio:** ecosistema-adsi.com (+3 TLDs)
- **Función:** Framework de construcción de organismos digitales
- **Analogía:** El sistema operativo

### ODI — Organismo Digital Industrial
- **Qué es:** Entidad cognitiva que opera en múltiples industrias
- **Dominios:** liveodi.com, somosindustriasodi.com
- **Función:** Procesamiento de intenciones, ejecución de tareas
- **Analogía:** El cerebro y sistema nervioso

### SRM — Somos Repuestos Motos (y otras verticales)
- **Qué es:** Implementación específica por industria
- **Dominios:** somosrepuestosmotos.com, larocamotorepuestos.com
- **Función:** Catálogo, ventas, servicio al cliente
- **Analogía:** Los órganos especializados

---

## Repositorios del Ecosistema

```
juandavidjd/
│
├── odi/                    ← Documentación conceptual
│   ├── CLAUDE_ODI_v5.2_PRODUCTION.md
│   ├── ACTA_CERTIFICACION_ODI_v17_1.md
│   └── 90+ PDFs arquitectónicos
│
├── odi-vende/              ← Producción (/opt/odi/)
│   ├── core/
│   │   ├── odi_core.py
│   │   ├── intent_override_gate.py
│   │   ├── industry_skins.py      ← NUEVO
│   │   ├── domain_handlers.py
│   │   └── radar_orchestrator.py
│   ├── config/
│   └── data/
│
├── extrac/                 ← Desarrollo activo
│   ├── CATRMU_ARCHITECTURE.md
│   ├── ECOSISTEMA_CATRMU_ADSI_ODI_SRM.md  ← ESTE ARCHIVO
│   ├── industry_skins.py
│   ├── intent_override_gate.py
│   └── landing-odi/
│       └── pages/
│           ├── catrmu.tsx
│           └── odi-os.tsx
│
├── extracii/               ← Scripts de extracción (827 archivos)
│   └── Scrapers, processors, catalog builders
│
├── PDF/                    ← Procesamiento de catálogos (470 archivos)
│   └── Web scrapers, PDF extraction, Shopify tools
│
└── cycle-nexus-pro/        ← Frontend React/Vite
    └── src/, supabase/
```

---

## Infraestructura de Producción

### Servidor Principal
```
IP: 64.23.170.118
OS: Ubuntu 24 LTS
Proveedor: DigitalOcean (~$24/mes)
```

### Docker Containers (7 activos)
| Container | Puerto | Función |
|-----------|--------|---------|
| odi-n8n | 5678 | Workflow engine (cerebro) |
| odi-voice | 7777 | Motor de voz ElevenLabs |
| odi-m62-fitment | 8802 | Motor de compatibilidad |
| odi-postgres | 5432 | Base de datos |
| odi-redis | 6379 | Cache, pub/sub |
| odi-prometheus | 9090 | Métricas |
| odi-grafana | 3000 | Dashboards |

### Dominios (27 total en IONOS)

| Nivel | Dominios | IP/Destino |
|-------|----------|------------|
| CATRMU | catrmu.com (+3) | 64.23.170.118 |
| ADSI | ecosistema-adsi.com (+3) | Vercel |
| ODI | liveodi.com (+3), somosindustriasodi.com (+3) | Vercel |
| SRM | somosrepuestosmotos.com, larocamotorepuestos.com (+3) | 64.23.170.118 |
| SALUD | matzudentalaesthetics.com, mis-cubiertas.com, cabezasanas.com (+3) | 64.23.170.118 |

---

## Flujo de Datos

```
                    Usuario envía mensaje
                            │
                            ▼
                    ┌───────────────┐
                    │   CATRMU      │  Punto de entrada universal
                    │  (Gateway)    │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │    ADSI       │  Clasificación y routing
                    │  (Framework)  │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │     ODI       │  Intent Override Gate
                    │   (Engine)    │  Domain Lock
                    └───────┬───────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
       ┌─────────┐    ┌─────────┐    ┌─────────┐
       │   SRM   │    │  SALUD  │    │ ENTRETEN│
       │(Motos)  │    │(Dental) │    │(Turismo)│
       └─────────┘    └─────────┘    └─────────┘
            │               │               │
            ▼               ▼               ▼
       ChromaDB        ChromaDB        ChromaDB
       Shopify         Leads           (Pendiente)
       WhatsApp        WhatsApp
```

---

## Componentes Core

### 1. Intent Override Gate (v1.5)
```python
# Prioridades de override
P0_CRITICAL  → SAFETY (emergencias)
P1_HIGH      → Cambio de industria
P2_MEDIUM    → Ajuste de contexto
P3_META      → Reset de identidad
```

### 2. Industry Skins
```python
SKINS_REGISTRY = {
    "SRM": SKIN_SRM,           # Transporte/Motos
    "MATZU": SKIN_MATZU,       # Salud/Dental
    "COVERS": SKIN_COVERS,     # Salud/Bruxismo
    "CABEZAS": SKIN_CABEZAS,   # Salud/Capilar
    "CATRMU": SKIN_CATRMU,     # Universal
}
```

### 3. RADAR v3.0 (9 disciplinas)
| Disciplina | Función |
|------------|---------|
| Bayesian Scorer | Ranking de productos |
| Markov Predictor | Predicción de intención |
| Product Graph | Recomendaciones |
| Monte Carlo | Riesgo de inventario |
| Anomaly Detector | Detección de fraude |
| Sentiment Analyzer | Análisis de tono |
| Funnel Tracker | Conversión |
| Wavelet Analysis | Ciclos |
| Topological Data | Clusters |

### 4. LLM Failover Chain
```
Gemini 2.5 Flash → GPT-4o-mini → Groq Llama 3.3 70B → Lobotomy
     ~1700ms          ~800ms           ~333ms            0ms
```

### 5. Dual Voice (Tony + Ramona)
| Persona | Voice ID | Rol |
|---------|----------|-----|
| Tony Maestro | qpjUiwx7YUVAavnmh2sF | Técnico (S1-S4) |
| Ramona Anfitriona | (pendiente) | Hospitalidad (S0, S5-S6) |

---

## APIs y Webhooks

| Endpoint | Función |
|----------|---------|
| odi.larocamotorepuestos.com/webhook/odi-ingest | WhatsApp entrante |
| odi.catrmu.com/webhook/universal | CATRMU universal |
| localhost:5678/webhook/* | n8n workflows |
| localhost:8802/fitment/* | Motor de compatibilidad |

---

## Métricas del Ecosistema

| Métrica | Valor |
|---------|-------|
| Productos totales | 13,575 |
| Tiendas Shopify | 10 |
| Leads turismo | 5 activos |
| Disciplinas RADAR | 9/9 |
| Subsistemas | 5/5 ACTIVO |
| Tests Intent Gate | 12/12 PASS |
| Tests Industry Skins | 11/11 PASS |

---

## Estado de Implementación

### Completado ✅
- [x] Intent Override Gate v1.5
- [x] Domain Lock + Session State
- [x] Industry Skins (5 skins)
- [x] RADAR v3.0 Orchestrator
- [x] P2 SALUD (Matzu, COVER'S, Cabezas Sanas)
- [x] Botón Turismo v1.6
- [x] LLM Failover Chain
- [x] DNS CATRMU configurado
- [x] CATRMU landing page

### Pendiente ⏳
- [ ] Deploy industry_skins.py a servidor
- [ ] Nginx vhost para catrmu.com
- [ ] SSL Certbot para catrmu.com
- [ ] Indexar contenido Matzu (110+ fotos)
- [ ] Indexar contenido COVER'S
- [ ] Asignar Voice ID de Ramona

---

## Comandos de Verificación

```bash
# Estado de containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Test industry skins
python3 /opt/odi/core/industry_skins.py

# Test intent override gate
python3 /opt/odi/core/intent_override_gate.py

# Logs de n8n
docker logs odi-n8n --tail 50 -f

# SSL status
certbot certificates

# DNS check
dig catrmu.com +short
```

---

## Principios del Ecosistema

1. **Una lógica, infinitas industrias** — El core permanece, la piel cambia
2. **ODI no responde, ODI procesa** — Sin invención de contenido
3. **Trazabilidad soberana** — Todo se audita, nada se borra
4. **Presencia universal** — ODI habita cualquier industria
5. **Triple solidez** — Validación en 3 capas antes de ejecutar

---

*"CATRMU es el contenedor. ADSI es el framework. ODI es el organismo. SRM es la especialización."*
