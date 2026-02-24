#!/usr/bin/env python3
"""
PDF Image to Shopify Replacer V18
- Vision AI describes PDF images
- Fuzzy match against Shopify titles
- Replace AI images with real PDF images
"""

import os
import sys
import json
import time
import base64
import logging
import requests
from pathlib import Path
from difflib import SequenceMatcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PDFToShopifyReplacer:
    def __init__(self, store_name: str):
        self.store_name = store_name
        self.load_credentials()
        self.vision_cache = {}

    def load_credentials(self):
        """Load Shopify and API credentials"""
        config_path = f'/opt/odi/data/brands/{self.store_name.lower()}.json'
        with open(config_path) as f:
            config = json.load(f)

        shopify = config.get('shopify', {})
        self.shop_domain = shopify.get('shop_name', shopify.get('shop', ''))
        self.access_token = shopify.get('access_token', shopify.get('token', ''))

        if not self.shop_domain.endswith('.myshopify.com'):
            self.shop_domain = f'{self.shop_domain}.myshopify.com'

        self.shopify_base = f'https://{self.shop_domain}/admin/api/2024-01'
        self.headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }

        # Gemini for Vision
        self.gemini_key = os.getenv('GEMINI_API_KEY', '')
        if not self.gemini_key:
            with open('/opt/odi/.env') as f:
                for line in f:
                    if line.startswith('GEMINI_API_KEY='):
                        self.gemini_key = line.strip().split('=', 1)[1].strip('"\'')
                        break

    def get_shopify_products(self) -> list:
        """Get all products with ID, title, SKU"""
        products = []
        url = f'{self.shopify_base}/products.json?limit=250&fields=id,title,variants'

        while url:
            resp = requests.get(url, headers=self.headers)
            time.sleep(0.5)

            if resp.status_code != 200:
                logger.error(f'Shopify error: {resp.status_code}')
                break

            data = resp.json()
            for p in data.get('products', []):
                sku = ''
                if p.get('variants'):
                    sku = p['variants'][0].get('sku', '')
                products.append({
                    'id': p['id'],
                    'title': p['title'],
                    'sku': sku
                })

            # Pagination
            link = resp.headers.get('Link', '')
            if 'rel="next"' in link:
                for part in link.split(','):
                    if 'rel="next"' in part:
                        url = part.split('<')[1].split('>')[0]
                        break
            else:
                url = None

        logger.info(f'Loaded {len(products)} products from Shopify')
        return products

    def describe_image_vision(self, image_path: str) -> str:
        """Use Gemini Vision to describe the image"""
        if image_path in self.vision_cache:
            return self.vision_cache[image_path]

        try:
            with open(image_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode()

            url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}'

            payload = {
                'contents': [{
                    'parts': [
                        {'text': 'Describe this motorcycle part in 5-10 words. Focus on: part type, brand if visible, size/specs. Example: "Oil filter for Bajaj Pulsar 200" or "Brake pads ceramic front disc". Just the description, no extra text.'},
                        {'inline_data': {'mime_type': 'image/png', 'data': img_data}}
                    ]
                }]
            }

            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                self.vision_cache[image_path] = text
                return text
        except Exception as e:
            logger.error(f'Vision error {image_path}: {e}')

        return ''

    def fuzzy_match(self, description: str, products: list, threshold: float = 0.5) -> dict:
        """Find best matching product by title similarity"""
        best_match = None
        best_score = 0

        desc_lower = description.lower()

        for p in products:
            title_lower = p['title'].lower()

            # Calculate similarity
            score = SequenceMatcher(None, desc_lower, title_lower).ratio()

            # Boost if key words match
            desc_words = set(desc_lower.split())
            title_words = set(title_lower.split())
            common = desc_words & title_words
            if len(common) >= 2:
                score += 0.2

            if score > best_score:
                best_score = score
                best_match = p

        if best_score >= threshold:
            return {'product': best_match, 'score': best_score}
        return None

    def delete_product_images(self, product_id: int) -> bool:
        """Delete all images from a product"""
        url = f'{self.shopify_base}/products/{product_id}/images.json'
        resp = requests.get(url, headers=self.headers)
        time.sleep(0.3)

        if resp.status_code != 200:
            return False

        images = resp.json().get('images', [])
        for img in images:
            del_url = f'{self.shopify_base}/products/{product_id}/images/{img["id"]}.json'
            requests.delete(del_url, headers=self.headers)
            time.sleep(0.3)

        return True

    def upload_image(self, product_id: int, image_path: str) -> bool:
        """Upload image to product"""
        try:
            with open(image_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode()

            url = f'{self.shopify_base}/products/{product_id}/images.json'
            payload = {
                'image': {
                    'attachment': img_data,
                    'filename': os.path.basename(image_path)
                }
            }

            resp = requests.post(url, headers=self.headers, json=payload)
            time.sleep(0.5)

            return resp.status_code == 200
        except Exception as e:
            logger.error(f'Upload error: {e}')
            return False

    def run(self, images_dir: str, threshold: float = 0.5):
        """Main process"""
        logger.info(f'=== PDF to Shopify Replacer: {self.store_name} ===')

        # Get products
        products = self.get_shopify_products()
        if not products:
            logger.error('No products found')
            return

        # Get valid images
        img_dir = Path(images_dir)
        images = list(img_dir.glob('*.png')) + list(img_dir.glob('*.jpg')) + list(img_dir.glob('*.ppm'))
        logger.info(f'Found {len(images)} images to process')

        stats = {'matched': 0, 'replaced': 0, 'failed': 0, 'no_match': 0}
        matches = []

        # Phase 1: Vision AI + Fuzzy Match
        logger.info('Phase 1: Vision AI description + fuzzy match...')
        for i, img_path in enumerate(images):
            if i % 50 == 0:
                logger.info(f'Describing {i}/{len(images)}...')

            desc = self.describe_image_vision(str(img_path))
            if not desc:
                stats['failed'] += 1
                continue

            match = self.fuzzy_match(desc, products, threshold)
            if match:
                matches.append({
                    'image': str(img_path),
                    'description': desc,
                    'product_id': match['product']['id'],
                    'product_title': match['product']['title'],
                    'score': match['score']
                })
                stats['matched'] += 1
            else:
                stats['no_match'] += 1

        logger.info(f'Phase 1 complete: {stats["matched"]} matches, {stats["no_match"]} no match')

        # Phase 2: Replace images
        logger.info('Phase 2: Replacing images in Shopify...')
        for i, m in enumerate(matches):
            if i % 20 == 0:
                logger.info(f'Replacing {i}/{len(matches)}...')

            # Delete existing
            self.delete_product_images(m['product_id'])

            # Upload new
            if self.upload_image(m['product_id'], m['image']):
                stats['replaced'] += 1
                logger.info(f'  OK {m["product_title"][:40]} <- {os.path.basename(m["image"])} (score: {m["score"]:.2f})')
            else:
                stats['failed'] += 1

        # Summary
        logger.info(f'=== COMPLETE: {self.store_name} ===')
        logger.info(f'Matched: {stats["matched"]}')
        logger.info(f'Replaced: {stats["replaced"]}')
        logger.info(f'Failed: {stats["failed"]}')
        logger.info(f'No match: {stats["no_match"]}')

        # Save matches for reference
        with open(f'/opt/odi/data/audit_results/{self.store_name}_pdf_matches.json', 'w') as f:
            json.dump(matches, f, indent=2)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: pdf_to_shopify_replacer.py STORE_NAME IMAGES_DIR [threshold]')
        sys.exit(1)

    store = sys.argv[1]
    images_dir = sys.argv[2]
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5

    replacer = PDFToShopifyReplacer(store)
    replacer.run(images_dir, threshold)
