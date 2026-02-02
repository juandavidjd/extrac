#!/bin/bash
#===============================================================================
# ODI - Indexar TODO el contenido de /profesion
# Ejecutar en el servidor de producción
#===============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║     ██████╗ ██████╗ ██╗    ██╗  ██╗██████╗                   ║"
echo "║    ██╔═══██╗██╔══██╗██║    ██║ ██╔╝██╔══██╗                  ║"
echo "║    ██║   ██║██║  ██║██║    █████╔╝ ██████╔╝                  ║"
echo "║    ██║   ██║██║  ██║██║    ██╔═██╗ ██╔══██╗                  ║"
echo "║    ╚██████╔╝██████╔╝██║    ██║  ██╗██████╔╝                  ║"
echo "║     ╚═════╝ ╚═════╝ ╚═╝    ╚═╝  ╚═╝╚═════╝                   ║"
echo "║                                                               ║"
echo "║    Knowledge Base Indexer - Full Profesion                   ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Variables
PROFESION_PATH="/mnt/volume_sfo3_01/profesion"
ODI_PATH="/opt/odi"
INDEXER_SCRIPT="$ODI_PATH/core/odi_kb_indexer_v2.py"
VENV_PATH="$ODI_PATH/venv"

# ============================================
# 1. Verificar requisitos
# ============================================
echo -e "${YELLOW}[1/6] Verificando requisitos...${NC}"

# Verificar que existe profesion
if [ ! -d "$PROFESION_PATH" ]; then
    echo -e "${RED}✗ No existe: $PROFESION_PATH${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Directorio profesion existe${NC}"

# Contar archivos
FILE_COUNT=$(find "$PROFESION_PATH" -type f \( -name "*.pdf" -o -name "*.md" -o -name "*.txt" -o -name "*.json" -o -name "*.csv" -o -name "*.py" \) 2>/dev/null | wc -l)
echo -e "${CYAN}  Archivos encontrados: $FILE_COUNT${NC}"

# Tamaño total
TOTAL_SIZE=$(du -sh "$PROFESION_PATH" 2>/dev/null | cut -f1)
echo -e "${CYAN}  Tamaño total: $TOTAL_SIZE${NC}"

# ============================================
# 2. Verificar/Crear entorno virtual
# ============================================
echo -e "${YELLOW}[2/6] Verificando entorno Python...${NC}"

if [ ! -d "$VENV_PATH" ]; then
    echo -e "${CYAN}  Creando entorno virtual...${NC}"
    python3 -m venv "$VENV_PATH"
fi

source "$VENV_PATH/bin/activate"
echo -e "${GREEN}✓ Entorno virtual activado${NC}"

# ============================================
# 3. Instalar dependencias
# ============================================
echo -e "${YELLOW}[3/6] Instalando dependencias...${NC}"

pip install --quiet --upgrade pip
pip install --quiet \
    openai \
    langchain \
    langchain-openai \
    langchain-community \
    chromadb \
    tiktoken \
    pdfplumber \
    markdown \
    beautifulsoup4 \
    redis \
    httpx \
    python-dotenv \
    watchdog

echo -e "${GREEN}✓ Dependencias instaladas${NC}"

# ============================================
# 4. Verificar API Key
# ============================================
echo -e "${YELLOW}[4/6] Verificando configuración...${NC}"

if [ -f "$ODI_PATH/.env" ]; then
    source "$ODI_PATH/.env"
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}✗ OPENAI_API_KEY no configurada${NC}"
    echo -e "${YELLOW}  Configura en: $ODI_PATH/.env${NC}"
    exit 1
fi
echo -e "${GREEN}✓ API Key configurada${NC}"

# ============================================
# 5. Copiar indexador si es necesario
# ============================================
echo -e "${YELLOW}[5/6] Preparando indexador...${NC}"

# Verificar si existe el script
if [ ! -f "$INDEXER_SCRIPT" ]; then
    echo -e "${CYAN}  Copiando indexador v2...${NC}"
    mkdir -p "$ODI_PATH/core"
    # El script debe estar en el mismo directorio que este
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$SCRIPT_DIR/../core/odi_kb_indexer_v2.py" ]; then
        cp "$SCRIPT_DIR/../core/odi_kb_indexer_v2.py" "$INDEXER_SCRIPT"
    else
        echo -e "${RED}✗ No se encontró odi_kb_indexer_v2.py${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Indexador listo${NC}"

# ============================================
# 6. Ejecutar indexación
# ============================================
echo -e "${YELLOW}[6/6] Iniciando indexación...${NC}"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Procesando $FILE_COUNT archivos de $PROFESION_PATH${NC}"
echo -e "${CYAN}  Esto puede tomar varios minutos...${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Ejecutar con modo reindex si se pasa --force
if [ "$1" == "--force" ]; then
    python3 "$INDEXER_SCRIPT" --reindex
else
    python3 "$INDEXER_SCRIPT" --index-all
fi

# ============================================
# Resultado
# ============================================
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ INDEXACIÓN COMPLETADA${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Embeddings guardados en:${NC}"
echo -e "  ${BLUE}/mnt/volume_sfo3_01/embeddings/profesion_kb${NC}"
echo ""
echo -e "${YELLOW}Para consultar:${NC}"
echo -e "  ${BLUE}python3 $ODI_PATH/core/odi_kb_query.py --query 'tu pregunta'${NC}"
echo ""
echo -e "${YELLOW}Para ver estadísticas:${NC}"
echo -e "  ${BLUE}python3 $INDEXER_SCRIPT --stats${NC}"
echo ""
echo -e "${YELLOW}Para modo watch (detectar cambios):${NC}"
echo -e "  ${BLUE}python3 $INDEXER_SCRIPT --watch${NC}"
echo ""

deactivate
