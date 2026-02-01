#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════════
#                     ODI ECOSYSTEM INSTALLER v1.0
#        Instalador masivo del Organismo Digital Industrial
# ══════════════════════════════════════════════════════════════════════════════════
#
# PROPOSITO:
#   Este script instala todo el ecosistema ODI en un servidor Linux.
#   Incluye: Python dependencies, Playwright, directorios, validacion.
#
# USO:
#   chmod +x install_odi_ecosystem.sh
#   ./install_odi_ecosystem.sh [--full | --minimal | --vigia-only]
#
# MODOS:
#   --full       : Instalacion completa (Vision + SRM + Vigia + Playwright)
#   --minimal    : Solo Vision + SRM (sin Playwright)
#   --vigia-only : Solo Vigia + Playwright
#   (default)    : --full
#
# ══════════════════════════════════════════════════════════════════════════════════

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ODI_VERSION="8.2"
PYTHON_MIN_VERSION="3.8"

# Directories
OUTPUT_DIR="${ODI_OUTPUT_DIR:-/tmp/odi_output}"
VIGIA_OUTPUT_DIR="${VIGIA_OUTPUT_DIR:-/tmp/vigia_output}"
SRM_OUTPUT_DIR="${SRM_OUTPUT_DIR:-/tmp/srm_output}"
LOG_DIR="${ODI_LOG_DIR:-/var/log/odi}"

# ══════════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE UTILIDAD
# ══════════════════════════════════════════════════════════════════════════════════

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                              ║"
    echo "║     ██████╗ ██████╗ ██╗    ███████╗ ██████╗ ██████╗ ███████╗██╗   ██╗███████╗║"
    echo "║    ██╔═══██╗██╔══██╗██║    ██╔════╝██╔════╝██╔═══██╗██╔════╝╚██╗ ██╔╝██╔════╝║"
    echo "║    ██║   ██║██║  ██║██║    █████╗  ██║     ██║   ██║███████╗ ╚████╔╝ ███████╗║"
    echo "║    ██║   ██║██║  ██║██║    ██╔══╝  ██║     ██║   ██║╚════██║  ╚██╔╝  ╚════██║║"
    echo "║    ╚██████╔╝██████╔╝██║    ███████╗╚██████╗╚██████╔╝███████║   ██║   ███████║║"
    echo "║     ╚═════╝ ╚═════╝ ╚═╝    ╚══════╝ ╚═════╝ ╚═════╝ ╚══════╝   ╚═╝   ╚══════╝║"
    echo "║                                                                              ║"
    echo "║                    ECOSYSTEM INSTALLER v1.0                                  ║"
    echo "║              \"No soy un chatbot, soy un organismo digital\"                   ║"
    echo "║                                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# ══════════════════════════════════════════════════════════════════════════════════
# VERIFICACIONES DEL SISTEMA
# ══════════════════════════════════════════════════════════════════════════════════

check_python() {
    log_step "Verificando Python"

    if check_command python3; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        log_info "Python $PYTHON_VERSION encontrado"

        # Comparar versiones
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
            log_info "Version de Python compatible"
            return 0
        else
            log_error "Se requiere Python >= $PYTHON_MIN_VERSION"
            return 1
        fi
    else
        log_error "Python3 no encontrado"
        return 1
    fi
}

check_pip() {
    log_step "Verificando pip"

    if check_command pip3; then
        PIP_VERSION=$(pip3 --version | awk '{print $2}')
        log_info "pip $PIP_VERSION encontrado"
        return 0
    else
        log_warn "pip3 no encontrado, intentando instalar..."
        python3 -m ensurepip --upgrade || {
            log_error "No se pudo instalar pip"
            return 1
        }
    fi
}

