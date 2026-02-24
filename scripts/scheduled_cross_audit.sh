#!/bin/bash
# Auditoría cruzada programada — cada 6 horas
# No tocar. Es independiente del pipeline.

LOG="/opt/odi/logs/cross_audit.log"
echo "$(date) — Auditoría cruzada programada iniciada" >> $LOG

# Auditar todas las empresas SRM con muestra de 10
curl -s -X POST http://localhost:8808/audit/all \
  -H "Content-Type: application/json" \
  -d '{"auditor":"scheduled","trigger_type":"scheduled","sample_size":10}' \
  >> $LOG 2>&1

echo "$(date) — Auditoría cruzada programada completada" >> $LOG
