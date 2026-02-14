-- ═══════════════════════════════════════════════════════════════════════════════
-- ODI Health Census v1 — Migración SQL para Postgres (odi-postgres:5432)
-- ═══════════════════════════════════════════════════════════════════════════════
-- Ejecutar: psql -h localhost -p 5432 -U odi -d odi -f V001_health_census.sql
-- Paradigma: Industria 5.0 — Postgres manda, Redis acelera.
-- Fecha: 13 Feb 2026
-- ═══════════════════════════════════════════════════════════════════════════════

BEGIN;

-- =========================
-- 0) Helpers
-- =========================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- =========================
-- 1) Nodos clínicos (Single Source of Truth)
-- =========================
CREATE TABLE IF NOT EXISTS odi_health_nodes (
    node_id TEXT PRIMARY KEY,                       -- Ej: "HLT-PEI-MATZU-001"
    clinic_name TEXT NOT NULL,
    doctor_name TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'CO',
    geo_lat NUMERIC,
    geo_lng NUMERIC,

    -- Capacidad base (declarativa)
    weekly_capacity INTEGER NOT NULL CHECK (weekly_capacity >= 0),
    weekly_booked   INTEGER NOT NULL DEFAULT 0 CHECK (weekly_booked >= 0),
    saturation_ratio NUMERIC NOT NULL DEFAULT 0.0 CHECK (saturation_ratio >= 0.0),
    redirect_threshold NUMERIC NOT NULL DEFAULT 0.85
        CHECK (redirect_threshold >= 0.0 AND redirect_threshold <= 1.0),

    -- SLA
    sla_response_minutes INTEGER NOT NULL DEFAULT 30 CHECK (sla_response_minutes >= 0),
    sla_followup_minutes INTEGER NOT NULL DEFAULT 60 CHECK (sla_followup_minutes >= 0),

    -- Estado / Gobernanza
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_certified BOOLEAN NOT NULL DEFAULT FALSE,
    certification_level TEXT CHECK (certification_level IN ('basic', 'advanced', 'master')),

    -- Turismo / Idiomas
    tourism_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    accepts_international BOOLEAN NOT NULL DEFAULT TRUE,
    language_support TEXT[] NOT NULL DEFAULT ARRAY['es']::TEXT[],

    -- Economía
    base_procedure_cost JSONB NOT NULL DEFAULT '{}'::jsonb,
    margin_factor NUMERIC NOT NULL DEFAULT 1.0 CHECK (margin_factor > 0.0),

    -- Auditoría
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Consistencia
    CONSTRAINT ck_booked_lte_capacity
        CHECK (weekly_booked <= weekly_capacity OR weekly_capacity = 0)
);

DROP TRIGGER IF EXISTS trg_odi_health_nodes_updated_at ON odi_health_nodes;
CREATE TRIGGER trg_odi_health_nodes_updated_at
    BEFORE UPDATE ON odi_health_nodes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_health_nodes_city_active
    ON odi_health_nodes(city, is_active);
CREATE INDEX IF NOT EXISTS idx_health_nodes_certified
    ON odi_health_nodes(is_certified, certification_level);
CREATE INDEX IF NOT EXISTS idx_health_nodes_tourism
    ON odi_health_nodes(tourism_enabled, accepts_international);


-- =========================
-- 2) Certificaciones por procedimiento (Educación ↔ Salud)
-- =========================
CREATE TABLE IF NOT EXISTS odi_health_certifications (
    id BIGSERIAL PRIMARY KEY,
    node_id TEXT NOT NULL REFERENCES odi_health_nodes(node_id) ON DELETE CASCADE,
    procedure_id TEXT NOT NULL,
    procedure_name TEXT NOT NULL DEFAULT '',
    university_partner TEXT NOT NULL,
    certification_date DATE NOT NULL,
    valid_until DATE,
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_cert_valid_until
        CHECK (valid_until IS NULL OR valid_until >= certification_date)
);

