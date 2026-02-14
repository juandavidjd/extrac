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
  - validate_webhook_signature():   Validación con replay protection
  - process_webhook():              Transición atómica DB

Versión: 1.1.0 — 14 Feb 2026 (hardened: replay protection, event validation, idempotency)
"""

import hashlib
import hmac
import json
import logging
import os
import time
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

# Replay protection: reject webhooks older than this (seconds)
WEBHOOK_TIMESTAMP_TOLERANCE = int(os.getenv("WOMPI_TIMESTAMP_TOLERANCE", "300"))

# Valid Wompi event types we process
VALID_EVENT_TYPES = {"transaction.updated"}


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
    Validar firma del webhook de Wompi con replay protection.
    Cadena: {timestamp}{raw_body}{events_secret}
    Retorna: (valid: bool, reason: str)
    """
    if not signature_header or not timestamp_header:
        logger.warning("Webhook rejected: missing signature or timestamp headers")
        return False, "Missing signature or timestamp headers"

    if not WOMPI_EVENTS_SECRET:
        logger.error("WOMPI_EVENTS_KEY not configured — rejecting webhook (production mode)")
        return False, "Events secret not configured — webhook rejected"

    # Replay protection: reject old timestamps
    try:
        ts = int(timestamp_header)
        now = int(time.time())
        age = abs(now - ts)
        if age > WEBHOOK_TIMESTAMP_TOLERANCE:
            logger.warning(
                "Webhook rejected: timestamp too old (age=%ds, tolerance=%ds, ts=%s)",
                age, WEBHOOK_TIMESTAMP_TOLERANCE, timestamp_header,
            )
            return False, f"Timestamp too old ({age}s > {WEBHOOK_TIMESTAMP_TOLERANCE}s tolerance)"
    except (ValueError, TypeError):
        logger.warning("Webhook rejected: invalid timestamp format: %s", timestamp_header)
        return False, "Invalid timestamp format"

    # Signature validation (Wompi spec: SHA256 of timestamp+body+secret)
    raw_message = f"{timestamp_header}{raw_body.decode('utf-8')}{WOMPI_EVENTS_SECRET}"
    expected = hashlib.sha256(raw_message.encode("utf-8")).hexdigest()

    if hmac.compare_digest(expected, signature_header):
        return True, "Webhook integrity check passed"
    else:
        logger.warning("Webhook rejected: signature mismatch (expected=%s...)", expected[:16])
        return False, "Invalid webhook signature"


def validate_webhook_event(event: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validar estructura y tipo del evento Wompi.
    Solo procesa event types conocidos.
    """
    event_type = event.get("event")
    if not event_type:
        return False, "Missing 'event' field in payload"

    if event_type not in VALID_EVENT_TYPES:
        logger.warning("Webhook ignored: unknown event type '%s'", event_type)
        return False, f"Unknown event type: {event_type}"

    tx_data = event.get("data", {}).get("transaction", {})
    if not tx_data:
        return False, "Missing transaction data in event"

    if not tx_data.get("reference"):
        return False, "Missing transaction reference"

    if not tx_data.get("status"):
        return False, "Missing transaction status"

    return True, "Event structure valid"


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
        # Validate event structure
        valid, reason = validate_webhook_event(event)
        if not valid:
            logger.warning("Webhook event validation failed: %s", reason)
            return {"ok": False, "detail": reason, "payment_status": "UNKNOWN", "booking_status": "UNKNOWN"}

        tx_data = event.get("data", {}).get("transaction", {})
        tx_reference = tx_data.get("reference")
        tx_status = tx_data.get("status")
        tx_id = tx_data.get("id", "")

        logger.info("Webhook received: ref=%s status=%s gateway_id=%s", tx_reference, tx_status, tx_id)

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

        # Idempotency guard: check if already processed before expensive DB call
        existing = pg_query(
            "SELECT status FROM odi_payments WHERE idempotency_key = %s",
            (tx_reference,),
        )
        if existing and len(existing) > 0 and existing[0].get("status") == "CAPTURED":
            logger.info("Idempotent: payment %s already CAPTURED, skipping", tx_reference)
            return {
                "ok": True,
                "detail": "Payment already captured (idempotent)",
                "payment_status": "CAPTURED",
                "booking_status": "CONFIRMED",
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
