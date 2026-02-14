# ODI - Ecosistema de Tiendas Shopify

## Servidor: 64.23.170.118 | Usuario: root | liveodi.com

### ORDEN MAESTRA v6 - 15,016 productos (13 Feb 2026)

| Tienda | Productos | Precio | Imagen | Shop |
|--------|-----------|--------|--------|------|
| DFG | 7,445 | 100% | 52% | 0se1jt-q1.myshopify.com |
| OH_IMPORTACIONES | 1,414 | 100% | 0% | 6fbakq-sj.myshopify.com |
| BARA | 698 | 100% | 100% | 4jqcki-jq.myshopify.com |
| DUNA | 1,200 | 0% | 100% | ygsfhq-fs.myshopify.com |
| IMBRA | 1,131 | 98% | 98% | 0i1mdf-gi.myshopify.com |
| YOKOMAR | 1,000 | 37% | 100% | u1zmhk-ts.myshopify.com |
| JAPAN | 734 | 0% | 98% | 7cy1zd-qz.myshopify.com |
| ARMOTOS | 377 | 97% | 0% | znxx5p-10.myshopify.com |
| MCLMOTOS | 349 | 97% | 0% | v023qz-8x.myshopify.com |
| CBI | 227 | 0% | 80% | yrf6hp-f6.myshopify.com |
| KAIQI | 138 | 79% | 100% | u03tqc-0e.myshopify.com |
| LEO | 120 | 0% | 100% | h1hywg-pq.myshopify.com |
| VITTON | 67 | 79% | 0% | hxjebc-it.myshopify.com |
| STORE | 66 | 0% | 86% | 0b6umv-11.myshopify.com |
| VAISAND | 50 | 0% | 100% | z4fpdj-mz.myshopify.com |

**JSONs listos:** `/opt/odi/data/orden_maestra_v6/`

### Pipeline SRM v6 (Orden Maestra)
- Script: `/opt/odi/scripts/process_stores_v6.py`
- Fuzzy image matching por titulo (DFG 3%->52%)
- Vision JSON parsing (variants, images arrays)
- CSV priority: Base_Datos_ > catalogo_imagenes_

## API ODI v2.2-sovereign - https://odi.larocamotorepuestos.com

| Endpoint | Funcion |
|----------|---------|
| /v1/webhook/whatsapp | GET: Verificacion Meta, POST: Recibir mensajes |
| /v1/webhook/whatsapp/test | POST: ?phone=...&message=...&provider=claude |
| /v1/webhook/whatsapp/status | GET: Estado + LLM providers |

## LLM Failover v1.0 (14 Feb 2026)
**Modulo:** `/opt/odi/core/llm_failover.py`
**Cadena:** `Gemini 2.0 Flash → GPT-4o → Claude Sonnet → Groq Llama 3.3 → Lobotomy`

| Provider | Modelo | Latencia | Status |
|----------|--------|----------|--------|
| Groq | llama-3.3-70b-versatile | ~760ms | OK (mas rapido) |
| Gemini | gemini-2.0-flash | ~3500ms | OK |
| OpenAI | gpt-4o | ~5700ms | OK |
| Claude | claude-sonnet-4-20250514 | ~7000ms | OK |
| Lobotomy | respuestas predefinidas | 0ms | Fallback emergencia |

**Uso Python:**
```python
from core.llm_failover import LLMFailover, Provider
llm = LLMFailover()
response = llm.generate("pregunta")
response = llm.generate("pregunta", preferred_provider=Provider.CLAUDE)
response = llm.generate_with_image("prompt", image_b64)
```

**CLI Test:**
```bash
python3 /opt/odi/core/llm_failover.py test  # Test todos los providers
python3 /opt/odi/core/llm_failover.py "tu pregunta"
```

**WhatsApp Handler:** `/opt/odi/core/whatsapp_routes.py` (integrado en odi-api)

## ODI VENDE v3.8 | RADAR v3.0 | Intent Gate v1.3
- Orquestador: `/opt/odi/core/odi_core.py`
- RADAR: 9 disciplinas (Bayesian, Markov, Graph, MonteCarlo, Anomaly, Sentiment, Funnel, Wavelet, Topology)

