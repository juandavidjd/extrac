#!/bin/bash
# ============================================================
# ODI — AUDITORÍA FORENSE Caso 001 (TX-CASE-001)
# ============================================================
set -uo pipefail

TX_ID="TX-CASE-001"
API_URL="${PAEM_API_URL:-https://api.liveodi.com}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ODI — AUDITORÍA FORENSE CASO 001                            ║"
echo "║  TX: $TX_ID | $TIMESTAMP                                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# PASO 1 — SELECT DE LA VERDAD
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PASO 1: SELECT DE LA VERDAD (payments ↔ bookings)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

docker exec odi-postgres psql -U odi -d odi -c   "SELECT p.status AS pay, b.status AS book, p.amount, p.updated_at FROM odi_payments p JOIN odi_health_bookings b ON p.transaction_id = b.transaction_id WHERE p.transaction_id = 'TX-CASE-001';"

# PASO 2 — LOGS DEL SERVICIO
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PASO 2: LOGS odi-paem-api (últimas 20 líneas)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

journalctl -u odi-paem-api --no-pager -n 20 2>/dev/null ||   tail -20 /opt/odi/logs/paem_api.log 2>/dev/null ||   echo "  [!] Sin logs"

# PASO 3 — EVENTOS
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PASO 3: RASTRO DE EVENTOS (odi_events)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

docker exec odi-postgres psql -U odi -d odi -c   "SELECT event_type, created_at FROM odi_events WHERE transaction_id = 'TX-CASE-001' ORDER BY created_at DESC LIMIT 10;" 2>/dev/null || echo "  (sin eventos)"

# PASO 4 — PUERTOS
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PASO 4: PUERTOS CRÍTICOS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ss -tlnp | grep -E "8807|8800|443|80|6379" | head -10

# PASO 5 — WEBHOOK
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PASO 5: WEBHOOK (debe rechazar sin firma)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

curl -s -X POST "$API_URL/webhooks/wompi" -H "Content-Type: application/json" -d '{}'

echo ""
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✓ AUDITORÍA COMPLETA                                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
