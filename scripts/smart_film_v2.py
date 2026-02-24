#!/usr/bin/env python3
"""Smart Film Generator V2 - Con franja clara para producto"""
import os
import json
import sys
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor, as_completed

class SmartFilmV2:
    def __init__(self, store='ARMOTOS'):
        self.store = store
        self.base_dir = f'/opt/odi/data/{store}'
        self.pages_dir = f'{self.base_dir}/hotspot_pages'
        self.output_dir = f'{self.base_dir}/smart_film_v2'
        self.hotspot_file = f'{self.base_dir}/hotspot_map_sample.json'
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Cargar coordenadas
        with open(self.hotspot_file) as f:
            data = json.load(f)
        self.hotspots = data.get('hotspots', {})
        
        # Cargar productos para nombres/precios
        products_file = f'/opt/odi/data/orden_maestra_v6/{store}_products.json'
        with open(products_file) as f:
            products = json.load(f)
        self.products = {str(p.get('sku', '')): p for p in products}
        
        # Font para banner
        try:
            self.font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)
            self.font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
        except:
            self.font = ImageFont.load_default()
            self.font_small = self.font
    
    def generate_film(self, page_key, product_info):
        """Genera película para un producto"""
        try:
            page_num = int(page_key.replace('page_', ''))
            sku = product_info.get('codigo', '')
            bbox = product_info.get('bbox', {})
            
            # Cargar página original
            page_path = f'{self.pages_dir}/page_{page_num}.png'
            if not os.path.exists(page_path):
                return None, f'Page not found: {page_path}'
            
            img = Image.open(page_path).convert('RGBA')
            w, h = img.size
            
            # Crear overlay negro α180
            overlay = Image.new('RGBA', (w, h), (0, 0, 0, 180))
            
            # Calcular zona clara (fila del producto)
            y_pct = bbox.get('y', 50)
            h_pct = bbox.get('h', 10)
            
            # Expandir franja para cubrir toda la fila
            strip_top = int((y_pct - 5) * h / 100)
            strip_bottom = int((y_pct + h_pct + 5) * h / 100)
            strip_top = max(0, strip_top)
            strip_bottom = min(h, strip_bottom)
            
            # Hacer la franja transparente en el overlay
            draw = ImageDraw.Draw(overlay)
            draw.rectangle([0, strip_top, w, strip_bottom], fill=(0, 0, 0, 0))
            
            # Combinar imagen + overlay
            result = Image.alpha_composite(img, overlay)
            
            # Agregar banner inferior
            banner_height = 60
            banner = Image.new('RGBA', (w, banner_height), (0, 0, 0, 220))
            banner_draw = ImageDraw.Draw(banner)
            
            # Obtener info del producto
            prod_data = self.products.get(sku, {})
            title = prod_data.get('title', f'SKU: {sku}')[:50]
            price = prod_data.get('price', '')
            
            # Texto en banner
            banner_draw.text((20, 10), title, fill='white', font=self.font)
            if price:
                price_text = f'' if isinstance(price, (int, float)) else str(price)
                banner_draw.text((20, 35), price_text, fill=(0, 255, 0), font=self.font_small)
            
            # Pegar banner
            result.paste(banner, (0, h - banner_height), banner)
            
            # Convertir a RGB y guardar
            result_rgb = result.convert('RGB')
            output_path = f'{self.output_dir}/page_{page_num:03d}_sku_{sku}.png'
            result_rgb.save(output_path, 'PNG', optimize=True)
            
            return output_path, None
            
        except Exception as e:
            return None, str(e)
    
    def generate_batch(self, limit=None):
        """Genera películas en batch"""
        tasks = []
        
        for page_key, page_data in self.hotspots.items():
            if isinstance(page_data, dict) and 'products' in page_data:
                for prod in page_data['products']:
                    if 'bbox' in prod:
                        tasks.append((page_key, prod))
        
        if limit:
            tasks = tasks[:limit]
        
        print(f'Generando {len(tasks)} películas...')
        
        success = 0
        errors = []
        
        for i, (page_key, prod) in enumerate(tasks):
            path, err = self.generate_film(page_key, prod)
            if path:
                success += 1
            else:
                errors.append({'sku': prod.get('codigo'), 'error': err})
            
            if (i + 1) % 10 == 0:
                print(f'  [{i+1}/{len(tasks)}] Success: {success}')
        
        print(f'\nCompletado: {success}/{len(tasks)}')
        if errors:
            print(f'Errores: {len(errors)}')
        
        return success, errors

if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    
    gen = SmartFilmV2('ARMOTOS')
    success, errors = gen.generate_batch(limit=limit)
    
    print(f'\nPelículas guardadas en: {gen.output_dir}')