## PAEM API v2.2.1 - Metabolismo Economico (14 Feb 2026)
**Servicio:** `odi-paem-api` (systemd) | Puerto: 8807 | PG: 172.18.0.4

| Endpoint | Funcion |
|----------|---------|
| https://api.liveodi.com/paem/pay/init | Iniciar pago Wompi |
| https://api.liveodi.com/webhooks/wompi | Webhook confirmacion |
| http://127.0.0.1:8807/health | Health check local |

**Tablas PostgreSQL:**
- `odi_payments` - Transacciones de pago
- `odi_health_bookings` - Reservas turismo salud
- `odi_health_nodes` - Clinicas/nodos de salud
- `odi_health_certifications` - Certificaciones
- `odi_events` - Audit trail
- `odi_reconciliation_reports` - Reportes V006 (auditoría financiera)

**V006 Reconciliation:** Detecta orphans, cierra HOLDs expirados, shadow accounting

**Migraciones:** `/opt/odi/data/turismo/migrations/V001-V006`

### Flujo Webhook Wompi
```
1. pay/init → PENDING/HOLD + checkout URL
2. Usuario paga en Wompi
3. Wompi POST /webhooks/wompi (firma HMAC)
4. Validar: SHA256(timestamp + body + WOMPI_EVENTS_KEY)
5. fn_odi_confirm_payment() → CAPTURED/CONFIRMED
6. Evento PAEM.PAYMENT_SUCCESS en odi_events
```

**Headers requeridos:**
- `x-event-checksum`: SHA256 hex
- `x-event-timestamp`: Unix timestamp

**Test webhook con firma:**
```bash
python3 << 'PY'
import hashlib, json, time, subprocess
SECRET = "prod_events_..."  # WOMPI_EVENTS_KEY
ts = str(int(time.time()))
body = json.dumps({"event":"transaction.updated","data":{"transaction":{"reference":"TX-CASE-001","status":"APPROVED"}}})
sig = hashlib.sha256(f"{ts}{body}{SECRET}".encode()).hexdigest()
subprocess.run(["curl","-s","-X","POST","http://127.0.0.1:8807/webhooks/wompi",
  "-H","Content-Type: application/json","-H",f"x-event-checksum: {sig}","-H",f"x-event-timestamp: {ts}","-d",body])
PY
```

## P2 SALUD v1.6 - Turismo Dental
| Procedimiento | USD | Ahorro vs USA |
|---------------|-----|---------------|
| Diseno sonrisa | $2,800-$5,500 | 70-80% |
| Implantes | $800-$2,000 | 70-80% |
| Carillas | $250-$450/u | 70-80% |

## Infraestructura
- **Dominios:** liveodi.com, ws.liveodi.com (:8765), api.liveodi.com (:8800 + :8807/paem)
- **Puertos:** 8800 (WhatsApp API), 8807 (PAEM), 8765 (WebSocket), 6379 (Redis)
- **PostgreSQL:** Docker `odi-postgres` @ 172.18.0.4:5432 | User: odi
- **WhatsApp:** Phone ID 969496722915650 | Verify: odi_whatsapp_verify_2026
- **Voz:** ElevenLabs Ramona (ZAQFLZQOmS9ClDGyVg6d)
- **LLM:** Gemini → GPT-4o → Claude Sonnet → Groq → Lobotomy (ver LLM Failover v1.0)
- **Backups:** GPG AES256, 3AM diario, 30 dias, `/opt/odi/backups/daily/`

