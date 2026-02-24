#!/usr/bin/env python3
"""Vision AI Image Mapper - Identifica productos en imágenes de PDF"""
import os, sys, json, base64, time, re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')
client = OpenAI()

def encode_image(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def identify_product(image_path):
    """Usa GPT-4o Vision para identificar el producto"""
    b64 = encode_image(image_path)
    try:
        resp = client.chat.completions.create(
            model='gpt-4o',
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'Identifica este repuesto de moto. Responde SOLO con JSON: {"tipo": "...", "descripcion": "...", "marca_compatible": "...", "keywords": ["...", "..."]}. Si no es un repuesto de moto, responde {"tipo": "NO_PRODUCTO"}'},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{b64}', 'detail': 'low'}}
                ]
            }],
            max_tokens=200
        )
        content = resp.choices[0].message.content.strip()
        # Extraer JSON
        if '{' in content:
            json_str = content[content.find('{'):content.rfind('}')+1]
            return json.loads(json_str)
    except Exception as e:
        print(f'Error: {e}')
    return {'tipo': 'ERROR'}

def match_to_products(vision_result, products):
    """Encuentra el mejor producto match"""
    if vision_result.get('tipo') in ['NO_PRODUCTO', 'ERROR']:
        return None, 0
    
    keywords = vision_result.get('keywords', [])
    tipo = vision_result.get('tipo', '').lower()
    desc = vision_result.get('descripcion', '').lower()
    marca = vision_result.get('marca_compatible', '').lower()
    
    best_match = None
    best_score = 0
    
    for p in products:
        title = p.get('title', '').lower()
        sku = p.get('sku', '').lower()
        score = 0
        
        # Match por tipo
        if tipo and tipo in title:
            score += 3
        
        # Match por keywords
        for kw in keywords:
            if kw.lower() in title:
                score += 2
        
        # Match por marca
        if marca and marca in title:
            score += 2
            
        # Match por descripcion
        for word in desc.split():
            if len(word) > 3 and word in title:
                score += 1
        
        if score > best_score:
            best_score = score
            best_match = p
    
    return best_match, best_score

def process_store(store, images_dir, products_json, sample_size=None):
    """Procesa imágenes de una tienda"""
    print(f'=== {store} ===')
    
    # Cargar productos
    with open(products_json) as f:
        products = json.load(f)
    print(f'Productos: {len(products)}')
    
    # Listar imágenes
    images = [f for f in os.listdir(images_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
    if sample_size:
        images = images[:sample_size]
    print(f'Imágenes a procesar: {len(images)}')
    
    results = {
        'store': store,
        'total_images': len(images),
        'matched': [],
        'no_match': [],
        'no_producto': []
    }
    
    for i, img_name in enumerate(images):
        img_path = os.path.join(images_dir, img_name)
        print(f'  [{i+1}/{len(images)}] {img_name}...', end=' ')
        
        vision = identify_product(img_path)
        
        if vision.get('tipo') == 'NO_PRODUCTO':
            results['no_producto'].append(img_name)
            print('NO_PRODUCTO')
            continue
        
        if vision.get('tipo') == 'ERROR':
            print('ERROR')
            continue
            
        match, score = match_to_products(vision, products)
        
        if match and score >= 3:
            results['matched'].append({
                'image': img_name,
                'product_id': match.get('id'),
                'sku': match.get('sku'),
                'title': match.get('title'),
                'score': score,
                'vision': vision
            })
            print(f'MATCH: {match.get("sku")} (score={score})')
        else:
            results['no_match'].append({
                'image': img_name,
                'vision': vision,
                'best_score': score
            })
            print(f'NO_MATCH (score={score})')
        
        time.sleep(0.5)  # Rate limit
    
    print(f'\nResumen {store}:')
    print(f'  Matched: {len(results["matched"])}')
    print(f'  No match: {len(results["no_match"])}')
    print(f'  No producto: {len(results["no_producto"])}')
    
    return results

if __name__ == '__main__':
    store = sys.argv[1]
    sample = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    images_dir = f'/mnt/volume_sfo3_01/profesion/ecosistema_odi/{store}/imagenes'
    products_json = f'/opt/odi/data/orden_maestra_v6/{store.lower()}_orden_maestra.json'
    
    results = process_store(store, images_dir, products_json, sample_size=sample)
    
    out_file = f'/opt/odi/data/audit_results/{store}_vision_map.json'
    with open(out_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f'\nResultados guardados en {out_file}')
