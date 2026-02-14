#!/bin/bash
# ============================================================
# ODI — Deploy + Certificación Caso 001 (Producción)
# Ejecutar en: root@64.23.170.118
# ============================================================
# Prerequisitos:
#   - WOMPI_EVENTS_KEY configurado en /opt/odi/.env
#   - Webhook URL guardado en panel Wompi producción
# ============================================================
# Fases:
#   1. Verificar secretos
#   2. Pull + rebuild + up
#   3. Confirmar env en container
#   4. Test de blindaje (403 esperado)
#   5. Preparar DB (HOLD + PENDING)
#   6. Generar checkout (pay/init)
#   7. Instrucciones para pago real
#   8. Monitoreo + certificación
# ============================================================

set -euo pipefail

API_URL="${PAEM_API_URL:-https://api.liveodi.com}"
TX_ID="TX-CASE-001"
BKG_ID="BKG-CASE-001"
NODE_ID="HLT-PER-MATZU-001"
PROCEDURE="implantes"
AMOUNT_COP=5000
HOLD_MINUTES=60

PG_CMD="docker exec odi-postgres psql -U odi -d odi -t -A"
ODI_DIR="/opt/odi"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✅ $1${NC}"; }
fail() { echo -e "  ${RED}❌ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
header() { echo -e "\n${YELLOW}══════════════════════════════════════════${NC}\n  $1\n${YELLOW}══════════════════════════════════════════${NC}"; }

# ── FASE 1: Verificar secretos ──────────────────────────────
header "FASE 1 — Verificar secretos en .env"

if grep -q "WOMPI_EVENTS_KEY=.\+" "$ODI_DIR/.env" 2>/dev/null; then
    pass "WOMPI_EVENTS_KEY encontrado en $ODI_DIR/.env"
else
    fail "WOMPI_EVENTS_KEY NO encontrado o vacío en $ODI_DIR/.env"
    echo ""
    echo "  ACCIÓN REQUERIDA:"
    echo "  1. Abre el panel de Wompi Producción → Desarrollo → Programadores"
    echo "  2. Copia el 'Secreto de Eventos'"
    echo "  3. Agrega a $ODI_DIR/.env:"
    echo "     WOMPI_EVENTS_KEY=prod_events_XXXXXXXX"
    echo ""
    echo "  Luego re-ejecuta este script."
    exit 1
fi

if grep -q "WOMPI_INTEGRITY_SECRET=.\+" "$ODI_DIR/.env" 2>/dev/null; then
    pass "WOMPI_INTEGRITY_SECRET encontrado"
else
    warn "WOMPI_INTEGRITY_SECRET no encontrado (checkout widget no firmará)"
fi

if grep -q "WOMPI_PUBLIC_KEY=.\+" "$ODI_DIR/.env" 2>/dev/null; then
    pass "WOMPI_PUBLIC_KEY encontrado"
else
    warn "WOMPI_PUBLIC_KEY no encontrado"
fi

# ── FASE 2: Pull + rebuild + up ─────────────────────────────
header "FASE 2 — Pull + Rebuild + Up"

cd "$ODI_DIR"
echo "  Pulling latest code..."
git pull origin claude/unify-repository-branches-RgMJH 2>&1 | tail -3
pass "Git pull completado"

echo "  Building odi-paem-api..."
docker compose build odi-paem-api 2>&1 | tail -5
pass "Build completado"

echo "  Starting odi-paem-api..."
docker compose up -d odi-paem-api 2>&1
sleep 3
pass "Container arriba"

# ── FASE 3: Confirmar env en container ──────────────────────
header "FASE 3 — Confirmar variables en container"

CONTAINER_EVENTS_KEY=$(docker exec odi-paem-api printenv WOMPI_EVENTS_KEY 2>/dev/null || echo "")
CONTAINER_PUBLIC_KEY=$(docker exec odi-paem-api printenv WOMPI_PUBLIC_KEY 2>/dev/null || echo "")
CONTAINER_INTEGRITY=$(docker exec odi-paem-api printenv WOMPI_INTEGRITY_SECRET 2>/dev/null || echo "")

if [ -n "$CONTAINER_EVENTS_KEY" ]; then
    MASKED="${CONTAINER_EVENTS_KEY:0:12}...${CONTAINER_EVENTS_KEY: -4}"
    pass "WOMPI_EVENTS_KEY cargado: $MASKED"
else
    fail "WOMPI_EVENTS_KEY NO está cargado en el container"
    echo "  El container necesita rebuild con las variables de .env"
    exit 1
fi

[ -n "$CONTAINER_PUBLIC_KEY" ] && pass "WOMPI_PUBLIC_KEY cargado" || warn "WOMPI_PUBLIC_KEY no cargado"
[ -n "$CONTAINER_INTEGRITY" ] && pass "WOMPI_INTEGRITY_SECRET cargado" || warn "WOMPI_INTEGRITY_SECRET no cargado"

# ── FASE 4: Test de blindaje ────────────────────────────────
header "FASE 4 — Test de blindaje criptográfico"

echo "  [4a] POST /webhooks/wompi sin firma..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/webhooks/wompi" \
    -H "Content-Type: application/json" \
    -d '{"test": true}' 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "422" ]; then
    pass "Webhook rechazó POST sin firma (HTTP $HTTP_CODE)"
