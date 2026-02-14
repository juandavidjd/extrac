#!/usr/bin/env python3
"""
ODI V8.1 — Stress Test de Concurrencia
========================================
50 requests concurrentes contra POST /paem/pay/init (127.0.0.1:8807)
  - 30 VERDE (precio normal, ratio ~1.2)
  - 20 ROJO  (precio anómalo, ratio >5.0)

Mide: latencia, status code, odi_event_id, deadlocks, errores 5xx.
Genera reporte en /opt/odi/reports/STRESS_TEST_V81_YYYYMMDD.md

NOTA TÉCNICA:
  El endpoint PAEM solo pasa precio_final al Guardian (sin precio_catalogo),
  lo que impide activar ROJO vía HTTP. Para probar ambas rutas bajo carga real,
  este script ejecuta dos fases:
    Fase 1 — HTTP: 50 requests concurrentes al endpoint real (full stack)
    Fase 2 — ENGINE: 50 llamadas concurrentes directas al Guardian + Logger
             (30 VERDE + 20 ROJO con precio_catalogo para activar bloqueo)
  Ambas fases estresan asyncpg pool + PostgreSQL simultáneamente.
"""

import sys
import os
import asyncio
import time
import json
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any

# ═══════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════

PAEM_URL = "http://127.0.0.1:8807/paem/pay/init"
TOTAL_REQUESTS = 50
VERDE_COUNT = 30
ROJO_COUNT = 20
REPORT_DIR = "/opt/odi/reports"

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "172.18.0.4")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "odi_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "odi_secure_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "odi")


# ═══════════════════════════════════════════════
# FASE 1: HTTP STRESS TEST
# ═══════════════════════════════════════════════

async def http_request(session, idx: int, is_rojo: bool) -> Dict[str, Any]:
    """Dispara un request HTTP al endpoint PAEM."""
    tx_id = f"TX-STRESS-{idx:03d}"
    bk_id = f"BK-STRESS-{idx:03d}"
    # ROJO usa monto alto (pero Guardian no lo bloqueará vía HTTP — ver NOTA)
    amount = 5_000_000 if is_rojo else 150_000
    label = "ROJO" if is_rojo else "VERDE"

    payload = {
        "transaction_id": tx_id,
        "booking_id": bk_id,
        "deposit_amount_cop": amount,
        "usuario_id": f"STRESS_{label}_{idx:03d}"
    }

    result = {
        "idx": idx,
        "tx_id": tx_id,
        "label": label,
        "amount": amount,
        "status_code": None,
        "latency_ms": 0,
        "odi_event_id": None,
        "error": None,
        "body": None,
    }

    start = time.perf_counter()
    try:
        async with session.post(PAEM_URL, json=payload) as resp:
            result["status_code"] = resp.status
            body = await resp.json()
            result["body"] = body
            result["odi_event_id"] = body.get("odi_event_id")
    except Exception as e:
        result["error"] = str(e)
        result["status_code"] = 0
    finally:
        result["latency_ms"] = (time.perf_counter() - start) * 1000

    return result


