-- ═══════════════════════════════════════════════════════════════════════════════
-- ODI Health Census — Seed Data Demo (Pereira + Red)
-- ═══════════════════════════════════════════════════════════════════════════════
-- Ejecutar después de V001_health_census.sql
-- Datos demo coherentes para pruebas end-to-end del PAEM.
-- ═══════════════════════════════════════════════════════════════════════════════

BEGIN;

-- =========================
-- Nodos clínicos
-- =========================

INSERT INTO odi_health_nodes (
    node_id, clinic_name, doctor_name, city, country, geo_lat, geo_lng,
    weekly_capacity, weekly_booked, redirect_threshold,
    sla_response_minutes, sla_followup_minutes,
    is_active, is_certified, certification_level,
    tourism_enabled, accepts_international, language_support,
    base_procedure_cost, margin_factor
) VALUES
(
    'HLT-PEI-MATZU-001',
    'Matzu Dental Aesthetics',
    'Dra. Paola Restrepo',
    'Pereira', 'CO', 4.8133, -75.6961,
    8, 3, 0.85,
    90, 120,
    TRUE, TRUE, 'master',
    TRUE, TRUE, ARRAY['es', 'en'],
    '{"carillas_porcelana": 2500, "diseno_sonrisa": 4000, "implantes_dentales": 3500, "blanqueamiento": 300}'::jsonb,
    1.0
),
(
    'HLT-PEI-DENTAL-002',
    'Clínica Dental Pereira Centro',
    'Dr. Carlos Mejía',
    'Pereira', 'CO', 4.8087, -75.6906,
    6, 5, 0.85,
    120, 180,
    TRUE, TRUE, 'advanced',
    TRUE, TRUE, ARRAY['es'],
    '{"implantes_dentales": 3000, "blanqueamiento": 250, "ortodoncia_express": 2000}'::jsonb,
    0.95
),
(
    'HLT-PEI-CABSANA-003',
    'Cabeza Sana — Salud Integral',
    'Dra. Laura Restrepo',
    'Pereira', 'CO', 4.8150, -75.6950,
    4, 1, 0.80,
    150, 240,
    TRUE, TRUE, 'basic',
    TRUE, FALSE, ARRAY['es'],
    '{"blanqueamiento": 200, "diseno_sonrisa": 3000}'::jsonb,
    0.90
)
ON CONFLICT (node_id) DO UPDATE SET
    clinic_name = EXCLUDED.clinic_name,
    doctor_name = EXCLUDED.doctor_name,
    weekly_capacity = EXCLUDED.weekly_capacity,
    weekly_booked = EXCLUDED.weekly_booked,
    base_procedure_cost = EXCLUDED.base_procedure_cost;


-- =========================
-- Certificaciones (Educación ↔ Salud)
-- =========================

INSERT INTO odi_health_certifications (
    node_id, procedure_id, procedure_name, university_partner,
    certification_date, valid_until, is_valid
) VALUES
-- Matzu: master en todo
('HLT-PEI-MATZU-001', 'carillas_porcelana', 'Carillas de Porcelana',
    'Universidad Tecnológica de Pereira', '2024-06-15', '2027-06-15', TRUE),
('HLT-PEI-MATZU-001', 'diseno_sonrisa', 'Diseño de Sonrisa Completo',
    'Universidad Tecnológica de Pereira', '2024-06-15', '2027-06-15', TRUE),
('HLT-PEI-MATZU-001', 'implantes_dentales', 'Implantes Dentales',
    'Universidad de Antioquia', '2023-03-10', '2026-03-10', TRUE),
('HLT-PEI-MATZU-001', 'blanqueamiento', 'Blanqueamiento Dental',
    'Universidad Tecnológica de Pereira', '2024-06-15', '2027-06-15', TRUE),

-- Dental 002: advanced en implantes y blanqueamiento
('HLT-PEI-DENTAL-002', 'implantes_dentales', 'Implantes Dentales',
    'Universidad CES', '2024-01-20', '2027-01-20', TRUE),
('HLT-PEI-DENTAL-002', 'blanqueamiento', 'Blanqueamiento Dental',
    'Universidad CES', '2024-01-20', '2027-01-20', TRUE),
('HLT-PEI-DENTAL-002', 'ortodoncia_express', 'Ortodoncia Express',
    'Universidad CES', '2024-01-20', '2027-01-20', TRUE),

-- Cabeza Sana: basic en blanqueamiento y diseño
('HLT-PEI-CABSANA-003', 'blanqueamiento', 'Blanqueamiento Dental',
    'Universidad Tecnológica de Pereira', '2025-08-01', '2028-08-01', TRUE),
('HLT-PEI-CABSANA-003', 'diseno_sonrisa', 'Diseño de Sonrisa Completo',
    'Universidad Tecnológica de Pereira', '2025-08-01', '2028-08-01', TRUE)

ON CONFLICT ON CONSTRAINT ux_cert_unique_valid DO UPDATE SET
    university_partner = EXCLUDED.university_partner,
    valid_until = EXCLUDED.valid_until;


-- =========================
-- Log de capacidad semana actual (snapshot auditable)
-- =========================

