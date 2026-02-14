"""
ODI WhatsApp Webhook Handler v1.0
=================================
Maneja mensajes de WhatsApp via Meta Cloud API.
Integra LLM Failover para generacion de respuestas.

Endpoints:
  GET  /v1/webhook/whatsapp       - Verificacion Meta
  POST /v1/webhook/whatsapp       - Recibir mensajes
  POST /v1/webhook/whatsapp/test  - Test sin Meta
  GET  /v1/webhook/whatsapp/status - Estado del sistema
"""

import os
import json
import hmac
import hashlib
import logging
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel

# LLM Failover
import sys
sys.path.insert(0, "/opt/odi/core")
from llm_failover import LLMFailover, Provider

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("whatsapp")

router = APIRouter(prefix="/v1/webhook/whatsapp", tags=["whatsapp"])

# Config
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "odi_whatsapp_verify_2026")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "969496722915650")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET")

# LLM con system prompt para ODI
llm = LLMFailover(
    system_prompt="""Eres ODI, asistente experto de repuestos de motos.
Responde de forma concisa, amigable y util.
Si no sabes algo, admitelo honestamente.
Formato: texto plano, sin markdown ni emojis excesivos.
Maximo 300 palabras."""
)

# Estadisticas
stats = {
    "messages_received": 0,
    "messages_sent": 0,
    "errors": 0,
    "last_message": None,
    "providers_used": {}
}


class WhatsAppMessage(BaseModel):
    phone: str
    message: str
    name: Optional[str] = None


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verifica firma HMAC de Meta."""
    if not WHATSAPP_APP_SECRET or not signature:
        return True  # Skip en dev

    expected = "sha256=" + hmac.new(
        WHATSAPP_APP_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


async def send_whatsapp_message(phone: str, text: str) -> bool:
    """Envia mensaje via WhatsApp Cloud API."""
    if not WHATSAPP_TOKEN:
        log.warning("WHATSAPP_TOKEN not configured")
        return False

    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text}
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                stats["messages_sent"] += 1
                return True
            else:
                log.error(f"WhatsApp API error: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        log.error(f"WhatsApp send error: {e}")
        return False


def extract_message_from_webhook(data: Dict) -> Optional[Dict]:
    """Extrae mensaje del payload de Meta."""
    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return None

        msg = messages[0]
        contacts = value.get("contacts", [{}])
        contact = contacts[0] if contacts else {}

        return {
            "phone": msg.get("from"),
            "message": msg.get("text", {}).get("body", ""),
            "name": contact.get("profile", {}).get("name"),
            "msg_id": msg.get("id"),
            "timestamp": msg.get("timestamp")
        }
    except Exception as e:
        log.error(f"Error extracting message: {e}")
        return None


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """Verificacion de webhook de Meta."""
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        log.info("WhatsApp webhook verified")
        return int(hub_challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("")
async def receive_webhook(request: Request):
    """Recibe mensajes de WhatsApp via Meta Cloud API."""
    # Verificar firma
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()

    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()

    # Extraer mensaje
    msg_data = extract_message_from_webhook(data)
    if not msg_data or not msg_data.get("message"):
        return {"status": "ok", "action": "ignored"}

    stats["messages_received"] += 1
    stats["last_message"] = datetime.now().isoformat()

    phone = msg_data["phone"]
    message = msg_data["message"]
    name = msg_data.get("name", "Usuario")

    log.info(f"[{phone}] {name}: {message}")

    # Generar respuesta con LLM Failover
    try:
        prompt = f"Usuario {name} pregunta: {message}"
        response = llm.generate(prompt)

        # Track provider usage
        provider = response.provider
        stats["providers_used"][provider] = stats["providers_used"].get(provider, 0) + 1

        # Enviar respuesta
        await send_whatsapp_message(phone, response.content)

        log.info(f"[{phone}] ODI ({provider}, {response.latency_ms}ms): {response.content[:100]}...")

        return {
            "status": "ok",
            "provider": provider,
            "latency_ms": response.latency_ms
        }

    except Exception as e:
        stats["errors"] += 1
        log.error(f"Error processing message: {e}")

        # Enviar mensaje de error amigable
        await send_whatsapp_message(
            phone,
            "Disculpa, tuve un problema procesando tu mensaje. Por favor intenta de nuevo."
        )

        return {"status": "error", "detail": str(e)}


@router.post("/test")
async def test_message(
    phone: str = Query(..., description="Numero de telefono"),
    message: str = Query(..., description="Mensaje de prueba"),
    provider: str = Query(None, description="Forzar proveedor: gemini, openai, claude, groq")
):
    """Endpoint de prueba sin pasar por Meta."""
    stats["messages_received"] += 1
    stats["last_message"] = datetime.now().isoformat()

    log.info(f"[TEST] {phone}: {message}")

    # Generar respuesta con LLM Failover
    try:
        prompt = f"Usuario pregunta: {message}"
        
        # Map provider string to enum
        preferred = None
        if provider:
            provider_map = {"gemini": Provider.GEMINI, "openai": Provider.OPENAI, 
                          "claude": Provider.CLAUDE, "groq": Provider.GROQ}
            preferred = provider_map.get(provider.lower())
        
        response = llm.generate(prompt, preferred_provider=preferred)

        provider = response.provider
        stats["providers_used"][provider] = stats["providers_used"].get(provider, 0) + 1

        log.info(f"[TEST] ODI ({provider}, {response.latency_ms}ms): {response.content[:100]}...")

        return {
            "status": "ok",
            "phone": phone,
            "input": message,
            "response": response.content,
            "provider": provider,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "fallback_chain": response.fallback_chain
        }

    except Exception as e:
        stats["errors"] += 1
        log.error(f"Test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Estado del sistema WhatsApp + LLM."""
    # Test LLM providers
    llm_status = {}
    for provider in Provider:
        if provider == Provider.LOBOTOMY:
            llm_status[provider.value] = "fallback"
        elif llm.api_keys.get(provider):
            llm_status[provider.value] = "configured"
        else:
            llm_status[provider.value] = "no_key"

    return {
        "status": "healthy",
        "service": "odi-whatsapp",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "whatsapp": {
            "phone_id": WHATSAPP_PHONE_ID,
            "token_configured": bool(WHATSAPP_TOKEN),
            "verify_token": WHATSAPP_VERIFY_TOKEN
        },
        "llm_chain": ["gemini", "openai", "claude", "groq", "lobotomy"],
        "llm_providers": llm_status,
        "stats": stats
    }
