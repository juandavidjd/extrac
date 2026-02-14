#\!/bin/bash
# ============================================================
# ODI — Backup PostgreSQL con GPG AES256
# Ejecutar: 3AM diario via cron
# Retención: 30 días
# ============================================================
set -euo pipefail

BACKUP_DIR="/opt/odi/backups/daily"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/odi_postgres_$TIMESTAMP.sql"
ENCRYPTED_FILE="$BACKUP_FILE.gpg"
RETENTION_DAYS=30
LOG_FILE="/opt/odi/logs/backup_postgres.log"

# Passphrase para GPG (en produccion usar variable de entorno o archivo seguro)
GPG_PASSPHRASE="${ODI_BACKUP_PASSPHRASE:-odi_backup_2026_secure}"

log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $1" | tee -a "$LOG_FILE"
}

log "=== INICIO BACKUP PostgreSQL ==="

# 1. Crear dump
log "Creando dump de base de datos odi..."
docker exec odi-postgres pg_dump -U odi -d odi --clean --if-exists > "$BACKUP_FILE"

if [ \! -s "$BACKUP_FILE" ]; then
    log "ERROR: Dump vacío o fallido"
    exit 1
fi

DUMP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "Dump creado: $DUMP_SIZE"

# 2. Encriptar con GPG AES256
log "Encriptando con GPG AES256..."
echo "$GPG_PASSPHRASE" | gpg --batch --yes --passphrase-fd 0 --symmetric --cipher-algo AES256 -o "$ENCRYPTED_FILE" "$BACKUP_FILE"

# 3. Eliminar dump sin encriptar
rm -f "$BACKUP_FILE"
ENCRYPTED_SIZE=$(du -h "$ENCRYPTED_FILE" | cut -f1)
log "Backup encriptado: $ENCRYPTED_FILE ($ENCRYPTED_SIZE)"

# 4. Limpiar backups antiguos (>30 días)
log "Limpiando backups > $RETENTION_DAYS días..."
DELETED=$(find "$BACKUP_DIR" -name "*.gpg" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)
log "Eliminados: $DELETED archivos antiguos"

# 5. Verificar integridad (desencriptar a /dev/null)
log "Verificando integridad..."
echo "$GPG_PASSPHRASE" | gpg --batch --yes --passphrase-fd 0 -d "$ENCRYPTED_FILE" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    log "✓ Integridad verificada"
else
    log "ERROR: Fallo verificación de integridad"
    exit 1
fi

# 6. Resumen
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "*.gpg" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "=== BACKUP COMPLETADO ==="
log "Total backups: $TOTAL_BACKUPS | Espacio usado: $TOTAL_SIZE"
