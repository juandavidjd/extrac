# ODI V8.1 — Stress Test de Concurrencia
**Fecha:** 2026-02-14T08:14:37Z
**Servidor:** 64.23.170.118 (localhost)
**Endpoint:** POST /paem/pay/init (puerto 8807)
**Requests totales:** 50 por fase (100 total)
**Mix:** 30 VERDE + 20 ROJO por fase

---

## Fase 1: HTTP Stress Test (Full Stack)

50 requests concurrentes contra el endpoint PAEM real.
Nota: Todas pasan Guardian como VERDE (endpoint no envía precio_catalogo).
Resultado esperado: 404 (booking inexistente) tras pasar Guardian.

### Latencia

| Métrica | Valor |
|---------|-------|
| Promedio | 182.5 ms |
| P50 (mediana) | 182.8 ms |
| P95 | 196.0 ms |
| Min | 166.2 ms |
| Max | 196.3 ms |

### Status Codes

| Code | Count | Significado |
|------|-------|-------------|
| 404 | 50 | Booking no encontrado (esperado) |

### Errores

| Tipo | Count |
|------|-------|
| 5xx Server Error | 0 |
| Conexión rechazada | 0 |
| Otros errores | 0 |

---

## Fase 2: Engine Stress Test (Guardian + Logger Directo)

50 llamadas concurrentes directas al motor de personalidad + audit logger.
30 con contexto VERDE (ratio 1.25) + 20 con contexto ROJO (ratio 50x).
Prueba la concurrencia real de asyncpg pool + PostgreSQL INSERT.

### Latencia

| Métrica | Valor |
|---------|-------|
| Promedio | 104.4 ms |
| P50 (mediana) | 104.6 ms |
| P95 | 109.2 ms |
| Min | 95.1 ms |
| Max | 110.0 ms |

### Resultados Guardian

| Estado | Count |
|--------|-------|
| rojo | 20 |
| verde | 30 |

### Event IDs Capturados

| Fase | IDs generados |
|------|---------------|
| HTTP | 0 / 50 |
| Engine | 50 / 50 |

---

## Verificación PostgreSQL

| Métrica | Valor |
|---------|-------|
| Total registros insertados (stress) | 100 |
| Deadlocks detectados | 0 |
| Conexiones activas (odi) | 11 |

### Registros por estado_guardian

| Estado | Count |
|--------|-------|
| verde | 80 |
| rojo | 20 |

### Registros por intent

| Intent | Count |
|--------|-------|
| PAY_INIT_AUTORIZADO | 80 |
| PAY_INIT_BLOQUEADO | 20 |

---

## Veredicto

| Check | Estado |
|-------|--------|
| HTTP 5xx errors | PASS — 0 errores |
| Conexiones rechazadas | PASS — 0 rechazadas |
| Deadlocks PostgreSQL | PASS — 0 deadlocks |
| Engine inserts | PASS — 100 registros |
| Guardian ROJO detecta anomalía | PASS — 20/20 |
| Guardian VERDE autoriza | PASS — 30/30 |

**RESULTADO: PASS**
Guardian + Logger + PostgreSQL soportan 50 requests concurrentes sin errores, deadlocks ni conexiones rechazadas.

---

*ODI no solo decide. ODI rinde cuentas.*
*Somos Industrias ODI.*
