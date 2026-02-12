#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# DEPLOY ECOSISTEMA ADSI — Landing Page + SSL
# ═══════════════════════════════════════════════════════════════════════════════
# Servidor: 64.23.170.118
# Ejecutar como: sudo bash deploy-ecosistema-adsi.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "DEPLOY ECOSISTEMA ADSI v1.0"
echo "═══════════════════════════════════════════════════════════════════════════════"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ok() { echo -e "${GREEN}[OK]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# ═══════════════════════════════════════════════════════════════════════════════
# PRE-REQUISITOS DNS
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║ REQUISITO: Configurar DNS en IONOS antes de ejecutar este script          ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║                                                                           ║"
echo "║ 1. Ir a IONOS → Dominios → ecosistema-adsi.com → DNS                      ║"
echo "║                                                                           ║"
echo "║ 2. Agregar estos registros A:                                             ║"
echo "║    ┌───────────────────────┬────────────────────┐                         ║"
echo "║    │ Host                  │ Apunta a           │                         ║"
echo "║    ├───────────────────────┼────────────────────┤                         ║"
echo "║    │ @                     │ 64.23.170.118      │                         ║"
echo "║    │ www                   │ 64.23.170.118      │                         ║"
echo "║    │ odi                   │ 64.23.170.118      │                         ║"
echo "║    └───────────────────────┴────────────────────┘                         ║"
echo "║                                                                           ║"
echo "║ 3. Repetir para: ecosistema-adsi.tienda, .online, .info                   ║"
echo "║                                                                           ║"
echo "║ 4. Esperar propagación DNS (5-30 min)                                     ║"
echo "║                                                                           ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar DNS
info "Verificando DNS..."
DNS_CHECK=$(dig +short ecosistema-adsi.com A 2>/dev/null || echo "")
if [ "$DNS_CHECK" = "64.23.170.118" ]; then
    ok "DNS ecosistema-adsi.com → 64.23.170.118"
else
    warn "DNS aún no propagado. Valor actual: '$DNS_CHECK'"
    read -p "¿Continuar de todos modos? (s/n): " CONTINUE
    if [ "$CONTINUE" != "s" ]; then
        echo "Abortado. Configura DNS primero."
        exit 1
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 1: Crear directorio web
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[1/4] Creando directorio web..."

mkdir -p /var/www/ecosistema-adsi
chown -R www-data:www-data /var/www/ecosistema-adsi
chmod 755 /var/www/ecosistema-adsi

ok "Directorio /var/www/ecosistema-adsi creado"

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 2: Crear landing page
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[2/4] Creando landing page..."

cat > /var/www/ecosistema-adsi/index.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ecosistema ADSI — Arquitectura, Diseño, Sistemas e Implementación</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Exo+2:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1e40af;
            --secondary: #10b981;
            --dark: #0f172a;
            --darker: #020617;
            --light: #f8fafc;
            --gray: #64748b;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Exo 2', sans-serif;
            background: linear-gradient(135deg, var(--dark) 0%, var(--darker) 100%);
            color: var(--light);
            min-height: 100vh;
        }

        .hero {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 2rem;
            position: relative;
            overflow: hidden;
        }

        .hero::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background:
                radial-gradient(circle at 20% 80%, rgba(37, 99, 235, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(16, 185, 129, 0.1) 0%, transparent 50%);
            pointer-events: none;
        }

        .logo-container {
            margin-bottom: 2rem;
            position: relative;
            z-index: 1;
        }

        .logo {
            width: 120px;
            height: 120px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            border-radius: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.5rem;
            font-weight: 700;
            color: white;
            box-shadow: 0 20px 60px rgba(37, 99, 235, 0.3);
            animation: float 6s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        h1 {
            font-size: clamp(2rem, 5vw, 3.5rem);
            font-weight: 700;
            margin-bottom: 0.5rem;
            position: relative;
            z-index: 1;
        }

        .acronym {
            display: flex;
            gap: 0.5rem;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 2rem;
            position: relative;
            z-index: 1;
        }

        .acronym span {
            background: rgba(255, 255, 255, 0.1);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-size: 0.9rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .acronym span:nth-child(1) { border-color: var(--primary); }
        .acronym span:nth-child(2) { border-color: var(--secondary); }
        .acronym span:nth-child(3) { border-color: #f59e0b; }
        .acronym span:nth-child(4) { border-color: #ef4444; }

        .tagline {
            font-size: 1.25rem;
            color: var(--gray);
            max-width: 600px;
            line-height: 1.6;
            margin-bottom: 3rem;
            position: relative;
            z-index: 1;
        }

        .pillars {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            max-width: 900px;
            width: 100%;
            position: relative;
            z-index: 1;
        }

        .pillar {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: left;
            transition: all 0.3s ease;
        }

        .pillar:hover {
            transform: translateY(-5px);
            border-color: var(--primary);
            background: rgba(37, 99, 235, 0.1);
        }

        .pillar h3 {
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .pillar p {
            color: var(--gray);
            font-size: 0.9rem;
            line-height: 1.5;
        }

        .footer {
            position: absolute;
            bottom: 2rem;
            text-align: center;
            color: var(--gray);
            font-size: 0.85rem;
        }

        .footer a {
            color: var(--primary);
            text-decoration: none;
        }

        .footer a:hover {
            text-decoration: underline;
        }

        .grid-bg {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image:
                linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            pointer-events: none;
        }
    </style>
</head>
<body>
    <div class="grid-bg"></div>

    <section class="hero">
        <div class="logo-container">
            <div class="logo">ADSI</div>
        </div>

        <h1>Ecosistema ADSI</h1>

        <div class="acronym">
            <span>Arquitectura</span>
            <span>Diseño</span>
            <span>Sistemas</span>
            <span>Implementación</span>
        </div>

        <p class="tagline">
            Metodología integral para la construcción de organismos digitales industriales.
            Desde la arquitectura conceptual hasta la implementación en producción.
        </p>

        <div class="pillars">
            <div class="pillar">
                <h3>🏗️ Arquitectura</h3>
                <p>Diseño de estructuras escalables, modularidad y patrones de integración empresarial.</p>
            </div>
            <div class="pillar">
                <h3>🎨 Diseño</h3>
                <p>Interfaces cognitivas, experiencia de usuario y flujos de interacción natural.</p>
            </div>
            <div class="pillar">
                <h3>⚙️ Sistemas</h3>
                <p>Infraestructura en la nube, contenedores, bases de datos y pipelines de datos.</p>
            </div>
            <div class="pillar">
                <h3>🚀 Implementación</h3>
                <p>Despliegue continuo, monitoreo, hardening y operaciones en producción.</p>
            </div>
        </div>

        <div class="footer">
            <p>Parte del ecosistema <a href="https://catrmu.com" target="_blank">CATRMU</a> | Powered by <a href="https://liveodi.com" target="_blank">ODI</a></p>
        </div>
    </section>
</body>
</html>
HTMLEOF

chown www-data:www-data /var/www/ecosistema-adsi/index.html
chmod 644 /var/www/ecosistema-adsi/index.html

ok "Landing page creada"

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 3: Configurar Nginx
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[3/4] Configurando Nginx..."

cat > /etc/nginx/sites-available/ecosistema-adsi.com << 'NGINXEOF'
server {
    listen 80;
    server_name ecosistema-adsi.com www.ecosistema-adsi.com ecosistema-adsi.tienda ecosistema-adsi.online ecosistema-adsi.info;

    root /var/www/ecosistema-adsi;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5678/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
}
NGINXEOF

# Habilitar sitio
ln -sf /etc/nginx/sites-available/ecosistema-adsi.com /etc/nginx/sites-enabled/

# Verificar configuración
nginx -t
if [ $? -eq 0 ]; then
    systemctl reload nginx
    ok "Nginx configurado y recargado"
else
    warn "Error en configuración Nginx"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════════
# FASE 4: SSL con Certbot
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "[4/4] Configurando SSL..."

# Verificar que Certbot está instalado
if ! command -v certbot &> /dev/null; then
    apt-get update -qq
    apt-get install -y certbot python3-certbot-nginx
fi

# Obtener certificado
certbot --nginx -d ecosistema-adsi.com -d www.ecosistema-adsi.com --non-interactive --agree-tos --email admin@ecosistema-adsi.com --redirect || {
    warn "Certbot falló para dominio principal. Intentar TLDs adicionales manualmente:"
    echo "  certbot --nginx -d ecosistema-adsi.tienda"
    echo "  certbot --nginx -d ecosistema-adsi.online"
    echo "  certbot --nginx -d ecosistema-adsi.info"
}

ok "SSL configurado"

# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICACIÓN FINAL
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "DEPLOY ECOSISTEMA ADSI COMPLETADO"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "URLs:"
echo "  https://ecosistema-adsi.com"
echo "  https://www.ecosistema-adsi.com"
echo ""
echo "TLDs adicionales (configurar DNS primero):"
echo "  https://ecosistema-adsi.tienda"
echo "  https://ecosistema-adsi.online"
echo "  https://ecosistema-adsi.info"
echo ""
echo "Archivos creados:"
echo "  /var/www/ecosistema-adsi/index.html"
echo "  /etc/nginx/sites-available/ecosistema-adsi.com"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
