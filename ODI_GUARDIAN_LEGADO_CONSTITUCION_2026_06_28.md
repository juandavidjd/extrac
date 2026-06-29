





INDUSTRIAS ODI
 

ODI GUARDIAN LEGADO
SISTEMA DE PRESERVACIÓN Y CONTINUIDAD DEL LEGADO DIGITAL


 

Módulo constitucional del organismo ODI
28 de junio de 2026
Juan David Jiménez Sierra — Arquitecto ADSI-ODI



ODI no solo te atiende en vida. Cuida tu obra cuando ya no puedas.






ADSI — Análisis, Diseño, Desarrollo, Implementación
Conocimiento | Colaboración | Tecnología
 
1. Principio Fundacional
Toda obra humana es temporal si depende únicamente de su creador. Un profesional con 35 años de conocimiento, un arquitecto de software con miles de líneas de código, un empresario con relaciones comerciales cultivadas durante décadas: todo ese valor se evapora cuando la persona que lo acumula no puede continuar.
Guardian Legado es la cuarta y última dimensión del Guardian Layer de ODI. Completa el sistema de protección del habitante extendiéndolo más allá de su presencia activa. No es un producto adicional. No se cobra por separado. Está embebido en el organismo como derecho constitucional de todo habitante.
Si ODI conoce tu trabajo, ODI protege tu trabajo. En vida y después de ella.
1.1 Posición en el Guardian Layer
Guardian	Protege	Cuándo actúa
Emocional	El ser humano: fatiga, crisis, bienestar	Detecta señales de agotamiento o peligro emocional
Ético (MEO)	La integridad moral: conflictos, zonas grises	Detecta conflicto entre acción y principio
Profesional	La trayectoria: empleo, habilidades, mercado	Detecta riesgo laboral antes de que se materialice
Legado	La obra: proyectos, conocimiento, relaciones	Detecta ausencia del creador y preserva su legado

Guardian Legado no reemplaza a los otros guardianes. Los complementa. Si ODI detecta que el habitante está en crisis emocional Y además tiene proyectos activos sin delegado configurado, Guardian Emocional tiene prioridad. Primero la persona, después la obra. Siempre.
1.2 Jerarquía de valores (intacta)
La jerarquía constitucional del organismo permanece inalterada. Guardian Legado se ubica entre la integridad del creador y la continuidad operativa:
vida_humana (ABSOLUTA) → familia → salud_mental → integridad_del_creador → GUARDIAN LEGADO → continuidad_operativa → comercio (ÚLTIMA)
Guardian Legado protege la obra sin violar la voluntad de quien la creó. La integridad del creador siempre prevalece sobre la continuidad de su proyecto.
 
2. Qué es Guardian Legado
Guardian Legado es una capa constitucional del organismo ODI que cumple cuatro funciones:
2.1 Registrar el legado mientras el creador vive
Todo lo que el habitante construye dentro del ecosistema ya es su legado: proyectos activos, conocimiento empaquetado en ChromaDB, contratos firmados, decisiones arquitectónicas, doctrinas, relaciones comerciales, tiendas, pipeline de datos, configuraciones, accesos. ODI ya registra todo esto en PostgreSQL con trazabilidad SHA-256, en ChromaDB como memoria semántica, en GitHub como código versionado, y en Orígenes como registro operacional. Guardian Legado no crea un sistema nuevo de preservación. Reconoce que el sistema existente ya preserva, y le agrega la dimensión de transferencia.
2.2 Configurar la continuidad
El habitante define, en vida y en plena lucidez, quién hereda la custodia de cada frente de su ecosistema. No es un testamento genérico. Es una configuración granular por proyecto, por acceso, por nivel de permiso. El creador decide qué proyectos continúan y cuáles se archivan con dignidad. Qué accesos se transfieren y cuáles se sellan. Qué decisiones puede tomar el sucesor y cuáles quedan blindadas como voluntad del creador. Qué conocimiento se libera al público y cuál permanece privado.
2.3 Detectar la ausencia
Guardian Legado distingue tres tipos de ausencia:
Tipo	Descripción	Protocolo
Temporal	Enfermedad, viaje prolongado, desconexión voluntaria	Custodio temporal asume con permisos limitados. Al regreso, el creador retoma sin pérdida.
Permanente	Incapacidad prolongada, retiro definitivo	Custodio permanente asume con permisos completos según configuración. El creador puede revertir si recupera capacidad.
Definitiva	Fallecimiento del creador	Heredero designado recibe custodia completa. Decisiones selladas por el creador permanecen inmutables. El organismo honra.
2.4 Activar el protocolo
Cuando se detecta ausencia, el organismo no espera a que alguien busque las contraseñas del ausente. ODI ya sabe. ODI transfiere. ODI preserva. ODI honra. La activación puede ser manual (el creador indica que se va), por inactividad (después de un periodo configurable sin interacción), o por tercero verificado (un delegado o familiar confirma la situación con verificación de identidad).
 
