#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# ODI API Deployment Script
# ══════════════════════════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════════════════════════════════════"
echo "  ODI API v1.0 - Deployment"
echo "═══════════════════════════════════════════════════════════════════════════"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ODI_HOME="/opt/odi"
REPO_PATH="/tmp/extrac/odi_production"

# ══════════════════════════════════════════════════════════════════════════════
# 1. Crear directorio API
# ══════════════════════════════════════════════════════════════════════════════
echo -e "\n${YELLOW}[1/5] Creando directorio API...${NC}"
mkdir -p $ODI_HOME/api
mkdir -p $ODI_HOME/logs

# ══════════════════════════════════════════════════════════════════════════════
# 2. Copiar archivos
# ══════════════════════════════════════════════════════════════════════════════
echo -e "\n${YELLOW}[2/5] Copiando archivos...${NC}"
cp $REPO_PATH/api/main.py $ODI_HOME/api/
cp $REPO_PATH/api/requirements.txt $ODI_HOME/api/

# ══════════════════════════════════════════════════════════════════════════════
# 3. Instalar dependencias
# ══════════════════════════════════════════════════════════════════════════════
echo -e "\n${YELLOW}[3/5] Instalando dependencias...${NC}"
pip3 install -r $ODI_HOME/api/requirements.txt --quiet

# ══════════════════════════════════════════════════════════════════════════════
# 4. Crear servicio systemd
# ══════════════════════════════════════════════════════════════════════════════
echo -e "\n${YELLOW}[4/5] Configurando servicio systemd...${NC}"

cat > /etc/systemd/system/odi-api.service << 'EOF'
[Unit]
Description=ODI API - Unified REST API for ODI Ecosystem
After=network.target odi-cortex-query.service
Wants=odi-cortex-query.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/odi/api
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8800
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=CORTEX_URL=http://127.0.0.1:8803
Environment=PIPELINE_URL=http://127.0.0.1:8804
Environment=JWT_SECRET=odi-production-secret-change-this
StandardOutput=append:/opt/odi/logs/api.log
StandardError=append:/opt/odi/logs/api_error.log
MemoryMax=512M

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

# ══════════════════════════════════════════════════════════════════════════════
# 5. Iniciar servicio
# ══════════════════════════════════════════════════════════════════════════════
echo -e "\n${YELLOW}[5/5] Iniciando servicio...${NC}"
systemctl enable odi-api
systemctl restart odi-api

sleep 3

# ══════════════════════════════════════════════════════════════════════════════
# Verificación
# ══════════════════════════════════════════════════════════════════════════════
echo -e "\n${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ODI API Deployment Complete${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════${NC}"

echo -e "\n${YELLOW}Verificando servicio...${NC}"
systemctl status odi-api --no-pager | head -10

echo -e "\n${YELLOW}Health check...${NC}"
curl -s http://127.0.0.1:8800/health | python3 -m json.tool || echo "API aún iniciando..."

echo -e "\n${GREEN}════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ODI API disponible en:${NC}"
echo -e "${GREEN}    - Local:  http://127.0.0.1:8800${NC}"
echo -e "${GREEN}    - Docs:   http://127.0.0.1:8800/docs${NC}"
echo -e "${GREEN}    - ReDoc:  http://127.0.0.1:8800/redoc${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════════════════${NC}"

# Firewall
echo -e "\n${YELLOW}Abriendo puerto 8800 en firewall...${NC}"
ufw allow 8800/tcp 2>/dev/null || true

echo -e "\n${GREEN}¡Listo!${NC}"
