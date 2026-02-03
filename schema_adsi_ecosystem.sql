-- ══════════════════════════════════════════════════════════════════════════════════
--                     ADSI ECOSYSTEM DATABASE SCHEMA
--                 PostgreSQL Schema for Multi-Tenant Industrial System
-- ══════════════════════════════════════════════════════════════════════════════════
--
-- Jerarquía:
--   ecosistema-adsi.com
--   └── somosindustrias.com (carga skin por industria)
--       └── somosrepuestosmotos.com (SRM)
--           └── Empresas: KAIQI, JAPAN, ARMOTOS...
--               └── Usuarios con Roles
--
-- ══════════════════════════════════════════════════════════════════════════════════

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ══════════════════════════════════════════════════════════════════════════════════
-- INDUSTRIAS
-- ══════════════════════════════════════════════════════════════════════════════════

CREATE TABLE industrias (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,           -- 'SRM', 'FERRETERIA', 'ELECTRONICA'
    nombre VARCHAR(255) NOT NULL,                  -- 'Somos Repuestos Motos'
    dominio VARCHAR(255) UNIQUE NOT NULL,          -- 'somosrepuestosmotos.com'
    descripcion TEXT,

    -- Configuración de Skin
    config_skin JSONB DEFAULT '{}'::jsonb,         -- Colores, logo, menús
    /*
    Ejemplo config_skin:
    {
        "colores": {
            "primario": "#E53B47",
            "secundario": "#0090FF",
            "fondo": "#0D0D0D"
        },
        "logo_url": "/logos/srm.svg",
        "menu_items": ["Catálogo", "Clientes", "Academia"],
        "tagline": "Tecnología + Catálogo Unificado"
    }
    */

    activa BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Datos iniciales
INSERT INTO industrias (codigo, nombre, dominio, config_skin) VALUES
('SRM', 'Somos Repuestos Motos', 'somosrepuestosmotos.com',
 '{"colores": {"primario": "#E53B47", "secundario": "#0090FF", "fondo": "#0D0D0D"}, "tagline": "Tecnología + Catálogo Unificado + Conocimiento Técnico"}'),
('FERRETERIA', 'Somos Ferretería', 'somosferreteria.com',
 '{"colores": {"primario": "#F59E0B", "secundario": "#78350F"}}'),
('ELECTRONICA', 'Somos Electrónica', 'somoselectronica.com',
 '{"colores": {"primario": "#10B981", "secundario": "#064E3B"}}');


-- ══════════════════════════════════════════════════════════════════════════════════
-- EMPRESAS
-- ══════════════════════════════════════════════════════════════════════════════════

CREATE TABLE empresas (
    id SERIAL PRIMARY KEY,
    industria_id INTEGER NOT NULL REFERENCES industrias(id),
    codigo VARCHAR(50) UNIQUE NOT NULL,            -- 'KAIQI', 'JAPAN', 'ARMOTOS'
    nombre VARCHAR(255) NOT NULL,
    nombre_comercial VARCHAR(255),

    -- Shopify Integration
    shopify_shop VARCHAR(255),                     -- 'u03tqc-0e.myshopify.com'
    shopify_token_encrypted TEXT,                  -- Token encriptado

    -- Configuración
    config JSONB DEFAULT '{}'::jsonb,
    /*
    {
        "productos_activos": 2847,
        "imagen_logo": "url",
        "contacto": {"email": "", "telefono": ""},
        "ubicacion": "Colombia"
    }
    */

    activa BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_empresas_industria ON empresas(industria_id);

-- Datos iniciales (SRM empresas)
INSERT INTO empresas (industria_id, codigo, nombre, shopify_shop) VALUES
(1, 'KAIQI', 'Kaiqi Repuestos', 'u03tqc-0e.myshopify.com'),
(1, 'JAPAN', 'Japan Motos', '7cy1zd-qz.myshopify.com'),
(1, 'ARMOTOS', 'Armotos', NULL),
(1, 'BARA', 'Bara Repuestos', '4jqcki-jq.myshopify.com'),
(1, 'DFG', 'DFG Motos', '0se1jt-q1.myshopify.com'),
(1, 'YOKOMAR', 'Yokomar', 'u1zmhk-ts.myshopify.com'),
(1, 'VAISAND', 'Vaisand', 'z4fpdj-mz.myshopify.com'),
(1, 'LEO', 'Leo Repuestos', 'h1hywg-pq.myshopify.com'),
(1, 'DUNA', 'Duna Motos', 'ygsfhq-fs.myshopify.com'),
(1, 'IMBRA', 'Imbra', '0i1mdf-gi.myshopify.com');


-- ══════════════════════════════════════════════════════════════════════════════════
-- ROLES
-- ══════════════════════════════════════════════════════════════════════════════════

CREATE TYPE nivel_rol AS ENUM ('ecosistema', 'industria', 'empresa');

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,            -- 'admin_adsi', 'vendedor', etc.
    nombre VARCHAR(255) NOT NULL,
    nivel nivel_rol NOT NULL,
    descripcion TEXT,

    -- Permisos como array de strings
    permisos TEXT[] DEFAULT '{}',
    /*
    Ejemplos de permisos:
    - '*' = acceso total
    - 'ver_catalogo'
    - 'editar_productos'
    - 'gestionar_usuarios'
    - 'ver_reportes'
    - 'cargar_catalogos'
    - 'ver_fichas_tecnicas'
    */

    -- Industria específica (null = aplica a todas)
    industria_id INTEGER REFERENCES industrias(id),

    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Roles del ecosistema
INSERT INTO roles (codigo, nombre, nivel, permisos, descripcion) VALUES
-- Nivel ecosistema
('admin_adsi', 'Administrador ADSI', 'ecosistema',
 ARRAY['*'], 'Acceso total al ecosistema ADSI'),

-- Nivel industria
('admin_industria', 'Administrador de Industria', 'industria',
 ARRAY['gestionar_empresas', 'ver_metricas_industria', 'configurar_catalogo_maestro', 'gestionar_academia'],
 'Administra una industria completa'),

-- Nivel empresa
('admin_empresa', 'Administrador de Empresa', 'empresa',
 ARRAY['gestionar_usuarios', 'ver_catalogo', 'configurar_shopify', 'ver_reportes', 'cargar_catalogos'],
 'Administra una empresa dentro de la industria'),

('jefe_catalogo', 'Jefe de Catálogo', 'empresa',
 ARRAY['cargar_catalogos', 'revisar_fichas', 'aprobar_productos', 'exportar_datos', 'ver_catalogo'],
 'Gestiona el catálogo de productos'),

('vendedor', 'Vendedor', 'empresa',
 ARRAY['ver_catalogo', 'buscar_productos', 'ver_fichas_tecnicas', 'ver_compatibilidades', 'generar_cotizaciones'],
 'Vende productos usando el catálogo'),

('tecnico_taller', 'Técnico de Taller', 'empresa',
 ARRAY['buscar_productos', 'ver_fichas_tecnicas', 'buscar_por_sistema', 'registrar_diagnosticos', 'ver_historial'],
 'Mecánico o técnico de taller'),

('invitado', 'Invitado', 'empresa',
 ARRAY['ver_catalogo_publico', 'buscar_productos'],
 'Usuario sin rol específico asignado');


-- ══════════════════════════════════════════════════════════════════════════════════
-- USUARIOS
-- ══════════════════════════════════════════════════════════════════════════════════

CREATE TABLE usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),                    -- bcrypt hash

    -- Información básica
    nombre VARCHAR(255) NOT NULL,
    telefono VARCHAR(50),
    avatar_url TEXT,

    -- Vinculación jerárquica
    empresa_id INTEGER REFERENCES empresas(id),   -- NULL si no pertenece a empresa específica
    rol_id INTEGER NOT NULL REFERENCES roles(id),

    -- Para usuarios sin empresa (talleres independientes, etc.)
    nombre_negocio VARCHAR(255),                   -- "Taller La Moto Feliz"
    tipo_negocio VARCHAR(100),                     -- "taller", "almacen_independiente"
    ubicacion VARCHAR(255),

    -- Metadata de ODI
    created_by_odi BOOLEAN DEFAULT false,
    odi_session_id UUID,                           -- Sesión donde ODI lo creó
    odi_metadata JSONB DEFAULT '{}'::jsonb,
    /*
    {
        "conversation_summary": "Usuario contactó preguntando por pastillas...",
        "detected_intent": "consulta_tecnica",
        "detected_role": "tecnico_taller",
        "confidence": 0.92
    }
    */

    -- Estado
    email_verificado BOOLEAN DEFAULT false,
    activo BOOLEAN DEFAULT true,
    ultimo_login TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_usuarios_empresa ON usuarios(empresa_id);
CREATE INDEX idx_usuarios_rol ON usuarios(rol_id);
CREATE INDEX idx_usuarios_email ON usuarios(email);
CREATE INDEX idx_usuarios_odi_session ON usuarios(odi_session_id);


-- ══════════════════════════════════════════════════════════════════════════════════
-- SESIONES ODI (Historial de conversaciones)
-- ══════════════════════════════════════════════════════════════════════════════════

CREATE TABLE sesiones_odi (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Usuario (puede ser null si aún no se ha creado)
    usuario_id UUID REFERENCES usuarios(id),

    -- Identificadores de canal
    canal VARCHAR(50) NOT NULL,                    -- 'whatsapp', 'web', 'voice'
    canal_id VARCHAR(255),                         -- Número de WhatsApp, session web, etc.

    -- Contexto detectado
    industria_detectada_id INTEGER REFERENCES industrias(id),
    empresa_detectada_id INTEGER REFERENCES empresas(id),
    rol_sugerido_id INTEGER REFERENCES roles(id),

    -- Conversación
    mensajes JSONB DEFAULT '[]'::jsonb,
    /*
    [
        {"rol": "user", "contenido": "Hola, tengo un taller", "timestamp": "..."},
        {"rol": "odi", "contenido": "¡Hola! ...", "timestamp": "..."}
    ]
    */

    -- Intents y acciones
    intents_detectados TEXT[] DEFAULT '{}',
    acciones_tomadas JSONB DEFAULT '[]'::jsonb,
    /*
    [
        {"accion": "USER_CREATED", "datos": {...}, "timestamp": "..."},
        {"accion": "PRODUCT_SEARCHED", "datos": {...}, "timestamp": "..."}
    ]
    */

    -- Estado
    estado VARCHAR(50) DEFAULT 'activa',           -- 'activa', 'cerrada', 'abandonada'

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

-- Índices
CREATE INDEX idx_sesiones_usuario ON sesiones_odi(usuario_id);
CREATE INDEX idx_sesiones_canal ON sesiones_odi(canal, canal_id);
CREATE INDEX idx_sesiones_estado ON sesiones_odi(estado);


-- ══════════════════════════════════════════════════════════════════════════════════
-- ACADEMIA - Progreso de usuarios
-- ══════════════════════════════════════════════════════════════════════════════════

CREATE TABLE academia_progreso (
    id SERIAL PRIMARY KEY,
    usuario_id UUID NOT NULL REFERENCES usuarios(id),

    -- Curso y módulo
    curso_id VARCHAR(100) NOT NULL,                -- 'fundamentos-srm'
    modulo_id VARCHAR(100),                        -- 'm1'
    leccion_id VARCHAR(100),                       -- 'l1'

    -- Progreso
    completado BOOLEAN DEFAULT false,
    porcentaje_avance INTEGER DEFAULT 0,           -- 0-100
    tiempo_invertido_segundos INTEGER DEFAULT 0,

    -- Evaluación
    intentos_evaluacion INTEGER DEFAULT 0,
    mejor_puntaje INTEGER,                         -- 0-100
    aprobado BOOLEAN DEFAULT false,

    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_progreso_usuario ON academia_progreso(usuario_id);
CREATE INDEX idx_progreso_curso ON academia_progreso(curso_id);

-- Constraint único: un usuario solo tiene un registro por curso/módulo/lección
CREATE UNIQUE INDEX idx_progreso_unico ON academia_progreso(usuario_id, curso_id, COALESCE(modulo_id, ''), COALESCE(leccion_id, ''));


-- ══════════════════════════════════════════════════════════════════════════════════
-- CERTIFICACIONES
-- ══════════════════════════════════════════════════════════════════════════════════

CREATE TABLE certificaciones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID NOT NULL REFERENCES usuarios(id),

    tipo VARCHAR(100) NOT NULL,                    -- 'SRM_PRO', 'SRM_NIVEL_1', etc.
    industria_id INTEGER REFERENCES industrias(id),

    -- Datos del certificado
    nombre_certificado VARCHAR(255) NOT NULL,
    descripcion TEXT,

    -- Validez
    fecha_emision TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_expiracion TIMESTAMP WITH TIME ZONE,     -- NULL si no expira

    -- Verificación
    codigo_verificacion VARCHAR(100) UNIQUE,       -- Código único para verificar

    activo BOOLEAN DEFAULT true
);

CREATE INDEX idx_certificaciones_usuario ON certificaciones(usuario_id);


-- ══════════════════════════════════════════════════════════════════════════════════
-- FUNCIONES ÚTILES
-- ══════════════════════════════════════════════════════════════════════════════════

-- Función para obtener la industria de un usuario
CREATE OR REPLACE FUNCTION get_usuario_industria(p_usuario_id UUID)
RETURNS INTEGER AS $$
DECLARE
    v_industria_id INTEGER;
BEGIN
    SELECT e.industria_id INTO v_industria_id
    FROM usuarios u
    LEFT JOIN empresas e ON u.empresa_id = e.id
    WHERE u.id = p_usuario_id;

    RETURN v_industria_id;
END;
$$ LANGUAGE plpgsql;


-- Función para verificar permiso de usuario
CREATE OR REPLACE FUNCTION usuario_tiene_permiso(p_usuario_id UUID, p_permiso TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_permisos TEXT[];
BEGIN
    SELECT r.permisos INTO v_permisos
    FROM usuarios u
    JOIN roles r ON u.rol_id = r.id
    WHERE u.id = p_usuario_id;

    -- Si tiene permiso '*' tiene acceso a todo
    IF '*' = ANY(v_permisos) THEN
        RETURN TRUE;
    END IF;

    RETURN p_permiso = ANY(v_permisos);
END;
$$ LANGUAGE plpgsql;


-- Función para crear usuario desde ODI
CREATE OR REPLACE FUNCTION crear_usuario_desde_odi(
    p_email VARCHAR,
    p_nombre VARCHAR,
    p_telefono VARCHAR,
    p_rol_codigo VARCHAR,
    p_empresa_id INTEGER,
    p_nombre_negocio VARCHAR,
    p_tipo_negocio VARCHAR,
    p_ubicacion VARCHAR,
    p_odi_session_id UUID,
    p_odi_metadata JSONB
)
RETURNS UUID AS $$
DECLARE
    v_usuario_id UUID;
    v_rol_id INTEGER;
BEGIN
    -- Obtener rol
    SELECT id INTO v_rol_id FROM roles WHERE codigo = p_rol_codigo;
    IF v_rol_id IS NULL THEN
        SELECT id INTO v_rol_id FROM roles WHERE codigo = 'invitado';
    END IF;

    -- Crear usuario
    INSERT INTO usuarios (
        email, nombre, telefono, rol_id, empresa_id,
        nombre_negocio, tipo_negocio, ubicacion,
        created_by_odi, odi_session_id, odi_metadata
    ) VALUES (
        p_email, p_nombre, p_telefono, v_rol_id, p_empresa_id,
        p_nombre_negocio, p_tipo_negocio, p_ubicacion,
        TRUE, p_odi_session_id, p_odi_metadata
    )
    RETURNING id INTO v_usuario_id;

    -- Actualizar sesión ODI
    UPDATE sesiones_odi
    SET usuario_id = v_usuario_id,
        acciones_tomadas = acciones_tomadas || jsonb_build_object(
            'accion', 'USER_CREATED',
            'usuario_id', v_usuario_id,
            'timestamp', NOW()
        )
    WHERE id = p_odi_session_id;

    RETURN v_usuario_id;
END;
$$ LANGUAGE plpgsql;


-- ══════════════════════════════════════════════════════════════════════════════════
-- VISTAS ÚTILES
-- ══════════════════════════════════════════════════════════════════════════════════

-- Vista de usuarios con contexto completo
CREATE OR REPLACE VIEW v_usuarios_completo AS
SELECT
    u.id,
    u.email,
    u.nombre,
    u.telefono,
    u.nombre_negocio,
    u.tipo_negocio,
    u.ubicacion,
    r.codigo AS rol_codigo,
    r.nombre AS rol_nombre,
    r.nivel AS rol_nivel,
    r.permisos,
    e.codigo AS empresa_codigo,
    e.nombre AS empresa_nombre,
    i.codigo AS industria_codigo,
    i.nombre AS industria_nombre,
    i.dominio AS industria_dominio,
    i.config_skin AS industria_skin,
    u.created_by_odi,
    u.created_at,
    u.ultimo_login
FROM usuarios u
JOIN roles r ON u.rol_id = r.id
LEFT JOIN empresas e ON u.empresa_id = e.id
LEFT JOIN industrias i ON e.industria_id = i.id OR r.industria_id = i.id;


-- Vista de empresas por industria con stats
CREATE OR REPLACE VIEW v_empresas_stats AS
SELECT
    e.id,
    e.codigo,
    e.nombre,
    e.shopify_shop,
    i.codigo AS industria_codigo,
    i.nombre AS industria_nombre,
    COUNT(DISTINCT u.id) AS total_usuarios,
    e.activa,
    e.created_at
FROM empresas e
JOIN industrias i ON e.industria_id = i.id
LEFT JOIN usuarios u ON u.empresa_id = e.id
GROUP BY e.id, i.codigo, i.nombre;


-- ══════════════════════════════════════════════════════════════════════════════════
-- TRIGGERS
-- ══════════════════════════════════════════════════════════════════════════════════

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_usuarios_updated_at
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_empresas_updated_at
    BEFORE UPDATE ON empresas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_industrias_updated_at
    BEFORE UPDATE ON industrias
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_sesiones_odi_updated_at
    BEFORE UPDATE ON sesiones_odi
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
