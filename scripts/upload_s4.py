#!/usr/bin/env python3
"""S4: Upload 2080 productos a Shopify ARMOTOS"""
import sys
sys.path.insert(0, "/opt/odi/core")

import importlib
import odi_shopify_uploader
importlib.reload(odi_shopify_uploader)

from odi_shopify_uploader import ShopifyUploader
import json
import time
import os
import glob

# Cargar productos
with open("/opt/odi/data/ARMOTOS/json/all_products_v12_2_corrected.json") as f:
    data = json.load(f)
    products = data.get("products", [])

print(f"Total productos a subir: {len(products)}", flush=True)

# Inicializar uploader
uploader = ShopifyUploader("ARMOTOS")
print(f"Shop: {uploader.shop}", flush=True)
has_create = hasattr(uploader, "create_product")
print(f"Tiene create_product: {has_create}", flush=True)

if not has_create:
    print("ERROR: Metodo create_product no encontrado!")
    sys.exit(1)

# Build SKU to image mapping
images_dir = "/opt/odi/data/ARMOTOS/smart_film_images"
sku_to_image = {}
for img_file in glob.glob(os.path.join(images_dir, "*.png")):
    filename = os.path.basename(img_file)
    if "_sku_" in filename:
        sku = filename.split("_sku_")[1].replace(".png", "")
        sku_to_image[sku] = img_file

print(f"Imagenes mapeadas: {len(sku_to_image)}", flush=True)
print("=" * 50, flush=True)

stats = {"created": 0, "failed": 0, "errors": []}
start_time = time.time()

for i, prod in enumerate(products):
    sku = prod.get("sku", prod.get("codigo", ""))
    if isinstance(sku, list):
        sku = sku[0]
    sku = str(sku).strip()
    
    title = prod.get("title", prod.get("titulo", ""))[:60]
    handle = prod.get("handle", "")
    body_html = prod.get("body_html", "")
    price = prod.get("price", prod.get("precio", 0))
    if isinstance(price, str):
        price = float(price.replace(".", "").replace(",", ".")) if price else 0
    
    # Find image
    image_path = sku_to_image.get(sku)
    
    # Create product via API
    result = uploader.create_product(
        title=title,
        handle=handle,
        body_html=body_html,
        price=float(price) if price else 0,
        sku=sku,
        image_path=image_path,
        status="active"
    )
    
    if result:
        stats["created"] += 1
    else:
        stats["failed"] += 1
        stats["errors"].append({"sku": sku, "title": title[:30]})
    
    # Progress every 100
    if (i + 1) % 100 == 0:
        elapsed = int(time.time() - start_time)
        print(f"  Progreso: {i+1}/2080 ({stats['created']} ok, {stats['failed']} err) - {elapsed}s", flush=True)
    
    time.sleep(0.5)

elapsed = int(time.time() - start_time)
print("=" * 50, flush=True)
print(f"RESULTADO: {stats['created']} creados, {stats['failed']} fallidos", flush=True)
print(f"Tiempo: {elapsed} segundos", flush=True)

# Guardar errores
if stats["errors"]:
    with open("/opt/odi/data/ARMOTOS/upload_errors.json", "w") as f:
        json.dump(stats["errors"], f, indent=2)
    print(f"Errores guardados en upload_errors.json", flush=True)
