#!/bin/bash
# ============================================================
# ODI — Backup PostgreSQL con GPG RSA4096 (asymmetric)
# Ejecutar: 3AM diario via cron
# Retención: 30 días
# Key: ODI Backup <backup@odi.larocamotorepuestos.com>
# ============================================================
set -euo pipefail

BACKUP_DIR="/opt/odi/backups/daily"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/odi_postgres_$TIMESTAMP.sql"
ENCRYPTED_FILE="$BACKUP_FILE.gpg"
RETENTION_DAYS=30
LOG_FILE="/opt/odi/logs/backup_postgres.log"
GPG_RECIPIENT="ODI Backup"

log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $1" | tee -a "$LOG_FILE"
}

log "=== INICIO BACKUP PostgreSQL ==="

# Create backup dir if not exists
mkdir -p "$BACKUP_DIR"

# 1. Crear dump
log "Creando dump de base de datos odi..."
docker exec odi-postgres pg_dump -U odi_user -d odi --clean --if-exists > "$BACKUP_FILE"

if [ ! -s "$BACKUP_FILE" ]; then
    log "ERROR: Dump vacío o fallido"
    exit 1
fi

DUMP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "Dump creado: $DUMP_SIZE"

# 2. Encriptar con GPG RSA4096 (asimétrico — solo necesita clave pública)
log "Encriptando con GPG RSA4096 (recipient: $GPG_RECIPIENT)..."
gpg --batch --yes --trust-model always --encrypt --recipient "$GPG_RECIPIENT" -o "$ENCRYPTED_FILE" "$BACKUP_FILE"

# 3. Eliminar dump sin encriptar
rm -f "$BACKUP_FILE"
ENCRYPTED_SIZE=$(du -h "$ENCRYPTED_FILE" | cut -f1)
log "Backup encriptado: $ENCRYPTED_FILE ($ENCRYPTED_SIZE)"

# 4. Limpiar backups antiguos (>30 días)
log "Limpiando backups > $RETENTION_DAYS días..."
DELETED=$(find "$BACKUP_DIR" -name "*.gpg" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)
log "Eliminados: $DELETED archivos antiguos"

# 5. Resumen
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "*.gpg" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "=== BACKUP COMPLETADO ==="
log "Total backups: $TOTAL_BACKUPS | Espacio usado: $TOTAL_SIZE"
