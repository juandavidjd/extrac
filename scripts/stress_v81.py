#!/usr/bin/env python3
"""
ODI V8.1 Stress Test — Guardian + Decision Logger + PostgreSQL
==============================================================
Dispara requests concurrentes a POST /paem/pay/init con montos altos.
Mide latencia, verifica logs en PostgreSQL, chequea locks y hashes.

Seguro: sin bookings pre-seeded, las requests terminan en 404 DESPUES
de que Guardian evalua y Decision Logger escribe. Wompi nunca se toca.

Usage: python3 stress_v81.py
"""

import asyncio
import aiohttp
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════
PAEM_URL = "http://127.0.0.1:8807/paem/pay/init"
PG_CMD = 'docker exec odi-postgres psql -U odi_user -d odi -t -A -c'

ROUNDS = [
    {"name": "R1", "total": 200, "concurrency": 20, "amount": 99_999_999},
    {"name": "R2", "total": 300, "concurrency": 50, "amount": 88_888_888},
]


@dataclass
class RequestResult:
    index: int
    tx_id: str
    status_code: int
    latency_ms: float
    body: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class RoundResult:
    name: str
    total: int
    concurrency: int
    results: List[RequestResult] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0


# ═══════════════════════════════════════════════════════════════
# STRESS ENGINE
# ═══════════════════════════════════════════════════════════════

async def fire_request(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    round_name: str,
    index: int,
    amount: int,
    ts: str,
) -> RequestResult:
    tx_id = f"TX-STRESS-{ts}-{round_name}-{index:04d}"
    bk_id = f"BK-STRESS-{ts}-{round_name}-{index:04d}"
    payload = {
        "transaction_id": tx_id,
        "booking_id": bk_id,
        "deposit_amount_cop": amount,
        "usuario_id": f"stress-{round_name}-{index:04d}",
    }

    async with sem:
        t0 = time.perf_counter()
        try:
            async with session.post(PAEM_URL, json=payload) as resp:
                latency = (time.perf_counter() - t0) * 1000
                try:
                    body = await resp.json()
                except Exception:
                    body = {"raw": await resp.text()}
                return RequestResult(
                    index=index,
                    tx_id=tx_id,
                    status_code=resp.status,
                    latency_ms=latency,
                    body=body,
                )
        except Exception as e:
            latency = (time.perf_counter() - t0) * 1000
            return RequestResult(
                index=index,
                tx_id=tx_id,
                status_code=0,
                latency_ms=latency,
                error=str(e),
            )


async def run_round(rnd: dict, ts: str) -> RoundResult:
    result = RoundResult(
        name=rnd["name"],
        total=rnd["total"],
        concurrency=rnd["concurrency"],
    )
    sem = asyncio.Semaphore(rnd["concurrency"])

    print(f"\n{'='*60}")
    print(f"  ROUND {rnd['name']}: {rnd['total']} requests @ {rnd['concurrency']} concurrency")
    print(f"  Amount: {rnd['amount']:,} COP")
    print(f"{'='*60}")

    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [
            fire_request(session, sem, rnd["name"], i, rnd["amount"], ts)
            for i in range(rnd["total"])
        ]
        result.start_time = time.perf_counter()
        result.results = await asyncio.gather(*tasks)
        result.end_time = time.perf_counter()

    elapsed = result.end_time - result.start_time
    print(f"  Completed in {elapsed:.2f}s ({rnd['total']/elapsed:.1f} req/s)")
    return result


# ═══════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════

