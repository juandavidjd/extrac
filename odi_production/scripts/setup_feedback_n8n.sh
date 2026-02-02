#!/bin/bash
#===============================================================================
# ODI - Configurar Feedback Instantáneo con n8n
# Conecta el sistema de KB con n8n para feedback en tiempo real
#===============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ODI Feedback Loop - Configuración n8n                       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar n8n
echo -e "${YELLOW}Verificando n8n...${NC}"
if curl -s http://localhost:5678/healthz > /dev/null 2>&1; then
    echo -e "${GREEN}✓ n8n está corriendo en localhost:5678${NC}"
else
    echo -e "${RED}✗ n8n no responde. Verificar con: docker ps | grep n8n${NC}"
    exit 1
fi

# Verificar Redis
echo -e "${YELLOW}Verificando Redis...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis está corriendo${NC}"
else
    echo -e "${RED}✗ Redis no responde${NC}"
    exit 1
fi

# Crear workflow de feedback en n8n
echo -e "${YELLOW}Creando webhook de feedback en n8n...${NC}"

# El workflow JSON para importar en n8n
WORKFLOW_JSON=$(cat << 'WORKFLOW'
{
  "name": "ODI Feedback Loop",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "odi-feedback",
        "responseMode": "onReceived",
        "responseData": "allEntries"
      },
      "id": "webhook-feedback",
      "name": "Webhook Feedback",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300]
    },
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "odi-kb-indexed",
        "responseMode": "onReceived"
      },
      "id": "webhook-indexed",
      "name": "Webhook KB Indexed",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 500]
    },
    {
      "parameters": {
        "conditions": {
          "number": [
            {
              "value1": "={{ $json.data.rating }}",
              "operation": "smallerEqual",
              "value2": 2
            }
          ]
        }
      },
      "id": "check-rating",
      "name": "Check Low Rating",
      "type": "n8n-nodes-base.if",
      "position": [450, 300]
    },
    {
      "parameters": {
        "channel": "odi:feedback:low",
        "messageData": "={{ JSON.stringify($json) }}"
      },
      "id": "redis-alert",
      "name": "Redis Alert",
      "type": "n8n-nodes-base.redis",
      "position": [650, 200]
    },
    {
      "parameters": {
        "channel": "odi:feedback:all",
        "messageData": "={{ JSON.stringify($json) }}"
      },
      "id": "redis-log",
      "name": "Redis Log",
      "type": "n8n-nodes-base.redis",
      "position": [650, 400]
    }
  ],
  "connections": {
    "Webhook Feedback": {
      "main": [[{"node": "Check Low Rating", "type": "main", "index": 0}]]
    },
    "Check Low Rating": {
      "main": [
        [{"node": "Redis Alert", "type": "main", "index": 0}],
        [{"node": "Redis Log", "type": "main", "index": 0}]
      ]
    }
  }
}
WORKFLOW
)

# Guardar workflow
WORKFLOW_FILE="/opt/odi/n8n/odi_feedback_workflow.json"
mkdir -p /opt/odi/n8n
echo "$WORKFLOW_JSON" > "$WORKFLOW_FILE"
echo -e "${GREEN}✓ Workflow guardado en $WORKFLOW_FILE${NC}"

# Configurar suscriptor Redis para feedback
echo -e "${YELLOW}Configurando suscriptor Redis...${NC}"

cat > /opt/odi/scripts/redis_feedback_subscriber.py << 'PYSCRIPT'
#!/usr/bin/env python3
"""
Suscriptor Redis para feedback de ODI
Escucha eventos y puede disparar acciones
"""
import redis
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def main():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    pubsub = r.pubsub()

    # Suscribirse a canales
    pubsub.subscribe('odi:kb:indexed', 'odi:feedback:low', 'odi:feedback:all')

    logger.info("Escuchando eventos de feedback...")

    for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel']
            try:
                data = json.loads(message['data'])
            except:
                data = message['data']

            logger.info(f"[{channel}] {data}")

            # Acciones según canal
            if channel == 'odi:feedback:low':
                logger.warning(f"⚠️ RATING BAJO DETECTADO: {data}")
                # Aquí puedes agregar: enviar email, notificar Slack, etc.

            elif channel == 'odi:kb:indexed':
                logger.info(f"📚 Documento indexado: {data.get('file', 'unknown')}")

if __name__ == "__main__":
    main()
PYSCRIPT

chmod +x /opt/odi/scripts/redis_feedback_subscriber.py
echo -e "${GREEN}✓ Suscriptor Redis creado${NC}"

# Crear servicio systemd para el suscriptor
echo -e "${YELLOW}Creando servicio systemd...${NC}"

cat > /etc/systemd/system/odi-feedback-subscriber.service << 'SERVICE'
[Unit]
Description=ODI Feedback Redis Subscriber
After=network.target redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/odi
ExecStart=/usr/bin/python3 /opt/odi/scripts/redis_feedback_subscriber.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
echo -e "${GREEN}✓ Servicio systemd creado${NC}"

# Mostrar instrucciones
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Feedback Loop Configurado!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Webhooks disponibles en n8n:${NC}"
echo -e "  POST http://localhost:5678/webhook/odi-feedback"
echo -e "  POST http://localhost:5678/webhook/odi-kb-indexed"
echo ""
echo -e "${YELLOW}Para iniciar el suscriptor:${NC}"
echo -e "  ${BLUE}systemctl start odi-feedback-subscriber${NC}"
echo -e "  ${BLUE}systemctl enable odi-feedback-subscriber${NC}"
echo ""
echo -e "${YELLOW}Para probar:${NC}"
echo -e "  ${BLUE}redis-cli PUBLISH odi:feedback:low '{\"rating\": 1, \"query\": \"test\"}'${NC}"
echo ""
echo -e "${YELLOW}Ver logs:${NC}"
echo -e "  ${BLUE}journalctl -u odi-feedback-subscriber -f${NC}"
echo ""
