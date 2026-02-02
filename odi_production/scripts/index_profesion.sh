#!/bin/bash
#===============================================================================
# Script para indexar todo el contenido de /mnt/volume_sfo3_01/profesion
#===============================================================================

set -e

ODI_HOME="/opt/odi"
PROFESION_PATH="/mnt/volume_sfo3_01/profesion"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║           ODI - Indexador de Conocimiento                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Verificar que existe el directorio
if [ ! -d "$PROFESION_PATH" ]; then
    echo "[ERROR] Directorio no encontrado: $PROFESION_PATH"
    echo ""
    echo "Verifica que el volumen este montado:"
    echo "  ls -la /mnt/volume_sfo3_01/"
    echo ""
    exit 1
fi

# Mostrar estadisticas
echo "[INFO] Analizando contenido de: $PROFESION_PATH"
echo ""

TOTAL_FILES=$(find "$PROFESION_PATH" -type f | wc -l)
PDF_COUNT=$(find "$PROFESION_PATH" -type f -name "*.pdf" | wc -l)
MD_COUNT=$(find "$PROFESION_PATH" -type f -name "*.md" | wc -l)
TXT_COUNT=$(find "$PROFESION_PATH" -type f -name "*.txt" | wc -l)
JSON_COUNT=$(find "$PROFESION_PATH" -type f -name "*.json" | wc -l)
TOTAL_SIZE=$(du -sh "$PROFESION_PATH" | cut -f1)

echo "  Total archivos:  $TOTAL_FILES"
echo "  PDFs:            $PDF_COUNT"
echo "  Markdown:        $MD_COUNT"
echo "  Text:            $TXT_COUNT"
echo "  JSON:            $JSON_COUNT"
echo "  Tamaño total:    $TOTAL_SIZE"
echo ""

# Confirmar
read -p "¿Iniciar indexacion? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelado."
    exit 0
fi

# Activar entorno virtual
echo ""
echo "[INFO] Activando entorno Python..."
source "$ODI_HOME/venv/bin/activate"

# Cargar variables de entorno
export $(grep -v '^#' "$ODI_HOME/config/.env" | xargs)

# Ejecutar indexador
echo "[INFO] Iniciando indexacion..."
echo ""

python "$ODI_HOME/core/odi_kb_indexer.py" --index

echo ""
echo "[OK] Indexacion completada!"
echo ""
echo "Para iniciar el servicio de consultas:"
echo "  systemctl start odi-query"
echo ""
echo "Para probar:"
echo "  curl -X POST http://localhost:8000/query \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"question\": \"¿Que es ODI?\"}'"
echo ""
