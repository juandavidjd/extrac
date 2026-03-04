#!/bin/bash
# ==============================================================================
# ODI GATEKEEPER v1.0 — Pipeline de Integración Blindada
# ==============================================================================
# Orquesta el flujo: Claude Code (propuesta) → Aider (integración) → Linters
# Previene que Claude Code escriba directamente en archivos de producción
# sin verificación.
#
# Uso:
#   ./gatekeeper.sh "Añade un campo phone al esquema User en FastAPI"
#   ./gatekeeper.sh --lint-only        # Solo ejecutar linters
#   ./gatekeeper.sh --verify           # Verificar estado del último cambio
#
# Requiere: ruff (Python), eslint (JS), aider-chat (opcional)
# ==============================================================================

set -euo pipefail

# --- CONFIGURACIÓN ---
PROPOSAL_FILE="PROPOSED_CHANGES.md"
AUDIT_LOG="gatekeeper_audit.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- FUNCIONES ---

log() {
    echo -e "${BLUE}[GATEKEEPER]${NC} $1"
    echo "[${TIMESTAMP}] $1" >> "${AUDIT_LOG}"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
    echo "[${TIMESTAMP}] OK: $1" >> "${AUDIT_LOG}"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[${TIMESTAMP}] WARN: $1" >> "${AUDIT_LOG}"
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    echo "[${TIMESTAMP}] FAIL: $1" >> "${AUDIT_LOG}"
}

separator() {
    echo "=================================================================="
}

# --- VERIFICACIÓN DE HERRAMIENTAS ---

check_tools() {
    log "Verificando herramientas instaladas..."
    local tools_ok=true

    # Python linter (ruff)
    if command -v ruff &> /dev/null; then
        success "ruff $(ruff --version 2>/dev/null || echo 'instalado')"
    else
        warn "ruff no instalado. Instalar: pip install ruff"
        tools_ok=false
    fi

    # Node linter (eslint) - solo si hay package.json
    if [ -f "package.json" ]; then
        if npx eslint --version &> /dev/null 2>&1; then
            success "eslint $(npx eslint --version 2>/dev/null || echo 'instalado')"
        else
            warn "eslint no instalado. Instalar: npm install eslint --save-dev"
            tools_ok=false
        fi
    fi

    # Aider (integrador opcional)
    if command -v aider &> /dev/null; then
        success "aider instalado"
    else
        warn "aider no instalado (opcional). Instalar: pip install -U aider-chat"
    fi

    # Git
    if command -v git &> /dev/null; then
        success "git $(git --version 2>/dev/null)"
    else
        fail "git no instalado (requerido)"
        exit 1
    fi

    if [ "$tools_ok" = false ]; then
        warn "Algunas herramientas faltan. El pipeline funcionara con capacidad reducida."
    fi
}

# --- FASE 1: SNAPSHOT PRE-CAMBIO ---

take_snapshot() {
    log "Tomando snapshot del estado actual (git diff)..."
    local changed_files
    changed_files=$(git diff --name-only 2>/dev/null || echo "")
    local untracked_files
    untracked_files=$(git ls-files --others --exclude-standard 2>/dev/null || echo "")

    if [ -n "$changed_files" ] || [ -n "$untracked_files" ]; then
        warn "Hay cambios pendientes antes de empezar:"
        if [ -n "$changed_files" ]; then
            echo "  Modificados: $changed_files"
        fi
        if [ -n "$untracked_files" ]; then
            echo "  Sin tracking: $untracked_files"
        fi
    else
        success "Working tree limpio"
    fi
}

# --- FASE 2: LINT PYTHON ---

