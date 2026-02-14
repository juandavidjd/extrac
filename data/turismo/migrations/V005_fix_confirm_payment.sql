-- ═══════════════════════════════════════════════════════════════════════════════
-- V005 — Fix fn_odi_confirm_payment (GET DIAGNOSTICS bug)
-- ═══════════════════════════════════════════════════════════════════════════════
-- Fecha: 2026-02-14
-- Fix: v_booking.status no puede usarse en GET DIAGNOSTICS antes de asignarse
--      Cambio a variable INT separada (v_rows)
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION public.fn_odi_confirm_payment(
    p_transaction_id text,
    p_gateway_reference text DEFAULT NULL,
    p_gateway_response jsonb DEFAULT '{}'::jsonb
)
RETURNS TABLE(ok boolean, error text, payment_status text, booking_status text)
LANGUAGE plpgsql
AS $$
DECLARE
    v_payment RECORD;
    v_booking RECORD;
    v_rows INT;
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

    GET DIAGNOSTICS v_rows = ROW_COUNT;

    -- 3. Registrar evento
    INSERT INTO odi_events (event_type, transaction_id, booking_id, payload)
    VALUES ('PAEM.PAYMENT_SUCCESS', p_transaction_id, v_payment.booking_id,
            jsonb_build_object(
                'gateway_reference', COALESCE(p_gateway_reference, ''),
                'confirmed_at', NOW()::TEXT,
                'bookings_updated', v_rows
            ));

    -- 4. Obtener estado final del booking
    SELECT b.status INTO v_booking
      FROM odi_health_bookings b
     WHERE b.transaction_id = p_transaction_id
     LIMIT 1;

    RETURN QUERY SELECT TRUE, NULL::TEXT, 'CAPTURED'::TEXT,
                 COALESCE(v_booking.status, 'NO_BOOKING')::TEXT;
END;
$$;

-- Verificar que la función existe
SELECT proname, proargtypes::regtype[] 
  FROM pg_proc 
 WHERE proname = 'fn_odi_confirm_payment';
