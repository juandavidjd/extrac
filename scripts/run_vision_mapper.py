#!/usr/bin/env python3
"""Vision AI Mapper - Procesa todas las imágenes"""
import os, sys, json, base64, time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')
client = OpenAI()

def encode_image(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def identify_product(image_path):
    b64 = encode_image(image_path)
    try:
        resp = client.chat.completions.create(
            model='gpt-4o',
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'Identifica este repuesto de moto. Responde SOLO JSON: {"tipo": "...", "desc": "...", "kw": ["..."]}'}, 
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{b64}', 'detail': 'low'}}
                ]
            }],
            max_tokens=100
        )
        content = resp.choices[0].message.content.strip()
        if '{' in content:
            return json.loads(content[content.find('{'):content.rfind('}')+1])
    except:
        pass
    return {'tipo': 'NO'}

def match_product(vision, products):
    if vision.get('tipo') in ['NO', 'NO_PRODUCTO', 'ERROR']:
        return None, 0
    
    kw = [k.lower() for k in vision.get('kw', [])]
    tipo = vision.get('tipo', '').lower()
    desc = vision.get('desc', '').lower()
    
    best, score = None, 0
    for p in products:
        t = p.get('title', '').lower()
        s = 0
        if tipo and tipo in t: s += 3
        for k in kw:
            if k in t: s += 2
        for w in desc.split():
            if len(w) > 3 and w in t: s += 1
        if s > score:
            score, best = s, p
    return best, score

def process_store(store):
    images_dir = f'/mnt/volume_sfo3_01/profesion/ecosistema_odi/{store}/imagenes'
    products_json = f'/opt/odi/data/orden_maestra_v6/{store}_products.json'
    
    with open(products_json) as f:
        products = json.load(f)
    
    images = sorted([f for f in os.listdir(images_dir) if f.endswith(('.png', '.jpg'))])
    
    print(f'=== {store}: {len(images)} imgs, {len(products)} prods ===')
    
    results = {'store': store, 'matched': [], 'no_match': [], 'no_prod': []}
    
    for i, img in enumerate(images):
        path = os.path.join(images_dir, img)
        vis = identify_product(path)
        
        if vis.get('tipo') in ['NO', 'NO_PRODUCTO']:
            results['no_prod'].append(img)
            status = 'X'
        else:
            match, score = match_product(vis, products)
            if match and score >= 3:
                results['matched'].append({
                    'img': img, 'id': match.get('id'), 
                    'sku': match.get('sku'), 'title': match.get('title')[:40],
                    'score': score
                })
                status = f'M:{match.get("sku")}'
            else:
                results['no_match'].append({'img': img, 'vis': vis})
                status = f'?:{score}'
        
        if (i+1) % 10 == 0:
            print(f'  [{i+1}/{len(images)}] M:{len(results["matched"])} X:{len(results["no_prod"])} ?:{len(results["no_match"])}')
        time.sleep(0.3)
    
    print(f'RESULTADO {store}: Matched={len(results["matched"])} NoProd={len(results["no_prod"])} NoMatch={len(results["no_match"])}')
    
    with open(f'/opt/odi/data/audit_results/{store}_vision_map.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    return results

if __name__ == '__main__':
    store = sys.argv[1]
    process_store(store)