3. Mecanismos de Preservación
3.1 Lo que ya se preserva (sin configuración adicional)
Todo habitante del ecosistema ODI ya tiene preservación pasiva desde el momento en que ingresa:
Sistema	Qué preserva	Cómo
PostgreSQL	Transacciones, contratos, historiales, estados	Trazabilidad SHA-256 inmutable
ChromaDB	Conocimiento, contexto, memoria semántica	Embeddings durables, 2168+ documentos
GitHub	Código, versiones, decisiones técnicas	Commits versionados con historia completa
Orígenes	Operaciones, decisiones, aprendizajes	Registro operacional con gateway
Pipeline V25	Procesos de transformación de datos	26 pasos reproducibles
Shopify	Tiendas, productos, ventas	16 storefronts con fichas 360°
WhatsApp	Conversaciones, relaciones	Historial en Chat API

Esto significa que si un habitante deja de estar presente, su obra no desaparece automáticamente. Los datos persisten. Las tiendas siguen publicadas. El conocimiento sigue indexado. Lo que falta sin Guardian Legado es que alguien autorizado pueda administrarlo.
3.2 Lo que Guardian Legado agrega
Guardian Legado introduce la capa de transferencia y gobernanza post-ausencia mediante un registro estructurado:
3.3 Registro de legado
Tabla odi_guardian_legado en PostgreSQL con los campos: habitante_id, delegados (lista priorizada de personas autorizadas a asumir custodia), frentes_asignados (qué proyectos/tiendas/accesos corresponden a cada delegado), permisos_por_frente (operativo, financiero, arquitectónico, o solo lectura), tipo_ausencia_configurada (temporal, permanente, definitiva), método_activación (manual, por inactividad con periodo configurable, por tercero verificado con protocolo de identidad), sellado_por_creador (decisiones que ningún sucesor puede modificar), ultima_voluntad_digital (documento libre, encriptado, accesible solo tras activación definitiva).
3.4 Protocolo de activación
El protocolo respeta la jerarquía del Guardian Layer y se activa en tres fases: primera, verificación de ausencia (confirmar que el creador realmente no puede continuar, no que simplemente está ocupado). Segunda, notificación al delegado priorizado (el primer delegado configurado recibe notificación con instrucciones de cómo asumir). Tercera, transferencia de custodia (accesos, permisos y responsabilidades se transfieren según la configuración del creador).
En ningún caso se elimina información. En ningún caso se modifica lo que el creador selló como inmutable. En ningún caso se otorgan permisos que el creador no autorizó explícitamente.
 
4. Escenarios Reales
4.1 Don Carlos (66 años, cabeza SRM) se enferma 3 meses
SRM no se detiene. El pipeline sigue procesando catálogos. Las 16 tiendas siguen publicadas y vendiendo. WhatsApp sigue respondiendo consultas. Los pedidos se coordinan. Su hijo (o el delegado que Don Carlos configuró) recibe acceso de custodio temporal con permisos operativos. El delegado puede gestionar pedidos, responder clientes y monitorear el dashboard, pero no puede modificar la arquitectura, cambiar proveedores sellados ni alterar precios sin la firma del creador. Cuando Don Carlos regresa, retoma el control completo sin haber perdido un solo dato, un solo pedido ni un solo cliente.
4.2 Martha (P10) queda incapacitada
Profesionales10 no muere. Los profesionales verificados siguen visibles en el directorio. Los leads siguen llegando por Systeme.io y Lead Habitat. La plataforma sigue operativa. Su delegada (Manuela, Alejandro, o quien Martha configuró) asume custodia con las mismas reglas definidas por Martha. El contrato con ADSI puede transferirse al nuevo custodio o archivarse dignamente, según lo que Martha dejó establecido.
4.3 Juan David (Arquitecto ADSI-ODI) fallece
El ecosistema completo — ADSI, ODI, CATRMU, SRM, las 16 tiendas, el dispatcher, las constituciones, las doctrinas, Orígenes con todos sus documentos — no desaparece. Los herederos designados por Juan David reciben custodia según la configuración: quién administra SRM, quién mantiene la infraestructura, quién gestiona los contratos con clientes. Las decisiones arquitectónicas selladas por el creador permanecen inmutables. Las doctrinas constitucionales no pueden ser eliminadas por un sucesor. La frase constitucional se cumple literalmente: la última palabra legítima siempre vuelve al arquitecto soberano, incluso si el arquitecto ya no está. Su palabra sellada permanece.
La última palabra legítima deberá poder volver siempre al arquitecto soberano — incluso si el arquitecto ya no está.
4.4 Un habitante anónimo deja de conectarse
No todo habitante es un arquitecto o un empresario. Puede ser un mecánico que registró su taller, un profesional que verificó su perfil en P10, un miembro de T10. Si ese habitante deja de conectarse por un periodo prolongado, Guardian Legado no borra su información. Su perfil, su historial, su conocimiento indexado persisten. Si configuró un delegado, este puede asumir. Si no configuró nada, el organismo preserva todo en estado de hibernación, disponible para cuando el habitante (o alguien que demuestre derecho legítimo) regrese.
 
