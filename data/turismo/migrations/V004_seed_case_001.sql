-- ═══════════════════════════════════════════════════════════════════════════════
-- ODI CASO 001 — Seed de prueba para validación económica real
-- ═══════════════════════════════════════════════════════════════════════════════
-- Ejecutar: psql -h localhost -p 5432 -U odi -d odi -f V004_seed_case_001.sql
-- Prerequisito: V003_payments_bookings.sql
-- ═══════════════════════════════════════════════════════════════════════════════

BEGIN;

-- Limpiar datos previos del caso 001
DELETE FROM odi_events WHERE transaction_id = 'TX-CASE-001';
DELETE FROM odi_payments WHERE transaction_id = 'TX-CASE-001';
DELETE FROM odi_health_bookings WHERE transaction_id = 'TX-CASE-001';

-- Booking en HOLD (60 minutos de gracia para prueba)
INSERT INTO odi_health_bookings (
    booking_id, transaction_id, node_id, procedure_id,
    status, hold_expires_at
) VALUES (
    'BKG-CASE-001', 'TX-CASE-001',
    'HLT-PEI-MATZU-001', 'implantes',
    'HOLD', NOW() + interval '60 minutes'
);

-- Payment en PENDING
INSERT INTO odi_payments (
    transaction_id, booking_id, gateway_name,
    amount, currency, status, idempotency_key
) VALUES (
    'TX-CASE-001', 'BKG-CASE-001', 'wompi',
    5000.00, 'COP', 'PENDING', 'TX-CASE-001'
);

COMMIT;

-- Verificar
SELECT 'BOOKING' AS entity, booking_id, status, hold_expires_at::TEXT
  FROM odi_health_bookings WHERE transaction_id = 'TX-CASE-001'
UNION ALL
SELECT 'PAYMENT', idempotency_key, status, created_at::TEXT
  FROM odi_payments WHERE transaction_id = 'TX-CASE-001';
