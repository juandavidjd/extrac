#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Payment API Routes — Endpoints PAEM para pagos Wompi
=====================================================
POST /paem/pay/init    → Iniciar checkout con firma de integridad
POST /webhooks/wompi   → Webhook de eventos Wompi (APPROVED → CAPTURED)

Se monta como APIRouter en el PAEM API (puerto 8807).

Versión: 1.0.0 — 13 Feb 2026
"""

import json
import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.industries.turismo.db.client import pg_query, pg_execute
from core.industries.turismo.payments_wompi import (
    generate_checkout_payload,
    process_webhook_event,
    validate_webhook_signature,
)

logger = logging.getLogger("odi.paem.payments.api")

router = APIRouter(tags=["PAEM Payments"])


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════════════════════════════════

class PayInitRequest(BaseModel):
    """Request para iniciar un pago Wompi."""
    transaction_id: str = Field(..., description="ID de transacción PAEM")
    booking_id: str = Field(..., description="ID del booking en HOLD")
    deposit_amount_cop: Decimal = Field(..., gt=0, description="Monto en COP")


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/paem/pay/init")
async def pay_init(data: PayInitRequest):
    """
    Iniciar flujo de pago Wompi.

    1. Valida que el booking existe y está en HOLD
    2. Valida/crea payment en PENDING (idempotente)
    3. Genera firma SHA256 de integridad
    4. Retorna payload listo para el widget de checkout
    """
    # 1. Validar booking en HOLD
    booking = pg_query(
        """SELECT booking_id, status, hold_expires_at
             FROM odi_health_bookings
            WHERE booking_id = %s AND transaction_id = %s""",
        (data.booking_id, data.transaction_id),
    )

    if not booking or len(booking) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Booking {data.booking_id} not found for transaction {data.transaction_id}",
        )

    bk = booking[0]
    if bk["status"] != "HOLD":
        raise HTTPException(
            status_code=409,
            detail=f"Booking status is {bk['status']}, expected HOLD",
        )

    # 2. UPSERT payment (idempotente por idempotency_key)
    existing_payment = pg_query(
        """SELECT id, status FROM odi_payments
            WHERE idempotency_key = %s""",
        (data.transaction_id,),
    )

    if existing_payment and len(existing_payment) > 0:
        pay = existing_payment[0]
        if pay["status"] == "CAPTURED":
            raise HTTPException(
                status_code=409,
                detail="Payment already captured",
            )
        # Payment exists in PENDING — continue to generate checkout
    else:
        # Crear payment en PENDING
        ok = pg_execute(
            """INSERT INTO odi_payments
                   (transaction_id, booking_id, gateway_name, amount, currency, status, idempotency_key)
               VALUES (%s, %s, 'wompi', %s, 'COP', 'PENDING', %s)
               ON CONFLICT (idempotency_key) DO NOTHING""",
            (data.transaction_id, data.booking_id, float(data.deposit_amount_cop), data.transaction_id),
        )
        if not ok:
            raise HTTPException(
                status_code=500,
                detail="Failed to create payment record",
            )

    # 3. Registrar evento
    pg_execute(
        """INSERT INTO odi_events (event_type, transaction_id, booking_id, payload)
           VALUES ('PAEM.PAY_INIT', %s, %s, %s::jsonb)""",
        (
            data.transaction_id,
            data.booking_id,
            json.dumps({"amount_cop": float(data.deposit_amount_cop)}),
        ),
    )

    # 4. Generar payload de checkout
    payload = generate_checkout_payload(
        transaction_id=data.transaction_id,
        amount_cop=data.deposit_amount_cop,
    )

    logger.info(
        "Pay init: tx=%s booking=%s amount=%s COP",
        data.transaction_id, data.booking_id, data.deposit_amount_cop,
    )

    return {
        "ok": True,
        "checkout": payload,
    }


@router.post("/paem/webhooks/wompi")
async def wompi_webhook_paem(request: Request):
    """Alias canónico bajo /paem/ para el webhook Wompi."""
    return await wompi_webhook(request)


@router.post("/paem/_debug/mock_webhook")
async def debug_mock_webhook(request: Request):
    """
    Mock webhook deshabilitado en producción.
    Solo disponible si ODI_DEBUG=1 en variables de entorno.
    """
    import os

    if os.getenv("ODI_DEBUG", "0") != "1":
        raise HTTPException(
            status_code=403,
            detail="Debug endpoint disabled in production",
        )

    body = await request.json()
    tx_id = body.get("transaction_id")
    if not tx_id:
        raise HTTPException(status_code=400, detail="transaction_id required")

    mock_event = {
        "event": "transaction.updated",
        "data": {
            "transaction": {
                "id": f"mock-wompi-{tx_id}",
                "reference": tx_id,
                "status": "APPROVED",
                "amount_in_cents": 0,
                "currency": "COP",
            }
        },
    }

    result = process_webhook_event(mock_event)
    logger.info("Mock webhook (DEBUG): tx=%s result=%s", tx_id, result)
    return result


@router.post("/webhooks/wompi")
async def wompi_webhook(request: Request):
    """
    Webhook de eventos Wompi.

    1. Valida firma HMAC (x-event-checksum + x-event-timestamp)
    2. Si evento APPROVED → transición atómica:
       - odi_payments:        PENDING → CAPTURED
       - odi_health_bookings: HOLD → CONFIRMED
       - odi_events:          PAEM.PAYMENT_SUCCESS
    3. Idempotente: si ya CAPTURED, retorna 200 sin re-procesar
    """
    raw_body = await request.body()

    # 1. Validar firma
    signature = request.headers.get("x-event-checksum")
    timestamp = request.headers.get("x-event-timestamp")

    valid, reason = validate_webhook_signature(raw_body, signature, timestamp)
    logger.info("Webhook signature validation: %s — %s", valid, reason)

    if not valid:
        raise HTTPException(status_code=403, detail=reason)

    # 2. Parsear evento
    try:
        event = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # 3. Procesar
    result = process_webhook_event(event)

    logger.info(
        "Webhook result: ok=%s payment=%s booking=%s",
        result.get("ok"),
        result.get("payment_status"),
        result.get("booking_status"),
    )

    return result
