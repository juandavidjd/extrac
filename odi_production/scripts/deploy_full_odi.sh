#!/bin/bash
# ============================================
# ODI Full Ecosystem Deployment
# ============================================
# Despliega todos los servicios ODI:
# - KB Daemon v2 (multi-lobe indexing)
# - Cortex Query API (port 8803)
# - Pipeline Service (port 8804)
# - Business Daemon (catalog watcher)
# ============================================

set -e

echo "============================================"
echo "ODI Full Ecosystem Deployment"
echo "============================================"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ODI_HOME="/opt/odi"
REPO_URL="https://github.com/juandavidjd/extrac.git"
BRANCH="claude/analyze-repository-9qwGC"

# 1. Crear estructura
echo -e "${YELLOW}[1/7] Creando estructura de directorios...${NC}"
mkdir -p $ODI_HOME/{core,scripts,services,data,logs,kb_cache}
mkdir -p $ODI_HOME/data/{business_jobs,pipeline_jobs}

# 2. Actualizar codigo
echo -e "${YELLOW}[2/7] Actualizando codigo desde repositorio...${NC}"
cd /tmp
rm -rf extrac_deploy
git clone --depth 1 -b $BRANCH $REPO_URL extrac_deploy

# 3. Copiar archivos
echo -e "${YELLOW}[3/7] Copiando archivos ODI...${NC}"
cp extrac_deploy/odi_production/core/*.py $ODI_HOME/core/
cp extrac_deploy/odi_production/scripts/*.sh $ODI_HOME/scripts/ 2>/dev/null || true
chmod +x $ODI_HOME/scripts/*.sh 2>/dev/null || true

# 4. Instalar dependencias
echo -e "${YELLOW}[4/7] Instalando dependencias Python...${NC}"
pip3 install --quiet \
    langchain langchain-openai langchain-community langchain-text-splitters \
    chromadb pdfplumber pdf2image \
    fastapi uvicorn httpx \
    watchdog python-dotenv pydantic \
    openai 2>/dev/null || true

# 5. Instalar servicios systemd
echo -e "${YELLOW}[5/7] Instalando servicios systemd...${NC}"
cp extrac_deploy/odi_production/services/*.service /etc/systemd/system/
systemctl daemon-reload

# 6. Habilitar servicios
echo -e "${YELLOW}[6/7] Habilitando servicios...${NC}"
systemctl enable odi-kb-daemon
systemctl enable odi-cortex-query 2>/dev/null || true
systemctl enable odi-pipeline-service
systemctl enable odi-business-daemon

# 7. Iniciar servicios
echo -e "${YELLOW}[7/7] Iniciando servicios...${NC}"
systemctl restart odi-kb-daemon
sleep 2

# Cortex Query en puerto 8803
cat > /etc/systemd/system/odi-cortex-query.service << 'EOF'
[Unit]
Description=ODI Cortex Query - API RAG multi-lobulo
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/odi/core
ExecStart=/usr/bin/python3 -m uvicorn odi_cortex_query:app --host 0.0.0.0 --port 8803
Restart=always
RestartSec=30
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:/opt/odi/logs/cortex_query_stdout.log
StandardError=append:/opt/odi/logs/cortex_query_stderr.log
MemoryMax=1G

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl restart odi-cortex-query
systemctl restart odi-pipeline-service
systemctl restart odi-business-daemon

# Limpiar
rm -rf /tmp/extrac_deploy

echo ""
echo "============================================"
echo -e "${GREEN}ODI Ecosystem Deployed!${NC}"
echo "============================================"
echo ""
echo "Servicios activos:"
echo "  - KB Daemon:        systemctl status odi-kb-daemon"
echo "  - Cortex Query:     http://localhost:8803"
echo "  - Pipeline Service: http://localhost:8804"
echo "  - Business Daemon:  watching /profesion/10 empresas..."
echo ""
echo "Logs:"
echo "  - tail -f /opt/odi/logs/*.log"
echo ""
echo "APIs:"
echo "  - curl http://localhost:8803/health"
echo "  - curl http://localhost:8804/health"
echo "  - curl http://localhost:8803/stats"
echo "  - curl http://localhost:8804/stores"
echo ""
