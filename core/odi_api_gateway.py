#!/usr/bin/env python3
"""
ODI API Gateway v1.0
Expone el ecosistema ODI al frontend SRM.
Puerto: 8815
"ODI está vivo en todo el ecosistema."
"""

from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from typing import Optional
import httpx
import time
import logging

log = logging.getLogger("odi-gateway")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ODI API Gateway", version="1.0.0")

# CORS — permitir frontend SRM (Lovable) + liveodi.com
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuración interna ---
CHAT_API = "http://localhost:8813"
CHROMADB_HOST = "localhost"
CHROMADB_PORT = 8000
FITMENT_URL = "http://172.18.0.5:8802"  # Docker network, no port-published

# ============================================================
# HEALTH
# ============================================================
@app.get("/health")
async def health():
    """Health check del gateway"""
    services = {}
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in [
            ("chat", f"{CHAT_API}/odi/chat/health"),
            ("fitment", f"{FITMENT_URL}/health"),
        ]:
            try:
                r = await client.get(url)
                services[name] = "ok" if r.status_code == 200 else "error"
            except Exception:
                services[name] = "unreachable"

    # ChromaDB via Python client
    try:
        import chromadb
        c = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        col = c.get_collection("odi_ind_motos")
        services["chromadb"] = f"ok ({col.count()} docs)"
    except Exception:
        services["chromadb"] = "unreachable"

    return {
        "status": "alive",
        "version": "1.0.0",
        "timestamp": time.time(),
        "services": services
    }


# ============================================================
# BÚSQUEDA DE PRODUCTOS — ChromaDB semántico
# ============================================================
@app.get("/products/search")
async def search_products(
    q: str = Query(..., description="Término de búsqueda"),
    limit: int = Query(20, ge=1, le=100),
    store: Optional[str] = Query(None, description="Filtrar por tienda"),
):
    """Búsqueda semántica de productos via ChromaDB."""
    try:
        import chromadb
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collection = client.get_collection("odi_ind_motos")

        # Pedir más resultados si hay filtro de tienda (post-filter)
        fetch_limit = limit * 3 if store else limit
        results = collection.query(
            query_texts=[q],
            n_results=min(fetch_limit, 100),
            include=["documents", "metadatas", "distances"]
        )

        products = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0

                if store and meta.get("store", "").lower() != store.lower():
                    continue

                products.append({
                    "sku": meta.get("sku", f"SKU-{i}"),
                    "nombre": meta.get("title", doc[:100] if doc else ""),
                    "categoria": meta.get("category", "Sin categoría"),
                    "precio_cop": meta.get("price", 0),
                    "imagen_url": meta.get("imagen_url", ""),
                    "fitment_summary": meta.get("compatible_models", ""),
                    "proveedor": meta.get("store", ""),
                    "shopify_url": meta.get("shopify_url", ""),
                    "relevance": round(1 - distance, 3) if distance else 0
                })

                if len(products) >= limit:
                    break

        return {
            "query": q,
            "total": len(products),
            "products": products
        }

    except Exception as e:
        log.error("Search error: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "hint": "ChromaDB puede no estar accesible"}
        )


# ============================================================
# ECOSISTEMA — 15 Tiendas con datos reales
# ============================================================
STORES_CONFIG = {
    "bara": {"name": "Bara Importaciones", "type": "importador", "shopify": "4jqcki-jq.myshopify.com", "palette": {"primary": "#D90429", "accent": "#2B2D42"}},
    "yokomar": {"name": "Yokomar", "type": "importador", "shopify": "u1zmhk-ts.myshopify.com", "palette": {"primary": "#FFC400", "accent": "#000000"}},
    "kaiqi": {"name": "Kaiqi Parts", "type": "distribuidor", "shopify": "u03tqc-0e.myshopify.com", "palette": {"primary": "#0047FF", "accent": "#0A1133"}},
    "dfg": {"name": "DFG", "type": "importador", "shopify": "0se1jt-q1.myshopify.com", "palette": {"primary": "#111111", "accent": "#666666"}},
    "duna": {"name": "Duna", "type": "importador", "shopify": "ygsfhq-fs.myshopify.com", "palette": {"primary": "#0077B6", "accent": "#023047"}},
    "imbra": {"name": "Imbra", "type": "importador", "shopify": "0i1mdf-gi.myshopify.com", "palette": {"primary": "#6C63FF", "accent": "#2D2B55"}},
    "japan": {"name": "Japan", "type": "fabricante", "shopify": "7cy1zd-qz.myshopify.com", "palette": {"primary": "#E3001B", "accent": "#1A1A1A"}},
    "leo": {"name": "Leo", "type": "fabricante", "shopify": "h1hywg-pq.myshopify.com", "palette": {"primary": "#FF6F00", "accent": "#212121"}},
    "store": {"name": "Store", "type": "almacen", "shopify": "0b6umv-11.myshopify.com", "palette": {"primary": "#0096C7", "accent": "#1A1A1A"}},
    "vaisand": {"name": "Vaisand", "type": "distribuidor", "shopify": "z4fpdj-mz.myshopify.com", "palette": {"primary": "#06D6A0", "accent": "#073B4C"}},
    "armotos": {"name": "Armotos", "type": "distribuidor", "shopify": "znxx5p-10.myshopify.com", "palette": {"primary": "#FF4500", "accent": "#1A1A1A"}},
    "vitton": {"name": "Vitton", "type": "almacen", "shopify": "hxjebc-it.myshopify.com", "palette": {"primary": "#8B4513", "accent": "#2F1B0E"}},
    "mclmotos": {"name": "MclMotos", "type": "almacen", "shopify": "v023qz-8x.myshopify.com", "palette": {"primary": "#1E90FF", "accent": "#0A1929"}},
    "cbi": {"name": "CBI", "type": "importador", "shopify": "yrf6hp-f6.myshopify.com", "palette": {"primary": "#228B22", "accent": "#0A2E0A"}},
    "oh_importaciones": {"name": "OH Importaciones", "type": "importador", "shopify": "6fbakq-sj.myshopify.com", "palette": {"primary": "#9C27B0", "accent": "#4A0072"}},
}

