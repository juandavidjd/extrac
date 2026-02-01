#!/usr/bin/env python3
"""
ODI Knowledge Base Query API
============================
API FastAPI para consultas RAG sobre la base de conocimiento de ODI.

Endpoints:
    POST /query          - Consulta RAG con contexto
    POST /search         - Busqueda semantica simple
    GET  /health         - Health check
    GET  /stats          - Estadisticas del indice
    POST /feedback       - Enviar feedback sobre respuesta

Uso:
    uvicorn odi_kb_query:app --host 0.0.0.0 --port 8000
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
import redis

# LangChain
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Load config
load_dotenv("/opt/odi/config/.env")

# Configuration
CONFIG = {
    "embeddings_path": os.getenv("EMBEDDINGS_PATH", "/opt/odi/embeddings"),
    "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
    "redis_host": os.getenv("REDIS_HOST", "localhost"),
    "redis_port": int(os.getenv("REDIS_PORT", "6379")),
    "feedback_webhook_url": os.getenv("FEEDBACK_WEBHOOK_URL", ""),
    "feedback_webhook_secret": os.getenv("FEEDBACK_WEBHOOK_SECRET", ""),
}

# Logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="ODI Knowledge Base API",
    description="API de consultas RAG para el Organismo Digital Industrial",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Models
# ============================================================================

class QueryRequest(BaseModel):
    """Request para consulta RAG."""
    question: str = Field(..., min_length=3, description="Pregunta a responder")
    context: Optional[str] = Field(None, description="Contexto adicional")
    k: int = Field(5, ge=1, le=20, description="Numero de documentos a recuperar")
    include_sources: bool = Field(True, description="Incluir fuentes en respuesta")
    voice: Optional[str] = Field("ramona", description="Voz: 'tony' (tecnico) o 'ramona' (amigable)")


class SearchRequest(BaseModel):
    """Request para busqueda semantica."""
    query: str = Field(..., min_length=3, description="Query de busqueda")
    k: int = Field(10, ge=1, le=50, description="Numero de resultados")
    filter_category: Optional[str] = Field(None, description="Filtrar por categoria")


class FeedbackRequest(BaseModel):
    """Request para enviar feedback."""
    query_id: str = Field(..., description="ID de la consulta")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    comment: Optional[str] = Field(None, description="Comentario opcional")
    correct_answer: Optional[str] = Field(None, description="Respuesta correcta si la original fue incorrecta")


class QueryResponse(BaseModel):
    """Response de consulta RAG."""
    query_id: str
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    timestamp: str
    voice: str


class SearchResponse(BaseModel):
    """Response de busqueda semantica."""
    query: str
    results: List[Dict[str, Any]]
    total: int
    timestamp: str


# ============================================================================
# Services
# ============================================================================

class ODIKnowledgeBaseService:
    """Servicio de Knowledge Base."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        logger.info("Inicializando ODI Knowledge Base Service...")

        # OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY no configurada")

        self.embeddings = OpenAIEmbeddings(
            model=CONFIG["embedding_model"],
            openai_api_key=api_key
        )

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            openai_api_key=api_key
        )

        # Vector store
        embeddings_path = Path(CONFIG["embeddings_path"])
        if not embeddings_path.exists():
            logger.warning(f"Embeddings path no existe: {embeddings_path}")
            embeddings_path.mkdir(parents=True, exist_ok=True)

        self.vectorstore = Chroma(
            persist_directory=str(embeddings_path),
            embedding_function=self.embeddings,
            collection_name="odi_knowledge_base"
        )

        # Redis
        try:
            self.redis = redis.Redis(
                host=CONFIG["redis_host"],
                port=CONFIG["redis_port"],
                decode_responses=True
            )
            self.redis.ping()
        except:
            self.redis = None
            logger.warning("Redis no disponible")

        # Prompts por voz
        self.prompts = {
            "tony": PromptTemplate(
                template="""Eres Tony Maestro, experto tecnico del sistema ODI.
Tu rol es dar respuestas precisas, tecnicas y directas.
Usa terminologia tecnica cuando sea apropiado.
Si no sabes algo, dilo claramente.

Contexto relevante:
{context}

Pregunta: {question}

Respuesta tecnica:""",
                input_variables=["context", "question"]
            ),
            "ramona": PromptTemplate(
                template="""Eres Ramona Anfitriona, asistente amigable del sistema ODI.
Tu rol es hacer que la informacion tecnica sea accesible y facil de entender.
Usa un tono calido y cercano, pero mantente informativa.
Si no sabes algo, ofrece alternativas o sugiere donde buscar.

Contexto relevante:
{context}

Pregunta: {question}

Respuesta amigable:""",
                input_variables=["context", "question"]
            )
        }

        self._initialized = True
        logger.info("ODI Knowledge Base Service inicializado")

    def search(self, query: str, k: int = 10, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """Busqueda semantica simple."""
        try:
            if filter_dict:
                results = self.vectorstore.similarity_search_with_score(
                    query, k=k, filter=filter_dict
                )
            else:
                results = self.vectorstore.similarity_search_with_score(query, k=k)

            return [
                {
                    "content": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                }
                for doc, score in results
            ]
        except Exception as e:
            logger.error(f"Error en busqueda: {e}")
            return []

    def query_rag(self, question: str, k: int = 5, voice: str = "ramona", context: str = "") -> Dict[str, Any]:
        """Consulta RAG completa."""
        import uuid

        query_id = str(uuid.uuid4())[:8]

        try:
            # Retrieve relevant documents
            docs = self.vectorstore.similarity_search(question, k=k)

            if not docs:
                return {
                    "query_id": query_id,
                    "answer": "No encontre informacion relevante sobre esa pregunta en la base de conocimiento.",
                    "sources": [],
                    "confidence": 0.0
                }

            # Build context
            doc_context = "\n\n".join([
                f"[Fuente: {doc.metadata.get('source', 'desconocida')}]\n{doc.page_content}"
                for doc in docs
            ])

            if context:
                doc_context = f"Contexto adicional: {context}\n\n{doc_context}"

            # Select prompt
            prompt = self.prompts.get(voice, self.prompts["ramona"])

            # Generate answer
            formatted_prompt = prompt.format(context=doc_context, question=question)
            response = self.llm.invoke(formatted_prompt)
            answer = response.content

            # Extract sources
            sources = [
                {
                    "file": doc.metadata.get("source", "desconocido"),
                    "category": doc.metadata.get("category", ""),
                    "chunk": doc.metadata.get("chunk_index", 0),
                    "snippet": doc.page_content[:200] + "..."
                }
                for doc in docs
            ]

            # Calculate confidence (basic heuristic)
            confidence = min(1.0, len(docs) / k * 0.8 + 0.2)

            # Log to Redis
            if self.redis:
                self.redis.lpush("odi:queries", json.dumps({
                    "query_id": query_id,
                    "question": question,
                    "voice": voice,
                    "sources_count": len(sources),
                    "timestamp": datetime.now().isoformat()
                }))
                self.redis.ltrim("odi:queries", 0, 999)  # Keep last 1000

            return {
                "query_id": query_id,
                "answer": answer,
                "sources": sources,
                "confidence": confidence
            }

        except Exception as e:
            logger.error(f"Error en query RAG: {e}")
            return {
                "query_id": query_id,
                "answer": f"Error procesando la consulta: {str(e)}",
                "sources": [],
                "confidence": 0.0
            }

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadisticas."""
        try:
            collection = self.vectorstore._collection
            doc_count = collection.count()
        except:
            doc_count = 0

        stats = {
            "total_documents": doc_count,
            "embeddings_path": CONFIG["embeddings_path"],
            "embedding_model": CONFIG["embedding_model"],
            "redis_connected": self.redis is not None
        }

        # Query stats from Redis
        if self.redis:
            stats["total_queries"] = self.redis.llen("odi:queries")
            stats["total_feedbacks"] = self.redis.llen("odi:feedbacks")

        return stats


# Singleton service
def get_service() -> ODIKnowledgeBaseService:
    return ODIKnowledgeBaseService()


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    service = get_service()
    return {
        "status": "healthy",
        "service": "odi-kb-query",
        "timestamp": datetime.now().isoformat(),
        "documents_indexed": service.get_stats().get("total_documents", 0)
    }


@app.get("/stats")
async def get_stats():
    """Estadisticas del servicio."""
    service = get_service()
    return service.get_stats()


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Consulta RAG sobre la base de conocimiento.

    Usa el contexto de documentos indexados para responder preguntas.
    """
    service = get_service()

    result = service.query_rag(
        question=request.question,
        k=request.k,
        voice=request.voice or "ramona",
        context=request.context or ""
    )

    return QueryResponse(
        query_id=result["query_id"],
        question=request.question,
        answer=result["answer"],
        sources=result["sources"] if request.include_sources else [],
        confidence=result["confidence"],
        timestamp=datetime.now().isoformat(),
        voice=request.voice or "ramona"
    )


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Busqueda semantica simple.

    Retorna documentos similares sin generar respuesta.
    """
    service = get_service()

    filter_dict = None
    if request.filter_category:
        filter_dict = {"category": request.filter_category}

    results = service.search(
        query=request.query,
        k=request.k,
        filter_dict=filter_dict
    )

    return SearchResponse(
        query=request.query,
        results=results,
        total=len(results),
        timestamp=datetime.now().isoformat()
    )


@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest, background_tasks: BackgroundTasks):
    """
    Enviar feedback sobre una respuesta.

    El feedback se usa para mejorar el sistema.
    """
    service = get_service()

    feedback_data = {
        "query_id": request.query_id,
        "rating": request.rating,
        "comment": request.comment,
        "correct_answer": request.correct_answer,
        "timestamp": datetime.now().isoformat()
    }

    # Store in Redis
    if service.redis:
        service.redis.lpush("odi:feedbacks", json.dumps(feedback_data))

    # Send to webhook in background
    webhook_url = CONFIG.get("feedback_webhook_url")
    if webhook_url:
        background_tasks.add_task(send_feedback_webhook, feedback_data, webhook_url)

    return {
        "status": "received",
        "query_id": request.query_id,
        "message": "Gracias por tu feedback!"
    }


async def send_feedback_webhook(feedback_data: Dict, webhook_url: str):
    """Envia feedback a webhook externo (n8n, etc.)."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json={
                    "type": "odi_feedback",
                    "data": feedback_data
                },
                headers={
                    "Content-Type": "application/json",
                    "X-ODI-Secret": CONFIG.get("feedback_webhook_secret", "")
                },
                timeout=10.0
            )
            logger.info(f"Feedback webhook sent: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending feedback webhook: {e}")


# ============================================================================
# Startup
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Inicializacion al arrancar."""
    logger.info("Starting ODI KB Query API...")
    # Pre-initialize service
    try:
        service = get_service()
        stats = service.get_stats()
        logger.info(f"Service ready. Documents indexed: {stats.get('total_documents', 0)}")
    except Exception as e:
        logger.error(f"Error initializing service: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