check_system_deps() {
    log_step "Verificando dependencias del sistema"

    # Lista de dependencias necesarias para Playwright
    DEPS=("wget" "curl" "git")
    MISSING_DEPS=()

    for dep in "${DEPS[@]}"; do
        if ! check_command "$dep"; then
            MISSING_DEPS+=("$dep")
        fi
    done

    if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
        log_warn "Dependencias faltantes: ${MISSING_DEPS[*]}"

        # Intentar instalar con apt (Debian/Ubuntu)
        if check_command apt-get; then
            log_info "Instalando con apt-get..."
            sudo apt-get update
            sudo apt-get install -y "${MISSING_DEPS[@]}"
        # Intentar con yum (CentOS/RHEL)
        elif check_command yum; then
            log_info "Instalando con yum..."
            sudo yum install -y "${MISSING_DEPS[@]}"
        else
            log_error "No se puede instalar dependencias automaticamente"
            return 1
        fi
    else
        log_info "Todas las dependencias del sistema presentes"
    fi
}

# ══════════════════════════════════════════════════════════════════════════════════
# INSTALACION DE DEPENDENCIAS PYTHON
# ══════════════════════════════════════════════════════════════════════════════════

install_python_deps() {
    log_step "Instalando dependencias Python"

    # Crear requirements.txt temporal
    REQUIREMENTS_FILE="$SCRIPT_DIR/requirements_odi.txt"

    cat > "$REQUIREMENTS_FILE" << 'EOF'
# ══════════════════════════════════════════════════════════════════════════════════
# ODI ECOSYSTEM - Python Dependencies
# ══════════════════════════════════════════════════════════════════════════════════

# Core
requests>=2.28.0
pandas>=1.5.0
numpy>=1.23.0

# PDF Processing
PyMuPDF>=1.21.0
pdf2image>=1.16.0
Pillow>=9.0.0

# OpenCV (Vision)
opencv-python-headless>=4.7.0

# AI Providers
openai>=1.0.0
anthropic>=0.18.0

# Web & API
httpx>=0.24.0
aiohttp>=3.8.0

# Data Processing
openpyxl>=3.1.0
python-dotenv>=1.0.0
fuzzywuzzy>=0.18.0
python-Levenshtein>=0.21.0

# Progress & CLI
rich>=13.0.0
tqdm>=4.65.0

# Async
aiofiles>=23.0.0

# Optional: Playwright (installed separately)
# playwright>=1.40.0
EOF

    log_info "Instalando desde requirements_odi.txt..."
    pip3 install --upgrade pip
    pip3 install -r "$REQUIREMENTS_FILE"

    log_info "Dependencias Python instaladas correctamente"
}

install_playwright() {
    log_step "Instalando Playwright + Chromium"

    log_info "Instalando paquete playwright..."
    pip3 install playwright

    log_info "Instalando navegador Chromium..."
    python3 -m playwright install chromium

    # Instalar dependencias del sistema para Playwright
    log_info "Instalando dependencias de Playwright..."
    python3 -m playwright install-deps chromium 2>/dev/null || {
        log_warn "No se pudieron instalar dependencias automaticamente"
        log_warn "Ejecutar manualmente: sudo npx playwright install-deps"
    }

    log_info "Playwright instalado correctamente"
}

# ══════════════════════════════════════════════════════════════════════════════════
# CONFIGURACION DE DIRECTORIOS
# ══════════════════════════════════════════════════════════════════════════════════

setup_directories() {
    log_step "Configurando directorios"

    DIRS=(
        "$OUTPUT_DIR"
        "$OUTPUT_DIR/crops"
        "$OUTPUT_DIR/csv"
        "$OUTPUT_DIR/json"
        "$OUTPUT_DIR/images"
        "$VIGIA_OUTPUT_DIR"
        "$VIGIA_OUTPUT_DIR/screenshots"
        "$VIGIA_OUTPUT_DIR/cache"
        "$SRM_OUTPUT_DIR"
        "$SRM_OUTPUT_DIR/shopify"
    )

    for dir in "${DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Creado: $dir"
        else
            log_info "Existe: $dir"
        fi
    done

    # Permisos
    chmod -R 755 "$OUTPUT_DIR" "$VIGIA_OUTPUT_DIR" "$SRM_OUTPUT_DIR" 2>/dev/null || true

    log_info "Directorios configurados"
}