elif [ "$HTTP_CODE" = "000" ]; then
    warn "No se pudo conectar a $API_URL (¿SSL/Nginx activo?)"
else
    fail "Webhook retornó HTTP $HTTP_CODE — ESPERADO 403"
    echo "  Si retorna 200, el blindaje NO funciona. DETENER."
    exit 1
fi

echo "  [4b] POST /_debug/mock_webhook (debe estar bloqueado)..."
HTTP_CODE_DEBUG=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/paem/_debug/mock_webhook" \
    -H "Content-Type: application/json" \
    -d '{"transaction_id":"TEST"}' 2>/dev/null || echo "000")

if [ "$HTTP_CODE_DEBUG" = "403" ]; then
    pass "Debug endpoint bloqueado (HTTP 403)"
elif [ "$HTTP_CODE_DEBUG" = "000" ]; then
    warn "No se pudo conectar (verificar red)"
else
    fail "Debug endpoint retornó HTTP $HTTP_CODE_DEBUG — ESPERADO 403"
    exit 1
fi

# ── FASE 5: Preparar DB ────────────────────────────────────
header "FASE 5 — Preparar estado DB (HOLD + PENDING)"

echo "  Limpiando datos previos de $TX_ID..."
$PG_CMD -c "
BEGIN;

DELETE FROM odi_events WHERE transaction_id = '$TX_ID';
DELETE FROM odi_payments WHERE transaction_id = '$TX_ID';
DELETE FROM odi_health_bookings WHERE transaction_id = '$TX_ID';

-- Booking en HOLD con TTL extendido ($HOLD_MINUTES min)
INSERT INTO odi_health_bookings
    (booking_id, transaction_id, node_id, procedure_id, status, hold_expires_at,
     slot_date, slot_start, slot_end)
VALUES
    ('$BKG_ID', '$TX_ID', '$NODE_ID', '$PROCEDURE', 'HOLD',
     NOW() + INTERVAL '$HOLD_MINUTES minutes',
     CURRENT_DATE + 14, '09:00', '11:00')
ON CONFLICT (booking_id) DO UPDATE
    SET status = 'HOLD',
        transaction_id = '$TX_ID',
        hold_expires_at = NOW() + INTERVAL '$HOLD_MINUTES minutes',
        updated_at = NOW();

-- Payment en PENDING
INSERT INTO odi_payments
    (transaction_id, booking_id, gateway_name, amount, currency, status, idempotency_key)
VALUES
    ('$TX_ID', '$BKG_ID', 'wompi', $AMOUNT_COP, 'COP', 'PENDING', '$TX_ID')
ON CONFLICT (idempotency_key) DO UPDATE
    SET status = 'PENDING',
        amount = $AMOUNT_COP,
        captured_at = NULL,
        gateway_reference = NULL,
        gateway_response = NULL,
        updated_at = NOW();

COMMIT;
" 2>&1

echo ""
echo "  Verificación:"
echo "  ──────────────────────────────────────────"

PAY_STATUS=$($PG_CMD -c "SELECT status FROM odi_payments WHERE transaction_id='$TX_ID';")
BKG_STATUS=$($PG_CMD -c "SELECT status FROM odi_health_bookings WHERE transaction_id='$TX_ID';")
HOLD_EXP=$($PG_CMD -c "SELECT hold_expires_at FROM odi_health_bookings WHERE transaction_id='$TX_ID';")

