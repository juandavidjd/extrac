#\!/bin/bash
# Limpieza automática de imágenes extraídas de PDFs
IMAGES_DIR="/opt/odi/data/pdf_images"
MAX_AGE_DAYS=30

if [ -d "$IMAGES_DIR" ]; then
    BEFORE=$(du -sh "$IMAGES_DIR" | cut -f1)
    find "$IMAGES_DIR" -type f -mtime +$MAX_AGE_DAYS -delete
    AFTER=$(du -sh "$IMAGES_DIR" | cut -f1)
    echo "$(date): pdf_images limpiado: $BEFORE -> $AFTER"
fi
