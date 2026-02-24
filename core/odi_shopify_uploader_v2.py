#!/usr/bin/env python3
"""
ODI Shopify Uploader v2 - Product creation and image upload
Handles creating products with Ficha 360, smart film images in Shopify.
Part of V12.2 ARMOTOS Reset pipeline.
"""
import os
import json
import base64
import httpx
import glob
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")


class ShopifyUploader:
    """Upload images and create products in Shopify."""
    
    def __init__(self, store: str):
        self.store = store.upper()
        self.shop = os.getenv(f"{self.store}_SHOP")
        self.token = os.getenv(f"{self.store}_TOKEN")
        self.api_version = "2025-01"
        
        if not self.shop or not self.token:
            raise ValueError(f"Missing credentials for store {self.store}")
        
        self.base_url = f"https://{self.shop}/admin/api/{self.api_version}"
        self.headers = {
            "X-Shopify-Access-Token": self.token,
            "Content-Type": "application/json"
        }
    
    def create_product(
        self,
        title: str,
        handle: str,
        body_html: str,
        price: float,
        sku: str,
        image_path: Optional[str] = None,
        status: str = "active"
    ) -> Optional[Dict]:
        """Create a new product in Shopify with image."""
        url = f"{self.base_url}/products.json"
        
        product_data = {
            "title": title[:60],
            "handle": handle,
            "body_html": body_html,
            "status": status,
            "vendor": "ARMOTOS",
            "variants": [{
                "price": str(price),
                "sku": sku,
                "inventory_management": None,
                "inventory_policy": "continue"
            }]
        }
        
        # Add image if provided
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            product_data["images"] = [{
                "attachment": image_data,
                "alt": title[:60]
            }]
        
        payload = {"product": product_data}
        
        try:
            resp = httpx.post(url, headers=self.headers, json=payload, timeout=120)
            resp.raise_for_status()
            return resp.json().get("product")
        except httpx.HTTPStatusError as e:
            print(f"HTTP Error {sku}: {e.response.status_code}")
            return None
        except Exception as e:
            print(f"Error {sku}: {e}")
            return None
    
    def get_product_count(self) -> int:
        """Get total product count."""
        url = f"{self.base_url}/products/count.json"
        try:
            resp = httpx.get(url, headers=self.headers, timeout=30)
            resp.raise_for_status()
            return resp.json().get("count", 0)
        except:
            return -1


def run_bulk_upload(json_path: str, images_dir: str, delay: float = 0.5):
    """Run bulk upload of products from JSON."""
    with open(json_path) as f:
        data = json.load(f)
        products = data.get("products", [])
    
    print(f"Total productos: {len(products)}", flush=True)
    
    uploader = ShopifyUploader("ARMOTOS")
    print(f"Shop: {uploader.shop}", flush=True)
    
    # Build SKU to image mapping
    sku_to_image = {}
    for img_file in glob.glob(os.path.join(images_dir, "*.png")):
        filename = os.path.basename(img_file)
        if "_sku_" in filename:
            sku = filename.split("_sku_")[1].replace(".png", "")
            sku_to_image[sku] = img_file
    
    print(f"Imagenes: {len(sku_to_image)}", flush=True)
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
            try:
                price = float(price.replace(",", ""))
            except:
                price = 0
        
        image_path = sku_to_image.get(sku)
        
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
        
        if (i + 1) % 100 == 0:
            elapsed = int(time.time() - start_time)
            created = stats["created"]
            failed = stats["failed"]
            print(f"  Progreso: {i+1}/{len(products)} ({created} ok, {failed} err) - {elapsed}s", flush=True)
        
        time.sleep(delay)
    
    elapsed = int(time.time() - start_time)
    print("=" * 50, flush=True)
    created = stats["created"]
    failed = stats["failed"]
    print(f"RESULTADO: {created} creados, {failed} fallidos", flush=True)
    print(f"Tiempo: {elapsed} segundos", flush=True)
    
    if stats["errors"]:
        with open("/opt/odi/data/ARMOTOS/upload_errors.json", "w") as f:
            json.dump(stats["errors"], f, indent=2)
    
    # Verify count
    final_count = uploader.get_product_count()
    print(f"Count final en Shopify: {final_count}", flush=True)
    
    return stats


if __name__ == "__main__":
    run_bulk_upload(
        json_path="/opt/odi/data/ARMOTOS/json/all_products_v12_2_corrected.json",
        images_dir="/opt/odi/data/ARMOTOS/smart_film_images",
        delay=0.5
    )
