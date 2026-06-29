# ODI · ARTÍCULO CONSTITUCIONAL · SISTEMA OPERATIVO DEL HÁBITAT

**Fecha:** 2026-06-29  
**Estado:** Artículo constitucional aprobado para integración doctrinal  
**Alcance:** ODI, Hábitat, Dispatcher, Widget Core, Dual Surface, Onboarding Relacional  
**Tesis:** ODI no es una aplicación. ODI es el sistema operativo del hábitat.

---

# ARTÍCULO XX · ESPECIFICACIÓN DE SISTEMA OPERATIVO DEL HÁBITAT

ODI no opera bajo el paradigma de navegación documental —páginas, rutas, menús y botones aislados— sino bajo el paradigma de **proyección de capacidades**.

El habitante no visita aplicaciones.  
El habitante expresa necesidades, continúa flujos y toma decisiones.  
ODI interpreta el contexto, convoca la capacidad adecuada y proyecta la interfaz mínima necesaria para avanzar.

```text
La web no desaparece técnicamente.
Desaparece como carga cognitiva para el humano.
```

---

# 1. ODI COMO SISTEMA OPERATIVO

ODI se define estructuralmente como el sistema operativo del hábitat digital del habitante.

```text
ODI                       = Sistema operativo del hábitat
Dispatcher / Nervio       = Kernel scheduler
Guardian Layer            = Capa de seguridad y permisos
ChromaDB                  = Memoria semántica
PostgreSQL                = Estado persistente y registro
Widgets                   = Procesos visuales portables
Rutas públicas            = Modo compatibilidad
Hábitat                   = Escritorio vivo del habitante
P10/T10/SRM/Systeme.io    = Capacidades instaladas
```

La función de ODI no es mostrar más pantallas.  
La función de ODI es reducir fricción, sostener continuidad y proyectar solo lo necesario.

---

# 2. DISPATCHER COMO KERNEL SCHEDULER

El Dispatcher actúa como kernel scheduler.

No pregunta al habitante qué página desea abrir.  
Detecta qué proceso debe ejecutarse según la necesidad, el contexto, la memoria, el estado del flujo y las restricciones del Guardian.

```text
Necesidad del habitante
→ interpretación contextual
→ selección de capacidad
→ carga del widget
→ proyección visual
→ decisión humana mínima
→ continuidad del flujo
```

Mientras el Nervio no esté vivo, esta operación solo puede existir como simulación controlada o modo compatibilidad.

```text
Sin NERVE_ALIVE no hay inyección contextual real.
```

---

# 3. WIDGET CORE COMO PROCESO PORTABLE

Todo componente de interfaz ODI debe nacer como `Widget Core`.

Un `Widget Core` es un proceso visual portable que:

```text
recibe datos;
renderiza estado;
emite eventos;
expone acciones;
acepta evidencia;
no conoce la ruta;
no conoce el router;
no depende de navegación;
no decide dónde vive.
```

El widget debe poder ejecutarse en:

```text
1. Modo Compatibilidad:
   Ruta pública para Martha, socias, aliados o auditoría contractual.

2. Modo Hábitat:
   Contenedor contextual inyectado por el Dispatcher en el Puesto de Control.
```

---

# 4. PROHIBICIONES EN WIDGET CORE

Dentro de un `Widget Core` quedan prohibidas las dependencias de navegación:

```text
useRouter()
useParams()
usePathname()
<Link>
navigate()
window.location
dependencia directa del route tree
estado acoplado al layout público
lectura directa de query params dentro del widget
```

Si un widget necesita datos, los recibe por props.

Si necesita disparar una acción, emite un callback/evento.

Si necesita contexto del flujo, recibe `flow_payload`.

```text
props        = interfaz estándar
callbacks    = system calls
flow_payload = stdin del proceso
audit_ref    = trazabilidad del sistema
```

Un widget que necesita saber qué página lo hospeda está roto como proceso del hábitat.

---

# 5. DUAL SURFACE COMO MODO DE COMPATIBILIDAD

La Dual Surface no duplica sistemas.

Es un mecanismo de compatibilidad para resolver la tensión entre contrato y visión.

```text
Una capacidad.
Un widget.
Dos superficies.
```

```text
Public Projection:
  La ruta pública renderiza el widget para mostrar la feature prometida.

Habitat Projection:
  El Puesto de Control recibe el mismo widget dentro del flujo del habitante.
```

Ejemplo:

```text
MatchingEngine
→ MatchingWidget
→ /buscar para Modo Público
→ Widget_SugerenciaProfesional para Modo Hábitat
```

