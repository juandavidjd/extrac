-- ═══════════════════════════════════════════════════════════════════════════════
-- ODI PAEM v2.2.1 — Metabolismo Económico: Bookings + Payments + Events
-- ═══════════════════════════════════════════════════════════════════════════════
-- Ejecutar: psql -h localhost -p 5432 -U odi -d odi -f V003_payments_bookings.sql
-- Prerequisito: V001_health_census.sql (set_updated_at(), odi_health_nodes)
-- Paradigma: Industria 5.0 — Postgres manda, Redis acelera.
-- Fecha: 13 Feb 2026
-- ═══════════════════════════════════════════════════════════════════════════════

BEGIN;

-- =========================
-- 1) Bookings clínicos (ciclo de vida: HOLD → CONFIRMED | EXPIRED | CANCELLED)
-- =========================
CREATE TABLE IF NOT EXISTS odi_health_bookings (
    booking_id TEXT PRIMARY KEY,                       -- "BKG-{uuid8}"
    transaction_id TEXT NOT NULL,
    node_id TEXT NOT NULL REFERENCES odi_health_nodes(node_id),
    procedure_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'HOLD'
        CHECK (status IN ('HOLD', 'CONFIRMED', 'EXPIRED', 'CANCELLED')),
    hold_expires_at TIMESTAMP,                         -- NULL cuando no está en HOLD
    slot_date DATE,
    slot_start TIME,
    slot_end TIME,
    lead_id TEXT,
    assignment_id TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_odi_bookings_updated_at ON odi_health_bookings;
CREATE TRIGGER trg_odi_bookings_updated_at
    BEFORE UPDATE ON odi_health_bookings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_bookings_txn
    ON odi_health_bookings(transaction_id);
CREATE INDEX IF NOT EXISTS idx_bookings_node_status
    ON odi_health_bookings(node_id, status);
CREATE INDEX IF NOT EXISTS idx_bookings_hold_expires
    ON odi_health_bookings(status, hold_expires_at)
    WHERE status = 'HOLD';


-- =========================
-- 2) Pagos (gateway-agnostic, primer gateway: Wompi)
-- =========================
CREATE TABLE IF NOT EXISTS odi_payments (
    id BIGSERIAL PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    booking_id TEXT REFERENCES odi_health_bookings(booking_id),
    gateway_name TEXT NOT NULL DEFAULT 'wompi',        -- wompi | stripe | manual
    amount NUMERIC NOT NULL CHECK (amount > 0),
    currency TEXT NOT NULL DEFAULT 'COP',
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'CAPTURED', 'FAILED', 'REFUNDED')),
    idempotency_key TEXT NOT NULL,
    gateway_reference TEXT,                            -- referencia del gateway (Wompi tx ID)
    gateway_response JSONB,                            -- payload completo del gateway
    captured_at TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT ux_payments_idempotency UNIQUE (idempotency_key)
);

DROP TRIGGER IF EXISTS trg_odi_payments_updated_at ON odi_payments;
CREATE TRIGGER trg_odi_payments_updated_at
    BEFORE UPDATE ON odi_payments
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_payments_txn
    ON odi_payments(transaction_id);
CREATE INDEX IF NOT EXISTS idx_payments_status
    ON odi_payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_booking
    ON odi_payments(booking_id);


-- =========================
-- 3) Event sourcing (auditoría atómica)
-- =========================
CREATE TABLE IF NOT EXISTS odi_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,                          -- PAEM.PAYMENT_SUCCESS, PAEM.HOLD_CREATED, etc.
    transaction_id TEXT,
    assignment_id TEXT,
    booking_id TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_type_created
    ON odi_events(event_type, created_at);
CREATE INDEX IF NOT EXISTS idx_events_txn
    ON odi_events(transaction_id);


-- =========================
-- 4) Función: confirmar booking atómicamente (HOLD → CONFIRMED)
-- =========================
CREATE OR REPLACE FUNCTION fn_odi_confirm_booking(p_booking_id TEXT)
RETURNS TABLE (
    ok BOOLEAN,
    error TEXT,
    out_booking_id TEXT,
    out_status TEXT
) AS $$
DECLARE
    v_booking RECORD;
