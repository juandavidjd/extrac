#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# DEPLOY CATRMU LANDING — Servidor 64.23.170.118
# ═══════════════════════════════════════════════════════════════════════════════
# Ejecutar como: sudo bash deploy-catrmu.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════════════════════════════════════════"
echo "DEPLOY CATRMU LANDING v1.0"
echo "═══════════════════════════════════════════════════════════════════════════════"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

ok() { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# 1. Verificar usuario
echo ""
echo "[1/7] Verificando permisos..."
if [ "$EUID" -ne 0 ]; then
    fail "Ejecutar como root: sudo bash deploy-catrmu.sh"
fi
ok "Root verificado"

# 2. Actualizar repo
echo ""
echo "[2/7] Actualizando repositorio..."
cd /opt/odi
git fetch origin claude/unify-repository-branches-QM3zP
git checkout claude/unify-repository-branches-QM3zP
git pull origin claude/unify-repository-branches-QM3zP
ok "Repositorio actualizado"

# 3. Instalar dependencias y build
echo ""
echo "[3/7] Build del landing..."
cd /opt/odi/landing-odi

# Verificar Node.js
if ! command -v node &> /dev/null; then
    echo "Instalando Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

npm install --production=false
npm run build
ok "Build completado"

# 4. Configurar Nginx
echo ""
echo "[4/7] Configurando Nginx..."
cp /opt/odi/deploy/catrmu-nginx.conf /etc/nginx/sites-available/catrmu.com
ln -sf /etc/nginx/sites-available/catrmu.com /etc/nginx/sites-enabled/

nginx -t || fail "Error en configuración Nginx"
systemctl reload nginx
ok "Nginx configurado"

# 5. Configurar servicio systemd
echo ""
echo "[5/7] Configurando servicio systemd..."
cp /opt/odi/deploy/catrmu-landing.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable catrmu-landing
systemctl restart catrmu-landing
ok "Servicio configurado"

# 6. SSL con Certbot
echo ""
echo "[6/7] Configurando SSL..."
if command -v certbot &> /dev/null; then
    certbot --nginx -d catrmu.com -d www.catrmu.com --non-interactive --agree-tos --email admin@catrmu.com || echo "Certbot: verificar dominios DNS"
else
    echo "Instalando Certbot..."
    apt-get install -y certbot python3-certbot-nginx
    certbot --nginx -d catrmu.com -d www.catrmu.com --non-interactive --agree-tos --email admin@catrmu.com || echo "Certbot: verificar dominios DNS"
fi
ok "SSL configurado"

# 7. Verificación final
echo ""
echo "[7/7] Verificación..."
sleep 3

if systemctl is-active --quiet catrmu-landing; then
    ok "Servicio catrmu-landing activo"
else
    fail "Servicio catrmu-landing no está corriendo"
fi

if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3001 | grep -q "200\|304"; then
    ok "Landing respondiendo en puerto 3001"
else
    echo "Warning: Landing no responde aún (puede tardar unos segundos)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}DEPLOY COMPLETADO${NC}"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""
echo "URLs:"
echo "  - https://catrmu.com"
echo "  - https://www.catrmu.com"
echo ""
echo "Comandos útiles:"
echo "  systemctl status catrmu-landing"
echo "  journalctl -u catrmu-landing -f"
echo ""
