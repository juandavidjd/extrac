#!/usr/bin/env python3
"""
ODI Catalog Page Uploader v1.0
Uploads real catalog pages as product images in Shopify

Each product gets its catalog page as the primary image.
"""

import os
import sys
import json
import base64
import time
import requests
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, "/opt/odi")
from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")

class CatalogPageUploader:
    def __init__(self, store: str = "ARMOTOS"):
        self.store = store
        self.data_dir = Path(f"/opt/odi/data/{store}")
        self.pages_dir = self.data_dir / "hotspot_pages"

        self.shop = os.getenv(f"{store}_SHOP")
        self.token = os.getenv(f"{store}_TOKEN")
        self.api_version = "2025-07"
        self.headers = {
            "X-Shopify-Access-Token": self.token,
            "Content-Type": "application/json"
        }

        # Load product JSON to get page mapping
        with open(self.data_dir / "json" / "all_products.json") as f:
            self.products_json = json.load(f)

        # Build SKU -> page mapping
        self.sku_to_page = {}
        for p in self.products_json:
            codigo = p.get("codigo", "")
            page = p.get("page", 0)
            if codigo and page:
                # Handle list codes
                if isinstance(codigo, list):
                    for c in codigo:
                        self.sku_to_page[str(c)] = page
                else:
                    self.sku_to_page[str(codigo)] = page

        print(f"Loaded {len(self.sku_to_page)} SKU->page mappings")

    def get_shopify_products(self):
        """Fetch all products from Shopify with their SKUs"""
        products = []
        url = f"https://{self.shop}/admin/api/{self.api_version}/products.json?limit=250&fields=id,title,variants,images"

        while url:
            resp = requests.get(url, headers=self.headers, timeout=60)
            if resp.status_code != 200:
                print(f"Error fetching products: {resp.status_code}")
                break

            data = resp.json()
            products.extend(data.get("products", []))

            # Pagination
            link = resp.headers.get("Link", "")
            url = None
            if "next" in link:
                for part in link.split(","):
                    if "next" in part:
                        url = part.split(";")[0].strip().strip("<>")
                        break

            print(f"  Fetched {len(products)} products...", end="\r")

        print(f"  Total: {len(products)} products from Shopify")
        return products

    def upload_image(self, product_id: int, image_path: str) -> bool:
        """Upload image to Shopify product"""
        try:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

            url = f"https://{self.shop}/admin/api/{self.api_version}/products/{product_id}/images.json"
            payload = {
                "image": {
                    "attachment": image_b64,
                    "position": 1  # Primary image
                }
            }

            resp = requests.post(url, json=payload, headers=self.headers, timeout=120)
            return resp.status_code in [200, 201]

        except Exception as e:
            print(f"    Error uploading: {e}")
            return False

    def delete_existing_images(self, product_id: int) -> int:
        """Delete all existing images from a product"""
        url = f"https://{self.shop}/admin/api/{self.api_version}/products/{product_id}/images.json"
        resp = requests.get(url, headers=self.headers, timeout=30)

        if resp.status_code != 200:
            return 0

        images = resp.json().get("images", [])
        deleted = 0

        for img in images:
            img_id = img.get("id")
            del_url = f"https://{self.shop}/admin/api/{self.api_version}/products/{product_id}/images/{img_id}.json"
            del_resp = requests.delete(del_url, headers=self.headers, timeout=30)
            if del_resp.status_code == 200:
                deleted += 1

        return deleted

    def run(self, limit: int = None, skip_existing: bool = True):
        """Upload catalog pages to all products"""
        print("=" * 70)
        print(f"CATALOG PAGE UPLOADER - {self.store}")
        print("=" * 70)

        # Get Shopify products
        print("\n[1] Fetching Shopify products...")
        shopify_products = self.get_shopify_products()

        # Build mapping
        print("\n[2] Mapping products to pages...")
        to_upload = []
        no_page = 0
        already_has_image = 0

        for p in shopify_products:
            pid = p.get("id")
            title = p.get("title", "")[:40]
            variants = p.get("variants", [])
            images = p.get("images", [])

            # Get SKU
            sku = None
            for v in variants:
                if v.get("sku"):
                    sku = str(v.get("sku")).strip()
                    break

            if not sku:
                continue

            # Find page
            page = self.sku_to_page.get(sku)
            if not page:
                no_page += 1
                continue

            # Check if already has image
            if skip_existing and images:
                already_has_image += 1
                continue

            # Check if page image exists
            page_img = self.pages_dir / f"page_{page}.png"
            if not page_img.exists():
                continue

            to_upload.append({
                "id": pid,
                "sku": sku,
                "title": title,
                "page": page,
                "image_path": str(page_img),
                "has_existing": len(images) > 0
            })

        print(f"    Products to upload: {len(to_upload)}")
        print(f"    Already have image: {already_has_image}")
        print(f"    No page mapping: {no_page}")

        if limit:
            to_upload = to_upload[:limit]
            print(f"    Limited to: {limit}")

        # Upload
        print(f"\n[3] Uploading catalog pages...")
        print("-" * 70)

        results = {"success": 0, "failed": 0, "deleted": 0}

        for i, item in enumerate(to_upload):
            pid = item["id"]
            sku = item["sku"]
            page = item["page"]
            title = item["title"]
            image_path = item["image_path"]

            # Delete existing images if any
            if item["has_existing"]:
                deleted = self.delete_existing_images(pid)
                results["deleted"] += deleted

            # Upload new image
            success = self.upload_image(pid, image_path)

            if success:
                results["success"] += 1
                status = "✓"
            else:
                results["failed"] += 1
                status = "✗"

            if (i + 1) % 25 == 0 or (i + 1) == len(to_upload):
                print(f"  [{i+1}/{len(to_upload)}] {status} {sku} -> page {page} | {title}")

            # Rate limiting
            time.sleep(0.5)

        # Summary
        print("\n" + "=" * 70)
        print("RESUMEN")
        print("=" * 70)
        print(f"  Imágenes subidas: {results['success']}")
        print(f"  Fallidas: {results['failed']}")
        print(f"  Imágenes previas eliminadas: {results['deleted']}")
        print("=" * 70)

        return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Catalog Page Uploader")
    parser.add_argument("--store", default="ARMOTOS", help="Store name")
    parser.add_argument("--limit", type=int, help="Limit products to upload")
    parser.add_argument("--replace", action="store_true", help="Replace existing images")

    args = parser.parse_args()

    uploader = CatalogPageUploader(args.store)
    results = uploader.run(limit=args.limit, skip_existing=not args.replace)
