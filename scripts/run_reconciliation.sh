#\!/bin/bash
# ============================================================
# ODI V006 — Financial Reconciliation Engine (Daily Audit)
# ============================================================
# Ejecutar en: root@64.23.170.118
#
# Uso:
#   bash scripts/run_reconciliation.sh
#
# Output:
#   /tmp/reconciliation_v006.log  — Reporte JSON completo
# ============================================================

set -euo pipefail

LOG_FILE="/tmp/reconciliation_v006.log"
ODI_DIR="/opt/odi"

echo "═══════════════════════════════════════════════════"
echo " ODI V006 — Financial Reconciliation Engine"
echo " $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo "═══════════════════════════════════════════════════"

cd "${ODI_DIR}"

# Configurar entorno para PostgreSQL en Docker
export PYTHONPATH="${ODI_DIR}"
export ODI_PG_HOST="${ODI_PG_HOST:-172.18.0.4}"
export ODI_PG_PORT="${ODI_PG_PORT:-5432}"
export ODI_PG_USER="${ODI_PG_USER:-odi}"
export ODI_PG_PASS="${ODI_PG_PASS:-odi}"
export ODI_PG_DB="${ODI_PG_DB:-odi}"

echo "[INFO] PostgreSQL: ${ODI_PG_HOST}:${ODI_PG_PORT}/${ODI_PG_DB}"
echo ""

python3 -m odi.services.reconciliation_service 2>&1 | tee "${LOG_FILE}"

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
