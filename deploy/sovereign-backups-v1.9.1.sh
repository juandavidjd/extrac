#!/usr/bin/env bash
# ===============================
# ODI v1.9.1 — SOVEREIGN BACKUPS (GPG + VERIFY + CRON)
# Server: 64.23.170.118 | User: odi | Path: /opt/odi
# Goal: Encrypted, verified, rotating backups (30d) with cron daily.
# ===============================
set -euo pipefail

echo "[STEP] 0) Preconditions"
whoami
cd /opt/odi

echo "[STEP] 1) Packages"
sudo apt-get update -y
sudo apt-get install -y gnupg rsync pigz jq

echo "[STEP] 2) Folders"
sudo mkdir -p /opt/odi/backups/encrypted
sudo mkdir -p /opt/odi/scripts/backup
sudo mkdir -p /opt/odi/logs
sudo chown -R odi:odi /opt/odi/backups /opt/odi/scripts/backup /opt/odi/logs
sudo chmod 750 /opt/odi/backups /opt/odi/backups/encrypted /opt/odi/scripts /opt/odi/scripts/backup /opt/odi/logs

echo "[STEP] 3) .env backup variables (NO PRINT)"
# Ensure .env exists and is private
sudo chown odi:odi /opt/odi/.env
sudo chmod 600 /opt/odi/.env
# Add only if missing (idempotent)
grep -q '^ODI_BACKUP_RETENTION_DAYS=' /opt/odi/.env || echo 'ODI_BACKUP_RETENTION_DAYS=30' >> /opt/odi/.env
grep -q '^ODI_BACKUP_PASSPHRASE=' /opt/odi/.env || echo 'ODI_BACKUP_PASSPHRASE=CHANGE_ME_LONG_RANDOM' >> /opt/odi/.env
echo "[IMPORTANT] Replace ODI_BACKUP_PASSPHRASE in /opt/odi/.env with a long random secret NOW."
echo "You can do: sudo nano /opt/odi/.env (do NOT commit .env)"

echo "[STEP] 4) Create backup script: backup_sovereign.sh"
cat > /opt/odi/scripts/backup/backup_sovereign.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail
LOG_FILE="/opt/odi/logs/backup.log"
exec >> "$LOG_FILE" 2>&1
ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
echo "[$(ts)] [START] backup_sovereign"

# Load env (do NOT echo secrets)
set +u
source /opt/odi/.env
set -u
RETENTION_DAYS="${ODI_BACKUP_RETENTION_DAYS:-30}"
PASSPHRASE="${ODI_BACKUP_PASSPHRASE:-}"
if [[ -z "$PASSPHRASE" || "$PASSPHRASE" == "CHANGE_ME_LONG_RANDOM" ]]; then
  echo "[$(ts)] [FATAL] ODI_BACKUP_PASSPHRASE is missing or default. Set it in /opt/odi/.env"
  exit 2
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
STAGE_DIR="/opt/odi/backups/${RUN_ID}"
OUT_GPG="/opt/odi/backups/encrypted/odi_backup_${RUN_ID}.tar.gz.gpg"
OUT_SHA="${OUT_GPG}.sha256"
mkdir -p "$STAGE_DIR"
echo "[$(ts)] [INFO] RUN_ID=$RUN_ID"

# -------------------
# 1) Snapshot turismo leads
# -------------------
if [[ -d "/opt/odi/data/turismo_leads" ]]; then
  mkdir -p "$STAGE_DIR/data"
  rsync -a --delete "/opt/odi/data/turismo_leads/" "$STAGE_DIR/data/turismo_leads/"
  echo "[$(ts)] [OK] turismo_leads synced"
else
  echo "[$(ts)] [WARN] /opt/odi/data/turismo_leads not found"
fi

# -------------------
# 2) MEMORY.md
# -------------------
if [[ -f "/opt/odi/MEMORY.md" ]]; then
  cp -f "/opt/odi/MEMORY.md" "$STAGE_DIR/MEMORY.md"
  echo "[$(ts)] [OK] MEMORY.md copied"
else
  echo "[$(ts)] [WARN] /opt/odi/MEMORY.md not found"
fi

# -------------------
# 3) Sanitized env (NO SECRETS)
# -------------------
if [[ -f "/opt/odi/.env" ]]; then
  # redact values
  grep -v '^\s*#' /opt/odi/.env | grep -v '^\s*$' | sed 's/=.*/=***REDACTED***/' > "$STAGE_DIR/env_sanitized.txt" || true
  echo "[$(ts)] [OK] env_sanitized.txt created"
fi