lint_python() {
    log "Ejecutando lint Python (ruff)..."

    if ! command -v ruff &> /dev/null; then
        warn "ruff no disponible, saltando lint Python"
        return 0
    fi

    # Buscar archivos Python en directorios relevantes
    local py_dirs=()
    [ -d "core" ] && py_dirs+=("core/")
    [ -d "odi_production" ] && py_dirs+=("odi_production/")
    [ -d "scripts" ] && py_dirs+=("scripts/")

    if [ ${#py_dirs[@]} -eq 0 ]; then
        # Si no hay subdirectorios conocidos, buscar .py en raiz
        if ls *.py &> /dev/null 2>&1; then
            py_dirs+=(".")
        else
            warn "No se encontraron archivos Python para validar"
            return 0
        fi
    fi

    local lint_failed=false
    for dir in "${py_dirs[@]}"; do
        log "  Validando: ${dir}"
        if ruff check "${dir}" --output-format=concise 2>/dev/null; then
            success "  ${dir} — limpio"
        else
            fail "  ${dir} — errores detectados"
            lint_failed=true
        fi
    done

    if [ "$lint_failed" = true ]; then
        fail "Lint Python FALLIDO. Corregir antes de continuar."
        return 1
    fi

    success "Lint Python completado sin errores"
    return 0
}

# --- FASE 3: LINT JAVASCRIPT/REACT ---

lint_js() {
    log "Ejecutando lint JavaScript/React (eslint)..."

    if [ ! -f "package.json" ]; then
        log "No hay package.json, saltando lint JS"
        return 0
    fi

    if ! npx eslint --version &> /dev/null 2>&1; then
        warn "eslint no disponible, saltando lint JS"
        return 0
    fi

    # Verificar si hay script lint en package.json
    if grep -q '"lint"' package.json 2>/dev/null; then
        if npm run lint 2>/dev/null; then
            success "Lint JS/React completado sin errores"
            return 0
        else
            fail "Lint JS/React FALLIDO. Corregir antes de continuar."
            return 1
        fi
    else
        warn "No hay script 'lint' en package.json"
        return 0
    fi
}

# --- FASE 4: VALIDACIÓN DJANGO ---

lint_django() {
    if [ ! -f "manage.py" ]; then
        return 0
    fi

    log "Ejecutando validacion Django (manage.py check)..."

    if python manage.py check 2>/dev/null; then
        success "Django check completado sin errores"
        return 0
    else
        fail "Django check FALLIDO"
        return 1
    fi
}

# --- FASE 5: VERIFICACIÓN POST-CAMBIO ---

verify_changes() {
    log "Verificando cambios en disco (git diff post-cambio)..."

    local changed_files
    changed_files=$(git diff --name-only 2>/dev/null || echo "")

    if [ -z "$changed_files" ]; then
        warn "No se detectaron cambios en disco"
        return 0
    fi

    success "Archivos modificados:"
    echo "$changed_files" | while read -r file; do
        if [ -f "$file" ]; then
            local lines
            lines=$(wc -l < "$file")
            echo "  $file ($lines lineas)"
        else
            fail "  $file — FILE_NOT_FOUND (alucinacion detectada)"
        fi
    done

    # Mostrar diff resumido
    log "Resumen de cambios (primeras 50 lineas del diff):"
    git diff --stat 2>/dev/null || true
}

# --- FASE 6: INTEGRACIÓN CON AIDER ---

run_aider_integration() {
    local task="$1"

    if ! command -v aider &> /dev/null; then
        warn "Aider no instalado. Saltando integracion automatica."
        warn "Los cambios en ${PROPOSAL_FILE} deben integrarse manualmente."
        return 0
    fi

    if [ ! -f "${PROPOSAL_FILE}" ]; then
        warn "No existe ${PROPOSAL_FILE}. Nada que integrar con Aider."
        return 0
    fi

    log "Ejecutando Aider en modo arquitecto..."
    aider --architect --message "Lee ${PROPOSAL_FILE} e integra los cambios en los archivos correspondientes. Respeta las reglas de CLAUDE.md. Si detectas logica inconsistente, aborta y reporta. Tarea: ${task}" 2>&1 || {
        fail "Aider encontro problemas durante la integracion"
        return 1
    }

    success "Aider completo la integracion"
    return 0
}

# --- MODOS DE EJECUCIÓN ---

mode_lint_only() {
    separator
    echo "ODI GATEKEEPER — MODO: SOLO LINTERS"
    separator

    check_tools

    local exit_code=0
    lint_python || exit_code=1
    lint_js || exit_code=1
    lint_django || exit_code=1

    separator
    if [ $exit_code -eq 0 ]; then
        success "Todos los linters pasaron"
    else
        fail "Algunos linters fallaron. Revisar errores arriba."
    fi

    return $exit_code
}

mode_verify() {
    separator
    echo "ODI GATEKEEPER — MODO: VERIFICACION"
    separator

    verify_changes

    separator
    log "Verificacion completada. Revisar output arriba."
}

mode_full() {
    local task="${1:-Tarea no especificada}"

    separator
    echo "ODI GATEKEEPER v1.0 — PIPELINE COMPLETO"
    echo "Tarea: ${task}"
    echo "Fecha: ${TIMESTAMP}"
    separator

    # Paso 1: Verificar herramientas
    check_tools
    echo ""

    # Paso 2: Snapshot pre-cambio
    take_snapshot
    echo ""

    # Paso 3: Si existe PROPOSED_CHANGES.md, intentar integrar con Aider
    if [ -f "${PROPOSAL_FILE}" ]; then
        log "Detectado ${PROPOSAL_FILE} — ejecutando integracion Aider"
        run_aider_integration "${task}"
        echo ""
    else
        log "No hay ${PROPOSAL_FILE}. Asumiendo cambios ya aplicados."
    fi

    # Paso 4: Linters
    local lint_exit=0
    lint_python || lint_exit=1
    lint_js || lint_exit=1
    lint_django || lint_exit=1
    echo ""

    # Paso 5: Verificacion post-cambio
    verify_changes
    echo ""

    # Paso 6: Resultado final
    separator
    if [ $lint_exit -eq 0 ]; then
        success "PIPELINE COMPLETADO — SERVIDOR LIMPIO"
        echo ""
        echo "Siguiente paso:"
        echo "  1. Revisar los cambios: git diff"
        echo "  2. Si todo OK:          git add . && git commit"
        echo "  3. Auditar con Codex:   python scripts/cross_audit.py"
    else
        fail "PIPELINE FALLIDO — CORREGIR ERRORES ANTES DE CONTINUAR"
        echo ""
        echo "Acciones requeridas:"
        echo "  1. Corregir errores de lint reportados arriba"
        echo "  2. Ejecutar de nuevo: ./gatekeeper.sh --lint-only"
        echo "  3. Una vez limpio: ./gatekeeper.sh \"${task}\""
    fi
    separator

    # Limpiar PROPOSED_CHANGES.md si la integracion fue exitosa
    if [ $lint_exit -eq 0 ] && [ -f "${PROPOSAL_FILE}" ]; then
        log "Limpiando ${PROPOSAL_FILE} (integracion exitosa)"
        rm -f "${PROPOSAL_FILE}"
    fi

    return $lint_exit
}

# --- MAIN ---

main() {
    case "${1:-}" in
        --lint-only)
            mode_lint_only
            ;;
        --verify)
            mode_verify
            ;;
        --help|-h)
            echo "Uso: ./gatekeeper.sh [OPCION] [TAREA]"
            echo ""
            echo "Opciones:"
            echo "  --lint-only    Solo ejecutar linters (ruff, eslint, django check)"
            echo "  --verify       Verificar estado de cambios en disco"
            echo "  --help         Mostrar esta ayuda"
            echo ""
            echo "Ejemplos:"
            echo "  ./gatekeeper.sh \"Agregar endpoint /health en FastAPI\""
            echo "  ./gatekeeper.sh --lint-only"
            echo "  ./gatekeeper.sh --verify"
            ;;
        *)
            mode_full "${*:-Tarea no especificada}"
            ;;
    esac
}

main "$@"
