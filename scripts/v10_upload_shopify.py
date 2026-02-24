#!/usr/bin/env python3
"""
ARMOTOS V10: Procesar y subir a Shopify
- Mapear imagenes a productos
- Deduplicar por codigo
- Consolidar variantes de color
- Normalizar titulos
- Generar Ficha 360
- Subir a Shopify
"""
import os, json, base64, time, re
from pathlib import Path
from collections import defaultdict
import requests
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

SHOP = os.getenv("ARMOTOS_SHOP") or os.getenv("SHOPIFY_ARMOTOS_SHOP")
TOKEN = os.getenv("ARMOTOS_TOKEN") or os.getenv("SHOPIFY_ARMOTOS_TOKEN")
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
BASE_URL = f"https://{SHOP}/admin/api/2025-01"

PRODUCTS_FILE = Path("/opt/odi/data/ARMOTOS/json/all_products.json")
IMAGES_DIR = Path("/opt/odi/data/ARMOTOS/images")

def normalize_title(title):
    """Normaliza titulo del producto"""
    if not title:
        return "Producto ARMOTOS"
    # Capitalize properly
    title = title.strip().title()
    # Remove excessive spaces
    title = " ".join(title.split())
    return title[:255]

def generate_ficha_360(product):
    """Genera HTML para ficha 360 del producto"""
    html = f"<div class=ficha-360>"
    html += f"<h3>{product.get("nombre", "Producto")}</h3>"
    if product.get("compatibilidad"):
        html += f"<p><strong>Compatible con:</strong> {product[compatibilidad]}</p>"
    if product.get("colores"):
        colors = ", ".join(product["colores"]) if isinstance(product["colores"], list) else product["colores"]
        html += f"<p><strong>Colores:</strong> {colors}</p>"
    html += f"<p><strong>Codigo:</strong> {product.get("codigo", "N/A")}</p>"
    html += "</div>"
    return html

def find_image_for_page(page_num):
    """Busca imagen para una pagina"""
    pattern = f"page_{page_num:03d}_img_*.png"
    matches = list(IMAGES_DIR.glob(pattern))
    if not matches:
        pattern = f"page_{page_num:03d}_img_*.jpeg"
        matches = list(IMAGES_DIR.glob(pattern))
    return matches[0] if matches else None

def deduplicate_products(products):
    """Deduplica productos por codigo, consolida variantes"""
    by_codigo = defaultdict(list)
    for p in products:
        codigo = str(p.get("codigo", "")).strip()
        if codigo:
            by_codigo[codigo].append(p)
    
    deduplicated = []
    for codigo, variants in by_codigo.items():
        # Take first variant as base
        base = variants[0].copy()
        
        # Consolidate colors from all variants
        all_colors = set()
        for v in variants:
            if v.get("colores"):
                if isinstance(v["colores"], list):
                    all_colors.update(v["colores"])
                else:
                    all_colors.add(v["colores"])
        if all_colors:
            base["colores"] = list(all_colors)
        
        # Keep highest price
        prices = [v.get("precio", 0) for v in variants if v.get("precio")]
        if prices:
            base["precio"] = max(prices)
        
        deduplicated.append(base)
    
    return deduplicated

def upload_product(product):
    """Sube un producto a Shopify"""
    # Find image
    page = product.get("page", 0)
    img_path = find_image_for_page(page)
    
    # Build product data
    title = normalize_title(product.get("nombre", "Producto"))
    body = generate_ficha_360(product)
    price = product.get("precio", 0)
    if isinstance(price, str):
        price = int(re.sub(r"[^\d]", "", price) or 0)
    
    data = {
        "product": {
            "title": title,
            "body_html": body,
            "vendor": "ARMOTOS",
            "product_type": "Repuesto Moto",
            "status": "active",
            "tags": product.get("compatibilidad", ""),
            "variants": [{
                "sku": str(product.get("codigo", "")),
                "price": str(price) if price else "0",
                "inventory_management": None
            }]
        }
    }
    
    # Add image if available
    if img_path and img_path.exists():
        try:
            with open(img_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            data["product"]["images"] = [{"attachment": img_b64}]
        except:
            pass
    
    # Upload
    for attempt in range(3):
        try:
            r = requests.post(f"{BASE_URL}/products.json", json=data, headers=HEADERS, timeout=60)
            if r.status_code == 201:
                return True, img_path is not None
            elif r.status_code == 429:
                time.sleep(3)
                continue
            else:
                return False, False
        except:
            time.sleep(2)
    return False, False

if __name__ == "__main__":
    print("=== ARMOTOS V10: UPLOAD SHOPIFY ===", flush=True)
    
    # Load products
    with open(PRODUCTS_FILE) as f:
        products = json.load(f)
    print(f"Productos raw: {len(products)}", flush=True)
    
    # Deduplicate
    products = deduplicate_products(products)
    print(f"Despues dedup: {len(products)}", flush=True)
    
    # Upload
    uploaded = 0
    with_img = 0
    errors = 0
    
    for i, p in enumerate(products, 1):
        ok, has_img = upload_product(p)
        if ok:
            uploaded += 1
            if has_img:
                with_img += 1
        else:
            errors += 1
        
        if i % 50 == 0:
            print(f"[{i}/{len(products)}] OK:{uploaded} IMG:{with_img} ERR:{errors}", flush=True)
        time.sleep(0.6)
    
    print(f"\n=== RESULTADO ===", flush=True)
    print(f"Total: {uploaded}/{len(products)}", flush=True)
    print(f"Con imagen: {with_img}", flush=True)
    print(f"Errores: {errors}", flush=True)
