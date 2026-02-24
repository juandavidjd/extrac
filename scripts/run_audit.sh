#!/bin/bash
# ODI Cross-Audit Runner v2.0
# Carga variables de entorno y ejecuta auditoria automatica

set -e

# Cargar OPENAI_API_KEY desde .env
export OPENAI_API_KEY=$(grep OPENAI_API_KEY /opt/odi/.env | cut -d= -f2)

# Ejecutar auditoria
cd /opt/odi
/usr/bin/python3 /opt/odi/scripts/cross_audit.py