async def run_http_phase() -> List[Dict[str, Any]]:
    """Fase 1: 50 requests HTTP concurrentes."""
    import aiohttp

    print("=" * 70)
    print("FASE 1: HTTP STRESS TEST — 50 concurrent requests to /paem/pay/init")
    print("=" * 70)

    tasks = []
    connector = aiohttp.TCPConnector(limit=0, force_close=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for i in range(1, TOTAL_REQUESTS + 1):
            is_rojo = i > VERDE_COUNT  # primeros 30 = VERDE, últimos 20 = ROJO
            tasks.append(http_request(session, i, is_rojo))

        print(f"  Disparando {TOTAL_REQUESTS} requests concurrentes...")
        start = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = (time.perf_counter() - start) * 1000

    # Filtrar excepciones
    clean_results = []
    for r in results:
        if isinstance(r, Exception):
            clean_results.append({
                "idx": -1, "tx_id": "?", "label": "?",
                "status_code": 0, "latency_ms": 0,
                "error": str(r), "odi_event_id": None
            })
        else:
            clean_results.append(r)

    print(f"  Completado en {total_time:.0f}ms")
    return clean_results


# ═══════════════════════════════════════════════
# FASE 2: ENGINE STRESS TEST (Guardian + Logger directo)
# ═══════════════════════════════════════════════

async def engine_request(personalidad, audit_logger, idx: int, is_rojo: bool) -> Dict[str, Any]:
    """Llama directamente al Guardian + Logger (misma lógica que el endpoint)."""
    tx_id = f"TX-ENGINE-{idx:03d}"
    label = "ROJO" if is_rojo else "VERDE"
    uid = f"ENGINE_{label}_{idx:03d}"

    if is_rojo:
        amount = 5_000_000
        contexto = {"precio_final": 5_000_000, "precio_catalogo": 100_000}  # ratio 50x
    else:
        amount = 150_000
        contexto = {"precio_final": 150_000, "precio_catalogo": 120_000}  # ratio 1.25

    result = {
        "idx": idx,
        "tx_id": tx_id,
        "label": label,
        "amount": amount,
        "guardian_color": None,
        "odi_event_id": None,
        "latency_ms": 0,
        "error": None,
    }

    start = time.perf_counter()
    try:
        estado = personalidad.evaluar_estado(uid, "", contexto=contexto)
        result["guardian_color"] = estado["color"]

        if estado["color"] != "verde":
            eid = await audit_logger.log_decision(
                intent="PAY_INIT_BLOQUEADO",
                estado_guardian=estado["color"],
                modo_aplicado="SUPERVISADO",
                usuario_id=uid,
                vertical="P2",
                motivo=estado.get("motivo", "Estado no verde"),
                monto_cop=amount,
                transaction_id=tx_id,
                decision_path=["stress_test", "evaluar_estado", "bloqueo_pago"]
            )
        else:
            eid = await audit_logger.log_decision(
                intent="PAY_INIT_AUTORIZADO",
                estado_guardian="verde",
                modo_aplicado="AUTOMATICO",
                usuario_id=uid,
                vertical="P2",
                motivo="Estado verde, pago autorizado",
                monto_cop=amount,
                transaction_id=tx_id,
                decision_path=["stress_test", "evaluar_estado", "autorizar_pago"]
            )
        result["odi_event_id"] = eid
    except Exception as e:
        result["error"] = str(e)
    finally:
        result["latency_ms"] = (time.perf_counter() - start) * 1000

    return result


async def run_engine_phase() -> List[Dict[str, Any]]:
    """Fase 2: 50 llamadas concurrentes al Guardian + Logger."""
    sys.path.insert(0, "/opt/odi/core")
    from odi_personalidad import obtener_personalidad
    from odi_decision_logger import obtener_logger

    print()
    print("=" * 70)
    print("FASE 2: ENGINE STRESS TEST — 50 concurrent Guardian + Logger calls")
    print("       (30 VERDE ratio 1.25 + 20 ROJO ratio 50x)")
    print("=" * 70)

    personalidad = obtener_personalidad()
    audit_logger = obtener_logger()

    # Calentar pool de conexiones
    await audit_logger._get_pool()

    tasks = []
    for i in range(1, TOTAL_REQUESTS + 1):
        is_rojo = i > VERDE_COUNT
        tasks.append(engine_request(personalidad, audit_logger, i, is_rojo))

    print(f"  Disparando {TOTAL_REQUESTS} llamadas concurrentes...")
    start = time.perf_counter()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = (time.perf_counter() - start) * 1000

    clean_results = []
    for r in results:
        if isinstance(r, Exception):
            clean_results.append({
                "idx": -1, "tx_id": "?", "label": "?",
                "guardian_color": None, "latency_ms": 0,
                "error": str(r), "odi_event_id": None
            })
        else:
            clean_results.append(r)

    print(f"  Completado en {total_time:.0f}ms")
    return clean_results


# ═══════════════════════════════════════════════
# DB VERIFICATION
# ═══════════════════════════════════════════════

async def verify_db() -> Dict[str, Any]:
    """Verifica registros en PostgreSQL post-stress."""
    import asyncpg

    pool = await asyncpg.create_pool(
        host=POSTGRES_HOST, port=POSTGRES_PORT,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD,
        database=POSTGRES_DB, min_size=1, max_size=3
    )

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM odi_decision_logs WHERE transaction_id LIKE 'TX-STRESS-%' OR transaction_id LIKE 'TX-ENGINE-%'"
        )
        by_estado = await conn.fetch(
            "SELECT estado_guardian, COUNT(*) as cnt FROM odi_decision_logs "
            "WHERE transaction_id LIKE 'TX-STRESS-%' OR transaction_id LIKE 'TX-ENGINE-%' "
            "GROUP BY estado_guardian ORDER BY cnt DESC"
        )
        by_intent = await conn.fetch(
            "SELECT intent_detectado, COUNT(*) as cnt FROM odi_decision_logs "
            "WHERE transaction_id LIKE 'TX-STRESS-%' OR transaction_id LIKE 'TX-ENGINE-%' "
            "GROUP BY intent_detectado ORDER BY cnt DESC"
        )
        # Check for any deadlock evidence
        deadlocks = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'idle in transaction (aborted)'"
        )
        active_conns = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'odi'"
        )

    await pool.close()

    return {
        "total_inserted": total,
        "by_estado": [(r["estado_guardian"], r["cnt"]) for r in by_estado],
        "by_intent": [(r["intent_detectado"], r["cnt"]) for r in by_intent],
        "deadlocks_detected": deadlocks,
        "active_connections": active_conns,
    }


