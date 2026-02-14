# ODI Production Deployment Guide

## Despliegue Rapido

### 1. Copiar al servidor

```bash
# Desde tu maquina local
scp -r odi_production root@64.23.170.118:/tmp/

# En el servidor
ssh root@64.23.170.118
mv /tmp/odi_production /opt/odi_install
cd /opt/odi_install
```

### 2. Ejecutar instalador

```bash
chmod +x install_odi.sh
./install_odi.sh
```

### 3. Configurar API Key

```bash
nano /opt/odi/config/.env

# Agregar tu OpenAI API Key:
OPENAI_API_KEY=sk-tu-key-aqui

# Opcional: Configurar webhook para n8n
FEEDBACK_WEBHOOK_URL=https://tu-n8n.com/webhook/odi-feedback
```

### 4. Indexar contenido

```bash
/opt/odi/scripts/index_profesion.sh
```

### 5. Iniciar servicios

```bash
systemctl start odi-indexer
systemctl start odi-query
systemctl start odi-feedback

# Habilitar inicio automatico
systemctl enable odi-indexer odi-query odi-feedback
```

### 6. Verificar

```bash
/opt/odi/scripts/health_check.sh

# O manualmente:
curl http://localhost:8000/health
```

---

## Arquitectura

```
/opt/odi/
├── config/
│   ├── .env              # Variables de entorno (API keys)
│   └── odi_config.yaml   # Configuracion general
├── core/
│   ├── odi_kb_indexer.py    # Indexador de documentos
│   ├── odi_kb_query.py      # API de consultas RAG
│   └── odi_feedback_loop.py # Procesador de feedback
├── scripts/
│   ├── index_profesion.sh   # Script de indexacion
│   └── health_check.sh      # Verificacion de salud
├── embeddings/              # Vector store (ChromaDB)
├── cache/                   # Cache de hashes
├── logs/                    # Logs de servicios
├── data/                    # Datos adicionales
└── venv/                    # Entorno virtual Python
```

---

## Endpoints API

### Health Check
```bash
GET /health
```

### Consulta RAG
```bash
POST /query
Content-Type: application/json

{
  "question": "¿Como funciona el sistema de fitment?",
  "k": 5,
  "voice": "ramona",
  "include_sources": true
}
```

### Busqueda Semantica
```bash
POST /search
Content-Type: application/json

{
  "query": "compatibilidad motos",
  "k": 10
}
```

### Enviar Feedback
```bash
POST /feedback
Content-Type: application/json

{
  "query_id": "abc123",
  "rating": 5,
  "comment": "Excelente respuesta"
}
```

### Estadisticas
```bash
GET /stats
```

---

## Voces: Tony vs Ramona

| Voz | Personalidad | Uso |
|-----|--------------|-----|
| **Tony Maestro** | Tecnico, preciso, directo | Datos tecnicos, alertas, metricas, fitment |
| **Ramona Anfitriona** | Amigable, calida, cercana | Bienvenidas, consultas, errores, cierre |

Ejemplo con Tony:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Especificaciones del kit de arrastre", "voice": "tony"}'
```

---

## Integracion con n8n

### Webhook de Feedback

Configura en `.env`:
```
FEEDBACK_WEBHOOK_URL=https://tu-n8n.com/webhook/odi-feedback
FEEDBACK_WEBHOOK_SECRET=tu-secreto
```

El webhook recibe:
```json
{
  "type": "odi_feedback",
  "data": {
    "query_id": "abc123",
    "rating": 4,
    "comment": "Buena respuesta",
    "timestamp": "2026-02-01T12:00:00"
  }
}
```

### Eventos disponibles:

| Evento | Descripcion |
|--------|-------------|
| `odi_feedback` | Nuevo feedback recibido |
| `odi_indexed` | Documento indexado |
| `odi_alert` | Alerta (rating bajo, errores) |

---

## Comandos Utiles

### Reindexar todo
```bash
source /opt/odi/venv/bin/activate
python /opt/odi/core/odi_kb_indexer.py --reindex
```

### Ver logs en tiempo real
```bash
journalctl -u odi-query -f
tail -f /opt/odi/logs/indexer.log
```

### Ver metricas en Redis
```bash
redis-cli get odi:metrics | jq
redis-cli llen odi:queries
redis-cli llen odi:feedbacks
```

### Reiniciar servicios
```bash
systemctl restart odi-indexer odi-query odi-feedback
```

---

## Troubleshooting

### "OPENAI_API_KEY no configurada"
```bash
nano /opt/odi/config/.env
# Verifica que la key este correcta
```

### "Directorio profesion no existe"
```bash
# Verificar que el volumen este montado
ls -la /mnt/volume_sfo3_01/
mount | grep volume_sfo3_01
```

### "Redis no disponible"
```bash
systemctl status redis-server
systemctl start redis-server
```

### API no responde
```bash
systemctl status odi-query
journalctl -u odi-query -n 50
```

---

## Seguridad

1. **No expongas el puerto 8000 directamente a Internet**
   - Usa un reverse proxy (nginx) con HTTPS
   - Configura autenticacion

2. **Protege las API keys**
   ```bash
   chmod 600 /opt/odi/config/.env
   ```

3. **Configura firewall**
   ```bash
   ufw allow from 127.0.0.1 to any port 8000
   ```

---

## Siguiente Paso: Conectar con WhatsApp

Una vez que ODI KB este funcionando, el siguiente paso es conectar con WhatsApp via n8n:

1. n8n recibe mensaje de WhatsApp
2. n8n llama a `POST /query` con la pregunta
3. ODI responde con voz Ramona
4. n8n envia respuesta a WhatsApp
5. Usuario recibe respuesta humanizada

Este es el flujo completo del feedback instantaneo.
