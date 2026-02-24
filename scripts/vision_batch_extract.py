#!/usr/bin/env python3
"""
V12.3 - Extraccion masiva de compatibilidad via Vision AI
Estrategia: 1 llamada por pagina, 3 en paralelo
"""
import os
import json
import base64
import asyncio
import httpx
from dotenv import load_dotenv
load_dotenv('/opt/odi/.env')

OPENAI_KEY = os.getenv('OPENAI_API_KEY')
PAGES_DIR = '/opt/odi/data/ARMOTOS/pages'
OUTPUT_FILE = '/opt/odi/data/ARMOTOS/vision_compat_results.json'

async def process_page(client, page_num, skus):
    """Process single page, extract all products."""
    page_file = os.path.join(PAGES_DIR, f'page_{page_num:03d}.png')
    
    if not os.path.exists(page_file):
        return {'page': page_num, 'status': 'no_file', 'products': []}
    
    with open(page_file, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    sku_list = ', '.join(skus[:15])  # Limit to avoid token overflow
    
    prompt = f'''Analiza esta pagina del catalogo ARMOTOS.
Para cada producto visible, extrae:
- codigo (SKU de 5 digitos)
- compatibilidad (motos compatibles, o Universal si aplica a todas)

Busca especificamente estos codigos: {sku_list}

Responde SOLO en formato JSON array:
[{{sku: XXXXX, compat: Honda CB110, Yamaha YBR}}]

Si un producto dice Universal o no especifica moto, pon Universal.'''

    try:
        resp = await client.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENAI_KEY}'},
            json={
                'model': 'gpt-4o',
                'messages': [{'role': 'user', 'content': [
                    {'type': 'text', 'text': prompt},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_b64}'}}
                ]}],
                'max_tokens': 1000
            },
            timeout=90
        )
        
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            # Parse JSON from response
            try:
                # Find JSON array in response
                start = content.find('[')
                end = content.rfind(']') + 1
                if start >= 0 and end > start:
                    products = json.loads(content[start:end])
                    return {'page': page_num, 'status': 'ok', 'products': products}
            except:
                pass
            return {'page': page_num, 'status': 'parse_error', 'raw': content[:200], 'products': []}
        else:
            return {'page': page_num, 'status': f'error_{resp.status_code}', 'products': []}
    except Exception as e:
        return {'page': page_num, 'status': f'exception', 'products': []}

async def process_batch(pages_data, batch_size=3):
    """Process pages in parallel batches."""
    results = []
    pages = list(pages_data.items())
    
    async with httpx.AsyncClient() as client:
        for i in range(0, len(pages), batch_size):
            batch = pages[i:i+batch_size]
            tasks = [process_page(client, int(page), [p['sku'] for p in prods]) 
                    for page, prods in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            # Progress
            done = len(results)
            ok = sum(1 for r in results if r['status'] == 'ok')
            print(f'  Progreso: {done}/{len(pages)} paginas ({ok} ok)', flush=True)
    
    return results

def main():
    print('V12.3 - Extraccion Vision AI por pagina')
    print('=' * 50)
    
    # Load grouped products
    with open('/tmp/products_by_page.json') as f:
        by_page = json.load(f)
    
    print(f'Paginas a procesar: {len(by_page)}')
    print(f'Batch size: 3 paralelas')
    print('=' * 50)
    
    # Process
    results = asyncio.run(process_batch(by_page, batch_size=3))
    
    # Stats
    ok = sum(1 for r in results if r['status'] == 'ok')
    total_prods = sum(len(r['products']) for r in results)
    
    print('=' * 50)
    print(f'Paginas OK: {ok}/{len(results)}')
    print(f'Productos extraidos: {total_prods}')
    
    # Save results
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'Guardado: {OUTPUT_FILE}')
    
    # Show sample
    print('\nMuestra de resultados:')
    for r in results[:3]:
        if r['products']:
            print(f'  Pagina {r["page"]}: {len(r["products"])} productos')
            for p in r['products'][:2]:
                print(f'    SKU {p.get("sku")}: {p.get("compat", "N/A")[:40]}')

if __name__ == '__main__':
    main()