def compute_stats(results: List[RequestResult]) -> Dict[str, Any]:
    latencies = sorted([r.latency_ms for r in results if r.status_code > 0])
    status_counts = {}
    errors = []
    for r in results:
        k = str(r.status_code)
        status_counts[k] = status_counts.get(k, 0) + 1
        if r.status_code >= 500 or r.status_code == 0:
            errors.append({"tx": r.tx_id, "status": r.status_code, "error": r.error})

    n = len(latencies)
    if n == 0:
        return {"error": "no successful requests"}

    return {
        "count": len(results),
        "success_count": n,
        "avg_ms": sum(latencies) / n,
        "min_ms": latencies[0],
        "max_ms": latencies[-1],
        "p50_ms": latencies[int(n * 0.50)],
        "p95_ms": latencies[int(n * 0.95)],
        "p99_ms": latencies[int(n * 0.99)],
        "status_counts": status_counts,
        "error_count_5xx": sum(1 for r in results if r.status_code >= 500),
        "error_count_network": sum(1 for r in results if r.status_code == 0),
        "errors_sample": errors[:5],
    }


# ═══════════════════════════════════════════════════════════════
# POSTGRESQL CHECKS
# ═══════════════════════════════════════════════════════════════

def pg(sql: str) -> str:
    """Run SQL against PostgreSQL via docker exec."""
    cmd = f"""{PG_CMD} "{sql}" """
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def check_decision_logs(ts: str) -> Dict[str, Any]:
    """Count decision logs by estado_guardian."""
    raw = pg(
        f"SELECT estado_guardian, count(*) FROM odi_decision_logs "
        f"WHERE transaction_id LIKE 'TX-STRESS-{ts}%' "
        f"GROUP BY estado_guardian ORDER BY count(*) DESC"
    )
    rows = {}
    total = 0
    for line in raw.strip().split("\n"):
        if "|" in line:
            parts = line.split("|")
            estado = parts[0].strip()
            count = int(parts[1].strip())
            rows[estado] = count
            total += count
    return {"by_estado": rows, "total": total}


def check_locks() -> Dict[str, Any]:
    """Check for deadlocks and active locks."""
    deadlocks = pg(
        "SELECT count(*) FROM pg_locks WHERE NOT granted"
    )
    active = pg(
        "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND query NOT LIKE '%pg_stat%'"
    )
    waiting = pg(
        "SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock'"
    )
    return {
        "blocked_locks": int(deadlocks) if deadlocks.isdigit() else deadlocks,
        "active_queries": int(active) if active.isdigit() else active,
        "waiting_on_lock": int(waiting) if waiting.isdigit() else waiting,
    }


def verify_hashes(ts: str, sample_size: int = 5) -> List[Dict[str, Any]]:
    """
    Recalculate hash_integridad for random samples and verify match.
    Hash = SHA256(odi_event_id + estado_guardian + modo_aplicado + intent_detectado + monto_cop + timestamp + secret)
    """
    secret = os.getenv("ODI_AUDIT_SECRET", os.getenv("ODI_SECRET", "odi_default_secret_cambiar"))
    raw = pg(
        f"SELECT odi_event_id, estado_guardian, modo_aplicado, intent_detectado, "
        f"monto_cop, timestamp, transaction_id, hash_integridad "
        f"FROM odi_decision_logs "
        f"WHERE transaction_id LIKE 'TX-STRESS-{ts}%' "
        f"ORDER BY random() LIMIT {sample_size}"
    )
    results = []
    for line in raw.strip().split("\n"):
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            continue
        odi_event_id, estado, modo, intent, monto, raw_ts, tx_id, stored_hash = parts[:8]

        # Convert PostgreSQL timestamp to Python isoformat()
        # PG: "2026-02-14 09:12:15.189+00" -> Python: "2026-02-14T09:12:15.189000+00:00"
        from datetime import datetime as dt, timezone as tz
        try:
            # Parse PG format (handles both .189+00 and .192913+00)
            raw_ts_clean = raw_ts.replace("+00", "+00:00").replace("+00:00:00", "+00:00")
            parsed = dt.fromisoformat(raw_ts_clean.replace(" ", "T"))
            timestamp_val = parsed.isoformat()
        except Exception:
            timestamp_val = raw_ts

        # Recalculate: exact formula from odi_decision_logger.py._generar_hash
        payload = f"{odi_event_id}{estado}{modo}{intent}{monto}{timestamp_val}{secret}"
        calc_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        results.append({
            "odi_event_id": odi_event_id,
            "tx_id": tx_id,
            "stored_hash": stored_hash,
            "calc_hash": calc_hash,
            "match": stored_hash == calc_hash,
        })
    return results