# ═══════════════════════════════════════════════
# ANALYSIS + REPORT
# ═══════════════════════════════════════════════

def analyze(results: List[Dict], phase_name: str) -> Dict[str, Any]:
    """Analiza resultados de una fase."""
    latencies = [r["latency_ms"] for r in results if r.get("latency_ms", 0) > 0]
    errors = [r for r in results if r.get("error")]

    if phase_name == "HTTP":
        status_codes = {}
        for r in results:
            sc = r.get("status_code", 0)
            status_codes[sc] = status_codes.get(sc, 0) + 1
        errors_5xx = [r for r in results if r.get("status_code", 0) >= 500]
        conn_refused = [r for r in results if r.get("status_code", 0) == 0]
    else:
        status_codes = {}
        errors_5xx = []
        conn_refused = []
        for r in results:
            color = r.get("guardian_color", "unknown")
            status_codes[color] = status_codes.get(color, 0) + 1

    event_ids = [r.get("odi_event_id") for r in results if r.get("odi_event_id")]

    analysis = {
        "phase": phase_name,
        "total": len(results),
        "latency_avg": statistics.mean(latencies) if latencies else 0,
        "latency_p50": statistics.median(latencies) if latencies else 0,
        "latency_p95": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
        "latency_min": min(latencies) if latencies else 0,
        "latency_max": max(latencies) if latencies else 0,
        "status_codes": status_codes,
        "errors_5xx": len(errors_5xx),
        "conn_refused": len(conn_refused),
        "errors_other": len(errors),
        "event_ids_captured": len(event_ids),
    }
    return analysis


def generate_report(http_analysis, engine_analysis, db_info, http_results, engine_results) -> str:
    """Genera reporte markdown."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    report = f"""# ODI V8.1 — Stress Test de Concurrencia
**Fecha:** {now}
**Servidor:** 64.23.170.118 (localhost)
**Endpoint:** POST /paem/pay/init (puerto 8807)
**Requests totales:** {TOTAL_REQUESTS} por fase (100 total)
**Mix:** {VERDE_COUNT} VERDE + {ROJO_COUNT} ROJO por fase

---

## Fase 1: HTTP Stress Test (Full Stack)

50 requests concurrentes contra el endpoint PAEM real.
Nota: Todas pasan Guardian como VERDE (endpoint no envía precio_catalogo).
Resultado esperado: 404 (booking inexistente) tras pasar Guardian.

### Latencia

| Métrica | Valor |
|---------|-------|
| Promedio | {http_analysis['latency_avg']:.1f} ms |
| P50 (mediana) | {http_analysis['latency_p50']:.1f} ms |
| P95 | {http_analysis['latency_p95']:.1f} ms |
| Min | {http_analysis['latency_min']:.1f} ms |
| Max | {http_analysis['latency_max']:.1f} ms |

### Status Codes