Martha ve plataforma.  
El habitante vive hábitat.  
El código es uno.  
La proyección es doble.

---

# 6. HUD ODI · INTERFAZ COMO PROYECCIÓN NECESARIA

Las referencias visuales de HUD flotante confirman la dirección conceptual: la interfaz no debe sentirse como página web, sino como capa de información proyectada cuando el contexto lo exige.

Pero ODI no adopta el espectáculo por sí mismo.

```text
Una card aparece solo si ayuda a continuar el flujo.
```

Toda card flotante ODI debe ser:

```text
contextual;
anclada a un flujo, persona, entidad, producto, documento o trámite;
accionable;
auditable;
portable;
humana;
no decorativa.
```

Prohibido:

```text
cards sin función;
HUD ornamental;
texto falso decorativo;
saturación permanente;
cyberpunk oscuro como estética obligatoria;
botones genéricos de soporte;
interfaces que invitan a navegar en vez de mostrar qué sigue.
```

---

# 7. PRIMER CONTACTO · INICIACIÓN DEL HABITANTE

ODI no hace onboarding convencional.  
ODI cultiva relación.

En el primer contacto, ODI sí se presenta, guía y revela alcance.

Después, si el habitante ya exploró el ecosistema, ODI no repite la presentación. La relación fluye con madurez, memoria y naturalidad.

Estados relacionales del habitante:

```text
new
  Necesita presentación y recorrido guiado.

exploring
  Ya empezó a conocer ODI, pero aún está formando mapa mental.

activated
  Ya usó ODI en un caso real.

mature
  Ya no necesita explicación institucional.

trusted
  ODI puede anticipar, sugerir y operar con mayor naturalidad.
```

Regla:

```text
Primera vez: ODI se explica.
Segunda etapa: ODI se demuestra.
Tercera etapa: ODI se vuelve útil.
Cuarta etapa: ODI se vuelve natural.
Quinta etapa: ODI se vuelve parte de la vida del habitante.
```

---

# 8. RECORRIDO GUIADO VISUAL

El primer contacto debe incluir recorrido guiado con apoyo de visuales, imágenes, clips, microanimaciones o cards flotantes.

Objetivo:

```text
revelar alcance;
mostrar capacidades;
enseñar canales;
activar una primera experiencia real;
registrar que el habitante ya exploró el ecosistema.
```

Secuencia recomendada:

```text
1. Qué es ODI.
2. Qué conecta.
3. Qué puede resolver.
4. Cómo actúa.
5. Cómo hablar con ODI: voz, texto, señas.
6. Primera experiencia real.
7. Registro progresivo de preferencias y estado relacional.
```

No repetir el tour si el estado relacional indica que el habitante ya lo completó.

---

# 9. PRINCIPIOS DE INTERFAZ

```text
La interfaz no debe invitar a hablar.
Debe mostrar qué sigue.
```

```text
El habitante no navega páginas.
El habitante decide sobre lo que ODI ya procesó.
```

```text
Si una card no ayuda a decidir, validar, entender, autorizar, corregir o avanzar, sobra.
```

```text
Si no se ve en el browser, no está hecho.
Si no corre fuera de una ruta, no es Widget Core.
Si depende del router, no es portable.
Si no tiene audit_ref, no pertenece al organismo.
```

---

# 10. RELACIÓN CON NERVE_ALIVE

Esta doctrina no declara vivo al Hábitat.

El Hábitat operativo requiere:

```text
RUNTIME_BRIDGE aplicado;
re-H2 exit 0;
first task real;
GLOBAL_HOLD resuelto;
NERVE_ALIVE certificado con evidencia.
```

Antes de NERVE_ALIVE:

```text
se pueden construir widgets;
se pueden montar rutas públicas;
se pueden crear simuladores de hábitat;
se puede certificar portabilidad;
no se puede declarar inyección contextual real.
```

Después de NERVE_ALIVE:

```text
el Dispatcher monta widgets según contexto real;
las capacidades se ejecutan como procesos del hábitat;
el habitante recibe continuidad, no navegación.
```

---

# VEREDICTO CONSTITUCIONAL

ODI no es una aplicación.

ODI es el sistema operativo del hábitat.

Las webs no desaparecen.  
Se vuelven drivers, ventanas y superficies compatibles que ODI ejecuta por el habitante.

La interfaz no invita a navegar.  
La interfaz muestra qué sigue.

**Somos Industrias ODI.**
