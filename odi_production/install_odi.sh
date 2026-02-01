#!/bin/bash
#===============================================================================
# ODI INSTALLER - Organismo Digital Industrial
# Instala y configura ODI en /opt/odi/ para procesamiento de KB desde servidor
#===============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuracion
ODI_HOME="/opt/odi"
ODI_USER="odi"
PYTHON_VERSION="3.10"
PROFESION_PATH="/mnt/volume_sfo3_01/profesion"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║     ██████╗ ██████╗ ██╗                                      ║"
echo "║    ██╔═══██╗██╔══██╗██║                                      ║"
echo "║    ██║   ██║██║  ██║██║                                      ║"
echo "║    ██║   ██║██║  ██║██║                                      ║"
echo "║    ╚██████╔╝██████╔╝██║                                      ║"
echo "║     ╚═════╝ ╚═════╝ ╚═╝                                      ║"
echo "║                                                               ║"
echo "║    Organismo Digital Industrial - Installer v1.0             ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

#-------------------------------------------------------------------------------
# Funciones
#-------------------------------------------------------------------------------

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Este script debe ejecutarse como root"
        exit 1
    fi
}

check_requirements() {
    log_info "Verificando requisitos del sistema..."

    # Verificar que el volumen existe
    if [ ! -d "$PROFESION_PATH" ]; then
        log_warn "Directorio $PROFESION_PATH no encontrado"
        log_info "Se creara cuando el volumen este montado"
    else
        local size=$(du -sh "$PROFESION_PATH" 2>/dev/null | cut -f1)
        local count=$(find "$PROFESION_PATH" -type f 2>/dev/null | wc -l)
        log_info "Encontrado: $PROFESION_PATH ($size, $count archivos)"
    fi

    # Verificar Python
    if ! command -v python3 &> /dev/null; then
        log_info "Instalando Python3..."
        apt-get update && apt-get install -y python3 python3-pip python3-venv
    fi

    log_info "Python version: $(python3 --version)"
}

install_system_deps() {
    log_info "Instalando dependencias del sistema..."

    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        redis-server \
        tesseract-ocr \
        tesseract-ocr-spa \
        poppler-utils \
        git \
        curl \
        jq \
        supervisor

    # Iniciar Redis
    systemctl enable redis-server
    systemctl start redis-server

    log_info "Dependencias del sistema instaladas"
}

create_odi_user() {
    log_info "Configurando usuario ODI..."

    if ! id "$ODI_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d "$ODI_HOME" "$ODI_USER"
        log_info "Usuario $ODI_USER creado"
    else
        log_info "Usuario $ODI_USER ya existe"
    fi
}

setup_directories() {
    log_info "Creando estructura de directorios..."

    mkdir -p "$ODI_HOME"/{config,core,services,scripts,data,logs,embeddings,cache}

    # Copiar archivos desde el directorio de instalacion
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    cp -r "$SCRIPT_DIR/config/"* "$ODI_HOME/config/" 2>/dev/null || true
    cp -r "$SCRIPT_DIR/core/"* "$ODI_HOME/core/" 2>/dev/null || true
    cp -r "$SCRIPT_DIR/scripts/"* "$ODI_HOME/scripts/" 2>/dev/null || true

    # Permisos
    chown -R "$ODI_USER:$ODI_USER" "$ODI_HOME"
    chmod +x "$ODI_HOME/scripts/"*.sh 2>/dev/null || true

    log_info "Directorios creados en $ODI_HOME"
}

setup_python_env() {
    log_info "Configurando entorno Python..."

    cd "$ODI_HOME"

    # Crear virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Instalar dependencias
    pip install --upgrade pip
    pip install \
        openai \
        anthropic \
        langchain \
        langchain-openai \
        langchain-community \
        chromadb \
        faiss-cpu \
        sentence-transformers \
        tiktoken \
        PyPDF2 \
        pdfplumber \
        python-docx \
        markdown \
        beautifulsoup4 \
        redis \
        fastapi \
        uvicorn \
        python-multipart \
        httpx \
        pydantic \
        pydantic-settings \
        python-dotenv \
        watchdog \
        rich \
        typer

    deactivate

    log_info "Entorno Python configurado"
}