# ══════════════════════════════════════════════════════════════════════════════════
# CONFIGURACION DE VARIABLES DE ENTORNO
# ══════════════════════════════════════════════════════════════════════════════════

setup_env_template() {
    log_step "Creando template de variables de entorno"

    ENV_FILE="$SCRIPT_DIR/.env.template"

    cat > "$ENV_FILE" << 'EOF'
# ══════════════════════════════════════════════════════════════════════════════════
# ODI ECOSYSTEM - Environment Variables Template
# ══════════════════════════════════════════════════════════════════════════════════
# Copiar a .env y configurar valores reales

# ─────────────────────────────────────────────────────────────────────────────────
# AI PROVIDERS
# ─────────────────────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
AI_PROVIDER=OPENAI  # OPENAI o ANTHROPIC

# ─────────────────────────────────────────────────────────────────────────────────
# ODI KERNEL (Node.js Backend)
# ─────────────────────────────────────────────────────────────────────────────────
ODI_KERNEL_URL=http://localhost:3000
ODI_EVENT_ENDPOINT=/odi/vision/event

# ─────────────────────────────────────────────────────────────────────────────────
# SHOPIFY MULTI-TENANT
# ─────────────────────────────────────────────────────────────────────────────────
# KAIQI
KAIQI_SHOP=u03tqc-0e.myshopify.com
KAIQI_TOKEN=shpat_...

# JAPAN
JAPAN_SHOP=7cy1zd-qz.myshopify.com
JAPAN_TOKEN=shpat_...

# DUNA
DUNA_SHOP=ygsfhq-fs.myshopify.com
DUNA_TOKEN=shpat_...

# BARA
BARA_SHOP=4jqcki-jq.myshopify.com
BARA_TOKEN=shpat_...

# DFG
DFG_SHOP=0se1jt-q1.myshopify.com
DFG_TOKEN=shpat_...

# YOKOMAR
YOKOMAR_SHOP=u1zmhk-ts.myshopify.com
YOKOMAR_TOKEN=shpat_...

# VAISAND
VAISAND_SHOP=z4fpdj-mz.myshopify.com
VAISAND_TOKEN=shpat_...

# LEO
LEO_SHOP=h1hywg-pq.myshopify.com
LEO_TOKEN=shpat_...

# STORE
STORE_SHOP=0b6umv-11.myshopify.com
STORE_TOKEN=shpat_...

# IMBRA
IMBRA_SHOP=0i1mdf-gi.myshopify.com
IMBRA_TOKEN=shpat_...

# ─────────────────────────────────────────────────────────────────────────────────
# IMAGE SERVER
# ─────────────────────────────────────────────────────────────────────────────────
IMAGE_SERVER_URL=http://64.23.170.118/images

# ─────────────────────────────────────────────────────────────────────────────────
# OUTPUT DIRECTORIES
# ─────────────────────────────────────────────────────────────────────────────────
ODI_OUTPUT_DIR=/tmp/odi_output
SRM_OUTPUT_DIR=/tmp/srm_output
VIGIA_OUTPUT_DIR=/tmp/vigia_output

# ─────────────────────────────────────────────────────────────────────────────────
# VIGIA CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────────
VIGIA_SCAN_INTERVAL=86400  # 24 horas en segundos
VIGIA_HEADLESS=true
VIGIA_MAX_PRODUCTS=100

# ─────────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────────
LOG_LEVEL=INFO
LOG_FILE=/var/log/odi/odi.log

# ─────────────────────────────────────────────────────────────────────────────────
# DATABASE (PostgreSQL para CES Audit Ledger)
# ─────────────────────────────────────────────────────────────────────────────────
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=odi_ces
POSTGRES_USER=odi
POSTGRES_PASSWORD=...

# ─────────────────────────────────────────────────────────────────────────────────
# SYSTEME.IO (Lead Registration)
# ─────────────────────────────────────────────────────────────────────────────────
SYSTEME_API_KEY=...
SYSTEME_TAG_BUYER=comprador
SYSTEME_TAG_LEAD=prospecto
EOF

    log_info "Template creado: $ENV_FILE"

    # Copiar a .env si no existe
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        cp "$ENV_FILE" "$SCRIPT_DIR/.env"
        log_info "Copiado a .env - Recuerda configurar los valores reales"
    else
        log_warn ".env ya existe - no sobrescrito"
    fi
}

