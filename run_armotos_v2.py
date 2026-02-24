#!/usr/bin/env python3
"""
ARMOTOS Pipeline v2 - Completo con imágenes
"""
import sys
sys.path.insert(0, "/opt/odi/odi_production/extractors")

import os, json, time, requests, warnings, logging, base64
from dotenv import load_dotenv
import pdfplumber
import openai
import chromadb

warnings.filterwarnings("ignore")
load_dotenv("/opt/odi/.env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("arm")

PDF = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Armotos/CATALOGO NOVIEMBRE V01-2025 NF.pdf"
OUT = "/opt/odi/data/ARMOTOS"
os.makedirs(OUT + "/json", exist_ok=True)
os.makedirs(OUT + "/images", exist_ok=True)

PROMPT = "Extrae productos de este catalogo de motos. JSON: {products:[{sku,title,price,category,compatibility:[motos]}]}. Solo JSON valido."

def extract_images_batch(start_page, end_page):
    """Extrae imagenes de un rango de paginas."""
    from odi_vision_extractor_v3 import VisionProductDetector
    from pdf2image import convert_from_path
    
    detector = VisionProductDetector(use_gemini=True)
    all_images = []
    
    for page_num in range(start_page, end_page + 1):
        retries = 3
        while retries > 0:
            try:
                pages = convert_from_path(PDF, dpi=200, first_page=page_num, last_page=page_num)
                if not pages:
                    break
                
                temp_path = f"{OUT}/images/pg{page_num:03d}.png"
                pages[0].save(temp_path)
                
                products = detector.detect(temp_path)
                if products:
                    crops = detector.crop_products(temp_path, products, f"{OUT}/images", "ARMOTOS", page_num)
                    all_images.extend(crops)
                
                os.remove(temp_path)
                break
            except Exception as e:
                retries -= 1
                if retries > 0:
                    time.sleep(2)
        time.sleep(0.5)
    
    return all_images

def upload_image_to_product(shop, token, product_id, image_path):
    """Sube imagen a producto existente."""
    if not os.path.exists(image_path):
        return False
    
    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        
        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        payload = {"image": {"attachment": img_b64, "filename": os.path.basename(image_path)}}
        
        r = requests.post(
            f"https://{shop}/admin/api/2025-07/products/{product_id}/images.json",
            headers=headers, json=payload, timeout=60
        )
        return r.status_code in [200, 201]
    except:
        return False

def main():
    log.info("=" * 50)
    log.info("ARMOTOS PIPELINE v2 - IMAGENES")
    
    shop = os.getenv("ARMOTOS_SHOP")
    token = os.getenv("ARMOTOS_TOKEN")
    headers = {"X-Shopify-Access-Token": token}
    
    # Paso 1: Verificar que imagenes ya existen
    existing_images = [f for f in os.listdir(f"{OUT}/images") if f.startswith("ARMOTOS_") and f.endswith(".png")]
    log.info(f"Imagenes existentes: {len(existing_images)}")
    
    # Paso 2: Extraer imagenes de paginas faltantes (33-256)
    log.info("[1/3] Extrayendo imagenes de paginas 33-256...")
    
    BATCH_SIZE = 10
    for batch_start in range(33, 257, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE - 1, 256)
        log.info(f"  Batch: paginas {batch_start}-{batch_end}")
        
        try:
            imgs = extract_images_batch(batch_start, batch_end)
            log.info(f"    Extraidas: {len(imgs)} imagenes")
        except Exception as e:
            log.error(f"    Error: {e}")
        
        time.sleep(2)  # Pausa entre batches
    
    # Contar imagenes totales
    all_images = [f for f in os.listdir(f"{OUT}/images") if f.startswith("ARMOTOS_") and f.endswith(".png")]
    log.info(f"Total imagenes extraidas: {len(all_images)}")
    
    # Paso 3: Obtener productos de Shopify
    log.info("[2/3] Obteniendo productos de Shopify...")
    products = []
    since_id = 0
    while True:
        r = requests.get(
            f"https://{shop}/admin/api/2025-07/products.json?limit=250&since_id={since_id}",
            headers=headers
        )
        batch = r.json().get("products", [])
        if not batch:
            break
        products.extend(batch)
        since_id = batch[-1]["id"]
    
    log.info(f"  Productos en Shopify: {len(products)}")
    
    # Paso 4: Match y upload imagenes
    log.info("[3/3] Subiendo imagenes a productos...")
    
    # Crear indice de imagenes por pagina
    images_by_page = {}
    for img_file in all_images:
        # Parse: ARMOTOS_p002_prod01.png
        try:
            parts = img_file.replace(".png", "").split("_")
            page = int(parts[1].replace("p", ""))
            if page not in images_by_page:
                images_by_page[page] = []
            images_by_page[page].append(img_file)
        except:
            pass
    
    # Cargar productos con pagina del JSON
    json_path = f"{OUT}/json/products.json"
    if os.path.exists(json_path):
        with open(json_path) as f:
            local_products = json.load(f)
    else:
        local_products = []
    
    # Crear mapping titulo -> pagina
    title_to_page = {}
    for p in local_products:
        title = p.get("title", "").lower()[:50]
        page = p.get("page", 0)
        if title and page:
            title_to_page[title] = page
    
    uploaded = 0
    errors = 0
    
    for i, sp in enumerate(products):
        if i % 50 == 0:
            log.info(f"  Procesando {i}/{len(products)} (uploaded: {uploaded})")
        
        # Check if already has image
        if sp.get("images"):
            continue
        
        # Find matching image by title -> page
        title = sp.get("title", "").lower()[:50]
        page = title_to_page.get(title, 0)
        
        if page and page in images_by_page and images_by_page[page]:
            # Use first available image from that page
            img_file = images_by_page[page].pop(0)
            img_path = f"{OUT}/images/{img_file}"
            
            if upload_image_to_product(shop, token, sp["id"], img_path):
                uploaded += 1
            else:
                errors += 1
            
            time.sleep(0.3)  # Rate limit
    
    log.info(f"Uploaded: {uploaded}, Errors: {errors}")
    
    # Verificacion final
    log.info("=" * 50)
    log.info("VERIFICACION FINAL")
    
    with_img = 0
    without_img = 0
    since_id = 0
    while True:
        r = requests.get(
            f"https://{shop}/admin/api/2025-07/products.json?limit=250&fields=id,images&since_id={since_id}",
            headers=headers
        )
        batch = r.json().get("products", [])
        if not batch:
            break
        for p in batch:
            if p.get("images"):
                with_img += 1
            else:
                without_img += 1
        since_id = batch[-1]["id"]
    
    total = with_img + without_img
    log.info(f"Con imagen: {with_img} ({with_img/total*100:.1f}%)")
    log.info(f"Sin imagen: {without_img} ({without_img/total*100:.1f}%)")
    log.info("=" * 50)

if __name__ == "__main__":
    main()