BEGIN
    -- Bloquear fila para evitar race conditions
    SELECT b.booking_id, b.status, b.hold_expires_at, b.transaction_id
      INTO v_booking
      FROM odi_health_bookings b
     WHERE b.booking_id = p_booking_id
       FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'BOOKING_NOT_FOUND'::TEXT, p_booking_id, 'UNKNOWN'::TEXT;
        RETURN;
    END IF;

    -- Ya confirmado → idempotencia
    IF v_booking.status = 'CONFIRMED' THEN
        RETURN QUERY SELECT TRUE, NULL::TEXT, p_booking_id, 'CONFIRMED'::TEXT;
        RETURN;
    END IF;

    -- Solo se puede confirmar un HOLD
    IF v_booking.status != 'HOLD' THEN
        RETURN QUERY SELECT FALSE, 'INVALID_STATUS'::TEXT, p_booking_id, v_booking.status;
        RETURN;
    END IF;

    -- Verificar expiración del HOLD
    IF v_booking.hold_expires_at IS NOT NULL AND v_booking.hold_expires_at < NOW() THEN
        UPDATE odi_health_bookings
           SET status = 'EXPIRED'
         WHERE booking_id = p_booking_id;

        INSERT INTO odi_events (event_type, transaction_id, booking_id, payload)
        VALUES ('PAEM.HOLD_EXPIRED', v_booking.transaction_id, p_booking_id,
                jsonb_build_object('expired_at', NOW()::TEXT));

        RETURN QUERY SELECT FALSE, 'HOLD_EXPIRED'::TEXT, p_booking_id, 'EXPIRED'::TEXT;
        RETURN;
    END IF;

    -- Transición: HOLD → CONFIRMED
    UPDATE odi_health_bookings
       SET status = 'CONFIRMED', hold_expires_at = NULL
     WHERE booking_id = p_booking_id;

    INSERT INTO odi_events (event_type, transaction_id, booking_id, payload)
    VALUES ('PAEM.BOOKING_CONFIRMED', v_booking.transaction_id, p_booking_id,
            jsonb_build_object('confirmed_at', NOW()::TEXT));

    RETURN QUERY SELECT TRUE, NULL::TEXT, p_booking_id, 'CONFIRMED'::TEXT;
END;
$$ LANGUAGE plpgsql;


-- =========================
-- 5) Función: confirmar pago + booking atómicamente (para webhook)
-- =========================
CREATE OR REPLACE FUNCTION fn_odi_confirm_payment(
    p_transaction_id TEXT,
    p_gateway_reference TEXT DEFAULT NULL,
    p_gateway_response JSONB DEFAULT '{}'::jsonb
)
RETURNS TABLE (
    ok BOOLEAN,
    error TEXT,
    payment_status TEXT,
    booking_status TEXT
) AS $$
DECLARE
    v_payment RECORD;
    v_booking RECORD;
BEGIN
    -- Buscar payment por transaction_id
    SELECT p.id, p.status, p.booking_id
      INTO v_payment
      FROM odi_payments p
     WHERE p.transaction_id = p_transaction_id
       FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'PAYMENT_NOT_FOUND'::TEXT, 'UNKNOWN'::TEXT, 'UNKNOWN'::TEXT;
        RETURN;
    END IF;

    -- Idempotencia: ya capturado
    IF v_payment.status = 'CAPTURED' THEN
        SELECT b.status INTO v_booking
          FROM odi_health_bookings b
         WHERE b.transaction_id = p_transaction_id;
        RETURN QUERY SELECT TRUE, NULL::TEXT, 'CAPTURED'::TEXT,
                     COALESCE(v_booking.status, 'UNKNOWN')::TEXT;
        RETURN;
    END IF;

    IF v_payment.status != 'PENDING' THEN
        RETURN QUERY SELECT FALSE, 'INVALID_PAYMENT_STATUS'::TEXT, v_payment.status, 'UNKNOWN'::TEXT;
        RETURN;
    END IF;

    -- 1. Actualizar payment: PENDING → CAPTURED
    UPDATE odi_payments
       SET status = 'CAPTURED',
           captured_at = NOW(),
           gateway_reference = COALESCE(p_gateway_reference, gateway_reference),
           gateway_response = p_gateway_response
     WHERE id = v_payment.id;

    -- 2. Confirmar booking: HOLD → CONFIRMED
    UPDATE odi_health_bookings
       SET status = 'CONFIRMED', hold_expires_at = NULL
     WHERE transaction_id = p_transaction_id
       AND status = 'HOLD';

    GET DIAGNOSTICS v_booking.status = ROW_COUNT;

    -- 3. Registrar evento
    INSERT INTO odi_events (event_type, transaction_id, booking_id, payload)
    VALUES ('PAEM.PAYMENT_SUCCESS', p_transaction_id, v_payment.booking_id,
            jsonb_build_object(
                'gateway_reference', COALESCE(p_gateway_reference, ''),
                'confirmed_at', NOW()::TEXT
            ));

    SELECT b.status INTO v_booking
      FROM odi_health_bookings b
     WHERE b.transaction_id = p_transaction_id
     LIMIT 1;

    RETURN QUERY SELECT TRUE, NULL::TEXT, 'CAPTURED'::TEXT,
                 COALESCE(v_booking.status, 'NO_BOOKING')::TEXT;
END;
$$ LANGUAGE plpgsql;


COMMIT;

-- ═══════════════════════════════════════════════════════════════════════════════
-- V003 complete. Siguiente: V004_seed_case_001.sql para datos de prueba.
-- ═══════════════════════════════════════════════════════════════════════════════
