#!/usr/bin/env python3
"""
Image Uploader Base64 - Sube imagenes locales a Shopify via base64
"""
import os
import sys
import json
import time
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")
API_VERSION = "2024-01"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print("[" + ts + "] " + msg, flush=True)

def get_base64_image(filepath):
    """Convert local image to base64"""
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8")
    except Exception as e:
        return None

def update_product_image(shop, token, product_id, image_base64, filename):
    """Update product with base64 image"""
    url = "https://" + shop + "/admin/api/" + API_VERSION + "/products/" + str(product_id) + ".json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    
    # Determine content type
    ext = filename.lower().split(".")[-1]
    if ext == "png":
        content_type = "image/png"
    elif ext in ["jpg", "jpeg"]:
        content_type = "image/jpeg"
    else:
        content_type = "image/jpeg"
    
    data = {
        "product": {
            "id": product_id,
            "images": [{
                "attachment": image_base64,
                "filename": filename
            }]
        }
    }
    
    for attempt in range(3):
        try:
            r = requests.put(url, headers=headers, json=data, timeout=60)
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", 2))
                time.sleep(wait)
                continue
            return r.status_code == 200
        except:
            time.sleep(2 ** attempt)
    return False

def process_store(store_name, json_path, image_base_path):
    """Process a store - match products to images and upload"""
    shop = os.getenv(store_name + "_SHOP")
    token = os.getenv(store_name + "_TOKEN")
    
    if not shop or not token:
        log("ERROR: No credentials for " + store_name)
        return
    
    log("=" * 60)
    log("PROCESSING: " + store_name)
    log("=" * 60)
    
    # Load JSON to get image paths
    with open(json_path) as f:
        json_products = json.load(f)
    
    # Create SKU -> image path mapping
    sku_to_image = {}
    for p in json_products:
        sku = str(p.get("sku", "")).strip()
        img = p.get("image", "")
        if sku and img and isinstance(img, str) and img.startswith("/") and "placeholder" not in img.lower():
            sku_to_image[sku] = img
    
    log("JSON has " + str(len(sku_to_image)) + " products with local image paths")
    
    # Get products from Shopify
    log("Fetching products from Shopify...")
    shopify_products = []
    url = "https://" + shop + "/admin/api/" + API_VERSION + "/products.json?limit=250"
    
    while url:
        r = requests.get(url, headers={"X-Shopify-Access-Token": token}, timeout=30)
        if r.status_code != 200:
            break
        data = r.json()
        shopify_products.extend(data.get("products", []))
        
        link = r.headers.get("Link", "")
        if "rel=\"next\"" in link:
            for part in link.split(","):
                if "rel=\"next\"" in part:
                    url = part.split("<")[1].split(">")[0]
                    break
            else:
                url = None
        else:
            url = None
    
    log("Shopify has " + str(len(shopify_products)) + " products")
    
    # Count products without images
    without_image = [p for p in shopify_products if not p.get("images")]
    log("Products without images: " + str(len(without_image)))
    
    # Process products without images
    updated = 0
    errors = 0
    skipped = 0
    
    for i, product in enumerate(without_image):
        product_id = product["id"]
        
        # Get SKU from first variant
        sku = ""
        if product.get("variants"):
            sku = str(product["variants"][0].get("sku", "")).strip()
        
        # Find image path
        image_path = sku_to_image.get(sku, "")
        
        if not image_path or not os.path.exists(image_path):
            skipped += 1
            continue
        
        # Convert to base64
        image_b64 = get_base64_image(image_path)
        if not image_b64:
            skipped += 1
            continue
        
        # Upload
        filename = os.path.basename(image_path)
        success = update_product_image(shop, token, product_id, image_b64, filename)
        
        if success:
            updated += 1
        else:
            errors += 1
        
        if (updated + errors) % 50 == 0:
            log("  Progress: " + str(updated) + " updated, " + str(errors) + " errors, " + str(skipped) + " skipped")
        
        time.sleep(0.5)  # Rate limit
    
    log("")
    log("RESULTS for " + store_name + ":")
    log("  Updated: " + str(updated))
    log("  Errors: " + str(errors))
    log("  Skipped (no image match): " + str(skipped))
    
    return updated, errors, skipped

if __name__ == "__main__":
    store = sys.argv[1] if len(sys.argv) > 1 else "DFG"
    
    if store == "DFG":
        process_store(
            "DFG",
            "/opt/odi/data/orden_maestra_v6/DFG_products.json",
            "/mnt/volume_sfo3_01/profesion/ecosistema_odi/DFG/imagenes/"
        )
    elif store == "MCLMOTOS":
        process_store(
            "MCLMOTOS",
            "/opt/odi/data/orden_maestra_v6/MCLMOTOS_products.json",
            "/opt/odi/data/pdf_images/MCLMOTOS/"
        )
