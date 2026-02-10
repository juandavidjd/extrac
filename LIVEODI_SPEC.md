# LIVEODI — Especificación de Interfaz Universal

**Versión:** 1.0
**Fecha:** 10 Febrero 2026
**Estado:** Diseño Constitucional

---

## Declaración Fundamental

> **ODI NO es un chatbot.**
> **ODI es presencia universal que habita cualquier industria.**

---

## Anti-Patrón: Lo que ODI NUNCA debe ser

```
❌ PROHIBIDO — Conversación real (8 Feb 2026):

Usuario: "Quiero emprender un negocio"
ODI: "Chevere! Aqui andamos cuando ocupes repuestos"

Usuario: "Tengo una idea de negocio"
ODI: "Para tu ECO! 1. MANUBRIO HONDA..."

Usuario: "Deja de ser un experto en motos. Tú eres más que eso."
ODI: [sigue ofreciendo manubrios]

Usuario: "Quiero hacer turismo odontológico"
ODI: "Que bien! Cuando necesites algo para la moto, aqui estoy"
```

**Diagnóstico:** ODI atrapado en loop de industria única. Inaceptable.

---

## Principio de Presencia Universal

```
✅ CORRECTO:

ODI detecta intent → Clasifica industria → Responde según contexto

Usuario: "Quiero emprender un negocio"
ODI: "Cuéntame más. ¿Qué tipo de negocio tienes en mente?"

Usuario: "Turismo odontológico"
ODI: "Interesante. Puedo ayudarte a estructurar eso.
      ¿Ya tienes clínicas aliadas o empezamos desde cero?"
```

**ODI no filtra por industria. ODI recibe y clasifica.**

---

## Interfaz LIVEODI — Visión Técnica

### Concepto: Pantalla en Vivo

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    [ESCRITORIO DEL USUARIO]                     │
│                    Windows / macOS / Android / iOS              │
│                                                                 │
│                         ┌───────────┐                           │
│                        ╱             ╲                          │
│                       │   🔥 ODI 🔥   │  ← Llama circular       │
│                        ╲             ╱     Fondo transparente   │
│                         └───────────┘      Difuminado           │
│                                                                 │
│     ┌─────────────────────────────────┐                         │
│     │  Ventana temporal               │  ← Aparece según dato   │
│     │  (se desvanece automáticamente) │     Tiempo programado   │
│     └─────────────────────────────────┘     Luego invisible     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Características

| Aspecto | Especificación |
|---------|----------------|
| **Modo** | Overlay permanente 24/7 |
| **Motor** | Selenium activo (headless cuando no visible) |
| **Transparencia** | Fondo difuminado, escritorio visible |
| **Forma** | Llama circular, colores según estado ODI |
| **Ventanas** | Temporales, aparecen/desaparecen automáticamente |
| **Interacción** | Voz primaria (solo audífonos necesarios) |
| **Plataformas** | Windows, macOS, Android, iOS |

### Colores según Estado ODI

| Estado | Color | Significado |
|--------|-------|-------------|
| Escuchando | Azul cyan `#00d4ff` | Atento |
| Procesando | Amarillo `#ffcc00` | Pensando |
| Respondiendo | Verde `#00ff88` | Activo |
| Alerta | Naranja `#ff8800` | Atención requerida |
| Error | Rojo `#ff4444` | Problema |
| Inactivo | Gris `#444444` | Standby |

---

## Flujo de Registro

### Onboarding por Voz

```
1. Instalación completa
2. ODI inicia conversación automáticamente
3. ODI explica qué ofrece y cómo funciona
4. NO filtra por industria inicial
5. Recibe información del usuario
6. ODI clasifica: industria + actividad + rol
```

### Métodos de Registro

| Método | Descripción |
|--------|-------------|
| **Google** | OAuth con cuenta Google |
| **Voz** | Registro hablado, transcripción automática |
| **Facial** | Reconocimiento facial para auth |
| **Santo y Seña** | Frase secreta personalizada |