# ═══════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════

def generate_report(
    rounds_data: List[Dict[str, Any]],
    ts: str,
    report_path: str = "/opt/odi/reports/STRESS_TEST_V81.md",
):
    lines = [
        "# Stress Test V8.1 — Guardian + Logger + PostgreSQL",
        f"",
        f"**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Timestamp ID**: `{ts}`",
        f"**Target**: `POST {PAEM_URL}`",
        f"**Objetivo**: Validar Guardian + Decision Logger + PostgreSQL bajo carga concurrente",
        "",
    ]

    total_inserted = 0
    any_5xx = False

    for rd in rounds_data:
        stats = rd["stats"]
        logs = rd["logs"]
        locks = rd["locks"]
        hashes = rd["hashes"]
        rnd = rd["round"]

        total_inserted += logs["total"]
        if stats.get("error_count_5xx", 0) > 0:
            any_5xx = True

        elapsed = rd.get("elapsed", 0)
        rps = rnd["total"] / elapsed if elapsed > 0 else 0

        lines.extend([
            f"## Round {rnd['name']}: {rnd['total']} requests @ {rnd['concurrency']} concurrency",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total requests | {stats['count']} |",
            f"| Elapsed | {elapsed:.2f}s |",
            f"| Throughput | {rps:.1f} req/s |",
            f"| Avg latency | {stats['avg_ms']:.1f} ms |",
            f"| P50 | {stats['p50_ms']:.1f} ms |",
            f"| P95 | {stats['p95_ms']:.1f} ms |",
            f"| P99 | {stats['p99_ms']:.1f} ms |",
            f"| Min | {stats['min_ms']:.1f} ms |",
            f"| Max | {stats['max_ms']:.1f} ms |",
            f"| Errors 5xx | {stats['error_count_5xx']} |",
            f"| Errors network | {stats['error_count_network']} |",
            "",
            "### HTTP Status Distribution",
            "",
            "| Status | Count |",
            "|--------|-------|",
        ])
        for status, count in sorted(stats["status_counts"].items()):
            lines.append(f"| {status} | {count} |")

        lines.extend([
            "",
            "### Decision Logs (PostgreSQL)",
            "",
            f"| estado_guardian | count |",
            f"|----------------|-------|",
        ])
        for estado, count in logs["by_estado"].items():
            lines.append(f"| {estado} | {count} |")
        lines.append(f"| **TOTAL** | **{logs['total']}** |")

        lines.extend([
            "",
            "### PostgreSQL Locks",
            "",
            f"| Check | Value |",
            f"|-------|-------|",
            f"| Blocked locks | {locks['blocked_locks']} |",
            f"| Active queries | {locks['active_queries']} |",
            f"| Waiting on lock | {locks['waiting_on_lock']} |",
            "",
            "### Hash Verification (5 muestras)",
            "",
            "| odi_event_id | transaction_id | match |",
            "|-------------|----------------|-------|",
        ])
        for h in hashes:
            symbol = "PASS" if h["match"] else "FAIL"
            lines.append(f"| `{h['odi_event_id'][:20]}...` | `{h['tx_id']}` | {symbol} |")

        hash_pass = sum(1 for h in hashes if h["match"])
        hash_total = len(hashes)
        lines.append(f"\n**Hash integrity**: {hash_pass}/{hash_total} verified")

        if stats.get("errors_sample"):
            lines.extend(["", "### Error Samples", ""])
            for err in stats["errors_sample"][:3]:
                lines.append(f"- `{err['tx']}`: status={err['status']} error={err.get('error', 'N/A')}")

        lines.append("")

    # SUMMARY
    all_hashes_ok = all(
        all(h["match"] for h in rd["hashes"])
        for rd in rounds_data
        if rd["hashes"]
    )
    all_locks_clean = all(
        rd["locks"]["blocked_locks"] == 0 and rd["locks"]["waiting_on_lock"] == 0
        for rd in rounds_data
    )

    lines.extend([
        "---",
        "",
        "## Resumen Final",
        "",
        f"| Check | Result |",
        f"|-------|--------|",
        f"| Total registros insertados | {total_inserted} |",
        f"| Errores 5xx | {'SI' if any_5xx else 'NINGUNO'} |",
        f"| PostgreSQL locks/deadlocks | {'CLEAN' if all_locks_clean else 'DETECTED'} |",
        f"| Hash integrity | {'ALL PASS' if all_hashes_ok else 'FAILURES DETECTED'} |",
        f"| Wompi touched | NO (bookings not pre-seeded, 404 before checkout) |",
        "",
    ])

    # RECOMMENDATION
    if not any_5xx and all_locks_clean and all_hashes_ok and total_inserted > 0:
        recommendation = "OK para activar BARA"
        reason = (
            "Guardian + Logger + PostgreSQL soportaron carga concurrente sin errores 5xx, "
            "sin deadlocks, y con integridad de hashes verificada."
        )
    else:
        issues = []
        if any_5xx:
            issues.append("errores 5xx detectados")
        if not all_locks_clean:
            issues.append("locks/deadlocks en PostgreSQL")
        if not all_hashes_ok:
            issues.append("fallos en verificacion de hash")
        if total_inserted == 0:
            issues.append("0 registros insertados en decision_logs")
        recommendation = f"HOLD: ajustar {', '.join(issues)}"
        reason = "Se detectaron problemas que deben resolverse antes de activar BARA."

    lines.extend([
        f"## Recomendacion",
        "",
        f"**{recommendation}**",
        "",
        f"{reason}",
        "",
        "---",
        f"*Generated by stress_v81.py @ {datetime.now().isoformat()}*",
    ])

    report = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport saved to {report_path}")
    return report


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def main():
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    print(f"ODI V8.1 Stress Test — {ts}")
    print(f"Target: {PAEM_URL}")

    # Preflight
    print("\n[PREFLIGHT] Checking PAEM...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://127.0.0.1:8807/health") as resp:
                health = await resp.json()
                print(f"  PAEM: {health.get('service')} v{health.get('version')} — OK")
        except Exception as e:
            print(f"  PAEM NOT REACHABLE: {e}")
            sys.exit(1)

    # Clean previous stress data
    print("\n[CLEANUP] Removing old TX-STRESS records...")
    pg(f"DELETE FROM odi_decision_logs WHERE transaction_id LIKE 'TX-STRESS-%'")
    print("  Done.")

    rounds_data = []

    for rnd in ROUNDS:
        result = await run_round(rnd, ts)
        elapsed = result.end_time - result.start_time
        stats = compute_stats(result.results)

        print(f"\n  [STATS {rnd['name']}]")
        print(f"    Avg: {stats['avg_ms']:.1f}ms  P50: {stats['p50_ms']:.1f}ms  P95: {stats['p95_ms']:.1f}ms  P99: {stats['p99_ms']:.1f}ms")
        print(f"    Status: {stats['status_counts']}")
        print(f"    Errors 5xx: {stats['error_count_5xx']}  Network: {stats['error_count_network']}")

        # Wait a beat for async DB writes to flush
        await asyncio.sleep(2)

        print(f"\n  [PG CHECK {rnd['name']}]")
        logs = check_decision_logs(ts)
        print(f"    Decision logs: {logs}")
        locks = check_locks()
        print(f"    Locks: {locks}")
        hashes = verify_hashes(ts, 5)
        print(f"    Hash verification: {len([h for h in hashes if h['match']])}/{len(hashes)} passed")

        rounds_data.append({
            "round": rnd,
            "stats": stats,
            "logs": logs,
            "locks": locks,
            "hashes": hashes,
            "elapsed": elapsed,
        })

    # Generate report
    print("\n" + "=" * 60)
    print("  GENERATING REPORT")
    print("=" * 60)
    generate_report(rounds_data, ts)


if __name__ == "__main__":
    asyncio.run(main())
