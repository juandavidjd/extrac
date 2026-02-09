# Mapa de Dominios y Jerarquía Digital ADSI-ODI-CATRMU

**Versión:** 1.0
**Fecha:** 9 Febrero 2026
**Arquitecto:** Juan David Jiménez
**Estado:** Ratificado

---

## Principio Constitucional

> **ODI no es un rol, ni un experto, ni una industria.
> ODI es una presencia transversal que potencia cualquier industria.**

```
❌ PROHIBIDO: "Soy experto mecánico / chef / abogado"
✅ CORRECTO:  "Soy ODI. Dime qué necesitas."
```

ODI no se adapta a la página.
La página se organiza alrededor de ODI.

---

## Jerarquía de Territorios

```
┌─────────────────────────────────────────────────────────────────┐
│                         CATRMU                                  │
│              Catálogo Taxonómico de Referencia                  │
│                   Mercantil Universal                           │
│         (El País / La Escala / El Lenguaje Verdadero)           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                        ADSi                               │  │
│  │     Arquitectura, Diseño, Sistemas e Implementación       │  │
│  │              (La Constitución / El Marco)                 │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │                      ODI                            │  │  │
│  │  │         Organismo Digital Industrial                │  │  │
│  │  │    (Presencia Universal / Motor de Ejecución)       │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │              INDUSTRIAS                       │  │  │  │
│  │  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐         │  │  │  │
│  │  │  │  │IND_MOTOS│ │IND_SALUD│ │ IND_X   │         │  │  │  │
│  │  │  │  │  (SRM)  │ │(CABEZA) │ │(FUTURO) │         │  │  │  │
│  │  │  │  └─────────┘ └─────────┘ └─────────┘         │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Relación:**
- SRM es al ADSi lo que una **ciudad piloto** es a una nación
- ADSi es la **constitución**
- CATRMU es el **país**

---

## Inventario de Dominios Activos

### Nivel 0 — ODI (Presencia Universal)

| Dominio | Función | Estado |
|---------|---------|--------|
| `liveodi.com` | Identidad central de ODI | ✅ Activo |
| `liveodi.com/supervision.html` | Dashboard de supervisión real-time | ✅ Activo |
| `odi.larocamotorepuestos.com` | Webhook WhatsApp + APIs | ✅ Producción |

**Estructura propuesta:**
```
liveodi.com/
├── /                    → Quién es ODI (presencia)
├── /supervision         → Dashboard real-time (WebSocket)
├── /manifiesto          → MANIFIESTO_ODI.md renderizado
└── /estado              → Guardian status público
```

### Nivel 1 — ADSi (Constitución)

| Dominio | Función | Estado |
|---------|---------|--------|
| `ecosistema-adsi.com` | Marco constitucional ADSi | ✅ Activo |
| `ecosistema-adsi.online` | Alias/Redirect | Disponible |
| `ecosistema-adsi.info` | Alias/Redirect | Disponible |

**Estructura propuesta:**
```
ecosistema-adsi.com/
├── /                    → Qué es ADSi (metodología)
├── /constitucion        → Triple Solidez, Artículos
├── /metodologia         → ADSI explicado
├── /auditoria-publica   → Transparencia radical
├── /registro            → Onboarding de empresas
└── /casos               → Casos de éxito (SRM primero)
```

### Nivel 2 — Industrias (IND_*)

#### IND_MOTOS (Ciudad Piloto: SRM)

| Dominio | Función | Estado |
|---------|---------|--------|
| `somosrepuestosmotos.com` | Vertical motos B2B | ✅ Activo |
| `somosrepuestosmotos.online` | Alias | Disponible |
| `somosrepuestosmotos.info` | Alias | Disponible |

**Estructura:**
```
somosrepuestosmotos.com/
├── /                    → Landing industria motos
├── /clientes            → Lista de 10 tiendas
├── /marcas/             → Catálogo por marca
│   ├── /bara
│   ├── /yokomar
│   ├── /kaiqi
│   ├── /dfg
│   ├── /duna
│   ├── /imbra
│   ├── /japan
│   ├── /leo
│   ├── /store
│   └── /vaisand
├── /buscar              → Búsqueda semántica ODI
└── /contacto            → WhatsApp directo
```

#### IND_SALUD (Latente)

| Dominio | Función | Estado |
|---------|---------|--------|
| `cabezasanas.com` | Vertical salud mental | Parqueado |
| `cabezasanas.online` | Alias | Parqueado |
| `cabezasanas.info` | Alias | Parqueado |

#### Otros Dominios Disponibles

| Dominio | Posible Uso |
|---------|-------------|
| `miclusters.com` | Gestión de clusters industriales |
| `larocamotorepuestos.com` | Negocio principal La Roca |
| `somosindustrias.com` | Portal multi-industria |

---

## Meta-Intents con Ruteo a Páginas

ODI enruta soberanamente. No explica todo, deriva.

| Intent | Trigger | Response | Página Destino |
|--------|---------|----------|----------------|
| `QUIEN_ERES` | "quién eres" | "Soy ODI. Dime qué necesitas." | (No deriva, responde) |
| `EMPRESAS` | "qué empresas tienen" | Lista de 10 tiendas | `somosrepuestosmotos.com/clientes` |
| `AYUDA` | "cómo funciona esto" | Descripción de ODI | `ecosistema-adsi.com` |
| `REGISTRO` | "quiero registrarme" | Solicita nombre y correo | `ecosistema-adsi.com/registro` |
| `INFO_MARCA` | "qué vende duna" | Pide especificar producto | `somosrepuestosmotos.com/marcas/duna` |
| `SUPERVISION` | "estado del sistema" | Link a dashboard | `liveodi.com/supervision` |
| `MANIFIESTO` | "cuáles son tus reglas" | Link a constitución | `liveodi.com/manifiesto` |

---

## Estilo Visual: ADN de Supervisión

Todas las páginas del ecosistema heredan el ADN visual de `supervision.html`:

### Paleta de Colores

| Nombre | Código | Uso |
|--------|--------|-----|
| **Oscuridad Industrial** | `#0a0a0f` | Fondo principal |
| **Carbón Profundo** | `#1a1a2e` | Cards, contenedores |
| **Cian Vivo** | `#00d4ff` | Datos activos, enlaces |
| **Verde Guardian** | `#00ff88` | Estado OK, confirmaciones |
| **Amarillo Alerta** | `#ffcc00` | Warnings, atención |
| **Rojo Crítico** | `#ff4444` | Errores, bloqueos |
| **Blanco Dato** | `#ffffff` | Texto principal |
| **Gris Secundario** | `#888888` | Texto secundario |