DROP TRIGGER IF EXISTS trg_odi_health_cert_updated_at ON odi_health_certifications;
CREATE TRIGGER trg_odi_health_cert_updated_at
    BEFORE UPDATE ON odi_health_certifications
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_cert_node_proc_valid
    ON odi_health_certifications(node_id, procedure_id, is_valid);
CREATE INDEX IF NOT EXISTS idx_cert_valid_until
    ON odi_health_certifications(valid_until);

-- Una certificación válida por (node_id, procedure_id); histórico permitido
CREATE UNIQUE INDEX IF NOT EXISTS ux_cert_unique_valid
    ON odi_health_certifications(node_id, procedure_id) WHERE is_valid = TRUE;


-- =========================
-- 3) Log de capacidad semanal (auditable)
-- =========================
CREATE TABLE IF NOT EXISTS odi_health_capacity_log (
    id BIGSERIAL PRIMARY KEY,
    node_id TEXT NOT NULL REFERENCES odi_health_nodes(node_id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity >= 0),
    booked   INTEGER NOT NULL CHECK (booked >= 0),
    source TEXT NOT NULL DEFAULT 'manual',           -- manual | sync | api
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_log_booked_lte_capacity
        CHECK (booked <= capacity OR capacity = 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_capacity_node_week
    ON odi_health_capacity_log(node_id, week_start);
CREATE INDEX IF NOT EXISTS idx_capacity_week
    ON odi_health_capacity_log(week_start);


-- =========================
-- 4) Partners de entretenimiento (Turismo ↔ Recuperación)
-- =========================
CREATE TABLE IF NOT EXISTS odi_entertainment_partners (
    partner_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'cultural',        -- gastronomia, cultural, wellness, naturaleza
    impact_level TEXT NOT NULL CHECK (impact_level IN ('low', 'medium', 'high')),
    suitable_recovery_levels TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    estimated_price_usd NUMERIC NOT NULL DEFAULT 0.0,
    estimated_duration_hours NUMERIC NOT NULL DEFAULT 2.0,
    commission_rate NUMERIC NOT NULL DEFAULT 0.0 CHECK (commission_rate >= 0.0),
    description TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_odi_ent_updated_at ON odi_entertainment_partners;
CREATE TRIGGER trg_odi_ent_updated_at
    BEFORE UPDATE ON odi_entertainment_partners
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_ent_city_active
    ON odi_entertainment_partners(city, is_active);
CREATE INDEX IF NOT EXISTS idx_ent_impact
    ON odi_entertainment_partners(impact_level);


-- =========================
-- 5) Pesos de certificación (para scoring)
-- =========================
CREATE TABLE IF NOT EXISTS odi_certification_weights (
    certification_level TEXT PRIMARY KEY
        CHECK (certification_level IN ('basic', 'advanced', 'master')),
    weight NUMERIC NOT NULL CHECK (weight >= 0.0)
);

INSERT INTO odi_certification_weights(certification_level, weight) VALUES
 ('basic', 0.33),
 ('advanced', 0.66),
 ('master', 1.00)
ON CONFLICT (certification_level) DO UPDATE SET weight = EXCLUDED.weight;


-- =========================
-- 6) Hospitality partners (hospedaje)
-- =========================
CREATE TABLE IF NOT EXISTS odi_hospitality_partners (
    partner_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    partner_type TEXT NOT NULL DEFAULT 'hotel',       -- hotel, airbnb, hostal, clinica_hotel
    location_description TEXT NOT NULL DEFAULT '',
    distance_to_default_clinic_km NUMERIC,
    price_per_night_usd NUMERIC NOT NULL DEFAULT 0.0,
    recovery_friendly BOOLEAN NOT NULL DEFAULT TRUE,
    amenities TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    agreement_status TEXT NOT NULL DEFAULT 'pending', -- pending, active, expired
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_odi_hosp_updated_at ON odi_hospitality_partners;
CREATE TRIGGER trg_odi_hosp_updated_at
    BEFORE UPDATE ON odi_hospitality_partners
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =========================
-- 7) Vista: estado de carga calculado (para Grafana / admin / QA)
-- =========================
CREATE OR REPLACE VIEW v_odi_health_node_load AS
SELECT
  n.node_id,
  n.clinic_name,
  n.doctor_name,
  n.city,
  n.is_active,
  n.is_certified,
  n.certification_level,
  n.weekly_capacity,
  n.weekly_booked,
  CASE
    WHEN n.weekly_capacity = 0 THEN 1.0
    ELSE ROUND((n.weekly_booked::NUMERIC / NULLIF(n.weekly_capacity, 0)), 4)
  END AS saturation,
  n.redirect_threshold,
  CASE
    WHEN n.weekly_capacity = 0 THEN 'SATURATED'
    WHEN (n.weekly_booked::NUMERIC / NULLIF(n.weekly_capacity, 0)) >= n.redirect_threshold
        THEN 'SATURATED'
    WHEN (n.weekly_booked::NUMERIC / NULLIF(n.weekly_capacity, 0)) >= 0.70
        THEN 'HIGH_LOAD'
    ELSE 'AVAILABLE'
  END AS load_status,
  n.tourism_enabled,
  n.accepts_international,
  n.language_support,
  n.margin_factor,
  n.sla_response_minutes,
  n.updated_at
