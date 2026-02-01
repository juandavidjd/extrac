#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════════
#                     ODI PRODUCTION DEPLOYMENT v1.0
#        Despliega herramientas de extrac a /opt/odi/ en producción
# ══════════════════════════════════════════════════════════════════════════════════
#
# PREREQUISITOS:
#   - Acceso SSH al servidor: ssh root@odi-server
#   - /opt/odi/ ya existe con la estructura base
#
# USO:
#   # Desde máquina local:
#   scp deploy_to_production.sh root@odi-server:/tmp/
#   ssh root@odi-server "bash /tmp/deploy_to_production.sh"
#
#   # O directamente en el servidor:
#   bash deploy_to_production.sh
#
# ══════════════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
ODI_ROOT="/opt/odi"
PIPELINE_DIR="$ODI_ROOT/pipeline"
ASSETS_ROOT="/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI"
EXTRAC_SOURCE="${EXTRAC_SOURCE:-/home/user/extrac}"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    ODI PRODUCTION DEPLOYMENT v1.0                            ║"
echo "║              Desplegando Vision + SRM + Vigia a /opt/odi/                    ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─────────────────────────────────────────────────────────────────────────────────
# Verificar estructura
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}[1/6]${NC} Verificando estructura de producción..."

if [ ! -d "$ODI_ROOT" ]; then
    echo -e "${RED}Error: $ODI_ROOT no existe${NC}"
    exit 1
fi

echo -e "   ✅ $ODI_ROOT existe"

# Verificar assets
if [ -d "$ASSETS_ROOT" ]; then
    echo -e "   ✅ Assets encontrados en: $ASSETS_ROOT"
    echo -e "      - Data: $(ls -d "$ASSETS_ROOT/Data"/* 2>/dev/null | wc -l) empresas"
    echo -e "      - Logos: $(ls "$ASSETS_ROOT/logos_optimized"/*.png 2>/dev/null | wc -l) logos"
else
    echo -e "   ${YELLOW}⚠️  Assets no encontrados en $ASSETS_ROOT${NC}"
fi

# ─────────────────────────────────────────────────────────────────────────────────
# Crear directorio pipeline
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}[2/6]${NC} Creando directorio pipeline..."

mkdir -p "$PIPELINE_DIR"
mkdir -p "$PIPELINE_DIR/vision"
mkdir -p "$PIPELINE_DIR/srm"
mkdir -p "$PIPELINE_DIR/vigia"
mkdir -p "$PIPELINE_DIR/output"

echo -e "   ✅ Estructura creada: $PIPELINE_DIR"

# ─────────────────────────────────────────────────────────────────────────────────
# Copiar scripts principales
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}[3/6]${NC} Copiando scripts de pipeline..."

# Lista de scripts a copiar
SCRIPTS=(
    "odi_vision_extractor_v3.py"
    "srm_intelligent_processor.py"
    "odi_event_emitter.py"
    "odi_catalog_unifier.py"
    "odi_image_matcher.py"
    "odi_vigia_playwright.py"
    "caso_001_test.py"
)

# Buscar origen de scripts
if [ -d "$EXTRAC_SOURCE" ]; then
    SOURCE_DIR="$EXTRAC_SOURCE"
elif [ -d "/home/user/extrac" ]; then
    SOURCE_DIR="/home/user/extrac"
elif [ -d "$(pwd)" ] && [ -f "$(pwd)/odi_vision_extractor_v3.py" ]; then
    SOURCE_DIR="$(pwd)"
else
    echo -e "${YELLOW}   Scripts no encontrados localmente. Descargando desde repo...${NC}"
    # Clone from git if needed
    SOURCE_DIR="/tmp/extrac_deploy"
    rm -rf "$SOURCE_DIR"
    git clone --depth 1 https://github.com/juandavidjd/extrac.git "$SOURCE_DIR" 2>/dev/null || {
        echo -e "${RED}   No se pudo clonar repositorio${NC}"
        SOURCE_DIR=""
    }
fi

if [ -n "$SOURCE_DIR" ] && [ -d "$SOURCE_DIR" ]; then
    for script in "${SCRIPTS[@]}"; do
        if [ -f "$SOURCE_DIR/$script" ]; then
            cp "$SOURCE_DIR/$script" "$PIPELINE_DIR/"
            echo -e "   ✅ $script"
        else
            echo -e "   ${YELLOW}⚠️  $script no encontrado${NC}"
        fi
    done
