#!/usr/bin/env python3
"""
Certified Upload v1.0
Sube productos a Shopify solo con imagenes validadas.
"""
import os
import json
import time
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')

class CertifiedUploader:
    def __init__(self, store):
        self.store = store
        self.shop = os.getenv(f'{store}_SHOP') or os.getenv(f'SHOPIFY_{store}_SHOP')
        self.token = os.getenv(f'{store}_TOKEN') or os.getenv(f'SHOPIFY_{store}_TOKEN')
        self.base_url = f'https://{self.shop}/admin/api/2024-01'
        self.headers = {'X-Shopify-Access-Token': self.token, 'Content-Type': 'application/json'}
        self.stats = {'uploaded': 0, 'with_img': 0, 'without_img': 0, 'errors': 0}
    
    def upload_product(self, product):
        """Sube un producto a Shopify"""
        img_path = product.get('image', '')
        has_valid_img = img_path and os.path.exists(img_path)
        
        # Preparar datos del producto
        data = {
            'product': {
                'title': product.get('title', 'Sin titulo'),
                'body_html': product.get('description', ''),
                'vendor': product.get('vendor', self.store),
                'product_type': product.get('category', ''),
                'status': 'active',
                'variants': [{
                    'sku': str(product.get('sku', '')),
                    'price': str(product.get('price', 0) / 100) if product.get('price', 0) > 1000 else str(product.get('price', 0)),
                    'inventory_management': None
                }]
            }
        }
        
        # Agregar imagen solo si es valida
        if has_valid_img:
            try:
                with open(img_path, 'rb') as f:
                    img_data = base64.b64encode(f.read()).decode('utf-8')
                data['product']['images'] = [{'attachment': img_data}]
            except:
                has_valid_img = False
        
        # Subir a Shopify
        try:
            r = requests.post(f'{self.base_url}/products.json', json=data, headers=self.headers, timeout=30)
            if r.status_code == 201:
                self.stats['uploaded'] += 1
                if has_valid_img:
                    self.stats['with_img'] += 1
                else:
                    self.stats['without_img'] += 1
                return True
            else:
                self.stats['errors'] += 1
                return False
        except Exception as e:
            self.stats['errors'] += 1
            return False
    
    def upload_batch(self, products, batch_name=''):
        print(f'Subiendo {len(products)} productos {batch_name}')
        for i, p in enumerate(products, 1):
            self.upload_product(p)
            if i % 50 == 0:
                print(f'  [{i}/{len(products)}] OK:{self.stats["uploaded"]} ERR:{self.stats["errors"]}')
            time.sleep(0.5)  # Rate limit
        return self.stats

if __name__ == '__main__':
    import sys
    store = sys.argv[1] if len(sys.argv) > 1 else 'ARMOTOS'
    
    # Cargar productos validados
    valid_file = f'/opt/odi/data/{store}_valid_products.json'
    all_file = f'/opt/odi/data/orden_maestra_v6/{store}_products.json'
    
    with open(valid_file) as f:
        valid_products = json.load(f)
    
    with open(all_file) as f:
        all_products = json.load(f)
    
    no_img_products = [p for p in all_products if not p.get('image')]
    
    print(f'=== CERTIFIED UPLOAD: {store} ===')
    print(f'Con imagen valida: {len(valid_products)}')
    print(f'Sin imagen: {len(no_img_products)}')
    
    uploader = CertifiedUploader(store)
    uploader.upload_batch(valid_products, '(con imagen)')
    uploader.upload_batch(no_img_products, '(sin imagen)')
    
    print(f'\n=== RESULTADO ===')
    print(f'Total subidos: {uploader.stats["uploaded"]}')
    print(f'Con imagen: {uploader.stats["with_img"]}')
    print(f'Sin imagen: {uploader.stats["without_img"]}')
    print(f'Errores: {uploader.stats["errors"]}')
