-- ═══════════════════════════════════════════════════════════════════
-- ODI DATABASE SCHEMA v1.0
-- Organismo Digital Industrial — Base de Datos Relacional
-- Motor: PostgreSQL 15 (ya operativo en 172.18.0.4:5432)
-- Fecha: 20 Febrero 2026
-- Arquitecto: Juan David Jiménez
-- 
-- "Si no está en la base de datos, no existe para ODI."
-- ═══════════════════════════════════════════════════════════════════

-- NOTA: Las tablas odi_decision_logs, odi_humans, odi_overrides
-- YA EXISTEN de V8.1/V8.2. Este script NO las toca.
-- Solo crea las tablas NUEVAS para productos, taxonomía y pipeline.

BEGIN;

-- ═══════════════════════════════════════════════════════════════════
-- SCHEMA 1: CORE — Núcleo Multi-Industria
-- ═══════════════════════════════════════════════════════════════════

-- INDUSTRIAS: Verticales de negocio (Transporte, Salud, Entretenimiento)
CREATE TABLE IF NOT EXISTS industrias (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(30) UNIQUE NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    descripcion TEXT,
    activa BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE industrias IS 'Verticales de negocio ODI: TRANSPORTE, SALUD, ENTRETENIMIENTO';

-- RAMAS: Sub-verticales dentro de cada industria
CREATE TABLE IF NOT EXISTS ramas (
    id SERIAL PRIMARY KEY,
    industria_id INT NOT NULL REFERENCES industrias(id) ON DELETE RESTRICT,
    codigo VARCHAR(30) UNIQUE NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    dominio_principal VARCHAR(255),
    activa BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ramas_industria ON ramas(industria_id);
COMMENT ON TABLE ramas IS 'Sub-verticales: SRM (motos), DENTAL, CAPILAR, TURISMO';

-- EMPRESAS: Proveedores/Clientes de cada rama
CREATE TABLE IF NOT EXISTS empresas (
    id SERIAL PRIMARY KEY,
    rama_id INT NOT NULL REFERENCES ramas(id) ON DELETE RESTRICT,
    codigo VARCHAR(30) UNIQUE NOT NULL,
    razon_social VARCHAR(200) NOT NULL,
    nit VARCHAR(20),
    contacto_nombre VARCHAR(120),
    contacto_telefono VARCHAR(20),
    contacto_email VARCHAR(120),
    
    -- Shopify integration
    shopify_shop_url VARCHAR(255),
    shopify_api_key VARCHAR(255),
    shopify_api_password VARCHAR(255),
    
    -- Branding
    brand_color_primary VARCHAR(7),
    brand_color_secondary VARCHAR(7),
    logo_url TEXT,
    
    activa BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_empresas_rama ON empresas(rama_id);
CREATE INDEX idx_empresas_codigo ON empresas(codigo);
COMMENT ON TABLE empresas IS 'Proveedores: KAIQI, ARMOTOS, VITTON, MATZU, etc.';

-- ═══════════════════════════════════════════════════════════════════
-- SCHEMA 2: CATRMU — Taxonomía Universal
-- Catálogo Taxonómico de Referencia Mercantil Universal
-- ═══════════════════════════════════════════════════════════════════

-- CATEGORÍAS: Taxonomía jerárquica auto-referencial
CREATE TABLE IF NOT EXISTS categorias (
    id SERIAL PRIMARY KEY,
    parent_id INT REFERENCES categorias(id) ON DELETE SET NULL,
    rama_id INT NOT NULL REFERENCES ramas(id) ON DELETE RESTRICT,
    nivel INT NOT NULL CHECK (nivel BETWEEN 1 AND 5),
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    nombre_en VARCHAR(120),
    
    -- Templates para Ficha 360° por categoría
    template_beneficios JSONB DEFAULT '[]'::jsonb,
    template_material VARCHAR(200),
    template_info_tecnica TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categorias_parent ON categorias(parent_id);
CREATE INDEX idx_categorias_rama ON categorias(rama_id);
CREATE INDEX idx_categorias_nivel ON categorias(nivel);
COMMENT ON TABLE categorias IS 'Taxonomía CATRMU: nivel 1=Sistema, 2=SubSistema, 3=Tipo, 4=SubTipo, 5=Variante';

-- MARCAS DE MOTO: Whitelist verificada (anti-alucinación)
CREATE TABLE IF NOT EXISTS marcas_moto (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(60) UNIQUE NOT NULL,
    pais_origen VARCHAR(60),
    activa BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE marcas_moto IS 'Whitelist de marcas reales: AKT, YAMAHA, HONDA, BAJAJ, SUZUKI...';

-- MODELOS DE MOTO: Modelos verificados por marca
CREATE TABLE IF NOT EXISTS modelos_moto (
    id SERIAL PRIMARY KEY,
    marca_id INT NOT NULL REFERENCES marcas_moto(id) ON DELETE RESTRICT,
    nombre VARCHAR(80) NOT NULL,
    cilindraje INT,
    año_desde INT,
    año_hasta INT,
    tipo VARCHAR(30),
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(marca_id, nombre)
);

CREATE INDEX idx_modelos_marca ON modelos_moto(marca_id);
CREATE INDEX idx_modelos_cilindraje ON modelos_moto(cilindraje);
COMMENT ON TABLE modelos_moto IS 'Modelos verificados: Boxer CT, FZ 2.0, Pulsar 200. Si no está aquí, NO existe.';

-- ═══════════════════════════════════════════════════════════════════
-- SCHEMA 3: PRODUCTOS — Catálogo Unificado
-- ═══════════════════════════════════════════════════════════════════

-- PRODUCTOS: Tabla maestra. UN producto = UNA fila. Fuente de verdad.
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    empresa_id INT NOT NULL REFERENCES empresas(id) ON DELETE RESTRICT,
    categoria_id INT REFERENCES categorias(id) ON DELETE SET NULL,
    
    -- Identificación
    codigo_proveedor VARCHAR(50) NOT NULL,
    titulo_raw VARCHAR(300) NOT NULL,
    titulo_normalizado VARCHAR(300),
    descripcion_corta VARCHAR(500),
    
    -- Precios
    precio_sin_iva DECIMAL(12,2),
    precio_con_iva DECIMAL(12,2),
    precio_fuente VARCHAR(30),
    
    -- Inventario
    stock INT NOT NULL DEFAULT 0,
    status VARCHAR(15) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','archived')),
    
    -- Shopify sync
    shopify_product_id BIGINT,
    shopify_variant_id BIGINT,
    shopify_synced_at TIMESTAMPTZ,
    
    -- ChromaDB reference
    chromadb_doc_id VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Un código por empresa es único
    UNIQUE(empresa_id, codigo_proveedor)
);

CREATE INDEX idx_productos_empresa ON productos(empresa_id);
CREATE INDEX idx_productos_categoria ON productos(categoria_id);
CREATE INDEX idx_productos_status ON productos(status);
CREATE INDEX idx_productos_shopify ON productos(shopify_product_id);
CREATE INDEX idx_productos_titulo ON productos USING gin(to_tsvector('spanish', titulo_normalizado));
COMMENT ON TABLE productos IS 'FUENTE DE VERDAD. Un producto, una fila. Pipeline lee → procesa → guarda AQUÍ.';

-- PRODUCTO IMÁGENES: 1:N — Producto tiene muchas imágenes
CREATE TABLE IF NOT EXISTS producto_imagenes (
    id SERIAL PRIMARY KEY,
    producto_id INT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    
    url_origen TEXT NOT NULL,
    url_shopify TEXT,
    ruta_local TEXT,
    
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('real','pelicula','ai_midjourney','ai_freepik','placeholder','catalogo')),
    es_principal BOOLEAN NOT NULL DEFAULT false,
    orden INT NOT NULL DEFAULT 1,
    
    hash_archivo VARCHAR(64),
    ancho INT,
    alto INT,
    tamaño_bytes BIGINT,
    
    validada BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_prod_img_producto ON producto_imagenes(producto_id);
CREATE INDEX idx_prod_img_hash ON producto_imagenes(hash_archivo);
CREATE INDEX idx_prod_img_tipo ON producto_imagenes(tipo);
COMMENT ON TABLE producto_imagenes IS 'Imágenes por producto. Prioridad: real > pelicula > ai_midjourney > placeholder';

-- PRODUCTO COMPATIBILIDAD: N:M — Producto ↔ Motos
CREATE TABLE IF NOT EXISTS producto_compatibilidad (
    id SERIAL PRIMARY KEY,
    producto_id INT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    modelo_moto_id INT NOT NULL REFERENCES modelos_moto(id) ON DELETE RESTRICT,
    
    posicion VARCHAR(30),
    verificado BOOLEAN NOT NULL DEFAULT false,
    fuente VARCHAR(30) NOT NULL DEFAULT 'catalogo',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(producto_id, modelo_moto_id)
);

CREATE INDEX idx_compat_producto ON producto_compatibilidad(producto_id);
CREATE INDEX idx_compat_modelo ON producto_compatibilidad(modelo_moto_id);
COMMENT ON TABLE producto_compatibilidad IS 'Fitment real verificado. N:M entre productos y modelos de moto.';

-- FICHAS 360°: 1:1 — Ficha técnica completa por producto
CREATE TABLE IF NOT EXISTS fichas_360 (
    id SERIAL PRIMARY KEY,
    producto_id INT UNIQUE NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    
    body_html TEXT,
    material VARCHAR(200),
    especificaciones JSONB DEFAULT '{}'::jsonb,
    beneficios JSONB DEFAULT '[]'::jsonb,
    info_tecnica TEXT,
    
    enrichment_source VARCHAR(20) CHECK (enrichment_source IN ('chromadb','category_template','default','manual')),
    chromadb_score FLOAT,
    
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fichas_producto ON fichas_360(producto_id);
COMMENT ON TABLE fichas_360 IS 'Ficha 360° generada por pipeline. Enrichment desde ChromaDB o category_template.';

-- ═══════════════════════════════════════════════════════════════════
-- SCHEMA 4: PIPELINE — Trazabilidad de Procesamiento
-- ═══════════════════════════════════════════════════════════════════

-- ARCHIVOS FUENTE: Cada archivo que entra al SRM Intelligent
CREATE TABLE IF NOT EXISTS archivos_fuente (
    id SERIAL PRIMARY KEY,
    empresa_id INT NOT NULL REFERENCES empresas(id) ON DELETE RESTRICT,
    
    nombre_archivo VARCHAR(255) NOT NULL,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('csv','xlsx','xls','pdf','jpg','jpeg','png','zip','json')),
    ruta_servidor TEXT NOT NULL,
    tamaño_bytes BIGINT,
    hash_archivo VARCHAR(64),
    
    productos_extraidos INT DEFAULT 0,
    procesado BOOLEAN NOT NULL DEFAULT false,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_archivos_empresa ON archivos_fuente(empresa_id);
CREATE INDEX idx_archivos_hash ON archivos_fuente(hash_archivo);
COMMENT ON TABLE archivos_fuente IS 'Todo archivo que entra al SRM. CSV, Excel, PDF, imágenes, ZIP.';

-- PIPELINE EJECUCIONES: Log de cada ejecución del pipeline 6 pasos
CREATE TABLE IF NOT EXISTS pipeline_ejecuciones (
    id SERIAL PRIMARY KEY,
    empresa_id INT NOT NULL REFERENCES empresas(id) ON DELETE RESTRICT,
    archivo_fuente_id INT REFERENCES archivos_fuente(id) ON DELETE SET NULL,
    
    paso_actual INT NOT NULL CHECK (paso_actual BETWEEN 1 AND 6),
    paso_nombre VARCHAR(30) NOT NULL,
    status VARCHAR(15) NOT NULL CHECK (status IN ('running','completed','failed','cancelled')),
    
    productos_input INT DEFAULT 0,
    productos_output INT DEFAULT 0,
    productos_error INT DEFAULT 0,
    errores JSONB DEFAULT '[]'::jsonb,
    
    duracion_seg INT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ
);

CREATE INDEX idx_pipeline_empresa ON pipeline_ejecuciones(empresa_id);
CREATE INDEX idx_pipeline_status ON pipeline_ejecuciones(status);
CREATE INDEX idx_pipeline_fecha ON pipeline_ejecuciones(started_at DESC);
COMMENT ON TABLE pipeline_ejecuciones IS 'Log de pipeline: Ingesta→Extracción→Normalización→Unificación→Enriquecimiento→Ficha360°';

-- PRECIOS LOG: Historial de cambios de precio
CREATE TABLE IF NOT EXISTS precios_log (
    id SERIAL PRIMARY KEY,
    producto_id INT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    
    precio_anterior DECIMAL(12,2),
    precio_nuevo DECIMAL(12,2) NOT NULL,
    fuente VARCHAR(30) NOT NULL,
    notas VARCHAR(200),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_precios_producto ON precios_log(producto_id);
CREATE INDEX idx_precios_fecha ON precios_log(created_at DESC);
COMMENT ON TABLE precios_log IS 'Historial completo de precios. Cada cambio queda registrado con fuente.';

-- ═══════════════════════════════════════════════════════════════════
-- VISTAS ÚTILES
-- ═══════════════════════════════════════════════════════════════════

-- Vista: Resumen por empresa
CREATE OR REPLACE VIEW v_resumen_empresas AS
SELECT 
    e.codigo AS empresa,
    r.codigo AS rama,
    i.codigo AS industria,
    COUNT(p.id) AS total_productos,
    COUNT(p.id) FILTER (WHERE p.status = 'active') AS activos,
    COUNT(p.id) FILTER (WHERE p.status = 'draft') AS draft,
    COUNT(p.id) FILTER (WHERE p.precio_sin_iva IS NOT NULL AND p.precio_sin_iva > 0) AS con_precio,
    COUNT(pi.id) AS total_imagenes,
    COUNT(pi.id) FILTER (WHERE pi.tipo = 'real') AS imagenes_reales,
    COUNT(f.id) AS con_ficha_360
FROM empresas e
JOIN ramas r ON e.rama_id = r.id
JOIN industrias i ON r.industria_id = i.id
LEFT JOIN productos p ON p.empresa_id = e.id
LEFT JOIN producto_imagenes pi ON pi.producto_id = p.id AND pi.es_principal = true
LEFT JOIN fichas_360 f ON f.producto_id = p.id
GROUP BY e.codigo, r.codigo, i.codigo
ORDER BY i.codigo, r.codigo, e.codigo;

-- Vista: Productos sin precio
CREATE OR REPLACE VIEW v_productos_sin_precio AS
SELECT 
    e.codigo AS empresa,
    p.codigo_proveedor,
    p.titulo_normalizado,
    p.status
FROM productos p
JOIN empresas e ON p.empresa_id = e.id
WHERE p.precio_sin_iva IS NULL OR p.precio_sin_iva <= 0;

-- Vista: Productos sin imagen
CREATE OR REPLACE VIEW v_productos_sin_imagen AS
SELECT 
    e.codigo AS empresa,
    p.codigo_proveedor,
    p.titulo_normalizado,
    p.status
FROM productos p
JOIN empresas e ON p.empresa_id = e.id
LEFT JOIN producto_imagenes pi ON pi.producto_id = p.id
WHERE pi.id IS NULL;

-- Vista: Calidad de ficha por empresa
CREATE OR REPLACE VIEW v_calidad_fichas AS
SELECT 
    e.codigo AS empresa,
    COUNT(f.id) AS total_fichas,
    COUNT(f.id) FILTER (WHERE f.enrichment_source = 'chromadb') AS desde_chromadb,
    COUNT(f.id) FILTER (WHERE f.enrichment_source = 'category_template') AS desde_template,
    COUNT(f.id) FILTER (WHERE f.enrichment_source = 'default') AS desde_default,
    ROUND(AVG(f.chromadb_score)::numeric, 2) AS score_promedio
FROM empresas e
LEFT JOIN productos p ON p.empresa_id = e.id
LEFT JOIN fichas_360 f ON f.producto_id = p.id
GROUP BY e.codigo
ORDER BY e.codigo;

-- Vista: Pipeline últimas ejecuciones
CREATE OR REPLACE VIEW v_pipeline_reciente AS
SELECT 
    e.codigo AS empresa,
    pe.paso_actual,
    pe.paso_nombre,
    pe.status,
    pe.productos_input,
    pe.productos_output,
    pe.productos_error,
    pe.duracion_seg,
    pe.started_at
FROM pipeline_ejecuciones pe
JOIN empresas e ON pe.empresa_id = e.id
ORDER BY pe.started_at DESC
LIMIT 50;

-- ═══════════════════════════════════════════════════════════════════
-- DATOS INICIALES: Industrias, Ramas, y Empresas SRM
-- ═══════════════════════════════════════════════════════════════════

-- Industrias
INSERT INTO industrias (codigo, nombre, descripcion) VALUES
    ('TRANSPORTE', 'Industria Transporte', 'Repuestos y partes para vehículos motorizados'),
    ('SALUD', 'Industria Salud', 'Servicios y productos de salud: dental, capilar'),
    ('ENTRETENIMIENTO', 'Industria Entretenimiento', 'Turismo, experiencias, recreación')
ON CONFLICT (codigo) DO NOTHING;

-- Ramas
INSERT INTO ramas (industria_id, codigo, nombre, dominio_principal) VALUES
    ((SELECT id FROM industrias WHERE codigo='TRANSPORTE'), 'SRM', 'Somos Repuestos Motos', 'somosrepuestosmotos.com'),
    ((SELECT id FROM industrias WHERE codigo='SALUD'), 'DENTAL', 'Dental Aesthetics', 'matzudentalaesthetics.com'),
    ((SELECT id FROM industrias WHERE codigo='SALUD'), 'CAPILAR', 'Cabeza Sanas', 'cabezasanas.com'),
    ((SELECT id FROM industrias WHERE codigo='SALUD'), 'BRUXISMO', 'COVERS Lab', 'mis-cubiertas.com'),
    ((SELECT id FROM industrias WHERE codigo='ENTRETENIMIENTO'), 'TURISMO', 'Botón Turismo', NULL)
ON CONFLICT (codigo) DO NOTHING;

-- Empresas SRM (15 tiendas)
INSERT INTO empresas (rama_id, codigo, razon_social, brand_color_primary) VALUES
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'ARMOTOS', 'Armotos S.A.S', '#FF4500'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'BARA', 'Bara Importaciones', '#1E88E5'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'CBI', 'CBI Importaciones', '#43A047'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'DFG', 'DFG Distribuciones', '#111111'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'DUNA', 'Duna Importaciones', '#0077B6'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'IMBRA', 'Imbra S.A.S', '#6A1B9A'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'JAPAN', 'Industrias Japan', '#E3001B'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'KAIQI', 'Quianluj Kaiqi Colombia S.A.S', '#D32F2F'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'LEO', 'Industrias Leo', '#FF6F00'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'MCLMOTOS', 'MCL Motos', '#37474F'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'OH_IMPORTACIONES', 'OH Importaciones', '#9C27B0'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'STORE', 'Store Repuestos', '#455A64'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'VAISAND', 'Vaisand S.A.S', '#00695C'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'VITTON', 'Industrias Vitton', '#2E7D32'),
    ((SELECT id FROM ramas WHERE codigo='SRM'), 'YOKOMAR', 'Yokomar S.A.S', '#FFC400')
ON CONFLICT (codigo) DO NOTHING;

-- Empresas SALUD
INSERT INTO empresas (rama_id, codigo, razon_social) VALUES
    ((SELECT id FROM ramas WHERE codigo='DENTAL'), 'MATZU', 'Matzu Dental Aesthetics'),
    ((SELECT id FROM ramas WHERE codigo='BRUXISMO'), 'COVERS', 'COVERS Lab'),
    ((SELECT id FROM ramas WHERE codigo='CAPILAR'), 'CABEZAS_SANAS', 'Cabezas Sanas')
ON CONFLICT (codigo) DO NOTHING;

-- Marcas de moto (whitelist Colombia)
INSERT INTO marcas_moto (nombre, pais_origen) VALUES
    ('AKT', 'Colombia'),
    ('YAMAHA', 'Japón'),
    ('HONDA', 'Japón'),
    ('SUZUKI', 'Japón'),
    ('BAJAJ', 'India'),
    ('KAWASAKI', 'Japón'),
    ('TVS', 'India'),
    ('HERO', 'India'),
    ('KTM', 'Austria'),
    ('PULSAR', 'India'),
    ('AUTECO', 'Colombia'),
    ('KYMCO', 'Taiwán'),
    ('AYCO', 'Colombia'),
    ('UM', 'Estados Unidos'),
    ('VICTORY', 'Colombia'),
    ('VENTO', 'China'),
    ('JIALING', 'China'),
    ('LONCIN', 'China'),
    ('WANXIN', 'China'),
    ('KAIQI', 'China')
ON CONFLICT (nombre) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════
-- FUNCIONES DE UTILIDAD
-- ═══════════════════════════════════════════════════════════════════

-- Función: Auto-actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers de updated_at
CREATE OR REPLACE TRIGGER tr_industrias_updated BEFORE UPDATE ON industrias FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE OR REPLACE TRIGGER tr_ramas_updated BEFORE UPDATE ON ramas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE OR REPLACE TRIGGER tr_empresas_updated BEFORE UPDATE ON empresas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE OR REPLACE TRIGGER tr_productos_updated BEFORE UPDATE ON productos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE OR REPLACE TRIGGER tr_fichas_updated BEFORE UPDATE ON fichas_360 FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT;

-- ═══════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POST-MIGRACIÓN
-- ═══════════════════════════════════════════════════════════════════
-- Ejecutar después del COMMIT:
--
-- SELECT 'industrias' AS tabla, COUNT(*) FROM industrias
-- UNION ALL SELECT 'ramas', COUNT(*) FROM ramas
-- UNION ALL SELECT 'empresas', COUNT(*) FROM empresas
-- UNION ALL SELECT 'marcas_moto', COUNT(*) FROM marcas_moto
-- UNION ALL SELECT 'categorias', COUNT(*) FROM categorias
-- UNION ALL SELECT 'productos', COUNT(*) FROM productos;
--
-- ═══════════════════════════════════════════════════════════════════
