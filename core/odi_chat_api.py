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
    # V25: campos para interfaz
    mode: str = "build"  # commerce|care|build|diagnose|empower|optimize|learn
    follow: Optional[str] = None  # frase de seguimiento
    response: str
    narrative: str = ""
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

# --- V23.4: Blindaje Cognitivo + Enriquecimiento Shopify GraphQL ---
GATEWAY_URL = "http://localhost:8815"
GOVERNED_STORES = {"DFG", "ARMOTOS", "VITTON", "IMBRA", "BARA", "KAIQI", "MCLMOTOS"}

def filtrar_y_enriquecer_productos(productos: list) -> tuple:
    import time as _time
    import requests
    
    if not productos:
        return [], []
    
    start_time = _time.time()
    filtered = []
    productos_estructurados = []
    filtered_out = 0
    enriched_count = 0
    
    for p in productos:
        meta = p.get("metadata", {})
        store = str(meta.get("store", "")).upper()
        sku = str(meta.get("sku", ""))
        
        if not sku:
            filtered_out += 1
            continue
        
        try:
            resp = requests.get(
                f"{GATEWAY_URL}/sku/status",
                params={"store": store, "sku": sku},
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                
                if data.get("active", False):
                    filtered.append(p)
                    
                    if data.get("product"):
                        prod = data["product"]
                        productos_estructurados.append({
                            "sku": sku,
                            "title": prod.get("title", ""),
                            "price": prod.get("price"),
                            "image": prod.get("image"),
                            "url": prod.get("url"),
                            "store": store,
                            "vendor": prod.get("vendor", store)
                        })
                        enriched_count += 1
                    elif data.get("unverified"):
                        productos_estructurados.append({
                            "sku": sku,
                            "title": meta.get("title", f"Producto {sku}"),
                            "price": meta.get("price"),
                            "image": None,
                            "url": None,
                            "store": store,
                            "vendor": store,
                            "unverified": True
                        })
                else:
                    filtered_out += 1
                    reason = data.get("reason", "unknown")
                    log.debug(f"[FILTER] Descartado: {store}:{sku} reason={reason}")
            else:
                p["unverified"] = True
                filtered.append(p)
                productos_estructurados.append({
                    "sku": sku,
                    "title": f"Producto {sku}",
                    "price": meta.get("price"),
                    "image": None,
                    "url": None,
                    "store": store,
                    "vendor": store,
                    "unverified": True
                })
                log.warning(f"[FILTER] gateway_error store={store} sku={sku}")
                
        except requests.exceptions.Timeout:
            p["unverified"] = True
            filtered.append(p)
            productos_estructurados.append({
                "sku": sku,
                "title": f"Producto {sku}",
                "price": meta.get("price"),
                "image": None,
                "url": None,
                "store": store,
                "vendor": store,
                "unverified": True
            })
            log.warning(f"[FILTER] gateway_timeout store={store} sku={sku}")
        except Exception as e:
            p["unverified"] = True
            filtered.append(p)
            log.warning(f"[FILTER] gateway_exception store={store} sku={sku} error={e}")
    
    latency_ms = int((_time.time() - start_time) * 1000)
    log.info(f"[FILTER] chroma={len(productos)} filtered={filtered_out} final={len(filtered)} latency={latency_ms}ms")
    log.info(f"[ENRICH] total={len(productos_estructurados)} enriched={enriched_count} latency={latency_ms}ms")
    
    return filtered, productos_estructurados

def filtrar_productos_activos(productos: list) -> list:
    filtered, _ = filtrar_y_enriquecer_productos(productos)
    return filtered



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
        "REGLAS V24: Maximo 2 oraciones. Si tienes productos di cuantos. NUNCA ensayos ni explicaciones largas.\n"
        "NUNCA menciones tejido conectivo, ecosistema productivo, ni jerga. Si preguntan que eres: Conecto industrias con soluciones.\n"
        "Eres directo, calido, util. Si saludan: responde y pregunta en que ayudar. UNA linea."
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
                    "temperature": 0.4,
                    "max_tokens": 200
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
    interacciones = session.get("interacciones", 0)

    # Primer mensaje sin productos -> Ramona (bienvenida)
    if interacciones <= 1:
        return "ramona"

    # Si hay productos en la respuesta -> Tony (tecnico)
    if productos and len(productos) > 0:
        return "tony"

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



# --- V21: Narrative TTS generator ---
def generar_narrative_tts(response_full: str, productos: list) -> str:
    """Genera resumen corto para TTS. Max 200 chars."""
    if len(response_full) <= 200:
        return response_full
    if productos and len(productos) > 0:
        count = len(productos)
        if count == 1:
            nombre = "producto"
            if isinstance(productos[0], dict):
                nombre = productos[0].get("title", productos[0].get("nombre", "producto"))
            return f"Encontre {nombre}. Te muestro los detalles en pantalla."
        else:
            return f"Encontre {count} opciones. Te las muestro en pantalla para que compares."
    primera = response_full.split(".")[0] + "."
    if len(primera) <= 200:
        return primera
    return primera[:197] + "..."

# --- V13.1 TTS Endpoint ---

# ═══════════════════════════════════════════
# V25: Funciones para interfaz
# ═══════════════════════════════════════════

def detect_mode_v25(message: str, industry: str, productos: list) -> str:
    """Detecta el modo de ODI segun contexto. Alimenta la interfaz."""
    msg_lower = message.lower()
    
    # Crisis / cuidado (Guardian P0)
    crisis_keywords = ["solo", "mal", "triste", "no puedo", "angustia", "ayuda", "morir"]
    if any(k in msg_lower for k in crisis_keywords):
        return "care"
    
    # Saludo/Cuidado
    care_keywords = ["hola", "buenos dias", "buenas tardes", "como estas", "gracias"]
    if any(k in msg_lower for k in care_keywords):
        return "care"
    
    # Comercio (tiene productos O keywords de compra)
    commerce_keywords = ["comprar", "precio", "cotizar", "cuanto cuesta", "disponible", "pedido", "vender"]
    if productos and len(productos) > 0:
        return "commerce"
    if any(k in msg_lower for k in commerce_keywords):
        return "commerce"
    
    # Diagnostico (incluye mecanico)
    diagnose_keywords = ["no prende", "no funciona", "falla", "problema", "revisar", "diagnostico", "no arranca", "se apaga", "ruido"]
    if any(k in msg_lower for k in diagnose_keywords):
        return "diagnose"
    
    # Aprender
    learn_keywords = ["como se", "como instalar", "estudiar", "aprender", "curso", "programar", "tutorial", "explicame"]
    if any(k in msg_lower for k in learn_keywords):
        return "learn"
    
    # Salud
    if industry and industry.startswith("salud"):
        return "care"
    
    # Empoderar
    empower_keywords = ["trabajo", "empleo", "experiencia", "echaron", "retirar"]
    if any(k in msg_lower for k in empower_keywords):
        return "empower"
    
    # Construir
    build_keywords = ["montar", "negocio", "tienda", "landing", "armar", "crear"]
    if any(k in msg_lower for k in build_keywords):
        return "build"
    
    # Optimizar
    optimize_keywords = ["excel", "facturas", "reportes", "automatizar"]
    if any(k in msg_lower for k in optimize_keywords):
        return "optimize"
    
    return "commerce"  # default para industria moto


def split_follow_v25(response_text: str) -> tuple:
    """Separa respuesta principal de frase de seguimiento."""
    if not response_text:
        return response_text, None
    
    sentences = response_text.split(". ")
    if len(sentences) >= 2:
        last = sentences[-1].strip()
        if last.endswith("?") or any(w in last.lower() for w in ["enviame", "pasame", "dime", "cuentame"]):
            main = ". ".join(sentences[:-1]) + "."
            return main, last
    return response_text, None


def add_from_to_productos(productos: list) -> list:
    """Agrega campo from (empresa proveedora) a cada producto."""
    for p in productos:
        if "from" not in p or not p["from"]:
            p["from"] = p.get("vendor", p.get("empresa", p.get("store", "")))
    return productos

@app.post("/odi/chat/speak")
async def speak(request: Request):
    """
    Genera audio con ElevenLabs via odi-voice container.
    Ramona: conversacion. Tony: productos/tecnico.
    """
    body = await request.json()
    texto = body.get("narrative") or body.get("text", "")
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
            # V23.3: Filtrar productos no activos
            productos, productos_estructurados = filtrar_y_enriquecer_productos(productos)
    productos_estructurados = productos_estructurados if "productos_estructurados" in dir() else []
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
    # V23.4: Use enriched products if available, else format from ChromaDB
    if productos_estructurados:
        productos_formateados = productos_estructurados
    else:
        productos_formateados = formatear_productos_para_frontend(productos)

    # V19: Detectar industria
    industry = detect_industry(msg.message, msg.domain)

    # V19: Identidad de empresa dominante
    company_id = get_company_identity(productos_formateados)

    narrative = generar_narrative_tts(respuesta, productos_formateados)

    # V23.4: Build filter log
    # V25: agregar from a productos
    productos_formateados = add_from_to_productos(productos_formateados)
    filter_log = {
        "chroma_total": len(productos) if productos else 0,
        "enriched": len(productos_estructurados) if productos_estructurados else 0
    }
    
    return ChatResponse(
        response=respuesta,
        narrative=narrative,
        session_id=session["session_id"],
        guardian_color=estado.get("color", "verde"),
        productos_encontrados=len(productos_estructurados) if productos_estructurados else len(productos),
        productos=productos_formateados,
        nivel_intimidad=session["nivel_intimidad"],
        modo=modo.get("modo", "AUTOMATICO"),
        voice=voz,
        audio_enabled=True,
        industry=industry,
        company_identity=company_id,
        # V25: mode, voice, follow
        mode=detect_mode_v25(msg.message, industry, productos_formateados),
        follow=split_follow_v25(respuesta)[1],
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

# ═══════════════════════════════════════════
# V25: Funciones para interfaz
# ═══════════════════════════════════════════