# ══════════════════════════════════════════════════════════════════════════════════
# VALIDACION DE INSTALACION
# ══════════════════════════════════════════════════════════════════════════════════

validate_installation() {
    log_step "Validando instalacion"

    ERRORS=0

    # Verificar modulos Python
    log_info "Verificando modulos Python..."

    MODULES=("requests" "pandas" "PIL" "fitz" "cv2" "openai" "rich")
    for mod in "${MODULES[@]}"; do
        if python3 -c "import $mod" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $mod"
        else
            echo -e "  ${RED}✗${NC} $mod"
            ((ERRORS++))
        fi
    done

    # Verificar Playwright (si se instalo)
    if [ "$INSTALL_PLAYWRIGHT" = true ]; then
        log_info "Verificando Playwright..."
        if python3 -c "from playwright.sync_api import sync_playwright" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} playwright"
        else
            echo -e "  ${RED}✗${NC} playwright"
            ((ERRORS++))
        fi
    fi

    # Verificar scripts ODI
    log_info "Verificando scripts ODI..."

    SCRIPTS=(
        "odi_vision_extractor_v3.py"
        "srm_intelligent_processor.py"
        "odi_event_emitter.py"
        "odi_catalog_unifier.py"
        "odi_image_matcher.py"
    )

    for script in "${SCRIPTS[@]}"; do
        if [ -f "$SCRIPT_DIR/$script" ]; then
            echo -e "  ${GREEN}✓${NC} $script"
        else
            echo -e "  ${YELLOW}?${NC} $script (no encontrado)"
        fi
    done

    # Verificar Vigia
    if [ -f "$SCRIPT_DIR/odi_vigia_playwright.py" ]; then
        echo -e "  ${GREEN}✓${NC} odi_vigia_playwright.py"
    else
        echo -e "  ${YELLOW}?${NC} odi_vigia_playwright.py (no encontrado)"
    fi

    # Verificar directorios
    log_info "Verificando directorios..."

    DIRS=("$OUTPUT_DIR" "$VIGIA_OUTPUT_DIR" "$SRM_OUTPUT_DIR")
    for dir in "${DIRS[@]}"; do
        if [ -d "$dir" ] && [ -w "$dir" ]; then
            echo -e "  ${GREEN}✓${NC} $dir"
        else
            echo -e "  ${RED}✗${NC} $dir"
            ((ERRORS++))
        fi
    done

    if [ $ERRORS -gt 0 ]; then
        log_error "Validacion completada con $ERRORS errores"
        return 1
    else
        log_info "Validacion completada sin errores"
        return 0
    fi
}

# ══════════════════════════════════════════════════════════════════════════════════
# TEST RAPIDO
# ══════════════════════════════════════════════════════════════════════════════════

run_quick_test() {
    log_step "Ejecutando test rapido"

    # Test Event Emitter
    log_info "Probando Event Emitter..."
    python3 -c "
from odi_event_emitter import ODIEventEmitter, EventType
emitter = ODIEventEmitter(source='test', enabled=False)
emitter.emit(EventType.INFO, {'message': 'Test OK'})
print('  Event Emitter: OK')
"

    # Test Vision Extractor (import only)
    log_info "Probando Vision Extractor..."
    python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
# Solo verificar imports basicos
import fitz
import cv2
from PIL import Image
print('  Vision Extractor deps: OK')
"

    # Test Playwright (si esta instalado)
    if [ "$INSTALL_PLAYWRIGHT" = true ]; then
        log_info "Probando Playwright..."
        python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://example.com')
    title = page.title()
    browser.close()
    print(f'  Playwright: OK (titulo: {title})')
"
    fi

    log_info "Tests completados"
}

