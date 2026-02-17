#!/usr/bin/env python3
"""
ODI Freepik Image Generator v1.0
Generates product images using Freepik AI API

Modes:
- disabled: Supplier has real images, don't touch
- fill_missing: Generate only where NO image exists
- full: Generate for everything (supplier without visual catalog)
"""

import os
import sys
import json
import time
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

sys.path.insert(0, "/opt/odi")
from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("freepik_gen")

@dataclass
class FreepikConfig:
    enabled: bool = False
    mode: str = "disabled"  # disabled | fill_missing | full
    image_source: str = "supplier_catalog"

class FreepikImageGenerator:
    """Generates product images using Freepik AI API"""

    def __init__(self, store: str):
        self.store = store
        self.api_key = os.getenv("FREEPIK_API_KEY")
        self.api_url = "https://api.freepik.com/v1/ai/text-to-image"
        self.shop = os.getenv(f"{store}_SHOP")
        self.token = os.getenv(f"{store}_TOKEN")
        self.api_version = "2025-07"
        self.config = self._load_brand_config()
        self.output_dir = Path(f"/opt/odi/data/{store}/generated_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_brand_config(self) -> FreepikConfig:
        """Load brand configuration from brand.json"""
        config_path = Path(f"/opt/odi/data/{self.store}/brand.json")
        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
            return FreepikConfig(
                enabled=data.get("freepik_enabled", False),
                mode=data.get("freepik_mode", "disabled"),
                image_source=data.get("image_source", "supplier_catalog")
            )
        # Default config
        return FreepikConfig()

    def _build_prompt(self, product: Dict) -> str:
        """Build Freepik prompt from product data"""
        title = product.get("title", "motorcycle part")
        # Extract compatibility from tags or title
        compat = ""
        tags = product.get("tags", "")
        if isinstance(tags, str) and tags:
            motos = [t.strip() for t in tags.split(",") if any(m in t.lower() for m in ["pulsar", "tvs", "boxer", "discover", "platino", "apache", "ns", "bajaj", "honda", "yamaha", "suzuki", "kawasaki"])]
            if motos:
                compat = ", ".join(motos[:3])

        # Clean title for prompt
        clean_title = title.replace("- Armotos", "").strip()

        prompt = f"{clean_title}"
        if compat:
            prompt += f" compatible {compat}"
        prompt += ", motorcycle spare part on workshop metal table, "
        prompt += f"product tag with text '{clean_title}', "
        prompt += "realistic photography, workshop background, professional product shot, high detail"

        return prompt

    def _generate_image(self, prompt: str) -> Optional[str]:
        """Call Freepik API to generate image, returns image URL"""
        if not self.api_key:
            logger.error("FREEPIK_API_KEY not set")
            return None

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-freepik-api-key": self.api_key
        }

        payload = {
            "prompt": prompt,
            "negative_prompt": "blurry, low quality, distorted text, cartoon, illustration",
            "guidance_scale": 7,
            "num_images": 1,
            "image": {
                "size": "square_1_1"
            }
        }

        try:
            resp = requests.post(self.api_url, json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                images = data.get("data", [])
                if images:
                    return images[0].get("base64")
            else:
                logger.error(f"Freepik API error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Freepik request failed: {e}")

        return None

    def _upload_to_shopify(self, product_id: int, image_base64: str) -> bool:
        """Upload base64 image to Shopify product"""
        url = f"https://{self.shop}/admin/api/{self.api_version}/products/{product_id}/images.json"
        headers = {
            "X-Shopify-Access-Token": self.token,
            "Content-Type": "application/json"
        }
        payload = {
            "image": {
                "attachment": image_base64
            }
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            return resp.status_code == 200 or resp.status_code == 201
        except Exception as e:
            logger.error(f"Shopify upload failed: {e}")
            return False

    def _get_products_without_images(self, limit: int = None) -> List[Dict]:
        """Fetch products from Shopify that have no images"""
        products_without = []
        url = f"https://{self.shop}/admin/api/{self.api_version}/products.json?limit=250"
        headers = {"X-Shopify-Access-Token": self.token}

        while url:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                break

            data = resp.json()
            for p in data.get("products", []):
                if not p.get("images"):
                    products_without.append(p)
                    if limit and len(products_without) >= limit:
                        return products_without

            # Pagination
            link = resp.headers.get("Link", "")
            url = None
            if "next" in link:
                for part in link.split(","):
                    if "next" in part:
                        url = part.split(";")[0].strip().strip("<>")
                        break

        return products_without

    def _get_sample_by_categories(self, n_per_cat: int = 1) -> List[Dict]:
        """Get sample products from different categories"""
        categories = {
            "resorte": [], "caucho": [], "banda": [], "direccional": [],
            "cadena": [], "manigueta": [], "fusible": [], "base": [],
            "kit": [], "acople": []
        }

        products_without = self._get_products_without_images()
        logger.info(f"Found {len(products_without)} products without images")

        for p in products_without:
            title_lower = p.get("title", "").lower()
            for cat in categories:
                if cat in title_lower and len(categories[cat]) < n_per_cat:
                    categories[cat].append(p)
                    break

        sample = []
        for cat, prods in categories.items():
            sample.extend(prods)

        return sample

    def generate_for_product(self, product: Dict) -> Dict:
        """Generate and upload image for a single product"""
        pid = product.get("id")
        title = product.get("title", "Unknown")

        prompt = self._build_prompt(product)
        logger.info(f"Generating image for [{pid}] {title[:50]}...")
        logger.info(f"  Prompt: {prompt[:80]}...")

        image_b64 = self._generate_image(prompt)
        if not image_b64:
            return {"id": pid, "title": title, "status": "generation_failed"}

        # Save locally
        local_path = self.output_dir / f"{pid}.png"
        try:
            import base64
            with open(local_path, "wb") as f:
                f.write(base64.b64decode(image_b64))
        except:
            pass

        # Upload to Shopify
        uploaded = self._upload_to_shopify(pid, image_b64)
        status = "success" if uploaded else "upload_failed"

        return {
            "id": pid,
            "title": title,
            "prompt": prompt,
            "status": status,
            "local_path": str(local_path) if status == "success" else None
        }

    def run_batch(self, limit: int = None, sample_mode: bool = False) -> Dict:
        """Run batch image generation"""
        if not self.config.enabled and self.config.mode == "disabled":
            logger.warning(f"Freepik is disabled for {self.store}")
            return {"status": "disabled", "generated": 0}

        if self.config.mode not in ["fill_missing", "full"]:
            logger.warning(f"Invalid mode: {self.config.mode}")
            return {"status": "invalid_mode", "generated": 0}

        # Get products
        if sample_mode:
            products = self._get_sample_by_categories(n_per_cat=1)
        elif self.config.mode == "fill_missing":
            products = self._get_products_without_images(limit)
        else:
            # full mode - get all products (not implemented yet)
            products = self._get_products_without_images(limit)

        logger.info(f"Processing {len(products)} products in mode: {self.config.mode}")

        results = {"success": [], "failed": [], "total": len(products)}

        for i, product in enumerate(products):
            result = self.generate_for_product(product)
            if result["status"] == "success":
                results["success"].append(result)
            else:
                results["failed"].append(result)

            logger.info(f"[{i+1}/{len(products)}] {result['status']}")
            time.sleep(2)  # Rate limiting

        results["generated"] = len(results["success"])
        results["status"] = "completed"
        return results


def init_brand_config(store: str, enabled: bool = True, mode: str = "fill_missing"):
    """Initialize or update brand.json with Freepik config"""
    config_path = Path(f"/opt/odi/data/{store}/brand.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        with open(config_path) as f:
            data = json.load(f)
    else:
        data = {"nombre": store}

    data["freepik_enabled"] = enabled
    data["freepik_mode"] = mode
    data["image_source"] = "vision_ai + freepik_fill" if enabled else "supplier_catalog"

    with open(config_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"Brand config saved: {config_path}")
    return data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Freepik Image Generator")
    parser.add_argument("store", help="Store name (ARMOTOS, VITTON, etc.)")
    parser.add_argument("--init", action="store_true", help="Initialize brand.json")
    parser.add_argument("--mode", default="fill_missing", help="Freepik mode")
    parser.add_argument("--sample", action="store_true", help="Run sample (10 categories)")
    parser.add_argument("--limit", type=int, help="Limit products to process")

    args = parser.parse_args()

    if args.init:
        config = init_brand_config(args.store, enabled=True, mode=args.mode)
        print(json.dumps(config, indent=2))
    else:
        gen = FreepikImageGenerator(args.store)
        results = gen.run_batch(limit=args.limit, sample_mode=args.sample)
        print(json.dumps(results, indent=2, default=str))