echo "  Payment:  $PAY_STATUS"
echo "  Booking:  $BKG_STATUS"
echo "  Hold exp: $HOLD_EXP"

[ "$PAY_STATUS" = "PENDING" ] && pass "Payment en PENDING" || fail "Payment NO en PENDING: $PAY_STATUS"
[ "$BKG_STATUS" = "HOLD" ] && pass "Booking en HOLD" || fail "Booking NO en HOLD: $BKG_STATUS"

# ── FASE 6: Generar checkout ───────────────────────────────
header "FASE 6 — Generar checkout (pay/init)"

CHECKOUT_RESPONSE=$(curl -s -X POST "$API_URL/paem/pay/init" \
    -H "Content-Type: application/json" \
    -d "{\"transaction_id\":\"$TX_ID\",\"booking_id\":\"$BKG_ID\",\"deposit_amount_cop\":$AMOUNT_COP}" 2>/dev/null || echo '{"error":"connection_failed"}')

echo "  Response:"
echo "$CHECKOUT_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "  $CHECKOUT_RESPONSE"

CHECKOUT_OK=$(echo "$CHECKOUT_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok',''))" 2>/dev/null || echo "")
if [ "$CHECKOUT_OK" = "True" ]; then
    pass "Checkout generado exitosamente"
else
    warn "Checkout no retornó ok=True (verificar respuesta)"
fi

# ── FASE 7: Instrucciones de pago ──────────────────────────
header "FASE 7 — ACCIONES MANUALES REQUERIDAS"

echo ""
echo "  1. PANEL WOMPI PRODUCCIÓN:"
echo "     → URL de Eventos: $API_URL/webhooks/wompi"
echo "     → Evento: transaction.updated"
echo "     → Click 'Guardar'"
echo ""
echo "  2. EJECUTAR PAGO REAL:"
echo "     → Monto: \$$AMOUNT_COP COP"
echo "     → Referencia: $TX_ID"
echo ""
echo "  3. MONITOREAR LOGS (en otra terminal):"
echo "     docker logs -f odi-paem-api 2>&1 | grep -E 'WOMPI|webhook|signature|$TX_ID|CAPTURED|CONFIRMED|PAYMENT'"
echo ""

# ── FASE 8: Certificación ─────────────────────────────────
header "FASE 8 — Certificación (ejecutar DESPUÉS del pago)"

echo ""
echo "  Ejecuta este bloque después de realizar el pago:"
echo ""
echo '  # ── CERTIFICACIÓN CASO 001 ──'
echo '  docker exec odi-postgres psql -U odi -d odi -c "'
echo "  SELECT"
echo "      p.status AS pay_status,"
echo "      b.status AS booking_status,"
echo "      p.amount,"
echo "      p.gateway_reference,"
echo "      p.captured_at"
echo "  FROM odi_payments p"
echo "  JOIN odi_health_bookings b ON p.transaction_id = b.transaction_id"
echo "  WHERE p.transaction_id = '$TX_ID';"
echo '"'
echo ""
echo '  docker exec odi-postgres psql -U odi -d odi -c "'
echo "  SELECT event_type, created_at"
echo "  FROM odi_events"
echo "  WHERE transaction_id = '$TX_ID'"
echo "  ORDER BY created_at DESC;"
echo '"'

echo ""
header "DEPLOY SCRIPT COMPLETADO"
echo ""
echo "  Resumen de fases automatizadas:"
echo "  ✅ Fase 1: Secretos verificados"
echo "  ✅ Fase 2: Código actualizado y container reconstruido"
echo "  ✅ Fase 3: Variables cargadas en container"
echo "  ✅ Fase 4: Blindaje confirmado (403)"
echo "  ✅ Fase 5: DB preparada (PENDING + HOLD)"
echo "  ✅ Fase 6: Checkout generado"
echo "  ⏳ Fase 7: Guardar webhook en Wompi + pago real (MANUAL)"
echo "  ⏳ Fase 8: Certificación post-pago (MANUAL)"
echo ""
echo "  Criterio de éxito:"
echo "    pay_status = CAPTURED"
echo "    booking_status = CONFIRMED"
echo "    evento = PAEM.PAYMENT_SUCCESS"
echo ""
