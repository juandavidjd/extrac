#!/usr/bin/env python3
import json
import requests
import time
import os
import re

SHOP = os.environ.get('ARMOTOS_SHOP', 'znxx5p-10.myshopify.com')
TOKEN = os.environ.get('ARMOTOS_TOKEN')

SRM_BENEFITS = {
    'filtro': 'Protege el motor de impurezas',
    'aceite': 'Lubricacion optima del motor',
    'freno': 'Frenado seguro y eficiente',
    'pastilla': 'Frenado seguro y eficiente',
    'cadena': 'Transmision de potencia suave',
    'kit': 'Componentes originales',
    'bujia': 'Encendido eficiente',
    'suspension': 'Manejo estable',
    'amortiguador': 'Manejo estable',
    'espejo': 'Visibilidad clara',
    'manigueta': 'Control preciso',
    'cable': 'Transmision precisa',
    'rodamiento': 'Rotacion suave',
    'empaque': 'Sellado hermetico',
    'faro': 'Iluminacion potente',
    'direccional': 'Senalizacion visible',
    'bomba': 'Flujo constante',
    'clutch': 'Embrague suave',
    'valvula': 'Control optimo',
    'retenedor': 'Sellado efectivo',
    'palanca': 'Control ergonomico',
    'carburador': 'Mezcla perfecta',
    'rache': 'Arranque confiable',
    'radiador': 'Enfriamiento eficiente',
    'llanta': 'Agarre y traccion',
    'rin': 'Estructura resistente',
    'bateria': 'Energia confiable',
}

def get_benefit(title):
    title_lower = title.lower()
    for keyword, benefit in SRM_BENEFITS.items():
        if keyword in title_lower:
            return benefit
    return 'Repuesto de calidad para tu motocicleta'

def build_body_html(title, sku, compat):
    benefit = get_benefit(title)
    if not compat or compat.strip() == '':
        compat = 'Universal'
    NL = chr(10)
    html = '<div class=product-description>' + NL
    html += '<h3>Descripcion</h3>' + NL
    html += '<p>' + title + '. ' + benefit + '.</p>' + NL + NL
    html += '<h3>Compatibilidad</h3>' + NL
    html += '<p><strong>' + compat + '</strong></p>' + NL + NL
    html += '<h3>Especificaciones</h3>' + NL
    html += '<ul>' + NL
    html += '<li><strong>SKU:</strong> ' + str(sku) + '</li>' + NL
    html += '<li><strong>Marca:</strong> ARMOTOS</li>' + NL
    html += '<li><strong>Condicion:</strong> Nuevo</li>' + NL
    html += '</ul>' + NL + NL
    html += '<h3>Incluye</h3>' + NL
    html += '<ul>' + NL
    html += '<li>1x ' + title + '</li>' + NL
    html += '<li>Empaque original</li>' + NL
    html += '</ul>' + NL + NL
    html += '<h3>Envio</h3>' + NL
    html += '<p>Envio a toda Colombia. Entrega en 2-5 dias habiles.</p>' + NL + NL
    html += '<h3>Garantia</h3>' + NL
    html += '<p>Garantia de 30 dias por defectos de fabrica.</p>' + NL + NL
    html += '<h3>Soporte</h3>' + NL
    html += '<p>Asesoria tecnica por WhatsApp.</p>' + NL
    html += '</div>'
    return html

def get_next_link(link_header):
    if not link_header:
        return None
    parts = link_header.split(',')
    for part in parts:
        if 'rel=next' in part:
            match = re.search(r'<([^>]+)>', part)
            if match:
                return match.group(1)
    return None

def get_all_products():
    products = []
    url = 'https://' + SHOP + '/admin/api/2025-01/products.json?limit=250&status=active'
    headers = {'X-Shopify-Access-Token': TOKEN}
    while url:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print('Error:', resp.status_code)
            break
        data = resp.json()
        batch = data.get('products', [])
        if not batch:
            break
        products.extend(batch)
        print('  Obtenidos:', len(products), 'productos...')
        url = get_next_link(resp.headers.get('Link'))
        time.sleep(0.5)
    return products

def update_product(session, product_id, body_html):
    url = 'https://' + SHOP + '/admin/api/2025-01/products/' + str(product_id) + '.json'
    headers = {'X-Shopify-Access-Token': TOKEN, 'Content-Type': 'application/json'}
    data = {'product': {'id': product_id, 'body_html': body_html}}
    for attempt in range(3):
        try:
            resp = session.put(url, json=data, headers=headers, timeout=30)
            if resp.status_code == 200:
                return True
            elif resp.status_code == 429:
                time.sleep(2)
            else:
                return False
        except:
            time.sleep(1)
    return False

def main():
    print('V12.3 - Actualizacion body_html COMPLETA')
    print('=' * 60)
    print('Shop:', SHOP)
    
    vision_data = json.load(open('/opt/odi/data/ARMOTOS/vision_compat_results.json'))
    compat_map = {}
    for page_data in vision_data:
        for p in page_data.get('products', []):
            sku = p.get('sku', '').strip()
            compat = p.get('compat', 'Universal')
            if sku:
                compat_map[sku] = compat
    print('Compatibilidades Vision AI:', len(compat_map))
    
    print('Obteniendo productos de Shopify...')
    shopify_products = get_all_products()
    print('Productos Shopify:', len(shopify_products))
    
    session = requests.Session()
    ok = 0
    err = 0
    start = time.time()
    total = len(shopify_products)
    
    for i, p in enumerate(shopify_products):
        product_id = p['id']
        title = p['title']
        sku = ''
        variants = p.get('variants', [])
        if variants:
            sku = variants[0].get('sku', '')
        compat = compat_map.get(sku, 'Universal')
        body_html = build_body_html(title, sku, compat)
        if update_product(session, product_id, body_html):
            ok += 1
        else:
            err += 1
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start
            print('  Progreso:', i+1, '/', total, '(', ok, 'ok,', err, 'err) -', int(elapsed), 's')
        time.sleep(0.5)
    
    elapsed = time.time() - start
    print('=' * 60)
    print('RESULTADO:', ok, 'actualizados,', err, 'errores de', total)
    print('Tiempo:', int(elapsed), 'segundos')
    with_real = sum(1 for p in shopify_products if p.get('variants', [{}])[0].get('sku', '') in compat_map)
    print('Con compatibilidad Vision AI:', with_real)
    print('Con Universal:', total - with_real)

if __name__ == '__main__':
    main()