# Cache para conteos de tienda (evitar escanear 72k docs en cada request)
_store_counts_cache = {"data": None, "ts": 0}
CACHE_TTL = 300  # 5 minutos

def _get_store_counts():
    """Obtiene conteos por tienda desde ChromaDB con cache."""
    now = time.time()
    if _store_counts_cache["data"] and (now - _store_counts_cache["ts"]) < CACHE_TTL:
        return _store_counts_cache["data"]

    try:
        import chromadb
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collection = client.get_collection("odi_ind_motos")

        all_meta = collection.get(include=["metadatas"])
        counts = {}
        for meta in all_meta["metadatas"]:
            store_name = meta.get("store", "unknown").lower()
            counts[store_name] = counts.get(store_name, 0) + 1

        _store_counts_cache["data"] = counts
        _store_counts_cache["ts"] = now
        return counts
    except Exception as e:
        log.error("Store counts error: %s", e)
        return _store_counts_cache["data"] or {}


@app.get("/ecosystem/stores")
async def get_ecosystem():
    """Devuelve las 15 tiendas con conteos de productos de ChromaDB."""
    store_counts = _get_store_counts()

    stores = []
    for store_id, config in STORES_CONFIG.items():
        stores.append({
            "id": store_id,
            "name": config["name"],
            "type": config["type"],
            "palette": config["palette"],
            "shopify_url": f"https://{config['shopify']}",
            "landing": f"/{store_id}",
            "products_count": store_counts.get(store_id, 0),
            "status": "active" if store_counts.get(store_id, 0) > 0 else "pending"
        })

    categories = {}
    for s in stores:
        t = s["type"]
        if t not in categories:
            categories[t] = {"count": 0, "stores": []}
        categories[t]["count"] += 1
        categories[t]["stores"].append(s["id"])

    return {
        "total_stores": len(stores),
        "total_products": sum(s["products_count"] for s in stores),
        "stores": stores,
        "categories": categories
    }


@app.get("/stores/{store_id}/summary")
async def get_store_summary(store_id: str):
    """Resumen de una tienda específica."""
    if store_id not in STORES_CONFIG:
        return JSONResponse(status_code=404, content={"error": "Tienda no encontrada"})

    config = STORES_CONFIG[store_id]

    try:
        import chromadb
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collection = client.get_collection("odi_ind_motos")

        # Buscar por store (puede ser uppercase o lowercase)
        try:
            all_data = collection.get(
                where={"store": store_id.upper()},
                include=["metadatas", "documents"]
            )
        except Exception:
            all_data = collection.get(
                where={"store": store_id},
                include=["metadatas", "documents"]
            )

        products = all_data.get("metadatas", [])
        total = len(products)

        cat_counts = {}
        for p in products:
            cat = p.get("category", "Sin categoría")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        top_categories = sorted(
            [{"name": k, "count": v} for k, v in cat_counts.items()],
            key=lambda x: x["count"], reverse=True
        )[:6]

        recent = []
        for i, p in enumerate(products[:6]):
            recent.append({
                "sku": p.get("sku", f"SKU-{i}"),
                "nombre": p.get("title", ""),
                "precio_cop": p.get("price", 0),
                "imagen_url": p.get("imagen_url", "")
            })

    except Exception as e:
        log.error("Store summary error for %s: %s", store_id, e)
        total = 0
        top_categories = []
        recent = []

    return {
        "store": store_id,
        "name": config["name"],
        "type": config["type"],
        "palette": config["palette"],
        "shopify_url": f"https://{config['shopify']}",
        "stats": {
            "total_products": total,
            "categories": len(top_categories),
        },
        "top_categories": top_categories,
        "recent_products": recent
    }


