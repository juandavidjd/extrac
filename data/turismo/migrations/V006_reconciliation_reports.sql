-- ═══════════════════════════════════════════════════════════════════════════════
-- ODI V006 — Financial Reconciliation Engine
-- ═══════════════════════════════════════════════════════════════════════════════
-- Ejecutar: psql -h localhost -p 5432 -U odi -d odi -f V006_reconciliation_reports.sql
-- Prerequisito: V003_payments_bookings.sql (odi_payments, odi_health_bookings, odi_events)
-- Paradigma: Industria 5.0 — Auditoría soberana, trazabilidad inmutable.
-- Fecha: 14 Feb 2026
-- ═══════════════════════════════════════════════════════════════════════════════

BEGIN;

-- =========================
-- 1) Ampliar constraint de odi_payments para permitir EXPIRED
--    (zombie cleanup cierra PENDING → EXPIRED cuando el HOLD expiró)
-- =========================
ALTER TABLE odi_payments
    DROP CONSTRAINT IF EXISTS odi_payments_status_check;

ALTER TABLE odi_payments
    ADD CONSTRAINT odi_payments_status_check
    CHECK (status IN ('PENDING', 'CAPTURED', 'FAILED', 'REFUNDED', 'EXPIRED'));

-- =========================
-- 2) Tabla de reportes de reconciliación
-- =========================
CREATE TABLE IF NOT EXISTS odi_reconciliation_reports (
    report_id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    period      DATE        NOT NULL DEFAULT CURRENT_DATE,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
    summary     JSONB       NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recon_reports_period
    ON odi_reconciliation_reports(period);

COMMIT;
