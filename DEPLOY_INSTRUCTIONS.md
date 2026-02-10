# Deploy Intent Override Gate — Instrucciones Completas

**Fecha:** 10 Febrero 2026
**Servidor:** 64.23.170.118
**Objetivo:** Corregir el bug "Para tu ECO" en ODI

---

## Pre-Requisitos

- [ ] Acceso SSH a `root@64.23.170.118`
- [ ] Archivo `intent_override_gate.py` disponible
- [ ] Archivo `N8N_CORTEX_PATCH.md` leído

---

## Paso 1: Conectar al Servidor

```bash
ssh root@64.23.170.118
```

---

## Paso 2: Crear Directorio de Scripts

```bash
mkdir -p /opt/odi/scripts
chmod 755 /opt/odi/scripts
```

---

## Paso 3: Subir el Módulo Python

**Opción A: Desde tu máquina local**
```bash
scp intent_override_gate.py root@64.23.170.118:/opt/odi/scripts/
```

**Opción B: Crear directamente en el servidor**
```bash
cat > /opt/odi/scripts/intent_override_gate.py << 'PYEOF'
# [Pegar aquí el contenido completo de intent_override_gate.py]
PYEOF
```

---

## Paso 4: Verificar Tests

```bash
cd /opt/odi/scripts
python3 intent_override_gate.py
```

**Resultado esperado:**
```
======================================================================
INTENT OVERRIDE GATE — TEST SUITE
======================================================================

Test 1: ✅ PASS
Test 2: ✅ PASS
Test 3: ✅ PASS
Test 4: ✅ PASS
Test 5: ✅ PASS
Test 6: ✅ PASS
Test 7: ✅ PASS

======================================================================
RESULTADOS: 7 passed, 0 failed
======================================================================

✅ TODOS LOS TESTS PASARON. Listo para deploy.
```

---

## Paso 5: Backup de n8n

```bash
# Crear directorio de backup
BACKUP_DIR="/opt/odi/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Exportar workflows actuales
docker exec odi-n8n n8n export:workflow --all --output=/tmp/backup.json
docker cp odi-n8n:/tmp/backup.json $BACKUP_DIR/workflows_backup.json

echo "Backup creado en: $BACKUP_DIR"
```

---

## Paso 6: Configurar n8n (SHADOW FLOW)

### 6.1 Abrir n8n
```
URL: https://odi.larocamotorepuestos.com:5678
```

### 6.2 Duplicar Workflow
1. Abrir `ODI_v6_CORTEX`
2. Click en menú (⋮) → "Duplicate"
3. Renombrar a: `ODI_v6_CORTEX_INTENT_OVERRIDE_SHADOW`

### 6.3 Agregar Nodo "Intent Override Gate"
1. Click derecho en el canvas → "Add node"
2. Buscar "Code"
3. Posicionar DESPUÉS del nodo Webhook
4. Conectar: `Webhook → Code → [resto del flujo]`

### 6.4 Configurar el Nodo Code
**Nombre:** `Intent Override Gate`
**Language:** JavaScript
**Código:** (copiar de `N8N_CORTEX_PATCH.md`)

```javascript
// [Pegar código JavaScript del N8N_CORTEX_PATCH.md]
```

### 6.5 Desactivar Respuesta (para Shadow)
1. Encontrar el nodo de "WhatsApp Response"
2. Click derecho → "Deactivate"
3. Esto hace que el shadow solo loguee, no responda

### 6.6 Activar Shadow Workflow
1. Click en el toggle "Active" (esquina superior derecha)
2. Verificar que esté verde

---

## Paso 7: Monitorear Shadow (24 horas)

```bash
# Ver logs en tiempo real
docker logs odi-n8n -f --tail 100

# Buscar eventos de override
docker logs odi-n8n 2>&1 | grep "intent_override"
```

**Qué buscar:**
- Eventos `intent_override_gate`
- Triggers detectados correctamente
- Sin errores JavaScript

---

## Paso 8: Aplicar a Producción

### ⚠️ SOLO después de validar shadow por 24 horas

### 8.1 Editar Workflow de Producción
1. Abrir `ODI_v6_CORTEX` (el original)
2. NO duplicar, editar directamente

### 8.2 Insertar Nodo Override Gate
1. Agregar nodo "Code" después del Webhook
2. Pegar el código de `N8N_CORTEX_PATCH.md`

### 8.3 Agregar Bifurcación
1. Agregar nodo "IF" después del Code
2. Condición: `{{ $json.override }} == true`
3. Rama TRUE → Nuevo nodo "WhatsApp Response (Override)"
4. Rama FALSE → Flujo normal existente

### 8.4 Configurar WhatsApp Response (Override)
**Tipo:** HTTP Request
**Método:** POST
**URL:** `https://graph.facebook.com/v17.0/{{$env.PHONE_NUMBER_ID}}/messages`
**Body:**
```json
{
  "messaging_product": "whatsapp",
  "to": "{{ $json.from }}",
  "type": "text",
  "text": {
    "body": "{{ $json.canonical_response }}"
  }
}
```

### 8.5 Guardar y Activar
1. Click "Save"
2. Verificar toggle "Active" está verde

---

## Paso 9: Verificación Post-Deploy

### Test 1: Mensaje normal de motos
```bash
curl -X POST https://odi.larocamotorepuestos.com/webhook/odi-ingest \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"573001234567","text":{"body":"Busco piñon para AKT 125"}}]}}]}]}'
```
**Esperado:** NO override, flujo normal

### Test 2: Emprendimiento
```bash
curl -X POST https://odi.larocamotorepuestos.com/webhook/odi-ingest \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"573001234567","text":{"body":"Quiero emprender un negocio"}}]}}]}]}'
```
**Esperado:** Override P1, respuesta de emprendimiento

### Test 3: Urgencia
```bash
curl -X POST https://odi.larocamotorepuestos.com/webhook/odi-ingest \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"573001234567","text":{"body":"Llama a la policia urgencia"}}]}}]}]}'
```
**Esperado:** Override P0, respuesta de seguridad

---

## Rollback (si algo falla)

```bash
# Restaurar backup
docker cp /opt/odi/backups/[FECHA]/workflows_backup.json odi-n8n:/tmp/
docker exec odi-n8n n8n import:workflow --input=/tmp/workflows_backup.json

# Reiniciar n8n
docker restart odi-n8n

# Verificar
docker logs odi-n8n --tail 50
```

---

## Checklist Final

- [ ] Tests Python: 7/7 PASS
- [ ] Backup de workflows creado
- [ ] Shadow flow creado y activo
- [ ] Shadow monitoreado por 24h
- [ ] Producción actualizada
- [ ] Tests post-deploy ejecutados
- [ ] Logs verificados por errores

---

## Contacto de Emergencia

Si algo falla durante el deploy:
1. Ejecutar rollback inmediatamente
2. Verificar que WhatsApp sigue funcionando
3. Revisar logs: `docker logs odi-n8n --tail 100`

---

*"ODI responde por intención, no por industria."*
