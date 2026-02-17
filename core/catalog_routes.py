"""
ODI Catalog API Routes
Serves hotspot data and catalog page images for the frontend
"""

import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter(prefix="/catalog", tags=["catalog"])

DATA_DIR = Path("/opt/odi/data")

@router.get("/{store}/hotspots")
async def get_hotspots(store: str):
    """Get hotspot mapping data for a store"""
    store = store.upper()
    hotspot_file = DATA_DIR / store / "hotspot_map_sample.json"

    if not hotspot_file.exists():
        raise HTTPException(status_code=404, detail=f"Hotspot data not found for {store}")

    with open(hotspot_file) as f:
        data = json.load(f)

    return JSONResponse(content=data)


@router.get("/{store}/pages/{page}")
async def get_page_image(store: str, page: int):
    """Get catalog page image"""
    store = store.upper()
    image_path = DATA_DIR / store / "hotspot_pages" / f"page_{page}.png"

    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Page {page} not found")

    return FileResponse(
        path=str(image_path),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"}
    )


@router.get("/{store}/product/{sku}")
async def get_product_by_sku(store: str, sku: str):
    """Get product details by SKU"""
    store = store.upper()

    # Load from Shopify via existing infrastructure
    from core.shopify_client import get_product_by_sku as shopify_get

    try:
        product = await shopify_get(store, sku)
        return JSONResponse(content=product)
    except Exception as e:
        # Fallback to JSON data
        json_file = DATA_DIR / store / "json" / "all_products.json"
        if json_file.exists():
            with open(json_file) as f:
                products = json.load(f)

            for p in products:
                if str(p.get("codigo")) == sku:
                    return JSONResponse(content={
                        "id": sku,
                        "title": p.get("nombre", f"Producto {sku}"),
                        "price": p.get("precio", 0),
                        "compatibility": p.get("compatibilidad", "Universal"),
                        "page": p.get("page", 0)
                    })

        raise HTTPException(status_code=404, detail=f"Product {sku} not found")


@router.get("/{store}/pages")
async def list_pages(store: str):
    """List all available catalog pages"""
    store = store.upper()
    pages_dir = DATA_DIR / store / "hotspot_pages"

    if not pages_dir.exists():
        raise HTTPException(status_code=404, detail=f"No pages found for {store}")

    pages = []
    for f in pages_dir.glob("page_*.png"):
        page_num = int(f.stem.replace("page_", ""))
        pages.append({
            "number": page_num,
            "url": f"/catalog/{store}/pages/{page_num}"
        })

    pages.sort(key=lambda x: x["number"])
    return JSONResponse(content={"store": store, "pages": pages, "total": len(pages)})


@router.get("/{store}/srm-index")
async def get_srm_index(store: str):
    """Get SRM category index for a store"""
    store = store.upper()
    srm_file = DATA_DIR / store / "srm_index.json"

    if not srm_file.exists():
        raise HTTPException(status_code=404, detail=f"SRM index not found for {store}")

    with open(srm_file) as f:
        data = json.load(f)

    return JSONResponse(content=data)