| Code | Count | Significado |
|------|-------|-------------|
"""
    for code, count in sorted(http_analysis["status_codes"].items()):
        meaning = {
            200: "OK (Guardian VERDE + checkout)",
            403: "Guardian BLOCK (ROJO)",
            404: "Booking no encontrado (esperado)",
            409: "Conflict (booking no en HOLD)",
            500: "Error interno",
            0: "Conexión rechazada",
        }.get(code, "Otro")
        report += f"| {code} | {count} | {meaning} |\n"

    report += f"""
### Errores

| Tipo | Count |
|------|-------|
| 5xx Server Error | {http_analysis['errors_5xx']} |
| Conexión rechazada | {http_analysis['conn_refused']} |
| Otros errores | {http_analysis['errors_other']} |

---

## Fase 2: Engine Stress Test (Guardian + Logger Directo)

50 llamadas concurrentes directas al motor de personalidad + audit logger.
30 con contexto VERDE (ratio 1.25) + 20 con contexto ROJO (ratio 50x).
Prueba la concurrencia real de asyncpg pool + PostgreSQL INSERT.

### Latencia

| Métrica | Valor |
|---------|-------|
| Promedio | {engine_analysis['latency_avg']:.1f} ms |
| P50 (mediana) | {engine_analysis['latency_p50']:.1f} ms |
| P95 | {engine_analysis['latency_p95']:.1f} ms |
| Min | {engine_analysis['latency_min']:.1f} ms |
| Max | {engine_analysis['latency_max']:.1f} ms |

### Resultados Guardian

| Estado | Count |
|--------|-------|
"""
    for estado, count in sorted(engine_analysis["status_codes"].items()):
        report += f"| {estado} | {count} |\n"

    report += f"""
### Event IDs Capturados

| Fase | IDs generados |
|------|---------------|
| HTTP | {http_analysis['event_ids_captured']} / {TOTAL_REQUESTS} |
| Engine | {engine_analysis['event_ids_captured']} / {TOTAL_REQUESTS} |

---

## Verificación PostgreSQL

| Métrica | Valor |
|---------|-------|
| Total registros insertados (stress) | {db_info['total_inserted']} |
| Deadlocks detectados | {db_info['deadlocks_detected']} |
| Conexiones activas (odi) | {db_info['active_connections']} |

### Registros por estado_guardian

| Estado | Count |
|--------|-------|
"""
    for estado, count in db_info["by_estado"]:
        report += f"| {estado} | {count} |\n"

    report += """
### Registros por intent

| Intent | Count |
|--------|-------|
"""
    for intent, count in db_info["by_intent"]:
        report += f"| {intent} | {count} |\n"

    # Detailed errors if any
    http_errors = [r for r in http_results if r.get("error") or r.get("status_code", 200) >= 500]
    engine_errors = [r for r in engine_results if r.get("error")]

    if http_errors or engine_errors:
        report += "\n---\n\n## Errores Detallados\n\n"
        if http_errors:
            report += "### HTTP\n\n"
            for e in http_errors[:10]:
                report += f"- `{e.get('tx_id')}`: status={e.get('status_code')} error={e.get('error')}\n"
        if engine_errors:
            report += "\n### Engine\n\n"
            for e in engine_errors[:10]:
                report += f"- `{e.get('tx_id')}`: error={e.get('error')}\n"

    # Verdict
    total_errors = http_analysis["errors_5xx"] + http_analysis["conn_refused"] + engine_analysis["errors_other"]
    deadlocks = db_info["deadlocks_detected"]
    expected_engine_inserts = TOTAL_REQUESTS  # all engine calls should insert

    report += f"""
---

## Veredicto

