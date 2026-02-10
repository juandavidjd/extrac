#!/bin/bash
# ============================================================================
# INTENT OVERRIDE GATE — Deploy Script
# ============================================================================
# Versión: 1.0
# Fecha: 10 Febrero 2026
# Servidor: 64.23.170.118
# ============================================================================

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     INTENT OVERRIDE GATE — DEPLOYMENT                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# ============================================================================
# PASO 1: Crear directorio de scripts
# ============================================================================
echo ""
echo "📁 Paso 1: Creando directorio de scripts..."

mkdir -p /opt/odi/scripts
chmod 755 /opt/odi/scripts

# ============================================================================
# PASO 2: Copiar el módulo Python
# ============================================================================
echo "📄 Paso 2: Copiando intent_override_gate.py..."

# El archivo debe estar en el mismo directorio que este script
if [ -f "intent_override_gate.py" ]; then
    cp intent_override_gate.py /opt/odi/scripts/
    chmod 644 /opt/odi/scripts/intent_override_gate.py
    echo "   ✅ Módulo copiado a /opt/odi/scripts/"
else
    echo "   ❌ ERROR: intent_override_gate.py no encontrado"
    exit 1
fi

# ============================================================================
# PASO 3: Verificar tests
# ============================================================================
echo "🧪 Paso 3: Ejecutando tests..."

cd /opt/odi/scripts
python3 intent_override_gate.py

if [ $? -eq 0 ]; then
    echo "   ✅ Todos los tests pasaron"
else
    echo "   ❌ ERROR: Algunos tests fallaron"
    echo "   ⚠️  NO continuar con el deploy hasta corregir"
    exit 1
fi

# ============================================================================
# PASO 4: Verificar n8n está corriendo
# ============================================================================
echo "🐳 Paso 4: Verificando containers..."

if docker ps | grep -q "odi-n8n"; then
    echo "   ✅ odi-n8n está corriendo"
else
    echo "   ❌ ERROR: odi-n8n no está corriendo"
    echo "   Ejecutar: cd /opt/odi && docker compose up -d"
    exit 1
fi

# ============================================================================
# PASO 5: Backup del workflow actual
# ============================================================================
echo "💾 Paso 5: Creando backup del workflow..."

BACKUP_DIR="/opt/odi/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Exportar workflows de n8n
docker exec odi-n8n n8n export:workflow --all --output=/tmp/workflows_backup.json 2>/dev/null
docker cp odi-n8n:/tmp/workflows_backup.json $BACKUP_DIR/

echo "   ✅ Backup creado en $BACKUP_DIR"

# ============================================================================
# PASO 6: Instrucciones para n8n
# ============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     INSTRUCCIONES MANUALES PARA n8n                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "1. Abrir n8n: https://odi.larocamotorepuestos.com:5678"
echo ""
echo "2. CREAR SHADOW FLOW (para testing seguro):"
echo "   - Duplicar el workflow 'ODI_v6_CORTEX'"
echo "   - Renombrar a 'ODI_v6_CORTEX_INTENT_OVERRIDE_SHADOW'"
echo "   - Agregar nodo 'Code' después del Webhook"
echo "   - Pegar el código de N8N_CORTEX_PATCH.md"
echo "   - Desactivar el nodo de respuesta WhatsApp"
echo "   - Solo loguear, no responder"
echo ""
echo "3. VERIFICAR SHADOW por 24 horas:"
echo "   - Monitorear logs: docker logs odi-n8n -f"
echo "   - Buscar eventos: 'intent_override'"
echo ""
echo "4. SI TODO OK, aplicar a PRODUCCIÓN:"
echo "   - Editar 'ODI_v6_CORTEX'"
echo "   - Insertar nodo 'Intent Override Gate' después del Webhook"
echo "   - Agregar nodo IF: if override=true → responder canonical"
echo "   - Guardar y activar"
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     DEPLOY COMPLETADO                                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Archivos desplegados:"
echo "  /opt/odi/scripts/intent_override_gate.py"
echo ""
echo "Backup creado:"
echo "  $BACKUP_DIR/workflows_backup.json"
echo ""
echo "Siguiente paso: Configurar n8n manualmente"
echo ""
