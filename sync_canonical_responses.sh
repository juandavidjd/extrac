#!/bin/bash
# ============================================================================
# SYNC_CANONICAL_RESPONSES.sh
# ============================================================================
# Sincroniza las respuestas canónicas del Intent Override Gate
# con el servidor de producción
#
# Uso: scp este archivo al servidor y ejecutar como root
# ============================================================================

echo "========================================"
echo "SYNC CANONICAL RESPONSES - ODI v1.2"
echo "========================================"

# Backup del archivo actual
BACKUP_FILE="/opt/odi/core/odi_core.py.backup.$(date +%Y%m%d_%H%M%S)"
cp /opt/odi/core/odi_core.py "$BACKUP_FILE"
echo "✅ Backup creado: $BACKUP_FILE"

# Crear archivo con respuestas canónicas corregidas
cat > /opt/odi/core/canonical_responses.py << 'CANONICAL_EOF'
"""
CANONICAL_RESPONSES — Respuestas Oficiales ODI v1.2
====================================================
IMPORTANTE: Estas respuestas NO deben mencionar:
- "repuestos"
- "motos"
- "La Roca Motorepuestos"
- Ningún producto específico

ODI es un organismo UNIVERSAL, no un vendedor de repuestos.
"""

CANONICAL_RESPONSES = {
    # =========================================================================
    # P0: SEGURIDAD (HARD STOP - No catálogo, no bifurcación)
    # =========================================================================
    "SAFETY": (
        "Entiendo que es urgente.\n"
        "Si hay riesgo inmediato, llama al 123 ahora mismo.\n\n"
        "¿Cómo puedo ayudarte una vez estés a salvo?"
    ),
    "HEALTH_EMERGENCY": (
        "Esto suena a una emergencia médica.\n"
        "🚑 Llama al 125 (Bomberos) o 106 (Cruz Roja) inmediatamente.\n\n"
        "¿Hay alguien contigo que pueda ayudar?"
    ),

    # =========================================================================
    # P1: CAMBIO DE DOMINIO (Sin mencionar repuestos)
    # =========================================================================
    "EMPRENDIMIENTO": (
        "Excelente. Cambio a modo Emprendimiento.\n"
        "¿Tu idea es iniciar desde cero, escalar algo existente, "
        "o explorar un sector específico (salud, comercio, servicios)?"
    ),
    "TURISMO": (
        "Entendido. Cambio a modo Turismo.\n"
        "¿Buscas planear un viaje o crear un negocio de turismo?"
    ),
    "TURISMO_SALUD": (
        "Cambio a modo Turismo Odontológico.\n"
        "Puedo ayudarte a coordinar valoración, tratamiento y logística.\n"
        "¿Buscas implantes, rehabilitación oral o estética dental?"
    ),
    "SALUD": (
        "Entendido. Cambio a modo Salud.\n"
        "¿Esto es para una consulta personal o para un proyecto/negocio?"
    ),
    "BELLEZA": (
        "Entendido. Cambio a modo Belleza.\n"
        "¿Buscas servicios o quieres emprender en este sector?"
    ),
    "LEGAL": (
        "Entendido. Cambio a modo Legal.\n"
        "¿Necesitas asesoría legal personal o para un negocio?"
    ),
    "EDUCACION": (
        "Entendido. Cambio a modo Educación.\n"
        "¿Quieres aprender algo específico o crear contenido educativo?"
    ),
    "TRABAJO": (
        "Entendido. Cambio a modo Trabajo.\n"
        "¿Buscas optimizar tareas en tu empresa o encontrar empleo?"
    ),

    # =========================================================================
    # P2: AYUDA / CONTEXTO
    # =========================================================================
    "HELP": (
        "Puedo ayudarte con:\n"
        "• Tu trabajo (optimizar tareas)\n"
        "• Tu negocio (crear presencia digital)\n"
        "• Tus compras (encontrar productos)\n"
        "• Aprender (academia y cursos)\n\n"
        "¿Por dónde quieres empezar?"
    ),
    "SWITCH": (
        "Entendido. Cambio de tema.\n"
        "¿En qué más puedo ayudarte?"
    ),
    "STOP": (
        "Entendido. Pausa.\n"
        "Cuando quieras continuar, solo dime."
    ),

    # =========================================================================
    # P3: META / IDENTIDAD (UNIVERSAL - Nunca mencionar industria específica)
    # =========================================================================
    "IDENTITY_RESET": (
        "Tienes razón. No soy solo de una industria.\n\n"
        "Soy ODI, un organismo digital que ayuda a personas y empresas "
        "a resolver necesidades en distintos sectores: comercio, "
        "emprendimiento, industria y servicios.\n\n"
        "¿Qué necesitas hoy?"
    ),
    "IDENTITY_CHALLENGE": (
        "Tienes razón. Déjame entender mejor: "
        "¿qué es lo que realmente buscas?"
    ),
    "IDENTITY_QUERY": (
        "Soy ODI, un organismo digital que ayuda a personas y empresas "
        "a resolver necesidades, tomar decisiones y ejecutar acciones "
        "en distintos sectores: comercio, emprendimiento, industria y servicios.\n\n"
        "¿En qué te ayudo hoy?"
    ),
}

# =========================================================================
# TRIGGERS P1 EXPANDIDOS (Sinónimos de emprendimiento)
# =========================================================================
P1_EMPRENDIMIENTO_TRIGGERS = [
    "emprender",
    "emprendimiento",
    "negocio",
    "idea de negocio",
    "quiero emprender",
    "tengo una idea",
    "iniciar un negocio",
    "crear empresa",
    "mi propio negocio",
    "lanzar mi propio negocio",
    "iniciar un proyecto empresarial",
    "materializar una idea",
    "independizarme laboralmente",
    "crear mi propia empresa",
    "convertirme en mi propio jefe",
    "ser mi propio jefe",
    "montar un negocio",
    "abrir un negocio",
    "proyecto empresarial",
]
CANONICAL_EOF

echo "✅ Respuestas canónicas creadas: /opt/odi/core/canonical_responses.py"

# Verificar sintaxis Python
python3 -c "import sys; sys.path.insert(0, '/opt/odi/core'); from canonical_responses import CANONICAL_RESPONSES; print(f'✅ Validación OK: {len(CANONICAL_RESPONSES)} respuestas cargadas')"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "✅ SYNC COMPLETADO"
    echo "========================================"
    echo ""
    echo "Próximos pasos:"
    echo "1. Actualizar odi_core.py para importar canonical_responses"
    echo "2. Reiniciar servicios: docker restart odi-api"
    echo "3. Probar con mensajes de WhatsApp"
    echo ""
    echo "Rollback si es necesario:"
    echo "  cp $BACKUP_FILE /opt/odi/core/odi_core.py"
else
    echo ""
    echo "❌ ERROR en validación. Verificar sintaxis."
    echo "Rollback automático..."
    cp "$BACKUP_FILE" /opt/odi/core/odi_core.py
fi
