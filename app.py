import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.templating import Jinja2Templates
import json
import pandas as pd

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "output")
CELLS_DIR = os.path.join(OUTPUT_DIR, "cells")
SEGMENTS_DIR = os.path.join(OUTPUT_DIR, "segments")
CATALOG_DIR = os.path.join(OUTPUT_DIR, "catalog")

app = FastAPI(title="ADSI Extractor V5 Dashboard")

# Static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ---------------------------------------------------------
# Home – Tablero principal
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    catalog_path = os.path.join(CATALOG_DIR, "catalogo_adsi_master.csv")
    df = pd.read_csv(catalog_path) if os.path.exists(catalog_path) else pd.DataFrame()
    families = sorted(df["familia"].dropna().unique().tolist()) if not df.empty else []
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "families": families, "count": len(df)}
    )


# ---------------------------------------------------------
# Vista de productos (tabla)
# ---------------------------------------------------------
@app.get("/products", response_class=HTMLResponse)
async def products(request: Request):
    catalog_path = os.path.join(CATALOG_DIR, "catalogo_adsi_master.csv")
    df = pd.read_csv(catalog_path) if os.path.exists(catalog_path) else pd.DataFrame()
    return templates.TemplateResponse(
        "product_table.html",
        {"request": request, "products": df.to_dict("records")}
    )


# ---------------------------------------------------------
# Vista de páginas (JSON + celdas)
# ---------------------------------------------------------
@app.get("/page/{page_name}", response_class=HTMLResponse)
async def page_viewer(request: Request, page_name: str):
    json_file = os.path.join(SEGMENTS_DIR, f"{page_name}.json")
    json_data = {}

    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)

    # Recortes asociados
    cells = []
    for f in os.listdir(CELLS_DIR):
        if f.startswith(page_name):
            cells.append(f"/static/output/cells/{f}")

    return templates.TemplateResponse(
        "page_viewer.html",
        {
            "request": request,
            "page": page_name,
            "json": json_data,
            "cells": cells
        }
    )


# ---------------------------------------------------------
# Editor por producto
# ---------------------------------------------------------
@app.get("/edit/{sku}", response_class=HTMLResponse)
async def edit_product(request: Request, sku: str):
    file = os.path.join(CATALOG_DIR, "catalogo_adsi_master.csv")
    df = pd.read_csv(file)

    row = df[df["sku"] == sku].to_dict("records")
    if not row:
        return HTMLResponse("Producto no encontrado", status_code=404)

    return templates.TemplateResponse(
        "editor.html",
        {"request": request, "p": row[0]}
    )


# ---------------------------------------------------------
# API para guardar edición
# ---------------------------------------------------------
@app.post("/save-product/{sku}")
async def save_product(sku: str, request: Request):
    payload = await request.json()

    file = os.path.join(CATALOG_DIR, "catalogo_adsi_master.csv")
    df = pd.read_csv(file)

    idx = df.index[df["sku"] == sku]
    if len(idx) == 0:
        return JSONResponse({"error": "SKU no encontrado"}, status_code=404)

    for k, v in payload.items():
        if k in df.columns:
            df.loc[idx, k] = v

    df.to_csv(file, index=False)
    return JSONResponse({"status": "ok"})
