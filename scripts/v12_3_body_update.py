#!/usr/bin/env python3
import os, requests, json, time
from dotenv import load_dotenv
load_dotenv('/opt/odi/.env')

SHOP = os.environ.get('ARMOTOS_SHOP')
TOKEN = os.environ.get('ARMOTOS_TOKEN')

print('V12.3 - body_html update')
print('=' * 60)

products = json.load(open('/tmp/armotos_products.json'))
print('Productos:', len(products))

vision_data = json.load(open('/opt/odi/data/ARMOTOS/vision_compat_results.json'))
compat_map = {}
for page_data in vision_data:
    for p in page_data.get('products', []):
        sku = p.get('sku', '').strip()
        compat = p.get('compat', 'Universal')
        if sku:
            compat_map[sku] = compat
print('Compatibilidades:', len(compat_map))

SRM = {
    'filtro': 'Protege el motor de impurezas',
    'aceite': 'Lubricacion optima del motor',
    'freno': 'Frenado seguro y eficiente',
    'cadena': 'Transmision de potencia suave',
    'bujia': 'Encendido eficiente',
    'espejo': 'Visibilidad clara',
    'faro': 'Iluminacion potente',
}

def get_benefit(title):
    for k, v in SRM.items():
        if k in title.lower():
            return v
    return 'Repuesto de calidad para tu motocicleta'

def build_html(title, sku, compat):
    if not compat:
        compat = 'Universal'
    benefit = get_benefit(title)
    nl = chr(10)
    h = '<div class="product-description">' + nl
    h += '<h3>Descripcion</h3>' + nl
    h += '<p>' + title + '. ' + benefit + '.</p>' + nl*2
    h += '<h3>Compatibilidad</h3>' + nl
    h += '<p><strong>' + compat + '</strong></p>' + nl*2
    h += '<h3>Especificaciones</h3>' + nl
    h += '<ul>' + nl
    h += '<li><strong>SKU:</strong> ' + str(sku) + '</li>' + nl
    h += '<li><strong>Marca:</strong> ARMOTOS</li>' + nl
    h += '<li><strong>Condicion:</strong> Nuevo</li>' + nl
    h += '</ul>' + nl*2
    h += '<h3>Envio</h3>' + nl
    h += '<p>Envio a toda Colombia. 2-5 dias habiles.</p>' + nl*2
    h += '<h3>Garantia</h3>' + nl
    h += '<p>30 dias por defectos de fabrica.</p>' + nl
    h += '</div>'
    return h

session = requests.Session()
ok = 0
err = 0
start = time.time()
total = len(products)

for i, p in enumerate(products):
    pid = p['id']
    title = p['title']
    sku = p['sku']
    compat = compat_map.get(sku, 'Universal')
    html = build_html(title, sku, compat)
    
    url = 'https://' + SHOP + '/admin/api/2025-01/products/' + str(pid) + '.json'
    data = {'product': {'id': int(pid), 'body_html': html}}
    
    for attempt in range(3):
        try:
            resp = session.put(url, json=data, headers={'X-Shopify-Access-Token': TOKEN, 'Content-Type': 'application/json'}, timeout=30)
            if resp.status_code == 200:
                ok += 1
                break
            elif resp.status_code == 429:
                time.sleep(3)
            else:
                err += 1
                break
        except:
            time.sleep(2)
    else:
        err += 1
    
    if (i + 1) % 100 == 0:
        elapsed = time.time() - start
        print('Progreso:', i+1, '/', total, '-', ok, 'ok,', err, 'err -', int(elapsed), 's', flush=True)
    
    time.sleep(0.6)

elapsed = time.time() - start
print('=' * 60)
print('RESULTADO:', ok, 'ok,', err, 'err de', total)
print('Tiempo:', int(elapsed), 's')

with_real = sum(1 for p in products if p['sku'] in compat_map)
print('Con Vision AI:', with_real)
print('Con Universal:', total - with_real)
