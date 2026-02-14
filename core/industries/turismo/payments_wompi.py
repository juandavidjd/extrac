#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wompi Payment Service — Firma de integridad + Validación de webhooks
====================================================================
Gateway: Wompi (Colombia) — https://docs.wompi.co
Paradigma: Industria 5.0 — Atomicidad, idempotencia, trazabilidad.

Funciones:
  - generate_integrity_signature(): SHA256 para checkout widget
  - generate_checkout_payload():    Payload completo para iniciar pago
  - validate_webhook_signature():   HMAC para eventos entrantes
  - process_webhook():              Transición atómica DB

Versión: 1.0.0 — 13 Feb 2026
"""

import hashlib
import hmac
import json
import logging
import os
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("odi.paem.payments")


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

WOMPI_PUBLIC_KEY = os.getenv("WOMPI_PUBLIC_KEY", "")
WOMPI_INTEGRITY_SECRET = os.getenv("WOMPI_INTEGRITY_SECRET", "")
WOMPI_EVENTS_SECRET = os.getenv("WOMPI_EVENTS_KEY", "")
REDIRECT_URL = os.getenv("WOMPI_REDIRECT_URL", "https://api.adsi.com.co/payment-success")


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRITY SIGNATURE (para checkout widget)
# ══════════════════════════════════════════════════════════════════════════════

def generate_integrity_signature(
    reference: str,
    amount_in_cents: int,
    currency: str = "COP",
) -> str:
    """
    Generar firma SHA256 de integridad para el widget de Wompi.
    Cadena: {reference}{amount_in_cents}{currency}{integrity_secret}
    """
    raw = f"{reference}{amount_in_cents}{currency}{WOMPI_INTEGRITY_SECRET}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_checkout_payload(
    transaction_id: str,
    amount_cop: Decimal,
    currency: str = "COP",
) -> Dict[str, Any]:
    """
    Generar payload completo listo para el widget de checkout Wompi.
    Convierte COP a centavos y firma.
    """
    amount_in_cents = int(amount_cop * 100)
    signature = generate_integrity_signature(transaction_id, amount_in_cents, currency)

    return {
        "public_key": WOMPI_PUBLIC_KEY,
        "currency": currency,
        "amount_in_cents": amount_in_cents,
        "reference": transaction_id,
        "signature": signature,
        "redirect_url": REDIRECT_URL,
    }


# ══════════════════════════════════════════════════════════════════════════════
# WEBHOOK SIGNATURE VALIDATION (para eventos entrantes)
# ══════════════════════════════════════════════════════════════════════════════

def validate_webhook_signature(
    raw_body: bytes,
    signature_header: Optional[str],
    timestamp_header: Optional[str],
) -> Tuple[bool, str]:
    """
    Validar firma HMAC del webhook de Wompi.
    Cadena: {timestamp}{raw_body}{events_secret}
    Retorna: (valid: bool, reason: str)
    """
    if not signature_header or not timestamp_header:
        return False, "Missing signature or timestamp headers"

    if not WOMPI_EVENTS_SECRET:
        logger.warning("WOMPI_EVENTS_KEY not configured — skipping signature validation")
        return True, "Events secret not configured (sandbox mode)"

    raw_message = f"{timestamp_header}{raw_body.decode('utf-8')}{WOMPI_EVENTS_SECRET}"
    expected = hashlib.sha256(raw_message.encode("utf-8")).hexdigest()

    if hmac.compare_digest(expected, signature_header):
        return True, "Webhook integrity check passed"
    else:
        return False, "Invalid webhook signature"


# ══════════════════════════════════════════════════════════════════════════════
# WEBHOOK PROCESSING (transición atómica)
# ══════════════════════════════════════════════════════════════════════════════

def process_webhook_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesar evento de Wompi y ejecutar transición atómica en DB.
    Usa fn_odi_confirm_payment() para atomicidad.

    Retorna: {"ok": bool, "detail": str, "payment_status": str, "booking_status": str}
    """
    from core.industries.turismo.db.client import pg_query, pg_execute

    try:
        tx_data = event.get("data", {}).get("transaction", {})
        tx_reference = tx_data.get("reference")
        tx_status = tx_data.get("status")
        tx_id = tx_data.get("id", "")

        if not tx_reference:
            return {"ok": False, "detail": "No transaction reference in event"}

        logger.info("Webhook received: ref=%s status=%s", tx_reference, tx_status)

        if tx_status != "APPROVED":
            # Registrar evento no-aprobado pero no fallar
            pg_execute(
                """INSERT INTO odi_events (event_type, transaction_id, payload)
                   VALUES ('PAEM.PAYMENT_REJECTED', %s, %s::jsonb)""",
                (tx_reference, json.dumps({"gateway_status": tx_status, "gateway_id": tx_id})),
            )
            return {
                "ok": True,
                "detail": f"Event received but status={tx_status}, no transition",
                "payment_status": "PENDING",
                "booking_status": "HOLD",
            }

        # Ejecutar transición atómica
        logger.info("Signature verified — executing atomic transition for %s", tx_reference)

        result = pg_query(
            "SELECT * FROM fn_odi_confirm_payment(%s, %s, %s::jsonb)",
            (tx_reference, tx_id, json.dumps(tx_data)),
        )

        if result and len(result) > 0:
            row = result[0]
            if row.get("ok"):
                logger.info(
                    "Atomic transition executed — payment=%s booking=%s COMMIT successful",
                    row.get("payment_status"),
                    row.get("booking_status"),
                )
                return {
                    "ok": True,
                    "detail": "Atomic transition executed. COMMIT successful",
                    "payment_status": row.get("payment_status", "CAPTURED"),
                    "booking_status": row.get("booking_status", "CONFIRMED"),
                }
            else:
                logger.warning("Atomic transition failed: %s", row.get("error"))
                return {
                    "ok": False,
                    "detail": row.get("error", "Unknown DB error"),
                    "payment_status": row.get("payment_status", "UNKNOWN"),
                    "booking_status": row.get("booking_status", "UNKNOWN"),
                }
        else:
            logger.error("fn_odi_confirm_payment returned no result for %s", tx_reference)
            return {
                "ok": False,
                "detail": "Database function returned no result",
                "payment_status": "UNKNOWN",
                "booking_status": "UNKNOWN",
            }

    except Exception as e:
        logger.exception("Webhook processing error: %s", e)
        return {
            "ok": False,
            "detail": f"Internal error: {e}",
            "payment_status": "UNKNOWN",
            "booking_status": "UNKNOWN",
        }
