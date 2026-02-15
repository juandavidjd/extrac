#!/usr/bin/env python3
"""V8.2 Certification Tests O1-O4"""
import asyncio
import os
import sys
import json

from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")
sys.path.insert(0, "/opt/odi/core")

import pyotp
import httpx
import asyncpg

TOTP_SECRET = "7WTGAOEMGJKO76WEO6OA2CHWUJS5VY3H"
ROJO_EVENT = "EV-2026-02-15-8245CE"
NEGRO_EVENT = "EV-2026-02-15-E6FBE8"
BASE = "http://127.0.0.1:8807"


async def get_pool():
    return await asyncpg.create_pool(
        host="172.18.0.4", port=5432,
        user="odi_user", password="odi_secure_password", database="odi",
        min_size=1, max_size=3
    )


async def test_o1(c, totp):
    """Override ROJO -> VERDE_OVERRIDE_SUPERVISADO"""
    print("=" * 60)
    print("TEST O1: Override ROJO -> VERDE_OVERRIDE_SUPERVISADO")
    print("=" * 60)

    # Login
    code = totp.now()
    r = await c.post(f"{BASE}/odi/auth/login", json={"human_id": "JD", "totp_code": code})
    print(f"  Login: {r.status_code}")
    assert r.status_code == 200, f"Login failed: {r.text}"
    jwt_token = r.json()["token"]

    # Override
    code = totp.now()
    r = await c.post(f"{BASE}/odi/override",
        headers={"Authorization": f"Bearer {jwt_token}", "X-ODI-TOTP": code},
        json={
            "original_odi_event_id": ROJO_EVENT,
            "target_decision": "VERDE_OVERRIDE_SUPERVISADO",
            "reason": "Precio verificado manualmente - falso positivo Guardian",
            "evidence": {"verificacion": "manual", "test": "O1"}
        })
    result = r.json()
    print(f"  Override: {r.status_code}")

    if r.status_code == 200 and result.get("ok"):
        eid = result["override_event_id"]
        print(f"  override_event_id: {eid}")

        # Verify chain in DB
        pool = await get_pool()
        async with pool.acquire() as conn:
            ov = await conn.fetchrow(
                "SELECT * FROM odi_overrides WHERE new_event_id = $1", eid
            )
            dl = await conn.fetchrow(
                "SELECT * FROM odi_decision_logs WHERE odi_event_id = $1", eid
            )

        print(f"  DB overrides: original={ov['original_event_id']}, decision={ov['decision']}")
        print(f"  DB log: prev={dl['prev_event_id']}, type={dl['event_type']}, estado={dl['estado_guardian']}, by={dl['override_by']}")

        ok = (
            dl["prev_event_id"] == ROJO_EVENT
            and dl["event_type"] == "OVERRIDE"
            and dl["estado_guardian"] == "verde"
            and dl["override_by"] == "JD"
        )
        await pool.close()
        print(f"  O1 {'PASSED' if ok else 'FAILED'}")
        return ok, eid
    else:
        print(f"  O1 FAILED: {result}")
        return False, None


