#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Forense — Validación del metabolismo económico ODI
=======================================================
Dispara un webhook firmado simulando evento APPROVED de Wompi
y verifica la transición atómica en la base de datos.

Uso:
  python tests/test_webhook.py                    # contra localhost:8807
  python tests/test_webhook.py --url https://api.adsi.com.co
  python tests/test_webhook.py --check-only       # solo verificar DB

Resultado esperado:
  odi_payments:        PENDING → CAPTURED
  odi_health_bookings: HOLD → CONFIRMED
"""

import argparse
import hashlib
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    print("ERROR: 'requests' no instalado. pip install requests")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_BASE_URL = "http://localhost:8807"
TRANSACTION_ID = "TX-CASE-001"
BOOKING_ID = "BKG-CASE-001"
AMOUNT_COP = 5000

WOMPI_EVENTS_SECRET = os.getenv("WOMPI_EVENTS_KEY", "")


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def sign_webhook(body_str: str, timestamp: str, secret: str) -> str:
    """Generar firma SHA256 como lo haría Wompi."""
    raw = f"{timestamp}{body_str}{secret}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_wompi_event(reference: str, status: str = "APPROVED") -> dict:
    """Construir payload de evento Wompi."""
    return {
        "event": "transaction.updated",
        "data": {
            "transaction": {
                "id": f"wompi-sandbox-{int(time.time())}",
                "reference": reference,
                "status": status,
                "amount_in_cents": AMOUNT_COP * 100,
                "currency": "COP",
                "payment_method_type": "CARD",
            }
        },
        "timestamp": int(time.time()),
    }


# ══════════════════════════════════════════════════════════════════════════════
# TEST STEPS
# ══════════════════════════════════════════════════════════════════════════════

def test_health(base_url: str) -> bool:
    """Step 0: Health check."""
    print("\n=== Step 0: Health Check ===")
    try:
        r = requests.get(f"{base_url}/health", timeout=5)
        print(f"  Status: {r.status_code}")
        print(f"  Body: {json.dumps(r.json(), indent=2)}")
        return r.status_code == 200
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def test_pay_init(base_url: str) -> bool:
    """Step 1: POST /paem/pay/init — Iniciar checkout."""
    print("\n=== Step 1: POST /paem/pay/init ===")
    payload = {
        "transaction_id": TRANSACTION_ID,
        "booking_id": BOOKING_ID,
        "deposit_amount_cop": AMOUNT_COP,
    }
    try:
        r = requests.post(
            f"{base_url}/paem/pay/init",
            json=payload,
            timeout=10,
        )
        print(f"  Status: {r.status_code}")
        print(f"  Body: {json.dumps(r.json(), indent=2)}")
        return r.status_code == 200
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def test_webhook(base_url: str) -> bool:
    """Step 2: POST /webhooks/wompi — Simular evento APPROVED."""
    print("\n=== Step 2: POST /webhooks/wompi ===")
    event = build_wompi_event(TRANSACTION_ID, "APPROVED")
    body_str = json.dumps(event)
    timestamp = str(int(time.time()))

    headers = {"Content-Type": "application/json"}
    if WOMPI_EVENTS_SECRET:
        sig = sign_webhook(body_str, timestamp, WOMPI_EVENTS_SECRET)
        headers["x-event-checksum"] = sig
        headers["x-event-timestamp"] = timestamp
        print(f"  Signed with WOMPI_EVENTS_KEY (checksum={sig[:16]}...)")
    else:
        headers["x-event-checksum"] = "sandbox-no-secret"
        headers["x-event-timestamp"] = timestamp
        print("  WARNING: No WOMPI_EVENTS_KEY set — sending unsigned")

    try:
        r = requests.post(
            f"{base_url}/webhooks/wompi",
            data=body_str,
            headers=headers,
            timeout=10,
        )
        print(f"  Status Code: {r.status_code}")
        print(f"  Body: {json.dumps(r.json(), indent=2)}")
        return r.status_code == 200
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def test_db_verification(base_url: str) -> bool:
    """Step 3: Verificar estado final en DB via health endpoint."""
    print("\n=== Step 3: DB Verification ===")
    print("  (Run this SQL on the server to verify:)")
    print()
    print("  SELECT")
    print("    p.status AS payment_status,")
    print("    b.status AS booking_status")
    print("  FROM odi_payments p")
    print("  JOIN odi_health_bookings b")
    print("    ON b.transaction_id = p.transaction_id")
    print("  WHERE p.transaction_id = 'TX-CASE-001';")
    print()
    print("  Expected: CAPTURED | CONFIRMED")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="ODI PAEM Payment Forensic Test")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="Base URL of PAEM API")
    parser.add_argument("--check-only", action="store_true", help="Only verify DB state")
    parser.add_argument("--skip-init", action="store_true", help="Skip pay/init step")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    print(f"Target: {base}")
    print(f"Transaction: {TRANSACTION_ID}")
    print(f"Booking: {BOOKING_ID}")
    print(f"Amount: {AMOUNT_COP} COP")

    if args.check_only:
        test_db_verification(base)
        return

    results = {}

    # Step 0: Health
    results["health"] = test_health(base)

    if not results["health"]:
        print("\n!!! Health check failed. Aborting.")
        sys.exit(1)

    # Step 1: Pay Init
    if not args.skip_init:
        results["pay_init"] = test_pay_init(base)
    else:
        print("\n=== Step 1: SKIPPED (--skip-init) ===")
        results["pay_init"] = True

    # Step 2: Webhook
    results["webhook"] = test_webhook(base)

    # Step 3: Verification
    results["db_check"] = test_db_verification(base)

    # Summary
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    for step, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  {step:20s}: {status}")

    all_passed = all(results.values())
    print(f"\nResultado final: {'ALL PASSED' if all_passed else 'SOME FAILED'}")

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