## Comandos Utiles
```bash
ssh root@64.23.170.118
systemctl restart odi-api
systemctl restart odi-paem-api

# Test PAEM
curl -X POST https://api.liveodi.com/paem/pay/init -H "Content-Type: application/json" \
  -d '{"transaction_id":"TX-TEST","booking_id":"BKG-TEST","deposit_amount_cop":5000}'

# Forensic audit
bash /opt/odi/scripts/forensic_audit_case001.sh

# Reconciliación financiera V006
bash /opt/odi/scripts/run_reconciliation.sh

# Backup PostgreSQL (manual)
bash /opt/odi/scripts/backup_postgres.sh

# Restore PostgreSQL
bash /opt/odi/scripts/restore_postgres.sh /opt/odi/backups/daily/<archivo>.sql.gpg

# Test WhatsApp (default: Gemini)
curl -X POST 'http://localhost:8800/v1/webhook/whatsapp/test?phone=573001234567&message=llanta%20bws'

# Test WhatsApp forzando Claude
curl -X POST 'http://localhost:8800/v1/webhook/whatsapp/test?phone=573001234567&message=llanta%20bws&provider=claude'

# Test LLM Failover (todos los providers)
python3 /opt/odi/core/llm_failover.py test

# Auditoría inventario P1
python3 /opt/odi/scripts/inventory_audit_p1.py --store DFG

# Auditoría todas las tiendas
for s in ARMOTOS BARA CBI DFG DUNA IMBRA JAPAN KAIQI LEO MCLMOTOS OH_IMPORTACIONES STORE VAISAND VITTON YOKOMAR; do
  python3 /opt/odi/scripts/inventory_audit_p1.py --store $s
done
```

## GitHub
- Repo: https://github.com/juandavidjd/odi-vende

## Auditoría Inventario P1 (14 Feb 2026)
**Total: 15,658 productos | 481 listos (3.1%) | NAV: $2,616M COP**

| Tienda | Prod | Listos | NAV Draft (COP) | Bloqueador |
|--------|------|--------|-----------------|------------|
| DFG | 7,441 | 0 | 0 | Sin imagen |
| OH_IMPORTACIONES | 1,387 | 0 | 1,751M | Sin imagen |
| DUNA | 1,200 | 0 | 0 | Sin precio/img |
| IMBRA | 1,131 | 0 | 0 | - |
| ARMOTOS | 1,050 | 0 | 212M | - |
| YOKOMAR | 1,000 | 372 | 163M | - |
| JAPAN | 734 | 0 | 0 | Sin precio/img |
| BARA | 698 | 0 | 487M | - |
| MCLMOTOS | 349 | 0 | 0 | Sin imagen |
| CBI | 227 | 0 | 0 | Sin precio/img |
| KAIQI | 138 | 109 | 0 | - |
| LEO | 120 | 0 | 0 | Sin precio/img |
| VITTON | 67 | 0 | 0 | Sin imagen |
| STORE | 66 | 0 | 0 | Sin precio/img |
| VAISAND | 50 | 0 | 0 | Sin precio/img |

**Funcionales:** YOKOMAR (37%), KAIQI (79%)
**Script:** `python3 /opt/odi/scripts/inventory_audit_p1.py --store <TIENDA>`
**Reportes:** `/opt/odi/data/reports/p1_audit_summary_<tienda>.json`

## LOGRO 14 Feb 2026: LLM Failover + WhatsApp Handler
- Modulo `llm_failover.py`: cadena Gemini → GPT-4o → Claude → Groq → Lobotomy
- WhatsApp handler integrado con LLM failover en odi-api
- Todos los providers testeados y funcionando
- Endpoint `/v1/webhook/whatsapp/test?provider=X` para forzar provider

## LOGRO 14 Feb 2026: PAEM API v2.2.1 + Auditoría P1
- Servicio systemd `odi-paem-api` en :8807
- Nginx SSL: api.liveodi.com/paem/* + /webhooks/*
- PostgreSQL recuperado + migraciones V001-V006
- Webhook Wompi: firma HMAC SHA256 validada
- Auditoría P1: 15 tiendas escaneadas, NAV $2,616M COP
- Scripts: forensic_audit, backup_postgres, restore_postgres, inventory_audit_p1

## LOGRO 13 Feb 2026: ORDEN MAESTRA v6 COMPLETADA
- **15,016 productos** en 15 tiendas (JSONs listos)
- Fuzzy matching: DFG imagen 3%->52%
- Vision parsing: ARMOTOS/MCLMOTOS precio 0%->97%

## Pendientes
- Configurar URL webhook en panel Wompi produccion: `https://api.liveodi.com/webhooks/wompi`
- Aprobar JSONs y subir a Shopify
- Integrar LLM Failover en otros servicios (Pipeline, Cortex)
