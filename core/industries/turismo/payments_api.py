#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Payment API Routes — Endpoints PAEM para pagos Wompi
=====================================================
POST /paem/pay/init    -> Iniciar checkout con firma de integridad
POST /webhooks/wompi   -> Webhook de eventos Wompi (APPROVED -> CAPTURED)

Se monta como APIRouter en el PAEM API (puerto 8807).

Version: 1.2.0 — 14 Feb 2026
  v1.1.0: hardened (audit logging, event validation, debug disabled)
  v1.2.0: V8.1 Guardian + Decision Logger pre-Wompi
"""

import json
import logging
import sys
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.industries.turismo.db.client import pg_query, pg_execute
from core.industries.turismo.payments_wompi import (
    generate_checkout_payload,
    process_webhook_event,
    validate_webhook_signature,
    validate_webhook_event,
)

# V8.1 — Guardian + Decision Logger
sys.path.insert(0, "/opt/odi/core")
try:
    from odi_personalidad import obtener_personalidad
    from odi_decision_logger import obtener_logger
    _V81_ENABLED = True
except ImportError:
    _V81_ENABLED = False

logger = logging.getLogger("odi.paem.payments.api")

router = APIRouter(tags=["PAEM Payments"])


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════════════════════════════════

class PayInitRequest(BaseModel):
    """Request para iniciar un pago Wompi."""
    transaction_id: str = Field(..., description="ID de transaccion PAEM")
    booking_id: str = Field(..., description="ID del booking en HOLD")
    deposit_amount_cop: Decimal = Field(..., gt=0, description="Monto en COP")
    usuario_id: Optional[str] = Field(None, description="ID del usuario (V8.1)")


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/paem/pay/init")
async def pay_init(data: PayInitRequest):
    """
    Iniciar flujo de pago Wompi.

    V8.1: Guardian evalua ANTES de generar checkout.
    0. [V8.1] Guardian evalua estado + Decision Logger
    1. Valida que el booking existe y esta en HOLD
    2. Valida/crea payment en PENDING (idempotente)
    3. Genera firma SHA256 de integridad
    4. Retorna payload listo para el widget de checkout
    """
    odi_event_id = None
    uid = data.usuario_id or "ANONYMOUS"

    # ═══ V8.1: GUARDIAN PRE-WOMPI ═══
    if _V81_ENABLED:
        try:
            personalidad = obtener_personalidad()
            audit_logger = obtener_logger()

            # Guardian evalua
            estado = personalidad.evaluar_estado(
                usuario_id=uid,
                mensaje="",
                contexto={"precio_final": int(data.deposit_amount_cop)}
            )

            if estado["color"] not in ("verde",):
                # BLOQUEAR — No generar checkout
                odi_event_id = await audit_logger.log_decision(
                    intent="PAY_INIT_BLOQUEADO",
                    estado_guardian=estado["color"],
                    modo_aplicado="SUPERVISADO",
                    usuario_id=uid,
                    vertical="P2",
                    motivo=estado.get("motivo", "Estado no verde"),
                    monto_cop=int(data.deposit_amount_cop),
                    transaction_id=data.transaction_id,
                    decision_path=["evaluar_estado", "riesgo_detectado", "bloqueo_pago"]
                )
                logger.warning(
                    "V8.1 Guardian BLOCK: tx=%s estado=%s motivo=%s event=%s",
                    data.transaction_id, estado["color"],
                    estado.get("motivo"), odi_event_id
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "ok": False,
                        "error": "guardian_block",
                        "motivo": estado.get("motivo"),
                        "odi_event_id": odi_event_id
                    }
                )

            # Estado VERDE — log autorizacion
            odi_event_id = await audit_logger.log_decision(
                intent="PAY_INIT_AUTORIZADO",
                estado_guardian="verde",
                modo_aplicado="AUTOMATICO",
                usuario_id=uid,
                vertical="P2",
                motivo="Estado verde, pago autorizado",
                monto_cop=int(data.deposit_amount_cop),
                transaction_id=data.transaction_id,
                decision_path=["evaluar_estado", "estado_verde", "autorizar_pago"]
            )
            logger.info(
                "V8.1 Guardian OK: tx=%s event=%s",
                data.transaction_id, odi_event_id
            )
        except Exception as e:
            # V8.1 falla gracefully — no bloquear el flujo existente
            logger.error("V8.1 Guardian error (non-blocking): %s", e)

    # ═══ FLUJO EXISTENTE (intacto) ═══

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

    response = {
        "ok": True,
        "checkout": payload,
    }
    if odi_event_id:
        response["odi_event_id"] = odi_event_id

    return response


@router.post("/paem/webhooks/wompi")
async def wompi_webhook_paem(request: Request):
    """Alias canonico bajo /paem/ para el webhook Wompi."""
    return await wompi_webhook(request)


@router.post("/webhooks/wompi")
async def wompi_webhook(request: Request):
    """
    Webhook de eventos Wompi.

    1. Log de auditoria con IP origen
    2. Valida firma SHA256 (x-event-checksum + x-event-timestamp)
    3. Valida timestamp (replay protection: 5 min window)
    4. Valida tipo de evento (solo transaction.updated)
    5. Si evento APPROVED -> transicion atomica:
       - odi_payments:        PENDING -> CAPTURED
       - odi_health_bookings: HOLD -> CONFIRMED
       - odi_events:          PAEM.PAYMENT_SUCCESS
    6. Idempotente: si ya CAPTURED, retorna 200 sin re-procesar
    """
    raw_body = await request.body()

    # Audit log: IP + headers
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        "Webhook incoming: ip=%s content_length=%d user_agent=%s",
        client_ip,
        len(raw_body),
        request.headers.get("user-agent", "none"),
    )

    # 1. Validar firma + timestamp
    signature = request.headers.get("x-event-checksum")
    timestamp = request.headers.get("x-event-timestamp")

    valid, reason = validate_webhook_signature(raw_body, signature, timestamp)

    if not valid:
        logger.warning(
            "Webhook REJECTED: ip=%s reason=%s checksum=%s",
            client_ip, reason, (signature or "none")[:16],
        )
        raise HTTPException(status_code=403, detail=reason)

    # 2. Parsear evento
    try:
        event = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning("Webhook REJECTED: ip=%s reason=invalid_json", client_ip)
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # 3. Validar estructura y tipo de evento
    valid, reason = validate_webhook_event(event)
    if not valid:
        logger.warning("Webhook REJECTED: ip=%s reason=%s", client_ip, reason)
        raise HTTPException(status_code=400, detail=reason)

    # 4. Procesar
    result = process_webhook_event(event)

    logger.info(
        "Webhook result: ip=%s ok=%s payment=%s booking=%s ref=%s",
        client_ip,
        result.get("ok"),
        result.get("payment_status"),
        result.get("booking_status"),
        event.get("data", {}).get("transaction", {}).get("reference", "?"),
    )

    return result