# -------------------
# 4) Postgres dump (container)
# -------------------
if docker ps --format '{{.Names}}' | grep -q '^odi-postgres$'; then
  mkdir -p "$STAGE_DIR/db"
  DB_NAME="${ODI_DB_NAME:-}"
  if [[ -n "$DB_NAME" ]]; then
    docker exec -i odi-postgres pg_dump -U postgres "$DB_NAME" > "$STAGE_DIR/db/postgres_${DB_NAME}.sql"
    echo "[$(ts)] [OK] Postgres pg_dump db=$DB_NAME"
  else
    docker exec -i odi-postgres pg_dumpall -U postgres > "$STAGE_DIR/db/postgres_all.sql"
    echo "[$(ts)] [OK] Postgres pg_dumpall"
  fi
else
  echo "[$(ts)] [WARN] odi-postgres container not running; skipping db dump"
fi

# -------------------
# 5) Redis dump (optional)
# -------------------
if docker ps --format '{{.Names}}' | grep -q '^odi-redis$'; then
  mkdir -p "$STAGE_DIR/cache"
  docker exec -i odi-redis redis-cli SAVE >/dev/null 2>&1 || true
  docker exec -i odi-redis sh -lc 'ls -lah /data/dump.rdb 2>/dev/null && cat /data/dump.rdb' > "$STAGE_DIR/cache/redis_dump.rdb" || true
  if [[ -s "$STAGE_DIR/cache/redis_dump.rdb" ]]; then
    echo "[$(ts)] [OK] Redis dump captured"
  else
    echo "[$(ts)] [WARN] Redis dump not captured (path may differ)"
    rm -f "$STAGE_DIR/cache/redis_dump.rdb" || true
  fi
else
  echo "[$(ts)] [INFO] odi-redis not running; skipping redis dump"
fi

# -------------------
# 6) ChromaDB persistent data
# -------------------
if docker ps --format '{{.Names}}' | grep -q '^odi-chromadb$'; then
  mkdir -p "$STAGE_DIR/chroma"
  MOUNT_SRC="$(docker inspect odi-chromadb --format '{{range .Mounts}}{{if or (eq .Destination "/chroma") (eq .Destination "/chroma/chroma")}}{{.Source}}{{end}}{{end}}' | tr -d '\n')"
  if [[ -n "$MOUNT_SRC" && -d "$MOUNT_SRC" ]]; then
    rsync -a --delete "$MOUNT_SRC/" "$STAGE_DIR/chroma/"
    echo "[$(ts)] [OK] Chroma mount backed up from $MOUNT_SRC"
  else
    echo "[$(ts)] [WARN] Could not detect chroma mount on host; attempting in-container export"
    docker exec -i odi-chromadb sh -lc 'tar -C / -cf - chroma 2>/dev/null || tar -C / -cf - chroma/chroma 2>/dev/null' > "$STAGE_DIR/chroma/chroma_container.tar" || true
    if [[ -s "$STAGE_DIR/chroma/chroma_container.tar" ]]; then
      echo "[$(ts)] [OK] Chroma container tar captured"
    else
      echo "[$(ts)] [WARN] Chroma export not captured"
      rm -f "$STAGE_DIR/chroma/chroma_container.tar" || true
    fi
  fi
else
  echo "[$(ts)] [WARN] odi-chromadb not running; skipping chroma backup"
fi

# -------------------
# Create archive (pigz if available)
# -------------------
ARCHIVE="/opt/odi/backups/odi_backup_${RUN_ID}.tar.gz"
echo "[$(ts)] [INFO] Creating archive..."
if command -v pigz >/dev/null 2>&1; then
  tar -C "/opt/odi/backups" -cf - "$RUN_ID" | pigz -9 > "$ARCHIVE"
else
  tar -C "/opt/odi/backups" -czf "$ARCHIVE" "$RUN_ID"
fi
echo "[$(ts)] [OK] Archive created: $ARCHIVE"

# Encrypt symmetrically with passphrase (batch mode)
echo "[$(ts)] [INFO] Encrypting..."
gpg --batch --yes --pinentry-mode loopback \
  --passphrase "$PASSPHRASE" \
  -c -o "$OUT_GPG" "$ARCHIVE"
echo "[$(ts)] [OK] Encrypted: $OUT_GPG"

# checksum
sha256sum "$OUT_GPG" > "$OUT_SHA"
echo "[$(ts)] [OK] SHA256: $OUT_SHA"

# Cleanup plaintext archive + staging
rm -f "$ARCHIVE"
rm -rf "$STAGE_DIR"
echo "[$(ts)] [OK] Cleaned staging and plaintext"

