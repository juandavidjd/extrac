"""
ODI WhatsApp Webhook Handler v1.2 + Meta Intents + P2 SALUD
===========================================================
"""

import os
import re
import json
import hmac
import hashlib
import logging
import httpx
import chromadb
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
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

# Lista oficial de 15 proveedores ODI
ODI_EMPRESAS = [
    "ARMOTOS", "BARA", "CBI", "DFG", "DUNA", "IMBRA", "JAPAN", "KAIQI",
    "LEO", "MCLMOTOS", "OH IMPORTACIONES", "STORE", "VAISAND", "VITTON", "YOKOMAR"
]

SYSTEM_PROMPT = """Eres ODI, el Organismo Digital Industrial de La Roca Motorepuestos.
Conectas 15 proveedores de repuestos de motos en Colombia.

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
    "chromadb_queries": 0,
    "meta_intents": 0,
    "salud_intents": 0
}


# =============================================================================
# PASO 1: META INTENTS - Identidad ODI (NO pasan por RAG)
# =============================================================================

def detect_meta_intent(message: str, user_name: str = "Usuario") -> Optional[str]:
    """
    Detecta meta-intents que NO deben pasar por el RAG.
    Retorna respuesta directa o None si debe continuar al RAG.
    """
    msg = message.lower().strip()

    # Intent: Identidad ODI
    identity_patterns = [
        r"qui[eé]n eres", r"qu[eé] eres", r"c[oó]mo te llamas",
        r"eres un bot", r"eres humano", r"con qui[eé]n hablo"
    ]
    for pattern in identity_patterns:
        if re.search(pattern, msg):
            return (
                "Soy ODI, el Organismo Digital Industrial de La Roca Motorepuestos. "
                "Conecto 15 proveedores de repuestos de motos en Colombia. "
                "Preguntame por cualquier repuesto y te muestro opciones con precios reales."
            )

    # Intent: Saludo
    greeting_patterns = [
        r"^hola\b", r"^buenos d[ií]as", r"^buenas tardes", r"^buenas noches",
        r"^hey\b", r"^saludos"
    ]
    for pattern in greeting_patterns:
        if re.search(pattern, msg):
            hour = datetime.now().hour
            if hour < 12:
                saludo = "Buenos dias"
            elif hour < 18:
                saludo = "Buenas tardes"
            else:
                saludo = "Buenas noches"
            return (
                f"{saludo}, {user_name}! Soy ODI, tu asistente de repuestos de motos. "
                "Dime que repuesto necesitas y te muestro opciones de nuestros 15 proveedores."
            )

    # Intent: Lista de empresas
    empresas_patterns = [
        r"qu[eé] empresas", r"cu[aá]les empresas", r"lista.*empresas",
        r"qu[eé] proveedores", r"cu[aá]les proveedores", r"lista.*proveedores",
        r"qu[eé] tiendas", r"cu[aá]ntas tiendas", r"cu[aá]ntos proveedores"
    ]
    for pattern in empresas_patterns:
        if re.search(pattern, msg):
            empresas_str = ", ".join(ODI_EMPRESAS)
            return (
                f"ODI conecta 15 proveedores de repuestos de motos:\n\n"
                f"{empresas_str}\n\n"
                "Preguntame por cualquier repuesto y te muestro las mejores opciones."
            )

    return None


# =============================================================================
# PASO 2: P2 SALUD INTENT - Turismo Dental
# =============================================================================

def detect_salud_intent(message: str) -> Optional[str]:
    """
    Detecta intents de turismo dental / salud.
    Si PAEM esta disponible, redirige. Si no, responde con info basica.
    """
    msg = message.lower().strip()

    salud_keywords = [
        "dentista", "dental", "odontolog", "turismo dental", "implante",
        "bruxismo", "ortodoncia", "blanqueamiento", "caries", "carilla",
        "corona dental", "endodoncia", "periodoncia", "protesis dental"
    ]

    if not any(kw in msg for kw in salud_keywords):
        return None

    # Verificar si PAEM esta vivo
    paem_alive = False
    try:
        import requests
        r = requests.get("http://localhost:8807/health", timeout=2)
        paem_alive = r.status_code == 200
    except:
        pass

    if paem_alive:
        return (
            "Tenemos servicios de turismo dental en Cartagena, Colombia. "
            "Ahorro de 60-80% vs USA/Europa. Procedimientos disponibles:\n\n"
            "- Diseno de sonrisa: $2,800-$5,500 USD\n"
            "- Implantes dentales: $800-$2,000 USD\n"
            "- Carillas: $250-$450 USD/unidad\n"
            "- Blanqueamiento: $150-$300 USD\n\n"
            "Para agendar una valoracion, escribe 'AGENDAR DENTAL' o contacta directamente."
        )
    else:
        return (
            "Tenemos servicios de turismo dental en Colombia con ahorro de 60-80% vs USA/Europa. "
            "Para mas informacion, contacta directamente a nuestro equipo de salud."
        )


# =============================================================================
# PASO 3: Intent no-motos generico
# =============================================================================

def detect_non_moto_intent(message: str) -> Optional[str]:
    """
    Detecta si el usuario pregunta por algo que NO es motos ni salud.
    """
    msg = message.lower().strip()

    non_moto_patterns = [
        r"soy (panadero|chef|abogado|contador|ingeniero|arquitecto)",
        r"tengo (restaurante|tienda de ropa|negocio de)",
        r"vendo (comida|ropa|zapatos|tecnolog)",
        r"emprendimiento.*(comida|restaurante|ropa)"
    ]

    for pattern in non_moto_patterns:
        if re.search(pattern, msg):
            return (
                "ODI se especializa en repuestos de motos y turismo dental. "
                "Si tienes alguna moto o conoces a alguien que necesite repuestos, "
                "estoy para ayudarte con precios de 15 proveedores."
            )

    return None


# =============================================================================
# Core Functions
# =============================================================================

def search_knowledge(query: str, n_results: int = 8) -> List[Dict]:
    """
    Busca en TODA la base de conocimiento: productos, info tecnica, educativo.
    """
    if not chroma_collection:
        return []
    try:
        results = chroma_collection.query(query_texts=[query], n_results=n_results)
        stats["chromadb_queries"] += 1
        items = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                items.append({
                    "content": doc,
                    "type": meta.get("type", "unknown"),
                    "store": meta.get("store", ""),
                    "sku": meta.get("sku", ""),
                    "price": meta.get("price", 0),
                    "title": meta.get("title", ""),
                    "filename": meta.get("filename", ""),
                    "category": meta.get("category", ""),
                    "folder": meta.get("folder", ""),
                })
        return items
    except Exception as e:
        log.error(f"ChromaDB search error: {e}")
        return []


def search_products(query: str, n_results: int = 5) -> List[Dict]:
    """Alias para compatibilidad."""
    return search_knowledge(query, n_results)


def build_rag_prompt(user_message: str, items: List[Dict], user_name: str = "Usuario") -> str:
    prompt = f"{user_name} pregunta: {user_message}\n\n"
    
    # Separar por tipo
    products = [i for i in items if i.get("type") in ("product", "kb_chunk")]
    technical = [i for i in items if i.get("type") in ("kb_technical", "kb_manual")]
    educational = [i for i in items if i.get("type") in ("kb_sales_training", "kb_health", "kb_values", "kb_marketing", "kb_tutorial", "kb_business")]
    vendor = [i for i in items if i.get("type") == "kb_vendor_catalog"]
    
    has_content = False
    
    if products:
        has_content = True
        prompt += "PRODUCTOS DISPONIBLES:\n"
        prompt += "-" * 40 + "\n"
        for idx, p in enumerate(products[:4], 1):
            price = p.get("price", 0) or 0
            price_str = f"${int(price):,} COP" if price > 0 else "Consultar"
            prompt += f"{idx}. [{p.get('store','')}] {p.get('title','')}\n"
            prompt += f"   SKU: {p.get('sku','')} | Precio: {price_str}\n"
        prompt += "\n"
    
    if technical:
        has_content = True
        prompt += "INFORMACION TECNICA:\n"
        prompt += "-" * 40 + "\n"
        for t in technical[:2]:
            prompt += f"- {t.get('content','')[:500]}...\n"
        prompt += "\n"
    
    if educational:
        has_content = True
        prompt += "CONOCIMIENTO RELACIONADO:\n"
        prompt += "-" * 40 + "\n"
        for e in educational[:2]:
            source = e.get('folder') or e.get('filename', '')
            prompt += f"[{source}] {e.get('content','')[:400]}...\n"
        prompt += "\n"
    
    if vendor:
        has_content = True
        prompt += "CATALOGO PROVEEDOR:\n"
        for v in vendor[:1]:
            prompt += f"[{v.get('store','')}] {v.get('content','')[:300]}...\n"
        prompt += "\n"
    
    if has_content:
        prompt += "Usa esta informacion para responder de manera util y concisa."
    else:
        prompt += "(No se encontro informacion relacionada)"
    
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


def process_message(message: str, user_name: str = "Usuario") -> Tuple[str, str, dict]:
    """
    Procesa mensaje y retorna (respuesta, intent_type, metadata).
    Intent types: meta, salud, non_moto, rag
    """
    # PASO 1: Meta intents (identidad, saludo, empresas)
    meta_response = detect_meta_intent(message, user_name)
    if meta_response:
        stats["meta_intents"] += 1
        return meta_response, "meta", {}

    # PASO 2: P2 SALUD intent
    salud_response = detect_salud_intent(message)
    if salud_response:
        stats["salud_intents"] += 1
        return salud_response, "salud", {}

    # PASO 3: Non-moto intent
    non_moto_response = detect_non_moto_intent(message)
    if non_moto_response:
        return non_moto_response, "non_moto", {}

    # Default: RAG flow
    return None, "rag", {}


# =============================================================================
# Endpoints
# =============================================================================

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
        # Check intents BEFORE RAG
        response_text, intent_type, _ = process_message(message, name)

        if response_text:
            # Direct response (meta/salud/non_moto) - NO LLM
            log.info(f"[{phone}] ODI ({intent_type}): {response_text[:100]}...")
            await send_whatsapp_message(phone, response_text)
            return {"status": "ok", "intent": intent_type}

        # RAG flow
        products = search_knowledge(message, n_results=15)
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
        # Check intents BEFORE RAG
        response_text, intent_type, _ = process_message(message)

        if response_text:
            # Direct response (meta/salud/non_moto) - NO LLM
            log.info(f"[TEST] ODI ({intent_type}): {response_text[:100]}...")
            return {
                "status": "ok", "phone": phone, "input": message,
                "response": response_text, "intent": intent_type,
                "provider": "direct", "products_found": 0
            }

        # RAG flow
        products = search_knowledge(message, n_results=15)
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
            "intent": "rag", "provider": provider_used, "model": response.model,
            "latency_ms": response.latency_ms, "fallback_chain": response.fallback_chain,
            "products_found": len(products),
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
        "status": "healthy", "service": "odi-whatsapp", "version": "1.2.0",
        "timestamp": datetime.now().isoformat(),
        "whatsapp": {"phone_id": WHATSAPP_PHONE_ID, "token_configured": bool(WHATSAPP_TOKEN), "verify_token": WHATSAPP_VERIFY_TOKEN},
        "chromadb": chroma_status, "llm_chain": ["gemini", "openai", "claude", "groq", "lobotomy"],
        "llm_providers": llm_status, "stats": stats,
        "empresas_odi": ODI_EMPRESAS
    }
