#!/usr/bin/env python3
"""
ODI Chat API v1.0 — El organismo conversa
"ODI decide sin hablar. Habla solo cuando ya ha decidido."

Puerto: 8813
Dominio: chat.liveodi.com -> localhost:8813
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import uuid
import time
import json
import os
import logging
import httpx
import asyncio

# --- Imports ODI Core ---
import sys
sys.path.insert(0, '/opt/odi/core')
sys.path.insert(0, '/opt/odi')

from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")

from odi_personalidad import obtener_personalidad
from odi_decision_logger import obtener_logger

import chromadb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("odi.chat.api")

app = FastAPI(title="ODI Chat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://liveodi.com",
        "https://www.liveodi.com",
        "https://liveodi-chat.vercel.app",
        "https://liveodi-chat-juan-david-jimenez-sierras-projects.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ChromaDB Client ---
CHROMA_HOST = os.getenv("CHROMA_HOST", "127.0.0.1")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "odi_ind_motos")

chroma_collection = None
try:
    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    chroma_collection = chroma_client.get_collection(CHROMA_COLLECTION)
    log.info("ChromaDB connected: %d docs in %s", chroma_collection.count(), CHROMA_COLLECTION)
except Exception as e:
    log.warning("ChromaDB connection failed: %s", e)

# --- Modelos ---
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    usuario_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    guardian_color: str = "verde"
    productos_encontrados: int = 0
    nivel_intimidad: int = 0
    modo: str = "AUTOMATICO"

# --- Estado de sesiones (memoria — Redis despues) ---
sessions = {}

def get_or_create_session(session_id: Optional[str] = None) -> dict:
    """Crear o recuperar sesion de conversacion"""
    if session_id and session_id in sessions:
        sessions[session_id]["interacciones"] += 1
        return sessions[session_id]

    new_id = session_id or f"ses-{uuid.uuid4().hex[:12]}"
    sessions[new_id] = {
        "session_id": new_id,
        "interacciones": 1,
        "nivel_intimidad": 0,
        "historial": [],
        "created_at": time.time(),
        "perfil_usuario": {
            "nivel_tech": 0.5,
            "paciencia_requerida": 0.5,
            "estilo": "desconocido"
        }
    }
    return sessions[new_id]

# --- ChromaDB Search ---
def buscar_chromadb(query: str, n_results: int = 5) -> list:
    """Busqueda semantica en ChromaDB usando Python client"""
    if not chroma_collection:
        return []
    try:
        results = chroma_collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        productos = []
        if results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                dist = results["distances"][0][i] if results.get("distances") else 1.0
                productos.append({
                    "texto": doc,
                    "metadata": meta,
                    "relevancia": max(0, 1 - dist)
                })
        return productos
    except Exception as e:
        log.error("ChromaDB search error: %s", e)
    return []

# --- Generador de respuesta con LLM ---
async def generar_respuesta_odi(
    mensaje: str,
    session: dict,
    productos: list
) -> str:
    """
    Genera la respuesta usando LLM con el prompt de personalidad V8.1.
    Integra las 4 dimensiones: Personalidad, Estado, Modo, Caracter.
    """
    personalidad = obtener_personalidad()

    # Generar prompt completo con 4 dimensiones
    prompt_personalidad = personalidad.generar_prompt(
        usuario_id=session["session_id"],
        mensaje=mensaje,
        perfil_usuario=session.get("perfil_usuario"),
        vertical="P1",
        nivel_intimidad=session.get("nivel_intimidad", 0),
        contexto_productos=productos[:3] if productos else None,
        memoria_conversacion=session.get("historial", [])[-10:]
    )

    # Construir contexto de productos
    contexto_productos = ""
    if productos:
        contexto_productos = "\n\nPRODUCTOS ENCONTRADOS:\n"
        for i, p in enumerate(productos[:5], 1):
            meta = p.get("metadata", {})
            nombre = meta.get("title", meta.get("nombre", "Producto"))
            precio = meta.get("price", meta.get("precio", "N/D"))
            tienda = meta.get("store", meta.get("tienda", ""))
            sku = meta.get("sku", "")
            contexto_productos += f"{i}. {nombre} -- ${precio} COP"
            if tienda:
                contexto_productos += f" ({tienda})"
            if sku:
                contexto_productos += f" [SKU: {sku}]"
            contexto_productos += "\n"

    # Historial de conversacion
    historial_texto = ""
    if session.get("historial"):
        ultimos = session["historial"][-6:]
        historial_texto = "\n\nHISTORIAL RECIENTE:\n"
        for h in ultimos:
            rol = "Usuario" if h["rol"] == "user" else "ODI"
            historial_texto += f"{rol}: {h['texto'][:200]}\n"

    # Mensaje completo al LLM
    prompt_completo = (
        f"{prompt_personalidad}\n"
        f"{contexto_productos}\n"
        f"{historial_texto}\n\n"
        f"MENSAJE DEL USUARIO: {mensaje}\n\n"
        "Responde como ODI. No como chatbot. Con criterio, calidez y precision.\n"
        "NUNCA uses frases como 'En que puedo ayudarte?', 'Gracias por tu compra', 'Te contactaremos pronto'.\n"
        "Se directo, funcional, y natural."
    )

    # Llamar a OpenAI GPT-4o
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": prompt_completo},
                        {"role": "user", "content": mensaje}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                log.error("OpenAI error %d: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        log.error("LLM Error: %s", e)

    # Fallback: respuesta sin LLM
    if productos:
        p = productos[0]
        meta = p.get("metadata", {})
        return f"Tengo {len(productos)} opciones. La mejor: {meta.get('title', 'producto')} a ${meta.get('price', 'consultar')} COP."
    return "Dame un momento. Que necesitas exactamente para tu moto?"

# --- Endpoint Principal ---
@app.post("/odi/chat")
async def chat(msg: ChatMessage):
    """
    Endpoint principal de conversacion.
    Recibe mensaje -> busca -> personalidad -> responde.
    """
    start = time.time()

    # 1. Sesion
    session = get_or_create_session(msg.session_id)

    # 2. Evaluar estado Guardian
    personalidad = obtener_personalidad()
    estado = personalidad.evaluar_estado(
        session["session_id"],
        msg.message,
        None
    )

    # 3. Buscar productos si el mensaje parece consulta
    productos = []
    mensaje_lower = msg.message.lower()
    es_busqueda = any(kw in mensaje_lower for kw in [
        "filtro", "bomba", "kit", "banda", "pastilla", "cadena",
        "aceite", "freno", "moto", "pulsar", "bajaj", "yamaha",
        "honda", "suzuki", "akt", "tvs", "hero", "precio",
        "cuanto", "tiene", "busco", "necesito",
        "repuesto", "pieza", "empaque", "tensor", "disco",
        "clutch", "embrague", "rodamiento", "retenedor", "corona",
        "llanta", "rin", "manigueta", "cable"
    ])

    if es_busqueda:
        productos = buscar_chromadb(msg.message, n_results=5)

    # 4. Generar respuesta con personalidad
    respuesta = await generar_respuesta_odi(msg.message, session, productos)

    # 5. Guardar en historial
    session["historial"].append({"rol": "user", "texto": msg.message, "t": time.time()})
    session["historial"].append({"rol": "odi", "texto": respuesta, "t": time.time()})

    # 6. Actualizar nivel de intimidad (progresivo)
    interacciones = session["interacciones"]
    if interacciones >= 50:
        session["nivel_intimidad"] = min(3, session["nivel_intimidad"])
    elif interacciones >= 15:
        session["nivel_intimidad"] = min(2, session["nivel_intimidad"])
    elif interacciones >= 4:
        session["nivel_intimidad"] = min(1, session["nivel_intimidad"])

    # 7. Determinar modo
    modo = personalidad.determinar_modo(
        session["session_id"],
        estado,
        session["nivel_intimidad"],
        None
    )

    elapsed = time.time() - start
    log.info(
        "Chat: sid=%s interacciones=%d guardian=%s productos=%d elapsed=%.2fs",
        session["session_id"], interacciones, estado.get("color", "verde"),
        len(productos), elapsed
    )

    return ChatResponse(
        response=respuesta,
        session_id=session["session_id"],
        guardian_color=estado.get("color", "verde"),
        productos_encontrados=len(productos),
        nivel_intimidad=session["nivel_intimidad"],
        modo=modo.get("modo", "AUTOMATICO")
    )

@app.get("/odi/chat/health")
async def health():
    chroma_ok = chroma_collection is not None
    chroma_count = 0
    if chroma_ok:
        try:
            chroma_count = chroma_collection.count()
        except Exception:
            chroma_ok = False
    return {
        "ok": True,
        "version": "1.0.0",
        "organismo": "ODI",
        "estado": "vivo",
        "chromadb": {"connected": chroma_ok, "docs": chroma_count},
        "openai": bool(os.getenv("OPENAI_API_KEY"))
    }

# --- Arranque ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("ODI_CHAT_PORT", "8813"))
    log.info("Starting ODI Chat API on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