# Rotation
echo "[$(ts)] [INFO] Rotation > ${RETENTION_DAYS} days"
find /opt/odi/backups/encrypted -name 'odi_backup_*.gpg' -type f -mtime +"$RETENTION_DAYS" -print -delete || true
find /opt/odi/backups/encrypted -name 'odi_backup_*.gpg.sha256' -type f -mtime +"$RETENTION_DAYS" -print -delete || true
echo "[$(ts)] [DONE] backup_sovereign"
BASH
chmod 750 /opt/odi/scripts/backup/backup_sovereign.sh

echo "[STEP] 5) Create verify script: verify_backup.sh"
cat > /opt/odi/scripts/backup/verify_backup.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail
LOG_FILE="/opt/odi/logs/backup.log"
exec >> "$LOG_FILE" 2>&1
ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

set +u
source /opt/odi/.env
set -u
PASSPHRASE="${ODI_BACKUP_PASSPHRASE:-}"
if [[ -z "$PASSPHRASE" || "$PASSPHRASE" == "CHANGE_ME_LONG_RANDOM" ]]; then
  echo "[$(ts)] [FATAL] ODI_BACKUP_PASSPHRASE is missing or default."
  exit 2
fi

FILE="${1:-}"
if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "[$(ts)] [FATAL] Provide .gpg file path to verify"
  exit 1
fi

SHA_FILE="${FILE}.sha256"
if [[ ! -f "$SHA_FILE" ]]; then
  echo "[$(ts)] [FATAL] Missing sha256 file: $SHA_FILE"
  exit 1
fi

echo "[$(ts)] [START] verify $FILE"
# checksum
sha256sum -c "$SHA_FILE"
# decrypt test to /tmp (no extraction)
TMP_OUT="/tmp/odi_restore_test_$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
gpg --batch --yes --pinentry-mode loopback --passphrase "$PASSPHRASE" \
  -o "$TMP_OUT" -d "$FILE" >/dev/null
# basic sanity: tar list
tar -tzf "$TMP_OUT" >/dev/null
rm -f "$TMP_OUT"
echo "[$(ts)] [OK] verify passed"
BASH
chmod 750 /opt/odi/scripts/backup/verify_backup.sh

echo "[STEP] 6) Create pre-index helper: pre_index_snapshot.sh"
cat > /opt/odi/scripts/backup/pre_index_snapshot.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail
bash /opt/odi/scripts/backup/backup_sovereign.sh
LATEST="$(ls -1t /opt/odi/backups/encrypted/*.gpg 2>/dev/null | head -n 1 || true)"
if [[ -z "$LATEST" ]]; then
  echo "[FATAL] No backup produced"
  exit 1
fi
bash /opt/odi/scripts/backup/verify_backup.sh "$LATEST"
echo "[OK] SAFE TO INDEX"
BASH
chmod 750 /opt/odi/scripts/backup/pre_index_snapshot.sh

echo "[STEP] 7) Ensure ownership/permissions"
sudo chown -R odi:odi /opt/odi/scripts/backup /opt/odi/backups /opt/odi/logs
sudo chmod 750 /opt/odi/scripts/backup /opt/odi/backups /opt/odi/backups/encrypted /opt/odi/logs

echo "[STEP] 8) Run smoke backup now (will fail if passphrase still default)"
/opt/odi/scripts/backup/backup_sovereign.sh || true

echo "[STEP] 9) If passphrase set, run again and verify"
echo "EDIT NOW: sudo nano /opt/odi/.env  (set ODI_BACKUP_PASSPHRASE to long random)"
echo "Then rerun:"
echo "  /opt/odi/scripts/backup/backup_sovereign.sh"
echo "  /opt/odi/scripts/backup/verify_backup.sh \$(ls -1t /opt/odi/backups/encrypted/*.gpg | head -n 1)"

echo "[STEP] 10) Install cron (user odi)"
( crontab -l 2>/dev/null | grep -v 'backup_sovereign.sh' || true
  echo "15 2 * * * /bin/bash /opt/odi/scripts/backup/backup_sovereign.sh >> /opt/odi/logs/backup.log 2>&1"
  echo "25 2 * * * /bin/bash /opt/odi/scripts/backup/verify_backup.sh \"\$(ls -1t /opt/odi/backups/encrypted/*.gpg 2>/dev/null | head -n 1)\" >> /opt/odi/logs/backup.log 2>&1"
) | crontab -

echo "[STEP] 11) Git: commit scripts only (NO backups)"
cd /opt/odi
git status --porcelain
git add scripts/backup/*.sh
git commit -m "feat(sec): v1.9.1 sovereign encrypted backups + verify + cron" || true
git push || true

echo "[DONE] v1.9.1 backup system installed. Provide outputs:"
echo "  ls -lh /opt/odi/backups/encrypted | tail"
echo "  tail -n 60 /opt/odi/logs/backup.log"
echo "  crontab -l | grep backup_sovereign"