FROM odi_health_nodes n;


-- =========================
-- 8) Función: obtener candidatos failover (core router query)
-- =========================
CREATE OR REPLACE FUNCTION fn_odi_failover_candidates(
    p_city TEXT,
    p_procedure_id TEXT,
    p_accepts_international BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    node_id TEXT,
    clinic_name TEXT,
    doctor_name TEXT,
    city TEXT,
    saturation NUMERIC,
    load_status TEXT,
    certification_level TEXT,
    certification_weight NUMERIC,
    sla_response_minutes INTEGER,
    margin_factor NUMERIC
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    n.node_id,
    n.clinic_name,
    n.doctor_name,
    n.city,
    CASE
      WHEN n.weekly_capacity = 0 THEN 1.0
      ELSE (n.weekly_booked::NUMERIC / NULLIF(n.weekly_capacity, 0))
    END AS saturation,
    CASE
      WHEN n.weekly_capacity = 0 THEN 'SATURATED'
      WHEN (n.weekly_booked::NUMERIC / NULLIF(n.weekly_capacity, 0)) >= n.redirect_threshold
          THEN 'SATURATED'
      WHEN (n.weekly_booked::NUMERIC / NULLIF(n.weekly_capacity, 0)) >= 0.70
          THEN 'HIGH_LOAD'
      ELSE 'AVAILABLE'
    END AS load_status,
    n.certification_level,
    COALESCE(w.weight, 0.0) AS certification_weight,
    n.sla_response_minutes,
    n.margin_factor
  FROM odi_health_nodes n
  JOIN odi_health_certifications c
    ON c.node_id = n.node_id
   AND c.procedure_id = p_procedure_id
   AND c.is_valid = TRUE
  LEFT JOIN odi_certification_weights w
    ON w.certification_level = n.certification_level
  WHERE n.is_active = TRUE
    AND n.is_certified = TRUE
    AND n.tourism_enabled = TRUE
    AND (p_accepts_international = FALSE OR n.accepts_international = TRUE)
  ORDER BY
    saturation ASC,
    certification_weight DESC,
    n.sla_response_minutes ASC;
END;
$$ LANGUAGE plpgsql;


COMMIT;

-- ═══════════════════════════════════════════════════════════════════════════════
-- ODI Health Census v1 — Schema listo.
-- Siguiente: ejecutar V001_seed_demo_data.sql para poblar nodos demo.
-- ═══════════════════════════════════════════════════════════════════════════════