# ============================================================
# FICHA 360° — Producto completo
# ============================================================
@app.get("/products/{sku}/360")
async def get_product_360(sku: str):
    """Ficha técnica completa de un producto."""
    try:
        import chromadb
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collection = client.get_collection("odi_ind_motos")

        meta = None
        doc = None

        # Buscar por SKU exacto
        try:
            results = collection.get(
                where={"sku": sku},
                include=["documents", "metadatas"],
                limit=1
            )
            if results["metadatas"]:
                meta = results["metadatas"][0]
                doc = results["documents"][0] if results["documents"] else ""
        except Exception:
            pass

        if not meta:
            # Fallback: búsqueda semántica
            results = collection.query(
                query_texts=[sku],
                n_results=1,
                include=["documents", "metadatas"]
            )
            if results["metadatas"] and results["metadatas"][0]:
                meta = results["metadatas"][0][0]
                doc = results["documents"][0][0] if results["documents"] else ""
            else:
                return JSONResponse(status_code=404, content={"error": "Producto no encontrado"})

        return {
            "srmCode": meta.get("sku", sku),
            "technicalName": meta.get("title", ""),
            "clientName": meta.get("store", ""),
            "category": meta.get("category", ""),
            "fitment": {
                "raw": meta.get("compatible_models", ""),
            },
            "images": [meta.get("imagen_url", "")] if meta.get("imagen_url") else [],
            "technicalDescription": doc if isinstance(doc, str) else str(doc),
            "precio_cop": meta.get("price", 0),
            "proveedor": meta.get("store", ""),
            "type": meta.get("type", "product"),
        }

    except Exception as e:
        log.error("Product 360 error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============================================================
# FITMENT — Motor de compatibilidad
# ============================================================
@app.get("/fitment/search")
async def fitment_search(
    brand: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Búsqueda libre"),
):
    """Búsqueda por compatibilidad. Proxy al Fitment Engine M6.2."""
    search_term = " ".join(filter(None, [brand, model, year, q])).strip()
    if not search_term:
        return JSONResponse(status_code=400, content={"error": "Proporciona al menos un parámetro de búsqueda"})

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{FITMENT_URL}/fitment/query",
                json={"q": search_term},
                headers={"Content-Type": "application/json"}
            )

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "vehicle": {"brand": brand, "model": model, "year": year},
                    "query": search_term,
                    "compatible_products": data.get("results_count", len(data.get("results", []))),
                    "answer": data.get("answer", ""),
                    "products": data.get("results", [])
                }

    except Exception as e:
        log.warning("Fitment engine error, falling back to ChromaDB: %s", e)

    # Fallback: ChromaDB
    try:
        import chromadb
        chroma = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collection = chroma.get_collection("odi_ind_motos")

        results = collection.query(
            query_texts=[search_term],
            n_results=50,
            include=["metadatas"]
        )

        products = []
        if results["metadatas"]:
            for meta in results["metadatas"][0]:
                products.append({
                    "sku": meta.get("sku", meta.get("codigo", "")),
                    "title": meta.get("nombre_tecnico", meta.get("nombre", "")),
                    "category": meta.get("categoria", ""),
                    "price": meta.get("precio", 0),
                    "compatibility": meta.get("fitment", meta.get("compatibilidad", "")),
                    "client": meta.get("store", "")
                })

        return {
            "vehicle": {"brand": brand, "model": model, "year": year},
            "query": search_term,
            "compatible_products": len(products),
            "products": products,
            "source": "chromadb_fallback"
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/fitment/brands")
async def fitment_brands():
    """Lista de marcas disponibles en Fitment Engine."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{FITMENT_URL}/fitment/brands")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        log.error("Fitment brands error: %s", e)
    return JSONResponse(status_code=503, content={"error": "Fitment engine no disponible"})


# ============================================================
# CHAT — Proxy al Chat API V13.1
# ============================================================
@app.post("/chat")
async def proxy_chat(request: Request):
    """Proxy al Chat API V13.1 — agrega campo productos estructurado."""
    body = await request.json()

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{CHAT_API}/odi/chat",
            json=body
        )
        data = resp.json()

    # Si hay productos mencionados, buscar en ChromaDB para datos estructurados
    if data.get("productos_encontrados", 0) > 0:
        try:
            import chromadb
            chroma = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
            collection = chroma.get_collection("odi_ind_motos")

            results = collection.query(
                query_texts=[body.get("message", "")],
                n_results=5,
                include=["metadatas"]
            )

            productos = []
            if results["metadatas"]:
                for meta in results["metadatas"][0]:
                    productos.append({
                        "sku": meta.get("sku", ""),
                        "nombre": meta.get("title", ""),
                        "precio_cop": meta.get("price", 0),
                        "imagen_url": meta.get("imagen_url", ""),
                        "proveedor": meta.get("store", ""),
                        "fitment": meta.get("compatible_models", "")
                    })

            data["productos"] = productos
        except Exception:
            data["productos"] = []

    return data


@app.post("/chat/speak")
async def proxy_speak(request: Request):
    """Proxy al TTS endpoint."""
    body = await request.json()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{CHAT_API}/odi/chat/speak",
            json=body
        )
        if resp.status_code == 200:
            return Response(
                content=resp.content,
                media_type="audio/mpeg"
            )
    return JSONResponse(status_code=503, content={"error": "TTS no disponible"})
