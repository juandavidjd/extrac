# ODI V8.1 — REPORTE DE CERTIFICACION
# Fecha: 2026-02-14T06:45:00Z
# Servidor: 64.23.170.118

## PERSONALIDAD (Dimension 1: QUIEN es ODI)

| Componente | Estado | Detalle |
|------------|--------|---------|
| Genes ADN | 7/7 cargados | GEN-001 a GEN-007 inmutables |
| Principio | Activo | "ODI decide sin hablar. Habla solo cuando ya ha decidido." |
| Declaracion | Activa | "Somos Industrias ODI." |
| Verticales | P1, P2, P3, P4 | Transporte, Salud, Turismo, Belleza |
| Perfiles | 5 arquetipos | don_carlos, andres, lucia, dona_martha, diego |
| Niveles intimidad | 0-4 | OBSERVADOR -> CONOCIDO -> CONFIDENTE -> CUSTODIO -> PUENTE |
| Frases prohibidas | 10 bloqueadas | + 3 frases de imitacion |
| Voz | Configurada | secretario_tecnico_brillante, calido_contenido |

## ESTADO (Dimension 2: Guardian Layer)

| Nivel | Color | Accion | Test |
|-------|-------|--------|------|
| Normal | VERDE | comercio_habilitado, cobro_permitido | OK |
| Alerta | AMARILLO | supervision_aumentada, log_extra | T4 PASS |
| Proteccion | ROJO | detener_operacion, no_cobrar, proteger_capital | T9 PASS |
| Emergencia | NEGRO | protocolo_emergencia, prioridad_vida_humana | T3 PASS |

- Detector emergencia: Activo (palabras clave + linea 106)
- Detector precio anomalo: Activo (ratio > 3.0 o < 0.2)
- Evalua contexto incluso sin mensaje (fix V8.1)

## MODO (Dimension 3: Operacional)

| Modo | Condicion | Puede cobrar | Puede vender |
|------|-----------|--------------|--------------|
| AUTOMATICO | nivel >= 2 AND ventas >= 5 | Si | Si |
| SUPERVISADO | Default / Alerta | Si | Si (con confirm) |
| CUSTODIO | Emergencia (negro) | No | No |

## CARACTER (Dimension 4: Calibrado)

- Calibracion por perfil de usuario: Activa
- Calibracion por vertical activa: Activa
- Calibracion por nivel intimidad: Activa
- Calibracion por estado guardian: Activa
- Deteccion de urgencia: Activa

## AUDITORIA COGNITIVA

| Componente | Estado | Detalle |
|------------|--------|---------|
| Tabla PostgreSQL | odi_decision_logs | 18 columnas, 6 indices, UUID PK |
| Vista | odi_audit_resumen | Resumen por estado_guardian |
| Logger | odi_decision_logger.py | Singleton, async, pool asyncpg |
| Hash integridad | SHA-256 | Determinista, detecta tamper |
| Fallback | /opt/odi/data/audit_fallback/ | JSON si PostgreSQL falla |
| Hook PAEM | payments_api.py v1.2.0 | Guardian -> Logger -> Wompi |
| Eventos criticos | 11 tipos | PAY_INIT, VENTA, ESTADO_CAMBIO, etc. |

## HOOK PAEM (Guardian pre-Wompi)

Flujo: POST /paem/pay/init
1. V8.1 Guardian evalua estado
2. Si != verde -> 403 guardian_block + log PAY_INIT_BLOQUEADO
3. Si verde -> log PAY_INIT_AUTORIZADO + checkout Wompi
4. Fail-safe: si V8.1 falla, flujo existente continua

## ARCHIVOS CREADOS

```
/opt/odi/personalidad/
  adn.yaml
  voz.yaml
  niveles_intimidad.yaml
  verticales/p1_transporte.yaml
  verticales/p2_salud.yaml
  verticales/p3_turismo.yaml
  verticales/p4_belleza.yaml
  perfiles/arquetipos.yaml
  guardian/etica.yaml
  guardian/red_humana.json
  frases/prohibidas.yaml
  frases/adn_expresado.yaml

/opt/odi/core/
  odi_personalidad.py    (465 lineas — motor 4 dimensiones)
  odi_decision_logger.py (270 lineas — auditoria cognitiva)

/opt/odi/core/industries/turismo/
  payments_api.py        (v1.2.0 — hook Guardian pre-Wompi)

/opt/odi/tests/
  test_v81.py            (suite 9/9)
```

## TESTS

| # | Test | Resultado |
|---|------|-----------|
| T1 | ADN carga 7 genes inmutables | PASS |
| T2 | Frases prohibidas cargadas (>=10) | PASS |
| T3 | Guardian detecta emergencia -> NEGRO | PASS |
| T4 | Guardian detecta alerta -> AMARILLO | PASS |
| T5 | Deteccion multi-vertical P1/P2/P3/P4 | PASS |
| T6 | Prompt dinamico contiene 4 dimensiones | PASS |
| T7 | Decision ROJO persiste en PostgreSQL | PASS |
| T8 | Hash SHA-256 determinista + tamper detection | PASS |
| T9 | Guardian bloquea PAY_INIT con precio anomalo | PASS |

**Total: 9/9 PASS**

## INTEGRIDAD VERIFICADA

- WhatsApp pipeline: NO TOCADO
- Shopify pipeline: NO TOCADO
- n8n workflows: NO TOCADO
- Wompi webhook hardening: INTACTO (solo se agrego pre-check)
- PAEM API v2.2.1: HEALTH OK despues de restart
- Backup: /opt/odi/backups/pre_personalidad_20260214_061728/

## CERTIFICACION

V8.1 — PERSONALIDAD + AUDITORIA COGNITIVA — CERTIFICADO
9/9 tests pasaron
Fecha: 2026-02-14
Servidor: 64.23.170.118

"ODI decide sin hablar. Habla solo cuando ya ha decidido."
"ODI no solo decide. ODI rinde cuentas."
"Somos Industrias ODI."