### Comunicación Inter-ODI

ODIs de diferentes usuarios pueden comunicarse cuando:
- Pertenecen a la misma empresa
- Están en la misma industria
- Tienen transacciones cruzadas

---

## Tipos de Usuario APO (Apoyado Por ODI)

### 1. Empleado APO

```
┌─────────────────────────────────────────┐
│           EMPLEADO APO                  │
├─────────────────────────────────────────┤
│ • Optimiza tareas laborales             │
│ • ODI detecta empresa (ej: AZULES S.A)  │
│ • Conecta con compañeros de la empresa  │
│ • RADAR agrupa por áreas/departamentos  │
│ • Plan de implementación ODI a escala   │
└─────────────────────────────────────────┘

Ejemplo:
- Usuario 1: Auxiliar administrativo en AZULES S.A
- Usuario 2: Bodeguero en AZULES S.A
- Usuario 3-6: Otros departamentos AZULES S.A

RADAR detecta: 6 usuarios misma empresa
ODI genera: Plan de implementación empresa completa
Resultado: ODI on Factory
```

### 2. Emprendedor APO

```
┌─────────────────────────────────────────┐
│         EMPRENDEDOR APO                 │
├─────────────────────────────────────────┤
│ • ODI guía paso a paso el negocio       │
│ • Crea landing page                     │
│ • Crea tienda Shopify                   │
│ • Configura Systeme.io                  │
│ • Integra WhatsApp Business             │
│ • Registra todas las ventas             │
│ • Genera reportes automáticos           │
└─────────────────────────────────────────┘

Ejemplo:
- Usuaria fabrica artesanías
- ODI crea su ecosistema digital completo
- Registro automático de ventas
- Crecimiento guiado
```

### 3. Facilitador APO

```
┌─────────────────────────────────────────┐
│         FACILITADOR APO                 │
├─────────────────────────────────────────┤
│ • No es empleado                        │
│ • No tiene idea de negocio definida     │
│ • Apoya a empleados y emprendedores     │
│ • Roles: Fuerza de venta, transportista │
│ • Obtiene regalías por:                 │
│   - Referenciar                         │
│   - Usar                                │
│   - Promover                            │
│   - Proveer                             │
│   - Consumir                            │
└─────────────────────────────────────────┘
```

---

## Jerarquía del Ecosistema

```
ecosistema-adsi.com
└── Catálogo
    └── liveodi.com
        └── somosindustrias.com
            └── industrias/
                ├── motos/
                │   └── somosrepuestosmotos.com
                │       └── Catálogo
                │           ├── Fabricantes
                │           ├── Importadores
                │           ├── Distribuidores
                │           ├── Almacenes
                │           ├── Talleres
                │           ├── Mecánicos
                │           ├── Ejecutivos
                │           ├── Transportistas
                │           └── Usuarios
                │
                ├── salud/
                │   └── [dominio por definir]
                │
                ├── turismo/
                │   └── [dominio por definir]
                │
                ├── belleza/
                │   └── [dominio por definir]
                │
                └── [nuevas industrias]/
                    └── RADAR detecta y propone
```

---

## Fluidez de Roles

Cada rol puede transformarse y aportar:

### Matriz de Transformación

