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
RED='\033[0;31m'
NC='\033[0m'

ODI_HOME="/opt/odi"

# Detectar directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Si no existe odi_production, usar /tmp/extrac
if [ ! -d "$REPO_DIR/odi_production" ]; then
    if [ -d "/tmp/extrac/odi_production" ]; then
        REPO_DIR="/tmp/extrac"
    else
        echo -e "${RED}Error: No se encontro odi_production en $REPO_DIR ni en /tmp/extrac${NC}"
        exit 1
    fi
fi

echo "Usando repositorio: $REPO_DIR"

# 1. Crear estructura
echo -e "${YELLOW}[1/8] Creando estructura de directorios...${NC}"
mkdir -p $ODI_HOME/{core,scripts,services,data,logs,kb_cache,n8n}
mkdir -p $ODI_HOME/data/{business_jobs,pipeline_jobs}
touch $ODI_HOME/logs/.gitkeep

# 2. Copiar archivos Python
echo -e "${YELLOW}[2/8] Copiando archivos ODI core...${NC}"
cp "$REPO_DIR/odi_production/core/"*.py $ODI_HOME/core/ 2>/dev/null || echo "Warning: No .py files in core"

# 3. Copiar extractors si existen
if [ -d "$REPO_DIR/odi_production/extractors" ]; then
    echo -e "${YELLOW}[3/8] Copiando extractors...${NC}"
    mkdir -p $ODI_HOME/extractors
    cp "$REPO_DIR/odi_production/extractors/"*.py $ODI_HOME/extractors/ 2>/dev/null || true
else
    echo -e "${YELLOW}[3/8] No hay extractors para copiar${NC}"
fi

# 4. Copiar n8n workflows
echo -e "${YELLOW}[4/8] Copiando workflows n8n...${NC}"
if [ -d "$REPO_DIR/odi_production/n8n" ]; then
    cp "$REPO_DIR/odi_production/n8n/"* $ODI_HOME/n8n/ 2>/dev/null || true
fi

# 5. Instalar dependencias
echo -e "${YELLOW}[5/8] Instalando dependencias Python...${NC}"
pip3 install --quiet --upgrade pip 2>/dev/null || true
pip3 install --quiet langchain langchain-openai langchain-community langchain-text-splitters chromadb 2>/dev/null || true
pip3 install --quiet pdfplumber pdf2image fastapi uvicorn httpx 2>/dev/null || true
pip3 install --quiet watchdog python-dotenv pydantic openai 2>/dev/null || true

# 6. Crear servicios systemd
echo -e "${YELLOW}[6/8] Creando servicios systemd...${NC}"

# KB Daemon
cat > /etc/systemd/system/odi-kb-daemon.service << 'EOFSERVICE'
[Unit]
Description=ODI KB Daemon - Auto-indexa documentos
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/odi/core
ExecStart=/usr/bin/python3 /opt/odi/core/odi_kb_daemon.py
Restart=always
RestartSec=30
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:/opt/odi/logs/kb_daemon.log
StandardError=append:/opt/odi/logs/kb_daemon_error.log
MemoryMax=1G

[Install]
WantedBy=multi-user.target
EOFSERVICE

# Cortex Query
cat > /etc/systemd/system/odi-cortex-query.service << 'EOFSERVICE'
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
StandardOutput=append:/opt/odi/logs/cortex_query.log
StandardError=append:/opt/odi/logs/cortex_query_error.log
MemoryMax=1G

[Install]
WantedBy=multi-user.target
EOFSERVICE

# Pipeline Service
cat > /etc/systemd/system/odi-pipeline-service.service << 'EOFSERVICE'
[Unit]
Description=ODI Pipeline Service - 6 pasos catalogo a Shopify
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/odi/core
ExecStart=/usr/bin/python3 -m uvicorn odi_pipeline_service:app --host 0.0.0.0 --port 8804
Restart=always
RestartSec=30
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:/opt/odi/logs/pipeline_service.log
StandardError=append:/opt/odi/logs/pipeline_service_error.log
MemoryMax=2G

[Install]
WantedBy=multi-user.target
EOFSERVICE

# Business Daemon
cat > /etc/systemd/system/odi-business-daemon.service << 'EOFSERVICE'
[Unit]
Description=ODI Business Daemon - Watcher de catalogos
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/odi/core
ExecStart=/usr/bin/python3 /opt/odi/core/odi_business_daemon.py
Restart=always
RestartSec=30
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:/opt/odi/logs/business_daemon.log
StandardError=append:/opt/odi/logs/business_daemon_error.log
MemoryMax=512M

[Install]
WantedBy=multi-user.target
EOFSERVICE

# 7. Habilitar e iniciar servicios
echo -e "${YELLOW}[7/8] Habilitando servicios...${NC}"
systemctl daemon-reload
systemctl enable odi-kb-daemon 2>/dev/null || true
systemctl enable odi-cortex-query 2>/dev/null || true
systemctl enable odi-pipeline-service 2>/dev/null || true
systemctl enable odi-business-daemon 2>/dev/null || true

# 8. Iniciar servicios
echo -e "${YELLOW}[8/8] Iniciando servicios...${NC}"
systemctl restart odi-kb-daemon 2>/dev/null || echo "Warning: kb-daemon failed to start"
sleep 2
systemctl restart odi-cortex-query 2>/dev/null || echo "Warning: cortex-query failed to start"
sleep 2
systemctl restart odi-pipeline-service 2>/dev/null || echo "Warning: pipeline-service failed to start"
sleep 1
systemctl restart odi-business-daemon 2>/dev/null || echo "Warning: business-daemon failed to start"

echo ""
echo "============================================"
echo -e "${GREEN}ODI Ecosystem Deployed!${NC}"
echo "============================================"
echo ""
echo "Verificar servicios:"
echo "  systemctl status odi-kb-daemon"
echo "  systemctl status odi-cortex-query"
echo "  systemctl status odi-pipeline-service"
echo "  systemctl status odi-business-daemon"
echo ""
echo "Health checks:"
echo "  curl http://localhost:8803/health"
echo "  curl http://localhost:8804/health"
echo ""
echo "Logs:"
echo "  tail -f /opt/odi/logs/*.log"
echo ""
