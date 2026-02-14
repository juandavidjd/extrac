#!/bin/bash
# ============================================================
# ODI V006 — Financial Reconciliation Engine (Daily Audit)
# ============================================================
# Ejecutar en: root@64.23.170.118  (o localmente con Postgres accesible)
#
# Uso:
#   bash scripts/run_reconciliation.sh
#
# Output:
#   /tmp/reconciliation_v006.log  — Reporte JSON completo
# ============================================================

set -euo pipefail

LOG_FILE="/tmp/reconciliation_v006.log"
CONTAINER="odi-paem-api"
SCRIPT_CMD="python3 -m odi.services.reconciliation_service"

echo "═══════════════════════════════════════════════════"
echo " ODI V006 — Financial Reconciliation Engine"
echo " $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "═══════════════════════════════════════════════════"

# Detect environment: Docker container available or local
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER}$"; then
    echo "[INFO] Ejecutando dentro del contenedor ${CONTAINER}..."
    docker exec "${CONTAINER}" ${SCRIPT_CMD} 2>&1 | tee "${LOG_FILE}"
else
    echo "[INFO] Contenedor no detectado. Ejecutando localmente..."
    cd "$(dirname "$0")/.."
    ${SCRIPT_CMD} 2>&1 | tee "${LOG_FILE}"
fi

EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "═══════════════════════════════════════════════════"
if [ ${EXIT_CODE} -eq 0 ]; then
    echo " [OK] Reporte guardado en ${LOG_FILE}"
else
    echo " [ERROR] Audit falló (exit code ${EXIT_CODE})"
fi
echo "═══════════════════════════════════════════════════"

exit ${EXIT_CODE}