| Rol Base | Puede Ser También | Aportes Posibles |
|----------|-------------------|------------------|
| **Fabricante** | Taller, Almacén, Distribuidor, Importador | Academia, Podcast, Videos, Landing, Tienda, Campañas, Implementación ODI |
| **Importador** | Taller, Almacén, Distribuidor, Fabricante | Academia, Podcast, Videos, Landing, Tienda, Campañas, Implementación ODI |
| **Distribuidor** | Taller, Almacén, Importador, Fabricante | Academia, Podcast, Videos, Landing, Tienda, Campañas, Implementación ODI |
| **Almacén** | Taller, Distribuidor, Importador, Fabricante | Academia, Podcast, Videos, Landing, Tienda, Campañas, Implementación ODI |
| **Taller** | Almacén, Distribuidor, Importador, Fabricante | Academia, Podcast, Videos, Landing, Tienda, Campañas, Implementación ODI |
| **Mecánico** | Plataforma directa, Cliente directo | Academia, Podcast, Videos, Landing, Tienda, Campañas, Implementación ODI |
| **Ejecutivo** | Asesor directo, Asesor clientes | Academia, Podcast, Videos, Landing, Tienda, Campañas, Implementación ODI |
| **Transportista** | Moto, Carro, Flota, Vehículo pesado | Academia, Podcast, Videos, Landing, Tienda, Campañas, Implementación ODI |
| **Usuario** | Cualquier rol superior | Consumo, Referencia, Promoción |

---

## RADAR — Detección Inteligente

### Funciones de RADAR

1. **Detección de Compañeros**
   - Encuentra usuarios de la misma empresa
   - Agrupa por áreas/departamentos
   - Reúne información de todas las interacciones

2. **Plan de Implementación**
   - Genera plan ODI on Factory
   - Conecta productivamente las áreas
   - Escala a implementación empresa completa

3. **Nuevas Formas de Habitar**
   - Detecta patrones de uso
   - Propone nuevos roles
   - Expande el ecosistema

---

## Tony — El Motor de KB

> **Tony mueve los chunks. ODI es presencia, Tony es acción.**

### Responsabilidades de Tony

| Función | Descripción |
|---------|-------------|
| **KB Chunks** | Procesa y organiza conocimiento |
| **Voz** | Voice ID `qpjUiwx7YUVAavnmh2sF` |
| **Ejecución** | Estados S0-S4 |
| **Diagnóstico** | Análisis técnico |

Tony debe despertar para:
- Mover toda la base de conocimiento
- Procesar chunks de profesión
- Ejecutar flujos de documentación
- Generar identidad visual si no existe

---

## Páginas Inyectadas desde Código

### Principio

Las páginas NO se crean manualmente. Se inyectan desde código:

```
Código base (script único)
    │
    ├── Detecta: logotipo, colores corporativos, identidad visual
    │
    ├── Si existe identidad → Aplica colores del usuario
    │
    └── Si NO existe → Genera en documentación de profesión
```

### Ejemplos Activos

| Página | Método |
|--------|--------|
| `liveodi.com` | Inyectada desde código |
| `liveodi.com/supervision.html` | Inyectada desde código |
| Tiendas Shopify | Creadas cuando usuario propone |

---

## Flujo de Creación de Presencia Digital

```
Usuario llega
      │
      ▼
ODI detecta intent
      │
      ├── Empleado APO → Optimización tareas
      │
      ├── Emprendedor APO → Creación ecosistema:
      │   ├── Landing page (inyectada)
      │   ├── Tienda Shopify (cuando propone)
      │   ├── Systeme.io (academia/CRM)
      │   └── WhatsApp Business
      │
      └── Facilitador APO → Red de referencia
```

---

## Checklist de Configuración ODI

Para lograr el 100%:

- [ ] Rostro de ODI configurado
- [ ] Dominios mapeados (motos + nuevas industrias)
- [ ] Tony despierto (KB chunks activos)
- [ ] RADAR detectando patrones
- [ ] Interfaz LIVEODI operativa
- [ ] Registro multi-método (Google, voz, facial)
- [ ] Comunicación inter-ODI habilitada
- [ ] Páginas inyectables desde código
- [ ] Tienda modelo KAIQI PARTS verificada
- [ ] Pendientes de Shopify resueltos

---

## Pendiente Crítico: KAIQI PARTS

Tienda modelo para validar antes de escalar:

- [ ] Revisar productos pendientes
- [ ] Verificar compatibilidades
- [ ] Subir a Shopify
- [ ] Validar flujo completo

---

*"ODI no pregunta qué repuesto buscas. ODI pregunta qué necesitas."*