### Principios de Diseño

1. **Oscuridad Industrial**
   Fondos profundos que evocan el "córtex" nocturno donde ODI trabaja.

2. **Neon de Estado**
   Cian y verde para flujos de datos "vivos" y estado del Guardian.

3. **Transparencia de Datos**
   Bloques de código, JSONs expandibles, trazas visibles.
   **La auditoría es pública.**

4. **Tipografía Monospace**
   `JetBrains Mono`, `Fira Code`, o `IBM Plex Mono` para datos técnicos.

5. **Sin Decoración Vacía**
   Cada elemento tiene función. No hay ornamentos.

### CSS Base

```css
:root {
  --odi-dark: #0a0a0f;
  --odi-card: #1a1a2e;
  --odi-cyan: #00d4ff;
  --odi-green: #00ff88;
  --odi-yellow: #ffcc00;
  --odi-red: #ff4444;
  --odi-text: #ffffff;
  --odi-muted: #888888;
}

body {
  background: var(--odi-dark);
  color: var(--odi-text);
  font-family: 'JetBrains Mono', monospace;
}

.card {
  background: var(--odi-card);
  border: 1px solid var(--odi-cyan);
  border-radius: 8px;
  padding: 1.5rem;
}

.status-ok { color: var(--odi-green); }
.status-warn { color: var(--odi-yellow); }
.status-error { color: var(--odi-red); }
.data-live { color: var(--odi-cyan); }
```

---

## Inventario de Activos del Organismo (v3.6)

### 1. Infraestructura de Soberanía (El Cuerpo)

| Activo | Descripción |
|--------|-------------|
| Servidor | `64.23.170.118` (DigitalOcean, Ubuntu 24 LTS) |
| Containers | 7 Docker activos (n8n, postgres, redis, voice, fitment, prometheus, grafana) |
| Volumen | `/mnt/volume_sfo3_01/` (datos pesados) |
| SSL | Let's Encrypt, auto-renovación |
| Reverse Proxy | Nginx |

### 2. Núcleo Cognitivo (El Hipocampo)

| Activo | Capacidad |
|--------|-----------|
| ChromaDB | 21,554 documentos semánticos |
| GPT-4o | Cerebro principal |
| Gemini 1.5 Pro | Router semántico, backup |
| Embeddings | Vectores para búsqueda rápida |

### 3. Capa Operativa (Los Órganos)

| Activo | Métrica |
|--------|---------|
| Shopify | 10 tiendas, 13,575 productos |
| WhatsApp | +57 322 5462101, 6 templates aprobados |
| ElevenLabs | Tony Maestro (activo), Ramona (pendiente) |
| Fitment | 1,865 modelos de motos |

### 4. Gobernanza (Sistema Inmune)

| Activo | Estado |
|--------|--------|
| Guardian | 🟢 Verde |
| Manifiesto | Artículo 0 ratificado |
| Triple Solidez | Activa |
| RADAR v3.0 | Monitoreo 24/7 |

---

## Flujo de Navegación del Usuario

```
Usuario llega
      │
      ▼
┌─────────────────────────────┐
│  "Soy ODI. Dime qué        │
│   necesitas."              │
└─────────────┬───────────────┘
              │
    ┌─────────┼─────────┬────────────┐
    ▼         ▼         ▼            ▼
 COMPRAR   ENTENDER   REGISTRAR   SUPERVISAR
    │         │          │            │
    ▼         ▼          ▼            ▼
  SRM      ADSI      ADSI        LIVEODI
 /marcas  /metodo   /registro   /supervision
```

---

## Próximos Pasos

1. **Blueprint Visual**
   Crear wireframes de cada página principal usando el estilo Supervisión.

2. **Implementación ecosistema-adsi.com**
   Desplegar estructura propuesta en Vercel.

3. **Unificación de navegación**
   Menú común entre liveodi.com, ecosistema-adsi.com, somosrepuestosmotos.com.

4. **CASO 001**
   Ejecutar primera venta real para validar todo el flujo.

---

## Firma

```
Arquitecto: Juan David Jiménez
Sistema: ODI v17.3
Documento: MAPA_DOMINIOS_ADSI.md v1.0
Fecha: 2026-02-09
```

---

*"ODI no se adapta a la página. La página se organiza alrededor de ODI."*