else
    echo -e "${RED}   No se encontró fuente de scripts${NC}"
fi

# Copiar requirements
if [ -f "$SOURCE_DIR/requirements.txt" ]; then
    cp "$SOURCE_DIR/requirements.txt" "$PIPELINE_DIR/"
    echo -e "   ✅ requirements.txt"
fi

# ─────────────────────────────────────────────────────────────────────────────────
# Instalar dependencias Python
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}[4/6]${NC} Instalando dependencias Python..."

if [ -f "$PIPELINE_DIR/requirements.txt" ]; then
    pip3 install -r "$PIPELINE_DIR/requirements.txt" --quiet 2>/dev/null || {
        echo -e "   ${YELLOW}Algunas dependencias no se instalaron${NC}"
    }
    echo -e "   ✅ Dependencias instaladas"
else
    echo -e "   ${YELLOW}⚠️  requirements.txt no encontrado${NC}"
fi

# ─────────────────────────────────────────────────────────────────────────────────
# Crear symlinks a assets
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}[5/6]${NC} Creando symlinks a assets del ecosistema..."

# Symlink a datos de empresas
if [ -d "$ASSETS_ROOT/Data" ]; then
    ln -sfn "$ASSETS_ROOT/Data" "$PIPELINE_DIR/empresas_data"
    echo -e "   ✅ empresas_data -> $ASSETS_ROOT/Data"
fi

# Symlink a logos
if [ -d "$ASSETS_ROOT/logos_optimized" ]; then
    ln -sfn "$ASSETS_ROOT/logos_optimized" "$PIPELINE_DIR/logos"
    echo -e "   ✅ logos -> $ASSETS_ROOT/logos_optimized"
fi

# Symlink a imágenes
if [ -d "$ASSETS_ROOT/Imagenes" ]; then
    ln -sfn "$ASSETS_ROOT/Imagenes" "$PIPELINE_DIR/imagenes_empresas"
    echo -e "   ✅ imagenes_empresas -> $ASSETS_ROOT/Imagenes"
fi

# Symlink a perfiles
if [ -d "$ASSETS_ROOT/Perfiles" ]; then
    ln -sfn "$ASSETS_ROOT/Perfiles" "$PIPELINE_DIR/perfiles"
    echo -e "   ✅ perfiles -> $ASSETS_ROOT/Perfiles"
fi

# ─────────────────────────────────────────────────────────────────────────────────
# Crear configuración de producción
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}[6/6]${NC} Creando configuración de producción..."

# Crear .env para pipeline si no existe
if [ ! -f "$PIPELINE_DIR/.env" ]; then
    cat > "$PIPELINE_DIR/.env" << 'ENVFILE'
# ODI Pipeline Configuration
# Generado por deploy_to_production.sh

# Directorios
ODI_OUTPUT_DIR=/opt/odi/pipeline/output
SRM_OUTPUT_DIR=/opt/odi/pipeline/output/srm
VIGIA_OUTPUT_DIR=/opt/odi/pipeline/output/vigia

# Image Server
IMAGE_SERVER_URL=http://64.23.170.118/images

# ODI Kernel
ODI_KERNEL_URL=http://localhost:3000
ODI_EVENT_ENDPOINT=/odi/vision/event

# Assets
ASSETS_ROOT=/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI
LOGOS_DIR=/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/logos_optimized
PERFILES_DIR=/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Perfiles

# Logging
LOG_LEVEL=INFO
ENVFILE
    echo -e "   ✅ .env creado"
else
    echo -e "   ✅ .env ya existe"
fi

# ─────────────────────────────────────────────────────────────────────────────────
# Resumen
# ─────────────────────────────────────────────────────────────────────────────────
echo -e "\n${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    DEPLOYMENT COMPLETADO                                     ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "Estructura desplegada:"
echo ""
ls -la "$PIPELINE_DIR/" 2>/dev/null | head -20
echo ""

echo "Próximos pasos:"
echo "  1. Verificar .env con credenciales de Shopify"
echo "  2. Probar Vision Extractor:"
echo -e "     ${YELLOW}cd $PIPELINE_DIR && python3 odi_vision_extractor_v3.py --help${NC}"
echo ""
echo "  3. Ejecutar Caso 001:"
echo -e "     ${YELLOW}cd $PIPELINE_DIR && python3 caso_001_test.py --check${NC}"
echo ""
