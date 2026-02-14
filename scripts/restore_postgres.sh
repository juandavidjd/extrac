#!/bin/bash
# ============================================================
# ODI — Restore PostgreSQL desde backup GPG
# Uso: ./restore_postgres.sh <archivo.sql.gpg>
# ============================================================
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Uso: $0 <archivo_backup.sql.gpg>"
    echo ""
    echo "Backups disponibles:"
    ls -lh /opt/odi/backups/daily/*.gpg 2>/dev/null || echo "  (ninguno)"
    exit 1
fi

BACKUP_FILE="$1"
GPG_PASSPHRASE="${ODI_BACKUP_PASSPHRASE:-odi_backup_2026_secure}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Archivo no encontrado: $BACKUP_FILE"
    exit 1
fi

echo "=== RESTORE PostgreSQL ==="
echo "Archivo: $BACKUP_FILE"
echo ""
read -p "¿Confirmar restore? Esto SOBRESCRIBIRÁ la base de datos actual. (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelado."
    exit 0
fi

echo "Desencriptando y restaurando..."
echo "$GPG_PASSPHRASE" | gpg --batch --yes --passphrase-fd 0 -d "$BACKUP_FILE" | \
    docker exec -i odi-postgres psql -U odi -d odi

echo ""
echo "✓ Restore completado"
echo ""
echo "Verificar con:"
echo "  docker exec odi-postgres psql -U odi -d odi -c dt odi_*"
