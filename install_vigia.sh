#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════════
#                     ODI VIGIA INSTALLER v1.0
#        Instalador rapido de Vigia + Playwright
# ══════════════════════════════════════════════════════════════════════════════════
#
# USO:
#   chmod +x install_vigia.sh
#   ./install_vigia.sh
#
# Este script instala solo los componentes necesarios para Vigia:
#   - Playwright
#   - Chromium browser
#   - Dependencias del sistema
#
# ══════════════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                   ODI VIGIA INSTALLER v1.0                                   ║"
echo "║              Sistema de Monitoreo de Competencia                             ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─────────────────────────────────────────────────────────────────────────────────
# Verificar Python
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}[1/5]${NC} Verificando Python..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python3 no encontrado${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "      $PYTHON_VERSION"

# ─────────────────────────────────────────────────────────────────────────────────
# Instalar dependencias base
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}[2/5]${NC} Instalando dependencias base..."

pip3 install --upgrade pip
pip3 install requests pandas aiofiles rich

# ─────────────────────────────────────────────────────────────────────────────────
# Instalar Playwright
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}[3/5]${NC} Instalando Playwright..."

pip3 install playwright

# ─────────────────────────────────────────────────────────────────────────────────
# Instalar Chromium
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}[4/5]${NC} Instalando Chromium browser..."

python3 -m playwright install chromium

# Intentar instalar dependencias del sistema
echo -e "\n${GREEN}[4.5/5]${NC} Instalando dependencias del sistema para Playwright..."

if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpango-1.0-0 \
        libcairo2 \
        libatspi2.0-0 \
        2>/dev/null || echo -e "${YELLOW}Algunas dependencias no se pudieron instalar${NC}"
else
    echo -e "${YELLOW}Sistema no Debian/Ubuntu - ejecutar manualmente: playwright install-deps${NC}"
fi

# ─────────────────────────────────────────────────────────────────────────────────
# Crear directorios
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}[5/5]${NC} Creando directorios..."

VIGIA_DIR="${VIGIA_OUTPUT_DIR:-/tmp/vigia_output}"
mkdir -p "$VIGIA_DIR/screenshots"
mkdir -p "$VIGIA_DIR/cache"
chmod -R 755 "$VIGIA_DIR"

echo -e "      Directorio: $VIGIA_DIR"

# ─────────────────────────────────────────────────────────────────────────────────
# Test rapido
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Ejecutando test de Playwright...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

python3 << 'PYTEST'
from playwright.sync_api import sync_playwright

print("  Iniciando Chromium headless...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("  Navegando a example.com...")
    page.goto("https://example.com")

    title = page.title()
    print(f"  Titulo obtenido: {title}")

    browser.close()
    print("\n  ✓ Playwright funcionando correctamente!")
PYTEST

# ─────────────────────────────────────────────────────────────────────────────────
# Resumen
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    VIGIA INSTALADO                                           ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "Componentes instalados:"
echo "  - Playwright"
echo "  - Chromium browser"
echo "  - Event Emitter (odi_event_emitter.py)"
echo "  - Vigia script (odi_vigia_playwright.py)"
echo ""
echo "Directorio de salida: $VIGIA_DIR"
echo ""
echo "Uso:"
echo -e "  ${YELLOW}python3 odi_vigia_playwright.py scan${NC}"
echo -e "  ${YELLOW}python3 odi_vigia_playwright.py search \"pastillas freno\"${NC}"
echo -e "  ${YELLOW}python3 odi_vigia_playwright.py category frenos${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────────
# Crear servicio CRON (opcional)
# ─────────────────────────────────────────────────────────────────────────────────
echo "Para programar escaneo diario a las 7AM:"
echo -e "  ${YELLOW}crontab -e${NC}"
echo -e "  ${YELLOW}0 7 * * * cd $SCRIPT_DIR && python3 odi_vigia_playwright.py scan >> /var/log/vigia.log 2>&1${NC}"
echo ""
