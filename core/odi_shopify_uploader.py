#!/usr/bin/env python3
"""
ODI Shopify Uploader - Product image and metadata uploader
Handles uploading smart film images and updating product titles in Shopify.
Part of V12 ARMOTOS Tienda Modelo pipeline.
"""
import os
import json
import base64
import httpx
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')


class ShopifyUploader:
    """Upload images and update products in Shopify."""
    
    def __init__(self, store: str):
        """
        Initialize uploader for a specific store.
        
        Args:
            store: Store name (e.g., 'ARMOTOS', 'DFG')
        """
        self.store = store.upper()
        self.shop = os.getenv(f'{self.store}_SHOP')
        self.token = os.getenv(f'{self.store}_TOKEN')
        self.api_version = '2025-01'
        
        if not self.shop or not self.token:
            raise ValueError(f'Missing credentials for store {self.store}')
        
        self.base_url = f'https://{self.shop}/admin/api/{self.api_version}'
        self.headers = {
            'X-Shopify-Access-Token': self.token,
            'Content-Type': 'application/json'
        }
    
    def get_product_by_sku(self, sku: str) -> Optional[Dict]:
        """Find product by SKU."""
        # Search in variants
        url = f'{self.base_url}/variants.json'
        params = {'sku': sku, 'limit': 1}
        
        try:
            resp = httpx.get(url, headers=self.headers, params=params, timeout=30)
            resp.raise_for_status()
            variants = resp.json().get('variants', [])
            
            if variants:
                product_id = variants[0].get('product_id')
                return self.get_product(product_id)
        except Exception as e:
            print(f'Error finding SKU {sku}: {e}')
        
        return None
    
    def get_product(self, product_id: int) -> Optional[Dict]:
        """Get product by ID."""
        url = f'{self.base_url}/products/{product_id}.json'
        
        try:
            resp = httpx.get(url, headers=self.headers, timeout=30)
            resp.raise_for_status()
            return resp.json().get('product')
        except:
            return None
    
    def upload_image(
        self,
        product_id: int,
        image_path: str,
        position: int = 1,
        alt: str = ''
    ) -> Optional[Dict]:
        """
        Upload image to product.
        
        Args:
            product_id: Shopify product ID
            image_path: Local path to image file
            position: Image position (1 = primary)
            alt: Alt text for image
        
        Returns:
            Image data dict if successful
        """
        if not os.path.exists(image_path):
            return None
        
        # Encode image
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        url = f'{self.base_url}/products/{product_id}/images.json'
        payload = {
            'image': {
                'attachment': image_data,
                'position': position,
                'alt': alt
            }
        }
        
        try:
            resp = httpx.post(url, headers=self.headers, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json().get('image')
        except Exception as e:
            print(f'Error uploading image: {e}')
            return None
    
    def update_product_title(self, product_id: int, title: str) -> bool:
        """Update product title."""
        url = f'{self.base_url}/products/{product_id}.json'
        payload = {'product': {'id': product_id, 'title': title}}
        
        try:
            resp = httpx.put(url, headers=self.headers, json=payload, timeout=30)
            resp.raise_for_status()
            return True
        except:
            return False
    
    def update_variant_price(self, variant_id: int, price: str) -> bool:
        """Update variant price."""
        url = f'{self.base_url}/variants/{variant_id}.json'
        payload = {'variant': {'id': variant_id, 'price': price}}
        
        try:
            resp = httpx.put(url, headers=self.headers, json=payload, timeout=30)
            resp.raise_for_status()
            return True
        except:
            return False
    
    def batch_upload_smart_film(
        self,
        images_dir: str,
        sku_to_product: Dict[str, int],
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Batch upload smart film images.
        
        Args:
            images_dir: Directory containing smart film images
            sku_to_product: Mapping of SKU to Shopify product ID
            dry_run: If True, don't actually upload
        
        Returns:
            Stats dict
        """
        stats = {'uploaded': 0, 'skipped': 0, 'failed': 0}
        
        for filename in os.listdir(images_dir):
            if not filename.endswith('.png'):
                continue
            
            # Extract SKU from filename (format: page_XXX_sku_XXXXX.png)
            parts = filename.replace('.png', '').split('_')
            sku = None
            for i, p in enumerate(parts):
                if p == 'sku' and i + 1 < len(parts):
                    sku = parts[i + 1]
                    break
            
            if not sku or sku not in sku_to_product:
                stats['skipped'] += 1
                continue
            
            if dry_run:
                print(f'[DRY RUN] Would upload {filename} to product {sku_to_product[sku]}')
                stats['uploaded'] += 1
                continue
            
            image_path = os.path.join(images_dir, filename)
            product_id = sku_to_product[sku]
            
            result = self.upload_image(product_id, image_path, position=2, alt=f'Catalog view - {sku}')
            
            if result:
                stats['uploaded'] += 1
            else:
                stats['failed'] += 1
        
        return stats


def get_uploader(store: str) -> ShopifyUploader:
    """Factory function to get uploader for store."""
    return ShopifyUploader(store)


if __name__ == '__main__':
    # Test
    uploader = get_uploader('ARMOTOS')
    product = uploader.get_product_by_sku('03510')
    if product:
        print(f'Found: {product["title"]}')
    else:
        print('Product not found')

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
        """
        Create a new product in Shopify.
        
        Args:
            title: Product title (max 60 chars)
            handle: URL-friendly handle
            body_html: HTML description (Ficha 360)
            price: Product price in COP
            sku: Product SKU code
            image_path: Optional path to image file
            status: Product status (active/draft)
        
        Returns:
            Created product dict if successful
        """
        url = f"{self.base_url}/products.json"
        
        # Build product payload
        product_data = {
            "title": title[:60],
            "handle": handle,
            "body_html": body_html,
            "status": status,
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
            print(f"HTTP Error creating {sku}: {e.response.status_code} - {e.response.text[:200]}")
            return None
        except Exception as e:
            print(f"Error creating {sku}: {e}")
            return None
    
    def bulk_create_from_json(
        self,
        json_path: str,
        images_dir: str,
        start_idx: int = 0,
        limit: int = None,
        delay: float = 0.5
    ) -> Dict:
        """
        Bulk create products from corrected JSON file.
        
        Args:
            json_path: Path to corrected products JSON
            images_dir: Directory with smart film images
            start_idx: Starting index (for resume)
            limit: Max products to create (None = all)
            delay: Delay between API calls in seconds
        
        Returns:
            Stats dict with created, failed, skipped counts
        """
        import time
        import glob
        
        # Load products
        with open(json_path, "r", encoding="utf-8") as f:
            products = json.load(f)
        
        # Build SKU to image mapping
        sku_to_image = {}
        for img_file in glob.glob(os.path.join(images_dir, "*.png")):
            filename = os.path.basename(img_file)
            # Format: page_XXX_sku_YYYYY.png or sku_YYYYY.png
            if "_sku_" in filename:
                sku = filename.split("_sku_")[1].replace(".png", "")
                sku_to_image[sku] = img_file
        
        stats = {"created": 0, "failed": 0, "skipped": 0, "errors": []}
        
        end_idx = len(products) if limit is None else min(start_idx + limit, len(products))
        
        print(f"Uploading products {start_idx+1} to {end_idx} of {len(products)}")
        print(f"Images mapped: {len(sku_to_image)}")
        print("=" * 50)
        
        for i, prod in enumerate(products[start_idx:end_idx], start=start_idx):
            # Extract SKU (handle list or string)
            sku = prod.get("codigo", "")
            if isinstance(sku, list):
                sku = sku[0] if sku else ""
            sku = str(sku).strip()
            
            title = prod.get("titulo", prod.get("title", ""))
            handle = prod.get("handle", "")
            body_html = prod.get("body_html", "")
            price = prod.get("precio", prod.get("price", 0))
            
            # Find image
            image_path = sku_to_image.get(sku)
            
            # Skip if missing critical data
            if not title or not sku:
                stats["skipped"] += 1
                continue
            
            # Create product
            result = self.create_product(
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
                stats["errors"].append({"idx": i, "sku": sku, "title": title[:30]})
            
            # Progress report every 100
            if (i + 1) % 100 == 0:
                print(f"  Progreso: {i+1}/{end_idx} ({stats['created']} ok, {stats['failed']} err)")
            
            time.sleep(delay)
        
        print("=" * 50)
        print(f"RESULTADO: {stats['created']} creados, {stats['failed']} fallidos, {stats['skipped']} saltados")
        
        return stats