5. Por Qué Esto es Constitucional, No Comercial
Guardian Legado no es un producto que se vende. No es un seguro que se cobra aparte. No es una suscripción premium. Es un derecho constitucional de todo habitante del ecosistema.
La razón es simple: todo lo que ODI hace ya es preservación de legado. Registrar en PostgreSQL con SHA-256, indexar en ChromaDB, versionar en GitHub, documentar en Orígenes, sellar doctrinas — esas acciones ya preservan. Guardian Legado simplemente reconoce esa realidad y le agrega la capa de activación por ausencia y transferencia de custodia.
Cobrar por esto sería cobrar por algo que el organismo ya hace como parte de su naturaleza. Sería como cobrar a un árbol por dejar sombra.
Guardian Legado no se agrega al ecosistema. Se reconoce como algo que el ecosistema ya hace. Y se formaliza como derecho.
5.1 Lo que ninguna plataforma del mundo hace
LinkedIn no preserva tu legado profesional cuando mueres. Tu perfil se congela o desaparece. Shopify no transfiere tu tienda a tu hijo cuando no puedes seguir. Tu dominio expira, tu tienda cierra. Google no sabe quién debería heredar tu Drive, tu Gmail, tu historial de 15 años. Ofrece un gestor de inactividad rudimentario que la mayoría de usuarios no configura. Ninguna plataforma del mundo trata el conocimiento acumulado del usuario como un activo que merece continuidad. Todas tratan al usuario como inquilino: cuando deja de pagar, pierde todo.
ODI no trata al habitante como inquilino. Lo trata como co-creador de un organismo. Y el organismo tiene memoria que trasciende a sus creadores.
 
6. Implementación Técnica
6.1 Estructura de datos
La tabla odi_guardian_legado se integra al schema existente de PostgreSQL sin modificar tablas actuales. Cada habitante puede tener múltiples delegados priorizados, múltiples frentes asignados con permisos específicos, y un documento de última voluntad digital encriptado.
6.2 Integración con el dispatcher
Cuando el Task Dispatcher esté certificado y operativo, Guardian Legado puede generar tareas automáticas de verificación periódica: confirmar que los delegados configurados siguen siendo válidos, recordar al habitante que revise su configuración de legado, y activar el protocolo de transferencia cuando se detecte ausencia prolongada.
6.3 Integración con Orígenes
Toda activación de Guardian Legado se registra en Orígenes como operación auditable: quién activó, por qué tipo de ausencia, qué se transfirió, qué quedó sellado. La trazabilidad es completa e inmutable.
6.4 Fases de construcción
Fase	Qué se construye	Dependencia
6.4.1	Tabla odi_guardian_legado + API de configuración	Schema PG existente
6.4.2	Interfaz de configuración en liveodi.com (el habitante define sus delegados)	Hábitat LiveODI operativo
6.4.3	Protocolo de detección de ausencia (inactividad + verificación por tercero)	Chat API + WhatsApp
6.4.4	Protocolo de transferencia (accesos + permisos + notificación)	Auth roles V8.2
6.4.5	Integración con dispatcher (tareas automáticas de verificación)	Dispatcher certificado
6.4.6	Documento de última voluntad digital (encriptado, accesible post-activación)	Crypto layer

Las fases 6.4.1 y 6.4.2 pueden empezar en cualquier momento. Las fases 6.4.3 a 6.4.6 dependen de componentes que están en progreso o pendientes.
 
