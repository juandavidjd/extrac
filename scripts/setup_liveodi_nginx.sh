#!/bin/bash
# ============================================================
# ODI — Setup Nginx + SSL para api.liveodi.com y ws.liveodi.com
# Ejecutar en: root@64.23.170.118
# Fecha: 14 Feb 2026
# ============================================================

set -euo pipefail

echo "=========================================="
echo "  ODI — Configuración Nginx + SSL"
echo "  api.liveodi.com + ws.liveodi.com"
echo "=========================================="

# --- 1. Verificar DNS ---
echo ""
echo "[1/6] Verificando resolución DNS..."
API_IP=$(dig +short api.liveodi.com | head -1)
WS_IP=$(dig +short ws.liveodi.com | head -1)

if [ "$API_IP" != "64.23.170.118" ]; then
    echo "  ❌ api.liveodi.com resuelve a '$API_IP' (esperado: 64.23.170.118)"
    echo "  Espera propagación DNS o verifica IONOS."
    exit 1
fi
echo "  ✅ api.liveodi.com → $API_IP"

if [ "$WS_IP" != "64.23.170.118" ]; then
    echo "  ⚠️  ws.liveodi.com resuelve a '$WS_IP' (esperado: 64.23.170.118)"
    echo "  Continuando solo con api.liveodi.com..."
    SKIP_WS=true
else
    echo "  ✅ ws.liveodi.com → $WS_IP"
    SKIP_WS=false
fi

# --- 2. Crear config Nginx para api.liveodi.com ---
echo ""
echo "[2/6] Creando configuración Nginx para api.liveodi.com..."

cat > /etc/nginx/sites-available/api-liveodi << 'NGINX_CONF'
server {
    listen 80;
    server_name api.liveodi.com;

    location / {
        proxy_pass http://127.0.0.1:8807;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8807/health;
        proxy_set_header Host $host;
    }
}
NGINX_CONF

echo "  ✅ /etc/nginx/sites-available/api-liveodi creado"

# --- 3. Crear config Nginx para ws.liveodi.com ---
if [ "$SKIP_WS" = false ]; then
    echo ""
    echo "[3/6] Creando configuración Nginx para ws.liveodi.com..."

    cat > /etc/nginx/sites-available/ws-liveodi << 'NGINX_CONF'
server {
    listen 80;
    server_name ws.liveodi.com;

    location / {
        proxy_pass http://127.0.0.1:7777;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
NGINX_CONF

    echo "  ✅ /etc/nginx/sites-available/ws-liveodi creado"
else
    echo ""
    echo "[3/6] ⏭️  Saltando ws.liveodi.com (DNS no resuelve aún)"
fi

# --- 4. Activar sitios (symlinks) ---
echo ""
echo "[4/6] Activando sitios..."

if [ ! -L /etc/nginx/sites-enabled/api-liveodi ]; then
    ln -s /etc/nginx/sites-available/api-liveodi /etc/nginx/sites-enabled/api-liveodi
    echo "  ✅ api-liveodi activado"
else
    echo "  ℹ️  api-liveodi ya estaba activado"
fi

if [ "$SKIP_WS" = false ] && [ ! -L /etc/nginx/sites-enabled/ws-liveodi ]; then
    ln -s /etc/nginx/sites-available/ws-liveodi /etc/nginx/sites-enabled/ws-liveodi
    echo "  ✅ ws-liveodi activado"
elif [ "$SKIP_WS" = false ]; then
    echo "  ℹ️  ws-liveodi ya estaba activado"
fi

# --- 5. Test y reload Nginx ---
echo ""
echo "[5/6] Validando y recargando Nginx..."

nginx -t 2>&1
if [ $? -eq 0 ]; then
    systemctl reload nginx
    echo "  ✅ Nginx recargado exitosamente"
else
    echo "  ❌ Error en configuración Nginx. Revisa arriba."
    exit 1
fi

# --- 6. Generar SSL con Certbot ---
echo ""
echo "[6/6] Generando certificados SSL con Let's Encrypt..."

if [ "$SKIP_WS" = false ]; then
    certbot --nginx -d api.liveodi.com -d ws.liveodi.com --non-interactive --agree-tos --redirect
else
    certbot --nginx -d api.liveodi.com --non-interactive --agree-tos --redirect
fi

if [ $? -eq 0 ]; then
    echo "  ✅ SSL configurado exitosamente"
else
    echo "  ❌ Error generando SSL. Verifica que el DNS ya propagó."
    exit 1
fi

# --- Verificación final ---
echo ""
echo "=========================================="
echo "  ✅ CONFIGURACIÓN COMPLETA"
echo "=========================================="
echo ""
echo "  Subdominios activos:"
echo "    https://api.liveodi.com  → :8807 (PAEM API)"
if [ "$SKIP_WS" = false ]; then
    echo "    https://ws.liveodi.com   → :7777 (Voice/WS)"
fi
echo ""
echo "  Verificar con:"
echo "    curl -s https://api.liveodi.com/health"
echo "    curl -s https://ws.liveodi.com/health"
echo ""
echo "  Certificados SSL:"
echo "    certbot certificates"
echo "=========================================="
