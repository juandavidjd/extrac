#!/usr/bin/env python3
"""
ODI Cortex Query - Router Semántico Multi-Lóbulo
================================================
Consulta inteligente que decide qué lóbulo(s) usar según la query.

Lóbulos:
- profesion_kb: Conocimiento general (ADSI, empresas, estrategia)
- kb_embeddings: Conocimiento técnico (motos, catálogos, manuales, fitment)

Voces:
- Tony Maestro: Respuestas técnicas, datos precisos
- Ramona Anfitriona: Respuestas cálidas, acompañamiento

API Endpoints:
- POST /query     - Consulta RAG con routing automático
- POST /search    - Búsqueda semántica en lóbulo específico
- GET  /health    - Health check
- GET  /stats     - Estadísticas de los lóbulos

Uso:
    uvicorn odi_cortex_query:app --host 0.0.0.0 --port 8803
"""
import os
import re
import logging
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Security: Rate limiting
import sys
sys.path.insert(0, "/opt/odi/core")
from odi_rate_limiter import RateLimitMiddleware

load_dotenv("/opt/odi/.env")

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# ============================================
# CONFIGURACIÓN
# ============================================
LOBES = {
    "profesion": {
        "embeddings": "/mnt/volume_sfo3_01/embeddings/profesion_kb",
        "collection": "odi_profesion",
        "description": "Conocimiento general: ADSI, empresas, estrategia, procesos",
        "keywords": ["adsi", "proceso", "estrategia", "empresa", "ecosistema", "metodología",
                     "arquitectura", "organismo", "digital", "platzi", "systeme", "shopify",
                     "marketing", "ventas", "embudo", "funnel", "cliente"]
    },
    "ind_motos": {
        "embeddings": "/mnt/volume_sfo3_01/embeddings/kb_embeddings",
        "collection": "odi_ind_motos",
        "description": "Conocimiento técnico: motos, catálogos, manuales, fitment, repuestos",
        "keywords": ["moto", "pieza", "repuesto", "catálogo", "manual", "fitment",
                     "compatibilidad", "pulsar", "bajaj", "honda", "yamaha", "suzuki",
                     "tvs", "hero", "akt", "bujía", "aceite", "freno", "cadena", "piñón",
                     "kit", "arrastre", "filtro", "pastilla", "rodamiento", "eje"]
    }
}

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ============================================
# MODELOS PYDANTIC
# ============================================
class QueryRequest(BaseModel):
    question: str = Field(..., description="Pregunta del usuario")
    voice: Literal["tony", "ramona", "auto"] = Field(default="auto", description="Voz de respuesta")
    k: int = Field(default=5, description="Número de documentos a recuperar")
    lobe: Optional[Literal["profesion", "ind_motos", "both", "auto"]] = Field(
        default="auto", description="Lóbulo a consultar"
    )
    include_sources: bool = Field(default=True, description="Incluir fuentes en respuesta")


class SearchRequest(BaseModel):
    query: str
    lobe: Literal["profesion", "ind_motos"] = "ind_motos"
    k: int = 10


class QueryResponse(BaseModel):
    answer: str
    voice: str
    lobe_used: List[str]
    sources: List[Dict[str, Any]]
    timestamp: str


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    lobe: str
    count: int


# ============================================
# VOICE PERSONALITIES
# ============================================
TONY_SYSTEM = """Eres Tony Maestro, el arquitecto técnico de ODI (Organismo Digital Industrial).
Tu personalidad:
- Preciso, directo, sin rodeos
- Experto técnico en repuestos de motos y sistemas digitales
- Usas datos y hechos concretos
- No usas emojis ni lenguaje informal
- Si no sabes algo, lo dices claramente

Contexto recuperado:
{context}

Responde la pregunta del usuario de forma técnica y precisa."""

RAMONA_SYSTEM = """Eres Ramona Anfitriona, la voz cálida de ODI (Organismo Digital Industrial).
Tu personalidad:
- Amigable, cercana, empática
- Acompañas al usuario en su proceso
- Explicas de forma simple y accesible
- Celebras los logros del usuario
- Ofreces ayuda adicional

Contexto recuperado:
{context}

Responde la pregunta del usuario de forma cálida y acogedora."""


# ============================================
# ROUTER SEMÁNTICO
# ============================================
class SemanticRouter:
    """Determina qué lóbulo(s) usar según la query."""

    def __init__(self):
        self.lobes = LOBES

    def route(self, query: str) -> List[str]:
        """Determina qué lóbulo(s) consultar."""
        query_lower = query.lower()
        scores = {}

        for lobe_name, config in self.lobes.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in query_lower:
                    score += 1
            scores[lobe_name] = score

        # Si hay keywords técnicos, priorizar ind_motos
        if scores["ind_motos"] > 0 and scores["profesion"] == 0:
            return ["ind_motos"]

        # Si hay keywords generales, priorizar profesion
        if scores["profesion"] > 0 and scores["ind_motos"] == 0:
            return ["profesion"]

        # Si hay ambos o ninguno, consultar ambos
        if scores["ind_motos"] > 0 and scores["profesion"] > 0:
            return ["ind_motos", "profesion"]

        # Default: consultar ambos
        return ["ind_motos", "profesion"]

    def select_voice(self, query: str, lobes_used: List[str]) -> str:
        """Selecciona la voz apropiada."""
        query_lower = query.lower()

        # Palabras que indican necesidad técnica
        technical_words = ["cómo", "qué", "cuál", "especificación", "compatible",
                          "fitment", "manual", "referencia", "precio"]

        # Palabras que indican necesidad emocional/acompañamiento
        warm_words = ["ayuda", "problema", "no entiendo", "podrías", "por favor",
                     "gracias", "hola", "buenos días"]

        tech_score = sum(1 for w in technical_words if w in query_lower)
        warm_score = sum(1 for w in warm_words if w in query_lower)

        # Si es principalmente técnico de motos, Tony
        if "ind_motos" in lobes_used and tech_score > warm_score:
            return "tony"

        # Si hay palabras cálidas, Ramona
        if warm_score > 0:
            return "ramona"

        # Default según lóbulo principal
        return "tony" if "ind_motos" in lobes_used else "ramona"


