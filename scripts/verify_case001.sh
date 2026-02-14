#!/bin/bash
# ============================================================
# ODI — Smoke Test Caso 001 (TX-CASE-001)
# Ejecutar en: root@64.23.170.118
# ============================================================
# Flujo:
#   a) Inicializar TX-CASE-001 en DB (HOLD/PENDING)
#   b) Disparar mock webhook (simula pago aprobado)
#   c) SELECTs de verificación cruzada
# ============================================================

set -euo pipefail

API_URL="${PAEM_API_URL:-https://api.liveodi.com}"
TX_ID="TX-CASE-001"
BKG_ID="BKG-CASE-001"
NODE_ID="matzu_001"
PROCEDURE="carillas_porcelana"
AMOUNT_COP=5000

PG_CMD="docker exec odi-postgres psql -U odi -d odi -t -A"

echo "=========================================="
echo "  ODI — SMOKE TEST CASO 001"
echo "  TX: $TX_ID | BKG: $BKG_ID"
echo "=========================================="

# --- PASO a: Inicializar datos de prueba en DB ---
echo ""
echo "[a] Inicializando TX-CASE-001 en base de datos..."

$PG_CMD -c "
BEGIN;

-- Limpiar datos previos del caso de prueba
DELETE FROM odi_events WHERE transaction_id = '$TX_ID';
DELETE FROM odi_payments WHERE transaction_id = '$TX_ID';
DELETE FROM odi_health_bookings WHERE transaction_id = '$TX_ID';

-- Crear booking en HOLD (TTL 15 min)
INSERT INTO odi_health_bookings
    (booking_id, transaction_id, node_id, procedure_id, status, hold_expires_at, slot_date, slot_start, slot_end)
VALUES
    ('$BKG_ID', '$TX_ID', '$NODE_ID', '$PROCEDURE', 'HOLD', NOW() + INTERVAL '15 minutes', CURRENT_DATE + 14, '09:00', '11:00')
ON CONFLICT (booking_id) DO UPDATE
    SET status = 'HOLD', hold_expires_at = NOW() + INTERVAL '15 minutes', updated_at = NOW();

-- Registrar evento de HOLD
INSERT INTO odi_events (event_type, transaction_id, booking_id, payload)
VALUES ('PAEM.HOLD_CREATED', '$TX_ID', '$BKG_ID', '{\"source\": \"smoke_test\"}');

COMMIT;
"

echo "  ✅ Booking en HOLD, listo para pago"

# --- PASO b-1: Iniciar flujo de pago ---
echo ""
echo "[b-1] Iniciando pago via POST /paem/pay/init..."

PAY_RESPONSE=$(curl -s -X POST "$API_URL/paem/pay/init" \
    -H "Content-Type: application/json" \
    -d "{\"transaction_id\":\"$TX_ID\",\"booking_id\":\"$BKG_ID\",\"deposit_amount_cop\":$AMOUNT_COP}")

echo "  Response:"
echo "  $PAY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "  $PAY_RESPONSE"

# --- PASO b-2: Disparar mock webhook (simula pago aprobado) ---
echo ""
echo "[b-2] Disparando mock webhook (simula Wompi APPROVED)..."

WEBHOOK_RESPONSE=$(curl -s -X POST "$API_URL/paem/_debug/mock_webhook" \
    -H "Content-Type: application/json" \
    -d "{\"transaction_id\":\"$TX_ID\"}")

echo "  Response:"
echo "  $WEBHOOK_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "  $WEBHOOK_RESPONSE"

# --- PASO c: SELECTs de verificación ---
echo ""
echo "=========================================="
echo "  VERIFICACIÓN CRUZADA"
echo "=========================================="

echo ""
echo "[c-1] Estado cruzado payments ↔ bookings:"
$PG_CMD -c "
SELECT
    p.status AS pay_status,
    b.status AS booking_status,
    p.amount,
    p.gateway_reference,
    p.captured_at,
    p.updated_at
FROM odi_payments p
JOIN odi_health_bookings b
    ON p.transaction_id = b.transaction_id
WHERE p.transaction_id = '$TX_ID';
"

echo ""
echo "[c-2] Eventos registrados:"
$PG_CMD -c "
SELECT
    event_type,
    created_at,
    payload::text
FROM odi_events
WHERE transaction_id = '$TX_ID'
ORDER BY created_at ASC;
"

echo ""
echo "[c-3] Validación de estados esperados:"
RESULT=$($PG_CMD -c "
SELECT
    CASE WHEN p.status = 'CAPTURED' AND b.status = 'CONFIRMED' THEN 'PASS' ELSE 'FAIL' END AS verdict
FROM odi_payments p
JOIN odi_health_bookings b ON p.transaction_id = b.transaction_id
WHERE p.transaction_id = '$TX_ID';
")

if [ "$RESULT" = "PASS" ]; then
    echo "  ✅ CASO 001 VERIFICADO: CAPTURED + CONFIRMED"
else
    echo "  ❌ CASO 001 FALLIDO: Estado inesperado ($RESULT)"
    echo "  Revisa los logs: docker logs --tail 50 odi-paem-api"
fi

echo ""
echo "=========================================="
echo "  SMOKE TEST COMPLETADO"
echo "=========================================="
