# Cycle Nexus Pro — Análisis e Integración ODI

**Versión:** 1.0
**Fecha:** 10 Febrero 2026
**Repositorio:** https://github.com/juandavidjd/cycle-nexus-pro
**Commits:** 90
**Estado:** Frontend SRM operativo

---

## Resumen Ejecutivo

**Cycle Nexus Pro** es el frontend oficial de SRM (Somos Repuestos Motos), construido en Lovable con React + TypeScript + Supabase. Este documento detalla su estructura y cómo integrarlo con la arquitectura ODI.

---

## Stack Tecnológico

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **React** | 18.3.1 | UI Framework |
| **TypeScript** | 5.8.3 | Tipado estático |
| **Vite** | 5.4.19 | Build tool |
| **Tailwind CSS** | 3.4.17 | Estilos |
| **shadcn-ui** | Latest | Componentes UI |
| **Supabase** | 2.86.2 | Auth + Database + Edge Functions |
| **React Query** | 5.83.0 | State management |
| **React Router** | 6.30.1 | Routing |
| **Recharts** | 2.15.4 | Gráficos |
| **Zod** | 3.25.76 | Validación |

---

## Estructura del Proyecto

```
cycle-nexus-pro/
├── src/
│   ├── App.tsx                    → Router principal
│   ├── main.tsx                   → Entry point
│   │
│   ├── pages/
│   │   ├── Index.tsx              → Landing page (Hero + Stats)
│   │   ├── Catalogo.tsx           → Catálogo SRM (5 categorías)
│   │   ├── Clientes.tsx           → Lista de clientes
│   │   ├── ClientPage.tsx         → Página dinámica por cliente
│   │   ├── Intelligent.tsx        → SRM Intelligent Processor
│   │   ├── Academia.tsx           → Academia SRM (20 módulos)
│   │   ├── AcademiaModulo.tsx     → Vista de módulo individual
│   │   ├── Auth.tsx               → Login/Register
│   │   └── NotFound.tsx           → 404
│   │
│   ├── components/
│   │   ├── agents/
│   │   │   ├── AgentChat.tsx      → Chat con agentes IA
│   │   │   └── SRMAgentsSuite.tsx → Suite de 5 agentes
│   │   │
│   │   ├── catalog/
│   │   │   ├── CategoryCard.tsx   → Card de categoría
│   │   │   ├── NewsTicker.tsx     → Noticias rotativas
│   │   │   └── AcademiaSection.tsx→ Sección academia
│   │   │
│   │   ├── intelligent/
│   │   │   ├── SRMIntelligentProcessor.tsx
│   │   │   ├── SRM360Viewer.tsx
│   │   │   ├── SRMPipelineVisual.tsx
│   │   │   └── SRMTechnicalChat.tsx
│   │   │
│   │   ├── NavigationHeader.tsx   → Header global
│   │   ├── FooterSRM.tsx          → Footer global
│   │   ├── SRMButton.tsx          → Botón estilizado
│   │   └── CatalogGrid.tsx        → Grid de productos
│   │
│   ├── data/
│   │   ├── catalog-categories.ts  → 5 categorías + 9 clientes
│   │   └── academia-modules.ts    → 20 módulos + 5 niveles
│   │
│   ├── hooks/
│   │   ├── useAuth.tsx            → Hook de autenticación
│   │   └── use-mobile.tsx         → Detección móvil
│   │
│   └── integrations/
│       └── supabase/
│           └── client.ts          → Cliente Supabase
│
├── supabase/
│   ├── config.toml                → Config (project_id: xljdaioompdmuxmbjgze)
│   ├── migrations/                → Migraciones DB
│   └── functions/
│       └── srm-agents/
│           └── index.ts           → Edge Function (5 agentes)
│
├── public/
│   └── logos/                     → Logos de clientes
│
├── .env                           → Variables de entorno
├── tailwind.config.ts             → Config Tailwind
└── package.json                   → Dependencias
```

---

## Rutas de la Aplicación

