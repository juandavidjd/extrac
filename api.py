from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from catalog_service import CatalogService
from product_service import ProductService
from image_service import ImageService
from auth import validate_api_key

app = FastAPI(title="ADSI Cloud API", version="1.0")

# CORS amplio para apps móviles, frontend ADSI y SRM-QK
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Servicios
catalog = CatalogService()
products = ProductService()
images = ImageService()


# -----------------------------------------------------
# ENDPOINTS PRINCIPALES
# -----------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "api": "ADSI Cloud API", "version": "1.0"}


# -------------------- CATÁLOGO COMPLETO --------------------

@app.get("/catalog")
def get_catalog(api_key: str = Query(...)):
    validate_api_key(api_key)
    return catalog.load_catalog()


# -------------------- PRODUCTO POR SKU --------------------

@app.get("/product/{sku}")
def get_product(sku: str, api_key: str = Query(...)):
    validate_api_key(api_key)
    data = products.get_product_by_sku(sku)
    if not data:
        raise HTTPException(status_code=404, detail="SKU no encontrado")
    return data


# -------------------- BUSCADOR GLOBAL --------------------

@app.get("/search")
def search(
    q: str = Query(..., description="Texto a buscar (SKU, código, descripción)"),
    limit: int = 50,
    api_key: str = Query(...)
):
    validate_api_key(api_key)
    return products.search(q, limit)


# -------------------- IMÁGENES --------------------

@app.get("/image/{filename}")
def get_image(filename: str, api_key: str = Query(...)):
    validate_api_key(api_key)
    return images.serve_image(filename)
