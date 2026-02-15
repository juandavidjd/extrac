"""
ODI WhatsApp Webhook Handler v1.1 + ChromaDB RAG
================================================
"""

import os
import json
import hmac
import hashlib
import logging
import httpx
import chromadb
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel

import sys
sys.path.insert(0, "/opt/odi/core")
from llm_failover import LLMFailover, Provider

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("whatsapp")

router = APIRouter(prefix="/v1/webhook/whatsapp", tags=["whatsapp"])

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "odi_whatsapp_verify_2026")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "969496722915650")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET")

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = "odi_ind_motos"

try:
    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    chroma_collection = chroma_client.get_collection(CHROMA_COLLECTION)
    log.info(f"ChromaDB connected: {chroma_collection.count()} docs in {CHROMA_COLLECTION}")
except Exception as e:
    log.warning(f"ChromaDB connection failed: {e}")
    chroma_collection = None

SYSTEM_PROMPT = """Eres ODI, asistente experto de repuestos de motos en Colombia.
Tu rol es ayudar a clientes a encontrar repuestos usando el catalogo de productos.

INSTRUCCIONES:
- Si recibes PRODUCTOS ENCONTRADOS, usales para responder con precios y detalles reales
- Menciona el proveedor/tienda de cada producto
- Si hay varios productos, presenta los mas relevantes (max 3-4)
- Formato: texto plano, conciso, amigable
- Si no hay productos relevantes, sugiere que el cliente describa mejor lo que busca
- Maximo 200 palabras"""

llm = LLMFailover(system_prompt=SYSTEM_PROMPT)

stats = {
    "messages_received": 0,
    "messages_sent": 0,
    "errors": 0,
    "last_message": None,
    "providers_used": {},
    "chromadb_queries": 0
}


def search_products(query: str, n_results: int = 5) -> List[Dict]:
    if not chroma_collection:
        return []
    try:
        results = chroma_collection.query(query_texts=[query], n_results=n_results)
        stats["chromadb_queries"] += 1
        products = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                products.append({
                    "content": doc,
                    "store": meta.get("store", ""),
                    "sku": meta.get("sku", ""),
                    "price": meta.get("price", ""),
                    "title": meta.get("title", "")
                })
        return products
    except Exception as e:
        log.error(f"ChromaDB search error: {e}")
        return []


def build_rag_prompt(user_message: str, products: List[Dict], user_name: str = "Usuario") -> str:
    prompt = f"{user_name} pregunta: {user_message}\n\n"
    if products:
        prompt += "PRODUCTOS ENCONTRADOS EN CATALOGO:\n"
        prompt += "-" * 40 + "\n"
        for i, p in enumerate(products, 1):
            prompt += f"{i}. [{p['store']}] {p['title']}\n"
            prompt += f"   SKU: {p['sku']} | Precio: ${p['price']} COP\n"
        prompt += "-" * 40 + "\n"
        prompt += "\nUsa estos productos para responder al cliente."
    else:
        prompt += "(No se encontraron productos relacionados en el catalogo)"
    return prompt


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    if not WHATSAPP_APP_SECRET or not signature:
        return True
    expected = "sha256=" + hmac.new(WHATSAPP_APP_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def send_whatsapp_message(phone: str, text: str) -> bool:
    if not WHATSAPP_TOKEN:
        log.warning("WHATSAPP_TOKEN not configured")
        return False
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": text}}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                stats["messages_sent"] += 1
                return True
            log.error(f"WhatsApp API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log.error(f"WhatsApp send error: {e}")
        return False


def extract_message_from_webhook(data: Dict) -> Optional[Dict]:
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
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        log.info("WhatsApp webhook verified")
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("")
async def receive_webhook(request: Request):
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    data = await request.json()
    msg_data = extract_message_from_webhook(data)
    if not msg_data or not msg_data.get("message"):
        return {"status": "ok", "action": "ignored"}
    stats["messages_received"] += 1
    stats["last_message"] = datetime.now().isoformat()
    phone = msg_data["phone"]
    message = msg_data["message"]
    name = msg_data.get("name", "Usuario")
    log.info(f"[{phone}] {name}: {message}")
    try:
        products = search_products(message, n_results=5)
        log.info(f"[{phone}] ChromaDB: {len(products)} productos encontrados")
        prompt = build_rag_prompt(message, products, name)
        response = llm.generate(prompt)
        provider = response.provider
        stats["providers_used"][provider] = stats["providers_used"].get(provider, 0) + 1
        await send_whatsapp_message(phone, response.content)
        log.info(f"[{phone}] ODI ({provider}, {response.latency_ms}ms): {response.content[:100]}...")
        return {"status": "ok", "provider": provider, "latency_ms": response.latency_ms, "products_found": len(products)}
    except Exception as e:
        stats["errors"] += 1
        log.error(f"Error processing message: {e}")
        await send_whatsapp_message(phone, "Disculpa, tuve un problema procesando tu mensaje. Por favor intenta de nuevo.")
        return {"status": "error", "detail": str(e)}


@router.post("/test")
async def test_message(
    phone: str = Query(..., description="Numero de telefono"),
    message: str = Query(..., description="Mensaje de prueba"),
    provider: str = Query(None, description="Forzar proveedor: gemini, openai, claude, groq")
):
    stats["messages_received"] += 1
    stats["last_message"] = datetime.now().isoformat()
    log.info(f"[TEST] {phone}: {message}")
    try:
        products = search_products(message, n_results=5)
        log.info(f"[TEST] ChromaDB: {len(products)} productos encontrados")
        prompt = build_rag_prompt(message, products)
        preferred = None
        if provider:
            provider_map = {"gemini": Provider.GEMINI, "openai": Provider.OPENAI, "claude": Provider.CLAUDE, "groq": Provider.GROQ}
            preferred = provider_map.get(provider.lower())
        response = llm.generate(prompt, preferred_provider=preferred)
        provider_used = response.provider
        stats["providers_used"][provider_used] = stats["providers_used"].get(provider_used, 0) + 1
        log.info(f"[TEST] ODI ({provider_used}, {response.latency_ms}ms): {response.content[:100]}...")
        return {
            "status": "ok", "phone": phone, "input": message, "response": response.content,
            "provider": provider_used, "model": response.model, "latency_ms": response.latency_ms,
            "fallback_chain": response.fallback_chain, "products_found": len(products),
            "products": [{"store": p["store"], "title": p["title"], "price": p["price"]} for p in products[:3]]
        }
    except Exception as e:
        stats["errors"] += 1
        log.error(f"Test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    llm_status = {}
    for provider in Provider:
        if provider == Provider.LOBOTOMY:
            llm_status[provider.value] = "fallback"
        elif llm.api_keys.get(provider):
            llm_status[provider.value] = "configured"
        else:
            llm_status[provider.value] = "no_key"
    chroma_docs = 0
    try:
        if chroma_collection:
            chroma_docs = chroma_collection.count()
    except:
        pass
    chroma_status = {"connected": chroma_collection is not None, "collection": CHROMA_COLLECTION, "docs": chroma_docs}
    return {
        "status": "healthy", "service": "odi-whatsapp", "version": "1.1.0",
        "timestamp": datetime.now().isoformat(),
        "whatsapp": {"phone_id": WHATSAPP_PHONE_ID, "token_configured": bool(WHATSAPP_TOKEN), "verify_token": WHATSAPP_VERIFY_TOKEN},
        "chromadb": chroma_status, "llm_chain": ["gemini", "openai", "claude", "groq", "lobotomy"],
        "llm_providers": llm_status, "stats": stats
    }
