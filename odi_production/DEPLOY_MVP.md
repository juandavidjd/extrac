# ODI MVP Deployment - Kaiqi Pilot

## Sistema Completo

ODI ahora tiene 4 servicios que trabajan juntos:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ODI PRODUCTION SYSTEM                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  KB Daemon v2          Cortex Query         Pipeline Service    │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐     │
│  │ /profesion  │──────│ POST /query │      │ POST /start │     │
│  │ /kb/IND_MOTOS│      │ Tony/Ramona │      │ 6 pasos     │     │
│  └─────────────┘      └─────────────┘      └─────────────┘     │
│        ↓                   :8803                :8804           │
│   Vector Stores                                   ↑             │
│                                                   │             │
│  Business Daemon ─────────────────────────────────┘             │
│  ┌─────────────────────────────────────────────┐               │
│  │ Watch: /10 empresas ecosistema ODI/Data/    │               │
│  │ Detect: PDF, XLSX, CSV                      │               │
│  │ Trigger: Pipeline automático                │               │
│  └─────────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment en Servidor

### 1. Ejecutar deployment completo

```bash
# En el servidor (SSH root@64.23.170.118)

# Clonar y ejecutar
cd /tmp
git clone -b claude/analyze-repository-9qwGC https://github.com/juandavidjd/extrac.git
chmod +x extrac/odi_production/scripts/deploy_full_odi.sh
bash extrac/odi_production/scripts/deploy_full_odi.sh
```

### 2. Verificar servicios

```bash
# Estado de servicios
systemctl status odi-kb-daemon
systemctl status odi-cortex-query
systemctl status odi-pipeline-service
systemctl status odi-business-daemon

# Health checks
curl http://localhost:8803/health
curl http://localhost:8804/health

# Stats
curl http://localhost:8803/stats
curl http://localhost:8804/stores
```

### 3. Configurar Shopify (en .env)

```bash
# Editar /opt/odi/.env y agregar:

# Kaiqi (Piloto)
KAIQI_SHOP=tu-tienda-kaiqi.myshopify.com
KAIQI_TOKEN=***REMOVED***xxxxxxxxxxxxx

# Resto de tiendas cuando estén listas...
```

## Test Kaiqi End-to-End

### 1. Verificar estructura de datos

```bash
ls -la "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Kaiqi/"
ls -la "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Imagenes/Kaiqi/"
```

### 2. Procesar catálogo manualmente (test)

```bash
# Copiar un PDF de prueba
cp /path/to/kaiqi-catalogo.pdf "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Kaiqi/"

# El Business Daemon detectará automáticamente y disparará el pipeline
# Ver logs:
tail -f /opt/odi/logs/business_daemon.log
```

### 3. Verificar jobs

```bash
# Ver jobs en pipeline
curl http://localhost:8804/pipeline/jobs | jq

# Ver estado de un job específico
curl http://localhost:8804/pipeline/status/{job_id} | jq
```

### 4. Consultar KB

```bash
# Query al Cortex
curl -X POST http://localhost:8803/query \
  -H "Content-Type: application/json" \
  -d '{"question": "qué piezas hay para Pulsar 200?"}'
```

## Flujo Automático

Una vez configurado:

1. **Usuario sube PDF** a `/Data/Kaiqi/`
2. **Business Daemon detecta** el nuevo archivo
3. **Crea Job** y lo envía al Pipeline Service
4. **Pipeline ejecuta 6 pasos**:
   - Extraer productos con Vision AI
   - Normalizar nombres/categorías
   - Enriquecer con descripciones SEO
   - Asignar fitment (compatibilidad)
   - Subir a Shopify
   - (Próximo: Generar campañas)
5. **Productos aparecen en Shopify** automáticamente

## Monitoreo

```bash
# Logs en tiempo real
tail -f /opt/odi/logs/*.log

# Memoria
free -h

# Procesos ODI
ps aux | grep odi

# Disk usage embeddings
du -sh /mnt/volume_sfo3_01/embeddings/*
```

## Troubleshooting

### Pipeline no procesa
```bash
# Verificar Pipeline Service
systemctl status odi-pipeline-service
journalctl -u odi-pipeline-service -f
```

### Catálogos no detectados
```bash
# Verificar Business Daemon
systemctl status odi-business-daemon
journalctl -u odi-business-daemon -f

# Verificar path
ls -la "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/"
```

### Error de memoria
```bash
# Reiniciar servicios
systemctl restart odi-pipeline-service
systemctl restart odi-business-daemon
```

## Próximos Pasos

1. [ ] Configurar tokens Shopify en .env
2. [ ] Test con catálogo Kaiqi real
3. [ ] Verificar productos en Shopify
4. [ ] Configurar resto de tiendas
5. [ ] Activar módulo de Campañas (Meta/Google)