INSERT INTO odi_health_capacity_log (node_id, week_start, capacity, booked, source) VALUES
('HLT-PEI-MATZU-001', DATE_TRUNC('week', CURRENT_DATE)::DATE, 8, 3, 'seed'),
('HLT-PEI-DENTAL-002', DATE_TRUNC('week', CURRENT_DATE)::DATE, 6, 5, 'seed'),
('HLT-PEI-CABSANA-003', DATE_TRUNC('week', CURRENT_DATE)::DATE, 4, 1, 'seed')
ON CONFLICT ON CONSTRAINT ux_capacity_node_week DO UPDATE SET
    booked = EXCLUDED.booked,
    source = 'seed_update';


-- =========================
-- Partners de entretenimiento (Eje Cafetero)
-- =========================

INSERT INTO odi_entertainment_partners (
    partner_id, name, city, category, impact_level,
    suitable_recovery_levels, estimated_price_usd, estimated_duration_hours,
    commission_rate, description, is_active
) VALUES
('ENT-PEI-CAFE-001',
    'Cata de Café de Origen — Hacienda Venecia',
    'Pereira', 'gastronomia', 'low',
    ARRAY['low', 'medium_low', 'medium', 'high'],
    35.0, 2.5, 0.15,
    'Recorrido por finca cafetera con degustación de 5 variedades. Bajo impacto.', TRUE),

('ENT-PEI-MUSEO-002',
    'Visita Museo de Arte de Pereira',
    'Pereira', 'cultural', 'low',
    ARRAY['low', 'medium_low', 'medium', 'high'],
    8.0, 1.5, 0.10,
    'Galería de arte contemporáneo colombiano. Climatizado, accesible.', TRUE),

('ENT-PEI-GASTRO-003',
    'Recorrido Gastronómico Centro Histórico',
    'Pereira', 'gastronomia', 'medium',
    ARRAY['medium_low', 'medium', 'high'],
    45.0, 3.0, 0.12,
    '6 paradas culinarias en el centro. Caminata suave de 2km.', TRUE),

('ENT-PEI-CHEF-004',
    'Chef Privado — Cena en Finca',
    'Cerritos', 'gastronomia', 'low',
    ARRAY['low', 'medium_low', 'medium', 'high'],
    80.0, 2.0, 0.20,
    'Chef prepara cena de 5 tiempos en su alojamiento. Cero esfuerzo.', TRUE),

('ENT-PEI-TERMAL-005',
    'Termales de Santa Rosa de Cabal',
    'Santa Rosa', 'wellness', 'medium',
    ARRAY['medium', 'high'],
    25.0, 4.0, 0.10,
    'Aguas termales naturales. Requiere caminata moderada en sendero.', TRUE),

('ENT-PEI-AVES-006',
    'Avistamiento de Aves — Otún Quimbaya',
    'Pereira', 'naturaleza', 'medium',
    ARRAY['medium', 'high'],
    40.0, 5.0, 0.08,
    'Guía bilingüe, 4km de sendero. Esfuerzo moderado.', TRUE)

ON CONFLICT (partner_id) DO UPDATE SET
    name = EXCLUDED.name,
    is_active = EXCLUDED.is_active;


-- =========================
-- Hospitality partners
-- =========================

INSERT INTO odi_hospitality_partners (
    partner_id, name, city, partner_type, location_description,
    distance_to_default_clinic_km, price_per_night_usd,
    recovery_friendly, amenities, agreement_status, is_active
) VALUES
('HOS-PEI-MOVICH-001',
    'Hotel Movich Pereira', 'Pereira', 'hotel', 'Centro, Pereira',
    1.2, 85.0, TRUE,
    ARRAY['wifi', 'room_service', 'parking', 'breakfast'],
    'pending', TRUE),

('HOS-PEI-SONESTA-002',
    'Sonesta Hotel Pereira', 'Pereira', 'hotel', 'Pinares, Pereira',
    2.5, 110.0, TRUE,
    ARRAY['wifi', 'spa', 'pool', 'gym', 'breakfast', 'airport_shuttle'],
    'pending', TRUE),

('HOS-PEI-APT-003',
    'Apartamento Recuperación Centro', 'Pereira', 'airbnb', 'Centro, Pereira',
    0.8, 45.0, TRUE,
    ARRAY['wifi', 'kitchen', 'washer', 'quiet_zone'],
    'pending', TRUE),

('HOS-PEI-FINCA-004',
    'Finca Cafetera El Descanso', 'Cerritos', 'airbnb', 'Rural, Cerritos',
    12.0, 65.0, TRUE,
    ARRAY['wifi', 'nature', 'private_chef_available', 'pool'],
    'pending', TRUE)

ON CONFLICT (partner_id) DO UPDATE SET
    name = EXCLUDED.name,
    is_active = EXCLUDED.is_active;


COMMIT;

-- ═══════════════════════════════════════════════════════════════════════════════
-- Verificación rápida:
--   SELECT * FROM v_odi_health_node_load;
--   SELECT * FROM fn_odi_failover_candidates('Pereira', 'implantes_dentales');
-- ═══════════════════════════════════════════════════════════════════════════════