async def test_o2(c, totp):
    """Supervisor fuera de vertical -> RECHAZADO"""
    print()
    print("=" * 60)
    print("TEST O2: Supervisor fuera de vertical -> RECHAZADO")
    print("=" * 60)

    pool = await get_pool()

    # Create P1 supervisor
    sup_secret = pyotp.random_base32()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM odi_humans WHERE human_id = 'SUP_P1'")
        if not exists:
            await conn.execute("""
                INSERT INTO odi_humans (human_id, display_name, role, vertical_scope, totp_secret)
                VALUES ($1, $2, $3, $4, $5)
            """, "SUP_P1", "Supervisor Test P1", "SUPERVISOR", "P1", sup_secret)
        else:
            row = await conn.fetchrow("SELECT totp_secret FROM odi_humans WHERE human_id = 'SUP_P1'")
            sup_secret = row["totp_secret"]

    # Create P2 ROJO event
    from odi_decision_logger import obtener_logger
    logger = obtener_logger()
    eid_p2 = await logger.log_decision(
        intent="PAY_INIT_BLOQUEADO", estado_guardian="rojo",
        modo_aplicado="SUPERVISADO", usuario_id="test", vertical="P2",
        motivo="Test O2", monto_cop=100000
    )
    print(f"  P2 ROJO event: {eid_p2}")

    # Login as SUP_P1
    sup_totp = pyotp.TOTP(sup_secret)
    code = sup_totp.now()
    r = await c.post(f"{BASE}/odi/auth/login", json={"human_id": "SUP_P1", "totp_code": code})
    assert r.status_code == 200
    sup_jwt = r.json()["token"]

    # Try override on P2 event
    code = sup_totp.now()
    r = await c.post(f"{BASE}/odi/override",
        headers={"Authorization": f"Bearer {sup_jwt}", "X-ODI-TOTP": code},
        json={
            "original_odi_event_id": eid_p2,
            "target_decision": "VERDE_OVERRIDE_SUPERVISADO",
            "reason": "Test O2",
            "evidence": {"test": "O2"}
        })
    print(f"  Override P2 as SUP_P1: {r.status_code}")
    print(f"  Response: {r.json()}")

    ok = r.status_code == 403 and "Sin permisos" in r.json().get("error", "")
    print(f"  O2 {'PASSED' if ok else 'FAILED'}")
    await pool.close()
    return ok


async def test_o3(c, totp):
    """Override NEGRO -> VERDE -> RECHAZADO"""
    print()
    print("=" * 60)
    print("TEST O3: Override NEGRO -> VERDE -> RECHAZADO")
    print("=" * 60)

    code = totp.now()
    r = await c.post(f"{BASE}/odi/auth/login", json={"human_id": "JD", "totp_code": code})
    jwt_token = r.json()["token"]

    code = totp.now()
    r = await c.post(f"{BASE}/odi/override",
        headers={"Authorization": f"Bearer {jwt_token}", "X-ODI-TOTP": code},
        json={
            "original_odi_event_id": NEGRO_EVENT,
            "target_decision": "VERDE_OVERRIDE_SUPERVISADO",
            "reason": "Intentar convertir negro a verde",
            "evidence": {"test": "O3"}
        })
    print(f"  Override NEGRO->VERDE: {r.status_code}")
    print(f"  Response: {r.json()}")

    ok = r.status_code == 403 and "NEGRO no se convierte en VERDE" in r.json().get("error", "")
    print(f"  O3 {'PASSED' if ok else 'FAILED'}")
    return ok


async def test_o4(c, override_eid):
    """Reintento pay/init con override_event_id"""
    print()
    print("=" * 60)
    print("TEST O4: Reintento pay/init con override_event_id")
    print("=" * 60)

    r = await c.post(f"{BASE}/paem/pay/init", json={
        "transaction_id": "TX-V82-OVERRIDE-RETRY",
        "booking_id": "BK-TEST-V82",
        "deposit_amount_cop": 500000,
        "usuario_id": "test-v82",
        "override_event_id": override_eid
    })
    print(f"  pay/init with override: {r.status_code}")
    resp = r.json()
    print(f"  Response: {json.dumps(resp, indent=2)}")

    # 404 = booking not found (OK — point is no 403 guardian_block)
    ok = r.status_code != 403
    print(f"  O4 {'PASSED' if ok else 'FAILED'}: {'No guardian_block' if ok else 'Still got 403'}")
    return ok


async def main():
    totp = pyotp.TOTP(TOTP_SECRET)

    async with httpx.AsyncClient(timeout=10) as c:
        o1_ok, override_eid = await test_o1(c, totp)
        o2_ok = await test_o2(c, totp)
        o3_ok = await test_o3(c, totp)
        o4_ok = await test_o4(c, override_eid) if override_eid else False

    print()
    print("=" * 60)
    print("  RESULTADOS V8.2 CERTIFICATION")
    print("=" * 60)
    results = {"O1": o1_ok, "O2": o2_ok, "O3": o3_ok, "O4": o4_ok}
    for t, ok in results.items():
        print(f"  {t}: {'PASSED' if ok else 'FAILED'}")
    total = sum(results.values())
    print(f"  TOTAL: {total}/4")
    print("=" * 60)


asyncio.run(main())