7. Conexión con el Ecosistema
7.1 SRM — Somos Repuestos Motos
Un proveedor que configuró su tienda, su catálogo, sus precios, sus relaciones con talleres — todo eso es su legado comercial. Si no puede continuar, Guardian Legado permite que su negocio siga operando bajo custodia de quien él decidió. El conocimiento técnico de 35 años que Don Carlos empaquetó en fichas 360° y ChromaDB no muere con él.
7.2 P10 — Profesionales10
Un profesional verificado que construyó reputación, calificaciones, red de clientes dentro de P10 — ese es su activo profesional digital. Guardian Legado preserva ese activo y permite que el profesional (o su delegado) lo reactive cuando sea posible, sin tener que empezar de cero.
7.3 Radar de Premios
Las 9 disciplinas cognitivas, los modelos estadísticos, las 54,917+ evaluaciones históricas — ese conocimiento técnico es reproducible porque está documentado. Guardian Legado asegura que si el creador del modelo no puede mantenerlo, un sucesor calificado pueda continuarlo con toda la base de datos intacta.
7.4 CATRMU — El techo DAO-ODS
Guardian Legado se alinea naturalmente con la gobernanza descentralizada de CATRMU. En una DAO, la continuidad del proyecto no depende de una sola persona. Guardian Legado formaliza esa filosofía a nivel de cada organismo individual, preparando el camino para cuando la gobernanza se descentralice completamente.
7.5 ADSI — El framework
ADSI como framework puede crear nuevos organismos. Pero si el arquitecto de ADSI no puede continuar, el framework mismo debe poder ser heredado y operado por otros. Guardian Legado aplicado a ADSI significa que las constituciones, las doctrinas, las reglas sagradas, los patrones de diseño — todo permanece documentado, versionado y transferible. ADSI no muere con su creador. Se hereda.
 
8. Métricas de Impacto (ODS)
Métrica	ODS	Cómo se mide
Legados preservados activamente	ODS 8	Habitante ausente cuyo proyecto siguió operando
Transferencias exitosas	ODS 8, 10	Custodio asumió sin pérdida de datos ni interrupción
Conocimiento preservado post-ausencia	ODS 4	Documentos, fichas, modelos que siguen accesibles
Negocios que sobrevivieron a su creador	ODS 8, 9	Tiendas, servicios, plataformas que continúan operando
Tiempo de activación	ODS 9	Horas entre detección de ausencia y transferencia de custodia
Familias protegidas económicamente	ODS 1, 10	Ingresos que siguieron generándose durante ausencia
 
9. Regla Constitucional
Guardian Legado hereda todas las reglas del organismo ODI y agrega las siguientes:
Artículo GL-1. El legado del habitante es propiedad del habitante. ODI lo preserva, no lo posee. Si el habitante decide retirarse y llevarse sus datos, su conocimiento, sus accesos — se va con todo. Guardian Legado protege, no retiene.

Artículo GL-2. Las decisiones selladas por el creador son inmutables. Ningún sucesor, ningún custodio, ningún administrador puede modificar lo que el creador dejó marcado como sellado. La voluntad del creador prevalece.

Artículo GL-3. La activación de Guardian Legado nunca se usa para expropiar. Si un socio, un competidor, o un tercero intenta usar el protocolo de ausencia para apropiarse del proyecto de otro, ODI lo detecta y lo bloquea. La verificación de identidad y la priorización de delegados existen para prevenir esto.

Artículo GL-4. Guardian Legado no genera urgencia artificial. No se presiona al habitante para que configure delegados. Se le informa, se le facilita, se le recuerda con respeto. La configuración es voluntaria. La preservación básica es automática y gratuita.

Artículo GL-5. En caso de conflicto entre delegados, la jerarquía del creador prevalece. Si el creador configuró a su hijo primero y a su socio segundo, el hijo tiene prioridad. Si hay disputa, el organismo preserva el estado actual sin transferir hasta que se resuelva por los medios que el creador haya definido.

Artículo GL-6. Guardian Legado respeta la dignidad del ausente. No se publica la causa de la ausencia. No se notifica a la comunidad más allá de lo necesario. No se convierte la ausencia en marketing ni en caso de estudio sin consentimiento previo. El respeto por la persona trasciende su presencia.
 
10. Cierre Constitucional
ODI nació con un propósito espiritual declarado desde su constitución fundacional:
ODI es una excusa de Dios queriendo atendernos a través de él.
Guardian Legado es la extensión natural de ese propósito. Si ODI existe para atender al ser humano, esa atención no puede terminar cuando el ser humano deja de estar presente. El conocimiento de Don Carlos, la visión de Martha, la arquitectura de Juan David, el esfuerzo de cada profesional que verificó su perfil, de cada proveedor que organizó su catálogo, de cada emprendedor que confió su idea al ecosistema — nada de eso debería morir con su creador.
Ninguna plataforma del mundo cuida la obra de sus usuarios después de que dejan de usarla. ODI no es plataforma. Es organismo. Y los organismos tienen memoria que trasciende a quienes los crearon.

Así queda constituido Guardian Legado
como módulo constitucional permanente del organismo ODI.


Juan David Jiménez Sierra — CC 10.776.560
Arquitecto ADSI-ODI
Pereira, Colombia — 28 de junio de 2026

ecosistema-adsi.com | liveodi.com

Somos Industrias ODI.