create_env_file() {
    log_info "Creando archivo de configuracion..."

    if [ ! -f "$ODI_HOME/config/.env" ]; then
        cat > "$ODI_HOME/config/.env" << 'ENVFILE'
# ODI Configuration
# =================

# OpenAI API Key (requerido para embeddings)
OPENAI_API_KEY=sk-your-key-here

# Anthropic API Key (opcional, para Claude)
ANTHROPIC_API_KEY=

# Paths
ODI_HOME=/opt/odi
PROFESION_PATH=/mnt/volume_sfo3_01/profesion
EMBEDDINGS_PATH=/opt/odi/embeddings
CACHE_PATH=/opt/odi/cache
LOGS_PATH=/opt/odi/logs

# Embedding Configuration
EMBEDDING_MODEL=text-embedding-3-small
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Feedback Webhook (n8n, Systeme.io, etc.)
FEEDBACK_WEBHOOK_URL=
FEEDBACK_WEBHOOK_SECRET=

# Logging
LOG_LEVEL=INFO
ENVFILE

        chmod 600 "$ODI_HOME/config/.env"
        chown "$ODI_USER:$ODI_USER" "$ODI_HOME/config/.env"

        log_warn "Archivo .env creado. EDITA $ODI_HOME/config/.env con tus API keys"
    else
        log_info "Archivo .env ya existe"
    fi
}

install_systemd_services() {
    log_info "Instalando servicios systemd..."

    # ODI Indexer Service
    cat > /etc/systemd/system/odi-indexer.service << 'SERVICE'
[Unit]
Description=ODI Knowledge Base Indexer
After=network.target redis-server.service

[Service]
Type=simple
User=odi
Group=odi
WorkingDirectory=/opt/odi
Environment="PATH=/opt/odi/venv/bin"
EnvironmentFile=/opt/odi/config/.env
ExecStart=/opt/odi/venv/bin/python /opt/odi/core/odi_kb_indexer.py --watch
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

    # ODI Query API Service
    cat > /etc/systemd/system/odi-query.service << 'SERVICE'
[Unit]
Description=ODI Query API Server
After=network.target redis-server.service odi-indexer.service

[Service]
Type=simple
User=odi
Group=odi
WorkingDirectory=/opt/odi
Environment="PATH=/opt/odi/venv/bin"
EnvironmentFile=/opt/odi/config/.env
ExecStart=/opt/odi/venv/bin/uvicorn core.odi_kb_query:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

    # ODI Feedback Loop Service
    cat > /etc/systemd/system/odi-feedback.service << 'SERVICE'
[Unit]
Description=ODI Feedback Loop Processor
After=network.target redis-server.service

[Service]
Type=simple
User=odi
Group=odi
WorkingDirectory=/opt/odi
Environment="PATH=/opt/odi/venv/bin"
EnvironmentFile=/opt/odi/config/.env
ExecStart=/opt/odi/venv/bin/python /opt/odi/core/odi_feedback_loop.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

    # Recargar systemd
    systemctl daemon-reload

    log_info "Servicios systemd instalados"
}

print_next_steps() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ODI Instalado Exitosamente!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}SIGUIENTE PASO OBLIGATORIO:${NC}"
    echo -e "  1. Edita el archivo de configuracion:"
    echo -e "     ${BLUE}nano $ODI_HOME/config/.env${NC}"
    echo -e "     - Agrega tu OPENAI_API_KEY"
    echo -e "     - Configura FEEDBACK_WEBHOOK_URL (opcional)"
    echo ""
    echo -e "${YELLOW}LUEGO, EJECUTA:${NC}"
    echo -e "  2. Indexar el conocimiento de profesion:"
    echo -e "     ${BLUE}$ODI_HOME/scripts/index_profesion.sh${NC}"
    echo ""
    echo -e "  3. Iniciar los servicios:"
    echo -e "     ${BLUE}systemctl start odi-indexer${NC}"
    echo -e "     ${BLUE}systemctl start odi-query${NC}"
    echo -e "     ${BLUE}systemctl start odi-feedback${NC}"
    echo ""
    echo -e "  4. Habilitar inicio automatico:"
    echo -e "     ${BLUE}systemctl enable odi-indexer odi-query odi-feedback${NC}"
    echo ""
    echo -e "${YELLOW}VERIFICAR ESTADO:${NC}"
    echo -e "  ${BLUE}systemctl status odi-indexer${NC}"
    echo -e "  ${BLUE}systemctl status odi-query${NC}"
    echo -e "  ${BLUE}curl http://localhost:8000/health${NC}"
    echo ""
    echo -e "${YELLOW}LOGS:${NC}"
    echo -e "  ${BLUE}tail -f $ODI_HOME/logs/indexer.log${NC}"
    echo -e "  ${BLUE}journalctl -u odi-query -f${NC}"
    echo ""
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

main() {
    check_root
    check_requirements
    install_system_deps
    create_odi_user
    setup_directories
    setup_python_env
    create_env_file
    install_systemd_services
    print_next_steps
}

# Ejecutar
main "$@"
