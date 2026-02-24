#!/usr/bin/env python3
"""ODI Image Replacer - Reemplaza imágenes en Shopify"""
import os
import json
import time
import requests
import base64
import logging
from typing import Optional, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/odi/logs/image_replacer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ImageReplacer:
    def __init__(self, store: str):
        self.store = store.upper()
        self.shop = None
        self.token = None
        self._load_credentials()
        
    def _load_credentials(self):
        config_path = f'/opt/odi/data/brands/{self.store.lower()}.json'
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)
            # Manejar diferentes formatos
            if 'shopify' in config:
                shop_config = config['shopify']
                self.shop = shop_config.get('shop', '').replace('.myshopify.com', '')
                self.token = shop_config.get('token')
            else:
                self.shop = config.get('shop_name', config.get('shop', ''))
                self.token = config.get('access_token', config.get('token'))
        
        if not self.shop or not self.token:
            raise ValueError(f'No credentials for {self.store}')
    
    def _api_call(self, method: str, endpoint: str, data: dict = None) -> Optional[dict]:
        url = f'https://{self.shop}.myshopify.com/admin/api/2024-01/{endpoint}'
        headers = {'X-Shopify-Access-Token': self.token, 'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                resp = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                resp = requests.post(url, headers=headers, json=data, timeout=60)
            elif method == 'DELETE':
                resp = requests.delete(url, headers=headers, timeout=30)
            else:
                return None
            
            if resp.status_code == 429:
                time.sleep(2)
                return self._api_call(method, endpoint, data)
            
            if resp.status_code in [200, 201]:
                return resp.json() if resp.text else {}
            elif resp.status_code == 204:
                return {}
            else:
                return None
        except Exception as e:
            logger.error(f'API error: {e}')
            return None
    
    def get_product_by_sku(self, sku: str) -> Optional[dict]:
        result = self._api_call('GET', f'variants.json?sku={sku}')
        if result and result.get('variants'):
            variant = result['variants'][0]
            product_id = variant.get('product_id')
            if product_id:
                prod_result = self._api_call('GET', f'products/{product_id}.json')
                if prod_result:
                    return prod_result.get('product')
        return None
    
    def delete_product_images(self, product_id: int) -> int:
        result = self._api_call('GET', f'products/{product_id}/images.json')
        if not result:
            return 0
        
        deleted = 0
        for img in result.get('images', []):
            img_id = img.get('id')
            if img_id:
                del_result = self._api_call('DELETE', f'products/{product_id}/images/{img_id}.json')
                if del_result is not None:
                    deleted += 1
                time.sleep(0.5)
        return deleted
    
    def upload_image(self, product_id: int, image_path: str) -> bool:
        if not os.path.exists(image_path):
            return False
        
        with open(image_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        
        data = {'image': {'attachment': img_data, 'filename': os.path.basename(image_path)}}
        result = self._api_call('POST', f'products/{product_id}/images.json', data)
        return result is not None
    
    def replace_images(self, images_dir: str, limit: int = None) -> Dict:
        files = sorted([f for f in os.listdir(images_dir) if f.endswith('.png')])
        if limit:
            files = files[:limit]
        
        results = {'total': len(files), 'success': 0, 'not_found': 0, 'failed': 0}
        
        logger.info(f'Reemplazando {len(files)} imágenes para {self.store}')
        
        for i, filename in enumerate(files):
            sku = filename.split('_sku_')[1].replace('.png', '') if '_sku_' in filename else filename.replace('.png', '')
            image_path = os.path.join(images_dir, filename)
            
            product = self.get_product_by_sku(sku)
            time.sleep(0.5)
            
            if not product:
                results['not_found'] += 1
                continue
            
            product_id = product['id']
            self.delete_product_images(product_id)
            time.sleep(0.5)
            
            if self.upload_image(product_id, image_path):
                results['success'] += 1
            else:
                results['failed'] += 1
            
            time.sleep(0.5)
            
            if (i + 1) % 100 == 0:
                logger.info(f'Progreso: {i+1}/{len(files)} | OK: {results["success"]} | NotFound: {results["not_found"]}')
        
        logger.info(f'Completado: {results["success"]}/{results["total"]}')
        return results

if __name__ == '__main__':
    import sys
    store = sys.argv[1] if len(sys.argv) > 1 else 'ARMOTOS'
    images_dir = sys.argv[2] if len(sys.argv) > 2 else f'/opt/odi/data/{store}/smart_film_v2'
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    replacer = ImageReplacer(store)
    results = replacer.replace_images(images_dir, limit=limit)
    
    with open(f'/opt/odi/data/audit_results/{store}_replacement_results.json', 'w') as f:
        json.dump(results, f, indent=2)
