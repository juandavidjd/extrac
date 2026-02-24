import os
import json
import base64
import httpx
import chromadb
from dotenv import load_dotenv
load_dotenv('/opt/odi/.env')

OPENAI_KEY = os.getenv('OPENAI_API_KEY')
client = chromadb.HttpClient(host='localhost', port=8000)
collection = client.get_collection('odi_ind_motos')

with open('/opt/odi/data/ARMOTOS/json/all_products_v12_2_corrected.json') as f:
    data = json.load(f)
    products = data.get('products', [])

pages_dir = '/opt/odi/data/ARMOTOS/pages'

BENEFICIOS = {
    'Disco de Freno': 'Frenado seguro y progresivo. Material resistente al calor.',
    'Repuesto Moto': 'Repuesto de calidad. Fabricacion segun normas OEM.',
}

test_products = []
seen = set()
for p in products:
    sku = p.get('sku', '')
    page = p.get('page', 0)
    if sku and page and page not in seen and len(test_products) < 5:
        page_file = os.path.join(pages_dir, f'page_{page:03d}.png')
        if os.path.exists(page_file):
            test_products.append(p)
            seen.add(page)

print('5 EJEMPLOS BODY_HTML CON COMPATIBILIDAD REAL')
print('=' * 70)

for i, p in enumerate(test_products, 1):
    sku = p.get('sku', '')
    title = p.get('title', '')
    price = p.get('price', 0)
    page = p.get('page', 0)
    page_file = os.path.join(pages_dir, f'page_{page:03d}.png')
    
    # ChromaDB category
    try:
        cr = collection.get(where={'sku': sku}, include=['metadatas'], limit=1)
        category = cr['metadatas'][0].get('category', 'Repuesto Moto') if cr['metadatas'] else 'Repuesto Moto'
    except:
        category = 'Repuesto Moto'
    
    # Vision AI compatibility
    compat = 'Universal'
    with open(page_file, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    try:
        resp = httpx.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENAI_KEY}'},
            json={
                'model': 'gpt-4o',
                'messages': [{'role': 'user', 'content': [
                    {'type': 'text', 'text': f'Producto codigo {sku}: lista motos compatibles separadas por coma. Si es Universal di Universal.'},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_b64}'}}
                ]}],
                'max_tokens': 100
            },
            timeout=60
        )
        if resp.status_code == 200:
            compat = resp.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f'Error Vision: {e}')
    
    benef = BENEFICIOS.get(category, 'Repuesto de calidad certificada.')
    
    print(f'\n[{i}] SKU {sku} | Pagina {page} | {category}')
    print(f'    Titulo: {title}')
    print(f'    Compatibilidad: {compat}')
    print(f'\n--- BODY_HTML ---')
    print(f'''<div class=ficha-360>
  <h3>Descripcion Tecnica</h3>
  <p>{title}. Repuesto de alta calidad.</p>
  
  <h3>Informacion Tecnica</h3>
  <ul>
    <li><strong>Codigo:</strong> {sku}</li>
    <li><strong>Categoria:</strong> {category}</li>
    <li><strong>Precio:</strong>  COP</li>
  </ul>
  
  <h3>Compatibilidad</h3>
  <p>{compat}</p>
  
  <h3>Beneficios</h3>
  <p>{benef}</p>
  
  <h3>Instalacion</h3>
  <p>Instalacion por tecnico calificado.</p>
  
  <h3>Garantia</h3>
  <p>ARMOTOS DEL VALLE. Garantia de calidad.</p>
</div>''')
    print('-' * 70)