| Ruta | Componente | Descripción |
|------|------------|-------------|
| `/` | Index | Landing page con carousel |
| `/catalogo` | Catalogo | 5 categorías + news ticker |
| `/clientes` | Clientes | Lista de 9 clientes activos |
| `/intelligent` | Intelligent | SRM Intelligent Processor |
| `/academia` | Academia | 20 módulos, 5 niveles |
| `/academia/modulo/:id` | AcademiaModulo | Módulo individual |
| `/auth` | Auth | Login/Register con Supabase |
| `/:clientId` | ClientPage | Página dinámica por cliente |

---

## Categorías del Catálogo

| ID | Categoría | Clientes | Gradiente |
|----|-----------|----------|-----------|
| `fabricantes` | Fabricantes | Japan, Leo | `red → orange` |
| `importadores` | Importadores | Bara, DFG, Duna, Yokomar, Vaisand | `blue → cyan` |
| `distribuidores` | Distribuidores | Kaiqi Parts, Store | `green → emerald` |
| `almacenes` | Almacenes | Kaiqi Parts, Store | `purple → pink` |
| `talleres` | Talleres | Kaiqi Parts | `amber → yellow` |

---

## Agentes IA (Edge Function)

La edge function `/srm-agents` implementa 5 agentes especializados:

| Agente | Tipo | Función |
|--------|------|---------|
| **Voice** | `voice` | Guiones para ElevenLabs (45-90s) |
| **Designer** | `designer` | Piezas gráficas Freepik/Canva |
| **Instructor** | `instructor` | Cursos Academia SRM |
| **Sales** | `sales` | PNL y neuromarketing |
| **Architect** | `architect` | Roles y permisos |

**Modelo IA:** `google/gemini-2.5-flash` via Lovable AI Gateway

**Autenticación:** JWT requerido (Supabase Auth)

---

## Academia SRM

### 5 Niveles

| Nivel | Título | Módulos |
|-------|--------|---------|
| 1 | Fundamentos SRM | 1, 2, 3 |
| 2 | Técnica SRM | 4, 5, 6, 7 |
| 3 | Ventas e Inventarios 360° | 8, 9, 10, 11 |
| 4 | Especialización por Rol | 12-17 |
| 5 | Certificación SRM PRO | 18, 19, 20 |

### 20 Módulos Implementados

- Módulo 1: Fundamentos de la Motocicleta
- Módulo 2: Terminología Técnica SRM
- ...hasta Módulo 20: Certificación SRM PRO

---

## Integración con ODI

### Arquitectura de Conexión

```
┌─────────────────────────────────────────────────────────────────┐
│                         ECOSISTEMA ODI                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────┐         ┌─────────────────┐              │
│   │  CYCLE-NEXUS    │         │     ODI         │              │
│   │   (Frontend)    │◄───────►│   (Backend)     │              │
│   │                 │         │                 │              │
│   │ • React/TS      │         │ • n8n workflows │              │
│   │ • Supabase      │         │ • WhatsApp API  │              │
│   │ • 5 Agentes IA  │         │ • ChromaDB      │              │
│   │ • Academia      │         │ • Shopify API   │              │
│   └────────┬────────┘         └────────┬────────┘              │
│            │                           │                        │
│            │         ┌─────────────────┘                        │
│            │         │                                          │
│            ▼         ▼                                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    LIVEODI.COM                          │   │
│   │                  (Interfaz VIVIR)                       │   │
│   │                                                         │   │
│   │  • Overlay permanente                                   │   │
│   │  • Cards efímeras                                       │   │
│   │  • Intent Override Gate                                 │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Puntos de Integración

| Componente Frontend | Conexión ODI | Método |
|---------------------|--------------|--------|
| `AgentChat.tsx` | ODI Cortex | REST API + Streaming |
| `SRMIntelligentProcessor.tsx` | Pipeline ODI | n8n webhook |
| Auth (Supabase) | ODI Actor Registry | JWT validation |
| Catálogo | ChromaDB | Semantic search |
| Academia | ODI Knowledge Base | Tony chunks |

### Webhooks Propuestos

| Endpoint | Función |
|----------|---------|
| `POST /api/odi/intent` | Clasificar intent de usuario |
| `POST /api/odi/search` | Búsqueda semántica ChromaDB |
| `POST /api/odi/catalog` | Procesar catálogo (pipeline) |
| `GET /api/odi/status` | Estado Guardian + sistema |

---

## Variables de Entorno

```env
# Supabase
VITE_SUPABASE_URL=https://xljdaioompdmuxmbjgze.supabase.co
VITE_SUPABASE_ANON_KEY=[key]

