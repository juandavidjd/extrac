#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# ODI PAEM — Smoke Tests para Metabolismo Económico
# ═══════════════════════════════════════════════════════════════════════════════
# Uso: bash tests/test_paem_payments_smoke.sh [BASE_URL]
# Default: https://api.adsi.com.co
# ═══════════════════════════════════════════════════════════════════════════════

BASE="${1:-https://api.adsi.com.co}"
PASS=0
FAIL=0

check() {
    local desc="$1"
    local expected="$2"
    local actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  [PASS] $desc (HTTP $actual)"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $desc (expected $expected, got $actual)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== ODI PAEM Payment Smoke Tests ==="
echo "Target: $BASE"
echo ""

# Test 1: Health check
echo "--- Test 1: Health Check ---"
HTTP=$(curl -s -o /tmp/paem_health.json -w "%{http_code}" "$BASE/health")
check "GET /health" "200" "$HTTP"
cat /tmp/paem_health.json | python3 -m json.tool 2>/dev/null
echo ""

# Test 2: Pay Init
echo "--- Test 2: POST /paem/pay/init ---"
HTTP=$(curl -s -o /tmp/paem_payinit.json -w "%{http_code}" \
  -X POST "$BASE/paem/pay/init" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TX-CASE-001",
    "booking_id": "BKG-CASE-001",
    "deposit_amount_cop": 5000
  }')
check "POST /paem/pay/init" "200" "$HTTP"
cat /tmp/paem_payinit.json | python3 -m json.tool 2>/dev/null
echo ""

# Test 3: Webhook (sin firma — depende de config)
echo "--- Test 3: POST /webhooks/wompi ---"
TIMESTAMP=$(date +%s)
BODY='{"event":"transaction.updated","data":{"transaction":{"id":"test-smoke","reference":"TX-CASE-001","status":"APPROVED","amount_in_cents":500000}}}'
HTTP=$(curl -s -o /tmp/paem_webhook.json -w "%{http_code}" \
  -X POST "$BASE/webhooks/wompi" \
  -H "Content-Type: application/json" \
  -H "x-event-checksum: sandbox-test" \
  -H "x-event-timestamp: $TIMESTAMP" \
  -d "$BODY")
# Accept 200 or 403 (403 = firma inválida, que es correcto en producción)
if [ "$HTTP" = "200" ] || [ "$HTTP" = "403" ]; then
    echo "  [PASS] POST /webhooks/wompi (HTTP $HTTP — expected 200 or 403)"
    PASS=$((PASS + 1))
else
    echo "  [FAIL] POST /webhooks/wompi (expected 200|403, got $HTTP)"
    FAIL=$((FAIL + 1))
fi
cat /tmp/paem_webhook.json | python3 -m json.tool 2>/dev/null
echo ""

# Summary
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