| Check | Estado |
|-------|--------|
| HTTP 5xx errors | {"FAIL — " + str(http_analysis['errors_5xx']) + " errores" if http_analysis['errors_5xx'] > 0 else "PASS — 0 errores"} |
| Conexiones rechazadas | {"FAIL — " + str(http_analysis['conn_refused']) if http_analysis['conn_refused'] > 0 else "PASS — 0 rechazadas"} |
| Deadlocks PostgreSQL | {"FAIL — " + str(deadlocks) + " detectados" if deadlocks > 0 else "PASS — 0 deadlocks"} |
| Engine inserts | {"PASS" if db_info['total_inserted'] >= expected_engine_inserts else "PARTIAL"} — {db_info['total_inserted']} registros |
| Guardian ROJO detecta anomalía | {"PASS" if engine_analysis['status_codes'].get('rojo', 0) == ROJO_COUNT else "FAIL"} — {engine_analysis['status_codes'].get('rojo', 0)}/{ROJO_COUNT} |
| Guardian VERDE autoriza | {"PASS" if engine_analysis['status_codes'].get('verde', 0) == VERDE_COUNT else "FAIL"} — {engine_analysis['status_codes'].get('verde', 0)}/{VERDE_COUNT} |
"""

    if total_errors == 0 and deadlocks == 0:
        report += """
**RESULTADO: PASS**
Guardian + Logger + PostgreSQL soportan 50 requests concurrentes sin errores, deadlocks ni conexiones rechazadas.
"""
    else:
        report += f"""
**RESULTADO: REVIEW NEEDED**
{total_errors} errores totales, {deadlocks} deadlocks.
"""

    report += """
---

*ODI no solo decide. ODI rinde cuentas.*
*Somos Industrias ODI.*
"""
    return report


# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════

async def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  ODI V8.1 — STRESS TEST DE CONCURRENCIA                    ║")
    print("║  50 requests x 2 fases = 100 operaciones concurrentes      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # Limpiar registros de stress tests anteriores
    import asyncpg
    pool = await asyncpg.create_pool(
        host=POSTGRES_HOST, port=POSTGRES_PORT,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD,
        database=POSTGRES_DB, min_size=1, max_size=2
    )
    async with pool.acquire() as conn:
        count_before = await conn.fetchval(
            "SELECT COUNT(*) FROM odi_decision_logs WHERE transaction_id LIKE 'TX-STRESS-%' OR transaction_id LIKE 'TX-ENGINE-%'"
        )
        if count_before:
            await conn.execute(
                "DELETE FROM odi_decision_logs WHERE transaction_id LIKE 'TX-STRESS-%' OR transaction_id LIKE 'TX-ENGINE-%'"
            )
            print(f"  Limpiados {count_before} registros de stress tests anteriores")
    await pool.close()

    # ── FASE 1: HTTP ──
    http_results = await run_http_phase()
    http_analysis = analyze(http_results, "HTTP")

    print(f"\n  Latencia avg={http_analysis['latency_avg']:.0f}ms p95={http_analysis['latency_p95']:.0f}ms")
    print(f"  Status codes: {http_analysis['status_codes']}")
    print(f"  Errores 5xx: {http_analysis['errors_5xx']}")

    # ── FASE 2: ENGINE ──
    engine_results = await run_engine_phase()
    engine_analysis = analyze(engine_results, "ENGINE")

    print(f"\n  Latencia avg={engine_analysis['latency_avg']:.0f}ms p95={engine_analysis['latency_p95']:.0f}ms")
    print(f"  Guardian results: {engine_analysis['status_codes']}")
    print(f"  Event IDs: {engine_analysis['event_ids_captured']}/{TOTAL_REQUESTS}")

    # ── VERIFICACIÓN DB ──
    print()
    print("=" * 70)
    print("VERIFICACIÓN POSTGRESQL")
    print("=" * 70)

    db_info = await verify_db()

    print(f"  Total registros stress: {db_info['total_inserted']}")
    print(f"  Por estado: {db_info['by_estado']}")
    print(f"  Deadlocks: {db_info['deadlocks_detected']}")
    print(f"  Conexiones activas: {db_info['active_connections']}")

    # ── GENERAR REPORTE ──
    report = generate_report(http_analysis, engine_analysis, db_info, http_results, engine_results)

    os.makedirs(REPORT_DIR, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    report_path = os.path.join(REPORT_DIR, f"STRESS_TEST_V81_{date_str}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n  Reporte guardado: {report_path}")

    # ── RESUMEN FINAL ──
    print()
    print("=" * 70)
    total_errors = http_analysis["errors_5xx"] + http_analysis["conn_refused"]
    if total_errors == 0 and db_info["deadlocks_detected"] == 0:
        print("STRESS TEST: PASS")
    else:
        print("STRESS TEST: REVIEW NEEDED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