# ODI Integration (propuestas)
VITE_ODI_API_URL=https://odi.larocamotorepuestos.com
VITE_ODI_WEBHOOK_URL=https://odi.larocamotorepuestos.com/webhook
```

---

## Migración a LIVEODI

Para evolucionar de "web tradicional" a interfaz VIVIR:

### Fase 1: Conectar APIs

```typescript
// src/integrations/odi/client.ts
export const odiClient = {
  classify: async (message: string) => {
    return fetch(`${ODI_API}/intent`, {
      method: 'POST',
      body: JSON.stringify({ message })
    });
  },
  search: async (query: string) => {
    return fetch(`${ODI_API}/search`, {
      method: 'POST',
      body: JSON.stringify({ query })
    });
  }
};
```

### Fase 2: Intent Override

```typescript
// src/hooks/useODIIntent.ts
export const useODIIntent = () => {
  const classify = async (message: string) => {
    const { category, industry, override } = await odiClient.classify(message);

    if (override) {
      // Cambiar contexto según INTENT_OVERRIDE_GATE.md
      handleOverride(override.level, override.action);
    }

    return { category, industry };
  };

  return { classify };
};
```

### Fase 3: Overlay VIVIR

```typescript
// src/components/vivir/VIVIROverlay.tsx
export const VIVIROverlay = () => {
  const [cards, setCards] = useState<EphemeralCard[]>([]);

  return (
    <div className="fixed inset-0 pointer-events-none z-50">
      {/* Llama central */}
      <ODIFlame status={guardianStatus} />

      {/* Cards efímeras */}
      {cards.map(card => (
        <EphemeralCard key={card.id} {...card} />
      ))}
    </div>
  );
};
```

---

## Clientes Activos (9)

| Cliente | Shopify | Categoría |
|---------|---------|-----------|
| Japan | 7cy1zd-qz.myshopify.com | Fabricante |
| Leo | h1hywg-pq.myshopify.com | Fabricante |
| Bara | 4jqcki-jq.myshopify.com | Importador |
| DFG | 0se1jt-q1.myshopify.com | Importador |
| Duna | ygsfhq-fs.myshopify.com | Importador |
| Yokomar | u1zmhk-ts.myshopify.com | Importador |
| Vaisand | z4fpdj-mz.myshopify.com | Importador |
| Kaiqi Parts | u03tqc-0e.myshopify.com | Distribuidor |
| Store | 0b6umv-11.myshopify.com | Distribuidor |

---

## Comandos de Desarrollo

```bash
# Instalar dependencias
cd /home/user/cycle-nexus-pro
npm install

# Desarrollo local
npm run dev

# Build producción
npm run build

# Preview build
npm run preview

# Lint
npm run lint
```

---

## Próximos Pasos

1. **[ ] Configurar webhooks ODI** en Supabase Edge Functions
2. **[ ] Conectar ChromaDB** para búsqueda semántica
3. **[ ] Implementar Intent Override Gate** en frontend
4. **[ ] Crear componente VIVIROverlay** para interfaz transparente
5. **[ ] Sincronizar datos** con 10 tiendas Shopify reales
6. **[ ] Activar Tony** para procesar KB chunks

---

*"cycle-nexus-pro es la piel visual de ODI. LIVEODI es su forma de habitar el mundo."*
