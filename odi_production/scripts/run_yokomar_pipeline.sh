#!/bin/bash
# ==============================================================================
#                    ODI YOKOMAR PIPELINE v1.0
#         Pipeline completo: Excel → CSV → Extractor → Normalizer
# ==============================================================================
#
# DESCRIPCION:
#   Automatiza el proceso completo de extraccion de precios de Yokomar.
#   NO requiere Java - usa pandas + openpyxl.
#
# USO:
#   ./run_yokomar_pipeline.sh                    # Usar rutas por defecto
#   ./run_yokomar_pipeline.sh /path/to/excel    # Especificar Excel
#
# REQUISITOS:
#   pip install pandas openpyxl pyyaml
#
# ==============================================================================

set -e  # Salir si hay error

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # Sin color

# Directorios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTRACTORS_DIR="${SCRIPT_DIR}/../extractors"
OUTPUT_DIR="/tmp/odi_output"

# Rutas por defecto
DEFAULT_XLSX="/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Yokomar/LISTA DE PRECIOS ACTUALIZADA YOKOMAR ENERO 28 2026 CON DESCUENTOS.xlsx"
DEFAULT_BASE_CSV="/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Yokomar/Base_Datos_Yokomar.csv"

# Banner
echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              ODI YOKOMAR PIPELINE v1.0                       ║"
echo "║       Excel → CSV → Extractor → Normalizado                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Determinar archivo Excel
if [ -n "$1" ]; then
    XLSX_FILE="$1"
else
    XLSX_FILE="$DEFAULT_XLSX"
fi

echo -e "${CYAN}[INFO]${NC} Archivo Excel: $XLSX_FILE"
echo -e "${CYAN}[INFO]${NC} Directorio salida: $OUTPUT_DIR"
echo ""

# Crear directorio de salida
mkdir -p "$OUTPUT_DIR"

# ==============================================================================
# PASO 1: Convertir Excel a CSV (sin Java)
# ==============================================================================
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PASO 1:${NC} Convirtiendo Excel a CSV..."
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

CSV_PRECIOS="${OUTPUT_DIR}/Lista_Precios_Yokomar_2026.csv"

if [ -f "$XLSX_FILE" ]; then
    python3 "${EXTRACTORS_DIR}/odi_xlsx_to_csv.py" "$XLSX_FILE" \
        --price-mode \
        -o "$CSV_PRECIOS"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK]${NC} CSV de precios generado: $CSV_PRECIOS"
    else
        echo -e "${RED}[ERROR]${NC} Fallo la conversion de Excel"
        exit 1
    fi
else
    echo -e "${YELLOW}[WARN]${NC} Archivo Excel no encontrado: $XLSX_FILE"
    echo -e "${YELLOW}[WARN]${NC} Continuando sin lista de precios..."
    CSV_PRECIOS=""
fi

echo ""

# ==============================================================================
# PASO 2: Ejecutar Extractor Industrial
# ==============================================================================
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PASO 2:${NC} Ejecutando extractor industrial..."
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

EXTRACTOR_CMD="python3 ${EXTRACTORS_DIR}/odi_industrial_extractor.py --profile yokomar"

if [ -n "$CSV_PRECIOS" ] && [ -f "$CSV_PRECIOS" ]; then
    EXTRACTOR_CMD="$EXTRACTOR_CMD --precios $CSV_PRECIOS"
fi

EXTRACTOR_CMD="$EXTRACTOR_CMD -o $OUTPUT_DIR"

echo -e "${CYAN}[CMD]${NC} $EXTRACTOR_CMD"
eval $EXTRACTOR_CMD

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[OK]${NC} Extractor completado"
else
    echo -e "${RED}[ERROR]${NC} Fallo el extractor"
    exit 1
fi

echo ""

# ==============================================================================
# PASO 3: Buscar archivo generado para normalizer
# ==============================================================================
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PASO 3:${NC} Verificando archivos generados..."
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Buscar el archivo REAL_INPUT mas reciente
REAL_INPUT=$(ls -t "${OUTPUT_DIR}"/YOK_REAL_INPUT.csv 2>/dev/null | head -1)

if [ -z "$REAL_INPUT" ]; then
    REAL_INPUT=$(ls -t "${OUTPUT_DIR}"/YOK_catalogo_*.csv 2>/dev/null | head -1)
fi

if [ -n "$REAL_INPUT" ] && [ -f "$REAL_INPUT" ]; then
    echo -e "${GREEN}[OK]${NC} Archivo para normalizer: $REAL_INPUT"

    # Contar productos
    TOTAL_PRODUCTOS=$(wc -l < "$REAL_INPUT")
    echo -e "${GREEN}[OK]${NC} Total productos: $((TOTAL_PRODUCTOS - 1))"
else
    echo -e "${YELLOW}[WARN]${NC} No se encontro archivo de salida"
fi

echo ""

# ==============================================================================
# RESUMEN FINAL
# ==============================================================================
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}PIPELINE COMPLETADO${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Archivos generados en: $OUTPUT_DIR"
ls -la "$OUTPUT_DIR"/*.csv 2>/dev/null || echo "  (ninguno)"
echo ""
echo -e "${CYAN}SIGUIENTE PASO (opcional):${NC}"
echo "  python3 odi_semantic_normalizer.py $REAL_INPUT"
echo ""