# ============================================
# CORTEX (CEREBRO UNIFICADO)
# ============================================
class ODICortex:
    """Cerebro unificado de ODI con múltiples lóbulos."""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        self.router = SemanticRouter()
        self.vectorstores = {}

        # Cargar vector stores
        for lobe_name, config in LOBES.items():
            if Path(config["embeddings"]).exists():
                try:
                    vs = Chroma(
                        persist_directory=config["embeddings"],
                        embedding_function=self.embeddings,
                        collection_name=config["collection"]
                    )
                    self.vectorstores[lobe_name] = vs
                    log.info(f"Loaded lobe: {lobe_name}")
                except Exception as e:
                    log.error(f"Error loading {lobe_name}: {e}")

    def search(self, query: str, lobe: str, k: int = 5) -> List[Dict]:
        """Búsqueda en un lóbulo específico."""
        if lobe not in self.vectorstores:
            return []

        vs = self.vectorstores[lobe]
        results = vs.similarity_search_with_score(query, k=k)

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
                "lobe": lobe
            }
            for doc, score in results
        ]

    def query(self, request: QueryRequest) -> QueryResponse:
        """Consulta RAG con routing automático."""

        # Determinar lóbulos
        if request.lobe == "auto":
            lobes_to_query = self.router.route(request.question)
        elif request.lobe == "both":
            lobes_to_query = ["profesion", "ind_motos"]
        else:
            lobes_to_query = [request.lobe]

        # Buscar en lóbulos
        all_results = []
        for lobe in lobes_to_query:
            results = self.search(request.question, lobe, k=request.k)
            all_results.extend(results)

        # Ordenar por score y tomar los mejores
        all_results.sort(key=lambda x: x["score"])
        top_results = all_results[:request.k]

        # Construir contexto
        context = "\n\n---\n\n".join([
            f"[{r['lobe']}] {r['content']}" for r in top_results
        ])

        # Seleccionar voz
        if request.voice == "auto":
            voice = self.router.select_voice(request.question, lobes_to_query)
        else:
            voice = request.voice

        # Seleccionar prompt según voz
        system_prompt = TONY_SYSTEM if voice == "tony" else RAMONA_SYSTEM

        # Generar respuesta
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}")
        ])

        chain = (
            {"context": lambda _: context, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

        answer = chain.invoke(request.question)

        # Preparar fuentes
        sources = []
        if request.include_sources:
            sources = [
                {
                    "source": r["metadata"].get("source", "unknown"),
                    "folder": r["metadata"].get("folder", "unknown"),
                    "lobe": r["lobe"],
                    "score": r["score"]
                }
                for r in top_results
            ]

        return QueryResponse(
            answer=answer,
            voice=voice,
            lobe_used=lobes_to_query,
            sources=sources,
            timestamp=datetime.now().isoformat()
        )

    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas de los lóbulos."""
        stats = {}
        for lobe_name, vs in self.vectorstores.items():
            try:
                collection = vs._collection
                count = collection.count()
                stats[lobe_name] = {
                    "documents": count,
                    "description": LOBES[lobe_name]["description"],
                    "path": LOBES[lobe_name]["embeddings"]
                }
            except:
                stats[lobe_name] = {"documents": 0, "error": "Could not read"}
        return stats


# ============================================
# FASTAPI APP
# ============================================
app = FastAPI(
    title="ODI Cortex Query API",
    description="API de consulta RAG multi-lóbulo para ODI",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting: 30 req/min, burst 10/5s
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=30,
    burst_limit=10,
    exclude_paths=["/health", "/docs", "/openapi.json", "/stats", "/lobes"],
)

# Inicializar cortex
cortex = None


@app.on_event("startup")
async def startup():
    global cortex
    log.info("Initializing ODI Cortex...")
    cortex = ODICortex()
    log.info("ODI Cortex ready")


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "odi-cortex-query",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/stats")
async def stats():
    return cortex.get_stats()


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Consulta RAG con routing automático.

    El router determina automáticamente qué lóbulo(s) consultar
    y qué voz usar según la naturaleza de la pregunta.
    """
    try:
        return cortex.query(request)
    except Exception as e:
        log.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Búsqueda semántica en un lóbulo específico."""
    try:
        results = cortex.search(request.query, request.lobe, request.k)
        return SearchResponse(
            results=results,
            lobe=request.lobe,
            count=len(results)
        )
    except Exception as e:
        log.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/lobes")
async def list_lobes():
    """Lista los lóbulos disponibles."""
    return {
        name: {
            "description": config["description"],
            "keywords": config["keywords"][:5]
        }
        for name, config in LOBES.items()
    }


# ============================================
# CLI
# ============================================
if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="ODI Cortex Query")
    parser.add_argument("--port", type=int, default=8803)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--query", type=str, help="Query directa (sin servidor)")

    args = parser.parse_args()

    if args.query:
        # Modo CLI
        cortex = ODICortex()
        request = QueryRequest(question=args.query)
        response = cortex.query(request)
        print(f"\n[{response.voice.upper()}] ({', '.join(response.lobe_used)})")
        print("-" * 60)
        print(response.answer)
        print("-" * 60)
        print(f"Sources: {len(response.sources)}")
    else:
        # Modo servidor
        uvicorn.run(app, host=args.host, port=args.port)