# ══════════════════════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ══════════════════════════════════════════════════════════════════════════════════

print_summary() {
    echo -e "\n${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                    INSTALACION COMPLETADA                                    ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo -e "${GREEN}ODI Ecosystem v$ODI_VERSION instalado correctamente${NC}\n"

    echo "Componentes instalados:"
    echo "  - Vision Extractor v3.0 (PDF -> Productos)"
    echo "  - SRM Processor v4.0 (Multi-tenant pipeline)"
    echo "  - Event Emitter v1.0 (Telemetria en tiempo real)"
    echo "  - Catalog Unifier v1.0 (Asociacion de imagenes)"
    echo "  - Image Matcher v1.0 (Matching semantico)"
    if [ "$INSTALL_PLAYWRIGHT" = true ]; then
        echo "  - Vigia Playwright v1.0 (Monitoreo de competencia)"
    fi

    echo ""
    echo "Directorios:"
    echo "  - Output general: $OUTPUT_DIR"
    echo "  - Vigia output:   $VIGIA_OUTPUT_DIR"
    echo "  - SRM output:     $SRM_OUTPUT_DIR"

    echo ""
    echo "Proximos pasos:"
    echo "  1. Configurar .env con credenciales reales"
    echo "  2. Iniciar ODI Kernel (Node.js backend)"
    echo "  3. Ejecutar test completo:"
    echo ""
    echo -e "     ${YELLOW}python3 odi_vision_extractor_v3.py catalogo.pdf --pages 1-5${NC}"
    echo ""

    if [ "$INSTALL_PLAYWRIGHT" = true ]; then
        echo "Para Vigia:"
        echo -e "     ${YELLOW}python3 odi_vigia_playwright.py scan${NC}"
        echo ""
    fi

    echo "Documentacion:"
    echo "  - README.md"
    echo "  - ODI_SYSTEM_MANIFEST.md"
    echo "  - ODI_VISION_COMPLETA.md"
    echo ""
}

# ══════════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════════

main() {
    print_banner

    # Parsear argumentos
    INSTALL_MODE="full"
    INSTALL_PLAYWRIGHT=true
    SKIP_TESTS=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                INSTALL_MODE="full"
                INSTALL_PLAYWRIGHT=true
                shift
                ;;
            --minimal)
                INSTALL_MODE="minimal"
                INSTALL_PLAYWRIGHT=false
                shift
                ;;
            --vigia-only)
                INSTALL_MODE="vigia"
                INSTALL_PLAYWRIGHT=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            -h|--help)
                echo "USO: $0 [--full | --minimal | --vigia-only] [--skip-tests]"
                echo ""
                echo "MODOS:"
                echo "  --full       : Instalacion completa (default)"
                echo "  --minimal    : Solo Vision + SRM (sin Playwright)"
                echo "  --vigia-only : Solo Vigia + Playwright"
                echo ""
                echo "OPCIONES:"
                echo "  --skip-tests : Omitir tests de validacion"
                exit 0
                ;;
            *)
                log_error "Opcion desconocida: $1"
                exit 1
                ;;
        esac
    done

    log_info "Modo de instalacion: $INSTALL_MODE"

    # Verificaciones del sistema
    check_python || exit 1
    check_pip || exit 1
    check_system_deps || exit 1

    # Instalacion
    if [ "$INSTALL_MODE" != "vigia" ]; then
        install_python_deps
    fi

    if [ "$INSTALL_PLAYWRIGHT" = true ]; then
        install_playwright
    fi

    # Configuracion
    setup_directories
    setup_env_template

    # Validacion
    validate_installation || log_warn "Algunos componentes no pasaron validacion"

    # Tests
    if [ "$SKIP_TESTS" = false ]; then
        run_quick_test || log_warn "Algunos tests fallaron"
    fi

    # Resumen
    print_summary
}

# Ejecutar
main "$@"
