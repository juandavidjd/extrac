"""
ODI API v1.0 - Organismo Digital Industrial
API unificada para conectar todos los servicios ODI

Endpoints:
- /v1/query         - Consulta natural a Cortex
- /v1/fitment       - Búsqueda compatibilidad
- /v1/auth/*        - Autenticación multi-nivel
- /v1/catalog/*     - Catálogo productos
- /v1/orders/*      - Gestión pedidos
- /v1/kb/*          - Knowledge Base management
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx
import hashlib
import secrets
import jwt
import os

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="ODI API",
    description="Organismo Digital Industrial - API Unificada",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS para PWA
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: ["https://app.odi.ai"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración interna
CORTEX_URL = os.getenv("CORTEX_URL", "http://127.0.0.1:8803")
PIPELINE_URL = os.getenv("PIPELINE_URL", "http://127.0.0.1:8804")
JWT_SECRET = os.getenv("JWT_SECRET", "odi-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer(auto_error=False)

# ══════════════════════════════════════════════════════════════════════════════
# MODELOS PYDANTIC
# ══════════════════════════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    question: str = Field(..., description="Pregunta en lenguaje natural")
    voice: str = Field(default="tony", description="Voz: tony (técnico) o ramona (amigable)")
    k: int = Field(default=5, description="Número de documentos a recuperar")
    user_id: Optional[str] = None
    canal: str = Field(default="api", description="Canal de origen")

class QueryResponse(BaseModel):
    answer: str
    voice: str
    lobe_used: List[str]
    sources: List[str]
    timestamp: str
    event_id: str

class FitmentRequest(BaseModel):
    marca: str
    modelo: str
    year: Optional[int] = None
    cilindraje: Optional[str] = None
    repuesto: Optional[str] = None

class AuthRegisterRequest(BaseModel):
    email: str
    password: str
    nombre: str
    telefono: Optional[str] = None
    santo_y_sena: Optional[str] = Field(None, description="Frase secreta para verificación WhatsApp")

class AuthLoginRequest(BaseModel):
    email: str
    password: str

class AuthVerifySecretRequest(BaseModel):
    telefono: str
    santo_y_sena: str

class ProductSearch(BaseModel):
    query: str
    marca: Optional[str] = None
    categoria: Optional[str] = None
    limit: int = 20

class OrderCreate(BaseModel):
    productos: List[Dict[str, Any]]
    cliente_telefono: str
    cliente_nombre: str
    direccion_envio: Optional[str] = None
    notas: Optional[str] = None

class KBIngestRequest(BaseModel):
    file_path: str
    lobe: str = "ind_motos"
    metadata: Optional[Dict[str, Any]] = None

# ══════════════════════════════════════════════════════════════════════════════
# BASE DE DATOS EN MEMORIA (Reemplazar con Supabase/PostgreSQL en producción)
# ══════════════════════════════════════════════════════════════════════════════

users_db: Dict[str, Dict] = {}
orders_db: Dict[str, Dict] = {}

# ══════════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_jwt_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    payload = verify_jwt_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return payload

def generate_event_id() -> str:
    return f"ODI-{int(datetime.now().timestamp() * 1000):X}"

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS: HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    """Health check del API"""
    return {
        "status": "healthy",
        "service": "odi-api",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health/services")
async def services_health():
    """Health check de todos los servicios ODI"""
    services = {}

    # Check Cortex
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{CORTEX_URL}/health")
            services["cortex"] = r.json() if r.status_code == 200 else {"status": "error"}
    except:
        services["cortex"] = {"status": "unreachable"}

    # Check Pipeline
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{PIPELINE_URL}/health")
            services["pipeline"] = r.json() if r.status_code == 200 else {"status": "error"}
    except:
        services["pipeline"] = {"status": "unreachable"}

    return {
        "api": {"status": "healthy"},
        "services": services,
        "timestamp": datetime.now().isoformat()
    }

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS: QUERY (Cortex)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/v1/query", response_model=QueryResponse)
async def query_cortex(request: QueryRequest):
    """
    Consulta al Cortex ODI (RAG multi-lóbulo)

    - Tony: respuestas técnicas precisas
    - Ramona: respuestas amigables y cálidas
    """
    event_id = generate_event_id()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{CORTEX_URL}/query",
                json={
                    "question": request.question,
                    "voice": request.voice,
                    "k": request.k
                }
            )

            if response.status_code == 200:
                data = response.json()
                return QueryResponse(
                    answer=data.get("answer", ""),
                    voice=data.get("voice", request.voice),
                    lobe_used=data.get("lobe_used", []),
                    sources=data.get("sources", []),
                    timestamp=data.get("timestamp", datetime.now().isoformat()),
                    event_id=event_id
                )
            else:
                raise HTTPException(status_code=502, detail="Error en Cortex")

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout consultando Cortex")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/fitment")
async def fitment_search(request: FitmentRequest):
    """
    Búsqueda de compatibilidad de repuestos por moto
    """
    # Construir pregunta natural para Cortex
    parts = []
    if request.repuesto:
        parts.append(request.repuesto)
    parts.append("para")
    parts.append(request.marca)
    parts.append(request.modelo)
    if request.year:
        parts.append(str(request.year))
    if request.cilindraje:
        parts.append(request.cilindraje)

    question = " ".join(parts)

    query_request = QueryRequest(
        question=question,
        voice="tony",
        k=10
    )

    return await query_cortex(query_request)

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS: AUTH
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/v1/auth/register")
async def register_user(request: AuthRegisterRequest):
    """
    Registro de nuevo usuario con santo y seña opcional
    """
    if request.email in users_db:
        raise HTTPException(status_code=400, detail="Email ya registrado")

    user_id = secrets.token_hex(16)
    users_db[request.email] = {
        "user_id": user_id,
        "email": request.email,
        "nombre": request.nombre,
        "telefono": request.telefono,
        "password_hash": hash_password(request.password),
        "santo_y_sena_hash": hash_password(request.santo_y_sena) if request.santo_y_sena else None,
        "created_at": datetime.now().isoformat()
    }

    token = create_jwt_token(user_id, request.email)

    return {
        "status": "ok",
        "user_id": user_id,
        "token": token,
        "message": "Usuario registrado exitosamente"
    }

@app.post("/v1/auth/login")
async def login_user(request: AuthLoginRequest):
    """
    Login con email y password
    """
    user = users_db.get(request.email)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if user["password_hash"] != hash_password(request.password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = create_jwt_token(user["user_id"], request.email)

    return {
        "status": "ok",
        "user_id": user["user_id"],
        "token": token,
        "nombre": user["nombre"]
    }

@app.post("/v1/auth/verify-secret")
async def verify_santo_y_sena(request: AuthVerifySecretRequest):
    """
    Verificar santo y seña (para WhatsApp)
    """
    # Buscar usuario por teléfono
    user = None
    for u in users_db.values():
        if u.get("telefono") == request.telefono:
            user = u
            break

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not user.get("santo_y_sena_hash"):
        raise HTTPException(status_code=400, detail="Usuario no tiene santo y seña configurado")

    if user["santo_y_sena_hash"] != hash_password(request.santo_y_sena):
        return {"verified": False, "message": "Santo y seña incorrecto"}

    return {
        "verified": True,
        "user_id": user["user_id"],
        "nombre": user["nombre"],
        "message": "Identidad verificada"
    }

@app.get("/v1/auth/me")
async def get_current_user_info(user: Dict = Depends(get_current_user)):
    """
    Obtener información del usuario actual
    """
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")

    email = user.get("email")
    user_data = users_db.get(email)

    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {
        "user_id": user_data["user_id"],
        "email": user_data["email"],
        "nombre": user_data["nombre"],
        "telefono": user_data.get("telefono")
    }

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS: CATALOG
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/v1/catalog/search")
async def search_catalog(request: ProductSearch):
    """
    Búsqueda en catálogo de productos
    """
    # Por ahora, usar Cortex para búsqueda semántica
    query_request = QueryRequest(
        question=f"productos: {request.query}" +
                 (f" marca {request.marca}" if request.marca else "") +
                 (f" categoría {request.categoria}" if request.categoria else ""),
        voice="tony",
        k=request.limit
    )

    return await query_cortex(query_request)

@app.get("/v1/catalog/product/{sku}")
async def get_product(sku: str):
    """
    Obtener información de un producto por SKU
    """
    query_request = QueryRequest(
        question=f"información del producto SKU {sku}",
        voice="tony",
        k=3
    )

    return await query_cortex(query_request)

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS: ORDERS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/v1/orders")
async def create_order(request: OrderCreate, user: Dict = Depends(get_current_user)):
    """
    Crear nuevo pedido
    """
    order_id = f"ORD-{secrets.token_hex(8).upper()}"

    order = {
        "order_id": order_id,
        "productos": request.productos,
        "cliente_telefono": request.cliente_telefono,
        "cliente_nombre": request.cliente_nombre,
        "direccion_envio": request.direccion_envio,
        "notas": request.notas,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "user_id": user.get("sub") if user else None
    }

    orders_db[order_id] = order

    return {
        "status": "ok",
        "order_id": order_id,
        "message": "Pedido creado exitosamente"
    }

@app.get("/v1/orders/{order_id}")
async def get_order(order_id: str):
    """
    Obtener estado de un pedido
    """
    order = orders_db.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    return order

@app.get("/v1/orders")
async def list_orders(user: Dict = Depends(get_current_user)):
    """
    Listar pedidos del usuario
    """
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")

    user_orders = [
        o for o in orders_db.values()
        if o.get("user_id") == user.get("sub")
    ]

    return {"orders": user_orders}

# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS: KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/v1/kb/ingest")
async def ingest_to_kb(request: KBIngestRequest, user: Dict = Depends(get_current_user)):
    """
    Ingestar documento a la Knowledge Base
    """
    # TODO: Integrar con KB Daemon
    return {
        "status": "queued",
        "file_path": request.file_path,
        "lobe": request.lobe,
        "message": "Documento encolado para procesamiento"
    }

@app.get("/v1/kb/stats")
async def kb_stats():
    """
    Estadísticas de la Knowledge Base
    """
    return {
        "lobes": {
            "ind_motos": {"documents": 208, "size_mb": 101},
            "profesion": {"documents": 551, "size_mb": 359}
        },
        "total_documents": 759,
        "total_size_mb": 460
    }

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8800)
