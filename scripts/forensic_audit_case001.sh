#!/bin/bash
# ============================================================
# ODI — AUDITORÍA FORENSE Caso 001 (TX-CASE-001)
# ============================================================
# Orden operativa: Recolección de evidencia cruda.
# NO modifica. NO reinicia. Solo recolecta.
# Ejecutar en: root@64.23.170.118
# ============================================================

set -uo pipefail

TX_ID="TX-CASE-001"
API_URL="${PAEM_API_URL:-https://api.liveodi.com}"
PG_CMD="docker exec odi-postgres psql -U odi -d odi"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ODI — AUDITORÍA FORENSE CASO 001                          ║"
echo "║  TX: $TX_ID                                       ║"
echo "║  Timestamp: $TIMESTAMP                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# ═══════════════════════════════════════════════════════════════════
# PASO 1 — SELECT DE LA VERDAD (SSOT)
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PASO 1: SELECT DE LA VERDAD (Estado cruzado payments ↔ bookings)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

$PG_CMD <<SQL
SELECT
    p.status AS pay_status,
    b.status AS booking_status,
    p.amount,
    p.updated_at
FROM odi_payments p
JOIN odi_health_bookings b
    ON p.transaction_id = b.transaction_id
WHERE p.transaction_id = '$TX_ID';
SQL

# ═══════════════════════════════════════════════════════════════════
# PASO 2 — LOGS DE WEBHOOK (CAJA NEGRA)
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PASO 2: LOGS DEL CONTENEDOR odi-paem-api (últimas 120 líneas)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

docker logs --tail 120 odi-paem-api

# ═══════════════════════════════════════════════════════════════════
# PASO 3 — RASTRO DE EVENTOS
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PASO 3: RASTRO DE EVENTOS (odi_events)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

$PG_CMD <<SQL
SELECT
    event_type,
    created_at,
    payload
FROM odi_events
WHERE transaction_id = '$TX_ID'
ORDER BY created_at DESC;
SQL

# ═══════════════════════════════════════════════════════════════════
# PASO 4 — VALIDACIÓN DE EXPOSICIÓN DE PUERTOS
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PASO 4: EXPOSICIÓN DE PUERTOS (ss -tulpn)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ss -tulpn

# ═══════════════════════════════════════════════════════════════════
# PASO 5 — VALIDACIÓN DE WEBHOOK HTTP
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PASO 5: VALIDACIÓN HTTP DEL WEBHOOK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

curl -i -X POST "$API_URL/paem/webhooks/wompi" \
    -H "Content-Type: application/json" \
    -d '{}' 2>&1

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  AUDITORÍA FORENSE COMPLETA                                 ║"
echo "║  Diagnóstico por capas:                                     ║"
echo "║    Capa 1 — Red (puertos, exposición)                       ║"
echo "║    Capa 2 — Firma (HMAC webhook)                            ║"
echo "║    Capa 3 — Transacción SQL (atomicidad)                    ║"
echo "║    Capa 4 — Idempotencia (re-procesamiento)                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
