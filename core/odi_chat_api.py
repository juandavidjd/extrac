#!/usr/bin/env python3
"""
ODI Chat API v1.0 — El organismo conversa
"ODI decide sin hablar. Habla solo cuando ya ha decidido."

Puerto: 8813
Dominio: chat.liveodi.com -> localhost:8813
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
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

app = FastAPI(title="ODI Chat API", version="1.1.0")

# --- V13.1 Voice Config ---
ODI_VOICE_URL = os.getenv("ODI_VOICE_URL", "http://127.0.0.1:7777")
ODI_VOICE_TOKEN = os.getenv("ODI_VOICE_TOKEN", "011ab9e9878f7ebc20b67137b7ac5f40a13bf4c5bc458f7447be0928ad251fdf")

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
    domain: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    guardian_color: str = "verde"
    productos_encontrados: int = 0
    productos: List = []
    nivel_intimidad: int = 0
    modo: str = "AUTOMATICO"
    voice: str = "ramona"
    audio_enabled: bool = True
    industry: str = "general"
    company_identity: Optional[dict] = None

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

# --- V19: Deteccion de industria multi-vertical ---
INDUSTRY_KEYWORDS = {
    "motos": [
        "filtro", "bomba", "kit", "banda", "pastilla", "cadena",
        "aceite", "freno", "moto", "pulsar", "bajaj", "yamaha",
        "honda", "suzuki", "akt", "tvs", "hero", "precio repuesto",
        "repuesto", "pieza", "empaque", "tensor", "disco",
        "clutch", "embrague", "rodamiento", "retenedor", "corona",
        "llanta", "rin", "manigueta", "cable", "bws", "nmax",
        "fz", "duke", "dominar", "boxer", "discover", "splendor",
    ],
    "salud_dental": [
        "dental", "diente", "dientes", "muela", "implante", "ortodoncia",
        "blanqueamiento", "sonrisa", "endodoncia",
        "periodoncia", "matzu", "odontolog",
    ],
    "salud_bruxismo": [
        "bruxismo", "cubierta", "protector nocturno", "smokover",
        "rechinar", "cover", "guarda oclusal", "ferula",
    ],
    "salud_capilar": [
        "capilar", "cabello", "calvicie", "pelo", "alopecia",
        "tratamiento capilar", "cabeza sana", "cabezas sanas",
        "injerto capilar", "minoxidil",
    ],
}

DOMAIN_MAP = {
    "somosrepuestosmotos.com": "motos",
    "www.somosrepuestosmotos.com": "motos",
    "matzudentalaesthetics.com": "salud_dental",
    "www.matzudentalaesthetics.com": "salud_dental",
    "mis-cubiertas.com": "salud_bruxismo",
    "www.mis-cubiertas.com": "salud_bruxismo",
    "cabezasanas.com": "salud_capilar",
    "www.cabezasanas.com": "salud_capilar",
}


INDUSTRY_VERTICAL = {
    "motos": "P1",
    "salud_dental": "P2",
    "salud_bruxismo": "P2",
    "salud_capilar": "P4",
    "general": "general",
}

def detect_industry(message: str, domain: str = None) -> str:
    """Detecta la industria del usuario por dominio o mensaje."""
    if domain:
        d = domain.lower().strip()
        if d in DOMAIN_MAP:
            return DOMAIN_MAP[d]
    msg = message.lower()
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            return industry
    return "general"


# --- V19: Identidades de empresas ---
LOGO_BASE = "/odi/v1/assets/logo"

COMPANY_IDENTITIES = {
    "BARA": {"name": "Bara Importaciones", "logo": f"{LOGO_BASE}/Bara.png", "colors": {"primary": "#1e1e1e", "accent": "#666666"}, "industry": "motos"},
    "DFG": {"name": "DFG Distribuciones", "logo": f"{LOGO_BASE}/DFG.png", "colors": {"primary": "#00aae6", "accent": "#0046a0"}, "industry": "motos"},
    "YOKOMAR": {"name": "Yokomar", "logo": f"{LOGO_BASE}/Yokomar.png", "colors": {"primary": "#aa6e14", "accent": "#be8232"}, "industry": "motos"},
    "KAIQI": {"name": "Kaiqi", "logo": f"{LOGO_BASE}/Kaiqi.png", "colors": {"primary": "#b4b4b4", "accent": "#323232"}, "industry": "motos"},
    "DUNA": {"name": "Duna", "logo": f"{LOGO_BASE}/Duna.png", "colors": {"primary": "#e6e6e6", "accent": "#b4b4b4"}, "industry": "motos"},
    "IMBRA": {"name": "Imbra", "logo": f"{LOGO_BASE}/Imbra.png", "colors": {"primary": "#f0821e", "accent": "#f08c1e"}, "industry": "motos"},
    "JAPAN": {"name": "Japan Motos", "logo": f"{LOGO_BASE}/Japan.png", "colors": {"primary": "#c81e1e", "accent": "#c81e28"}, "industry": "motos"},
    "LEO": {"name": "Leo Repuestos", "logo": f"{LOGO_BASE}/Leo.png", "colors": {"primary": "#fadc00", "accent": "#0046a0"}, "industry": "motos"},
    "STORE": {"name": "Store Repuestos", "logo": f"{LOGO_BASE}/Store.png", "colors": {"primary": "#3c6432", "accent": "#325a28"}, "industry": "motos"},
    "VAISAND": {"name": "Vaisand", "logo": f"{LOGO_BASE}/Vaisand.png", "colors": {"primary": "#142850", "accent": "#0a5a96"}, "industry": "motos"},
    "ARMOTOS": {"name": "Armotos", "logo": f"{LOGO_BASE}/Armotos.png", "colors": {"primary": "#2b2b2b", "accent": "#555555"}, "industry": "motos"},
    "VITTON": {"name": "Vitton", "logo": f"{LOGO_BASE}/Vitton.png", "colors": {"primary": "#00286e", "accent": "#001e6e"}, "industry": "motos"},
    "MCLMOTOS": {"name": "MCL Motos", "logo": f"{LOGO_BASE}/mcl.PNG", "colors": {"primary": "#333333", "accent": "#666666"}, "industry": "motos"},
    "CBI": {"name": "CBI", "logo": f"{LOGO_BASE}/cbi.png", "colors": {"primary": "#333333", "accent": "#666666"}, "industry": "motos"},
    "OH_IMPORTACIONES": {"name": "OH Importaciones", "logo": f"{LOGO_BASE}/OH1.png", "colors": {"primary": "#333333", "accent": "#666666"}, "industry": "motos"},
    "MATZU": {"name": "Matzu Dental Aesthetics", "logo": None, "colors": {"primary": "#4a90d9", "accent": "#2c5f8a"}, "industry": "salud_dental"},
    "COVERS": {"name": "Covers Lab", "logo": None, "colors": {"primary": "#6b4c9a", "accent": "#4a2d73"}, "industry": "salud_bruxismo"},
    "CABEZAS_SANAS": {"name": "Cabezas Sanas", "logo": None, "colors": {"primary": "#2e8b57", "accent": "#1a5c38"}, "industry": "salud_capilar"},
}


def get_company_identity(productos_formateados: list) -> dict:
    """Retorna identidad de la empresa dominante en los productos."""
    if not productos_formateados:
        return None
    store_counts = {}
    for p in productos_formateados:
        s = p.get("proveedor", "").upper()
        if s:
            store_counts[s] = store_counts.get(s, 0) + 1
    if not store_counts:
        return None
    dominant = max(store_counts, key=store_counts.get)
    identity = COMPANY_IDENTITIES.get(dominant)
    if identity:
        return {
            "name": identity["name"],
            "logo": identity["logo"],
            "colors": identity["colors"],
        }
    return {"name": dominant, "logo": None, "colors": {"primary": "#333333", "accent": "#666666"}}


# --- V18.2: Mapeo tienda -> Shopify URL ---
STORE_MAP = {
    "BARA": "https://4jqcki-jq.myshopify.com",
    "YOKOMAR": "https://u1zmhk-ts.myshopify.com",
    "KAIQI": "https://u03tqc-0e.myshopify.com",
    "DFG": "https://0se1jt-q1.myshopify.com",
    "DUNA": "https://ygsfhq-fs.myshopify.com",
    "IMBRA": "https://0i1mdf-gi.myshopify.com",
    "JAPAN": "https://7cy1zd-qz.myshopify.com",
    "LEO": "https://h1hywg-pq.myshopify.com",
    "STORE": "https://0b6umv-11.myshopify.com",
    "VAISAND": "https://z4fpdj-mz.myshopify.com",
    "ARMOTOS": "https://znxx5p-10.myshopify.com",
    "VITTON": "https://hxjebc-it.myshopify.com",
    "MCLMOTOS": "https://v023qz-8x.myshopify.com",
    "CBI": "https://yrf6hp-f6.myshopify.com",
    "OH_IMPORTACIONES": "https://6fbakq-sj.myshopify.com",
}

# --- V18.2: Formatear productos para frontend ---
def formatear_productos_para_frontend(resultados_chromadb: list) -> list:
    """Transforma resultados de ChromaDB en objetos para ProductCards."""
    productos = []
    for doc in resultados_chromadb:
        metadata = doc.get("metadata", {})
        producto = {
            "codigo": metadata.get("sku", metadata.get("codigo", "")),
            "nombre": metadata.get("title", metadata.get("nombre", metadata.get("technicalName", ""))),
            "precio_cop": metadata.get("price", metadata.get("precio", 0)),
            "proveedor": metadata.get("store", metadata.get("proveedor", metadata.get("supplier", ""))),
            "imagen_url": metadata.get("image_url", metadata.get("imagen", "")),
            "shopify_url": "",  # Se genera dinámicamente abajo
            "fitment": metadata.get("fitment", metadata.get("compatibilidad", [])),
            "disponible": metadata.get("available", True),
            "categoria": metadata.get("category", metadata.get("categoria", ""))
        }
        # Precio numerico
        try:
            producto["precio_cop"] = int(float(str(producto["precio_cop"]).replace(",", "")))
        except (ValueError, TypeError):
            producto["precio_cop"] = 0
        # V18.2: Generar shopify_url dinámicamente desde STORE_MAP
        store_url = STORE_MAP.get(producto["proveedor"].upper(), "")
        codigo = producto["codigo"]
        if store_url and codigo:
            producto["shopify_url"] = f"{store_url}/search?q={codigo}"

        if producto["nombre"]:
            productos.append(producto)
    return productos[:10]

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
        vertical=INDUSTRY_VERTICAL.get(session.get("_detected_industry", "general")) or "general",
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
    return "Dame un momento. ¿Qué necesitas exactamente?"

# --- V13.1 Voice Selection ---
def seleccionar_voz(mensaje: str, session: dict, productos: list) -> str:
    """
    Ramona: hospitalidad, bienvenida, emocional, validacion
    Tony: productos, precios, tecnico, fitment, diagnostico, ejecucion
    V18: productos check ANTES de interacciones (fix tony nunca activo)
    """
    # Si hay productos en la respuesta -> Tony (tecnico, sin importar interaccion)
    if productos and len(productos) > 0:
        return "tony"

    interacciones = session.get("interacciones", 0)

    # Primer mensaje sin productos -> Ramona (bienvenida)
    if interacciones <= 1:
        return "ramona"

    # Keywords tecnicas -> Tony
    msg_lower = mensaje.lower()
    tony_keywords = [
        "precio", "cuanto", "cuesta", "vale",
        "stock", "disponible", "hay",
        "envio", "entrega",
        "garantia",
        "ficha", "especificacion", "sku", "codigo", "referencia",
        "filtro", "aceite", "pastilla", "freno",
        "kit", "arrastre", "cadena", "pinon",
        "llanta", "rin", "eje", "rodamiento",
        "bujia", "cable", "guaya",
        "pulsar", "bajaj", "yamaha", "honda", "suzuki",
        "akt", "tvs", "hero", "kawasaki",
        "fitment", "compatible", "sirve para", "le sirve",
        "diagnostico", "problema", "falla"
    ]
    if any(kw in msg_lower for kw in tony_keywords):
        return "tony"

    return "ramona"


# --- V13.1 TTS Endpoint ---
@app.post("/odi/chat/speak")
async def speak(request: Request):
    """
    Genera audio con ElevenLabs via odi-voice container.
    Ramona: conversacion. Tony: productos/tecnico.
    """
    body = await request.json()
    texto = body.get("text", "")
    voz = body.get("voice", "ramona")

    if not texto:
        return JSONResponse(status_code=400, content={"error": "text requerido"})

    if len(texto) > 2000:
        texto = texto[:1997] + "..."

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{ODI_VOICE_URL}/odi/speak",
                json={"texto": texto, "voice": voz}
            )
            if resp.status_code == 200:
                return Response(
                    content=resp.content,
                    media_type="audio/mpeg",
                    headers={
                        "Content-Disposition": f"inline; filename=odi-{voz}.mp3",
                        "Cache-Control": "no-cache"
                    }
                )
            else:
                log.warning("TTS error %d from odi-voice", resp.status_code)
    except Exception as e:
        log.error("TTS Error: %s", e)

    return JSONResponse(status_code=503, content={"error": "voz no disponible"})


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

    # V19: detectar industria ANTES de buscar productos
    detected_industry = detect_industry(msg.message, msg.domain)
    session["_detected_industry"] = detected_industry

    # 3. Buscar productos SOLO si la industria tiene datos en ChromaDB
    productos = []
    if detected_industry == "motos":
        mensaje_lower = msg.message.lower()
        es_busqueda = any(
            kw in mensaje_lower
            for kws in INDUSTRY_KEYWORDS.values()
            for kw in kws
        ) or any(kw in mensaje_lower for kw in [
            "precio", "cuanto", "tiene", "busco", "necesito",
        ])
        if es_busqueda:
            productos = buscar_chromadb(msg.message, n_results=5)
    # salud_dental, salud_bruxismo, salud_capilar, general: sin productos (ChromaDB solo tiene motos)

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

    # 8. Seleccionar voz
    voz = seleccionar_voz(msg.message, session, productos)


    # 9. V18.2: Formatear productos para frontend
    productos_formateados = formatear_productos_para_frontend(productos)

    # V19: Detectar industria
    industry = detect_industry(msg.message, msg.domain)

    # V19: Identidad de empresa dominante
    company_id = get_company_identity(productos_formateados)

    return ChatResponse(
        response=respuesta,
        session_id=session["session_id"],
        guardian_color=estado.get("color", "verde"),
        productos_encontrados=len(productos),
        productos=productos_formateados,
        nivel_intimidad=session["nivel_intimidad"],
        modo=modo.get("modo", "AUTOMATICO"),
        voice=voz,
        audio_enabled=True,
        industry=industry,
        company_identity=company_id,
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
        "version": "1.1.0",
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
