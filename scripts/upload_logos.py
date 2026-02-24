#!/usr/bin/env python3
"""Upload logos to Shopify themes"""
import os, json, requests, base64, time

LOGOS = '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/logos_optimized'
BRANDS = '/opt/odi/data/brands'

# Map store to logo file
LOGO_MAP = {
    'japan': 'Japan.png',
    'kaiqi': 'Kaiqi.png',
    'yokomar': 'Yokomar.png',
    'bara': 'Bara.png',
    'cbi': 'cbi.png',
    'leo': 'Leo.png',
    'mclmotos': 'mcll.png',
    'duna': 'Duna.png',
    'vitton': 'Vitton.png',
    'dfg': 'DFG.png',
    'oh_importaciones': 'OH1.png',
    'armotos': 'Armotos.png',
    'imbra': 'Imbra.png',
    'store': 'Store.png',
    'vaisand': 'Vaisand.png'
}

def get_config(store):
    with open(f'{BRANDS}/{store.lower()}.json') as f:
        c = json.load(f)
    s = c.get('shopify', {})
    shop = s.get('shop_name', s.get('shop', ''))
    tok = s.get('access_token', s.get('token', ''))
    if not shop.endswith('.myshopify.com'):
        shop = f'{shop}.myshopify.com'
    return shop, tok

def upload_logo(store):
    logo_file = LOGO_MAP.get(store.lower())
    if not logo_file:
        print(f'{store}: No logo mapped')
        return False
    
    logo_path = f'{LOGOS}/{logo_file}'
    if not os.path.exists(logo_path):
        print(f'{store}: Logo not found {logo_file}')
        return False
    
    try:
        shop, tok = get_config(store)
    except Exception as e:
        print(f'{store}: Config error {e}')
        return False
    
    hdrs = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    base = f'https://{shop}/admin/api/2024-01'
    
    # Get main theme
    r = requests.get(f'{base}/themes.json', headers=hdrs)
    if r.status_code != 200:
        print(f'{store}: Theme API error {r.status_code}')
        return False
    
    themes = r.json().get('themes', [])
    main = [t for t in themes if t.get('role') == 'main']
    if not main:
        print(f'{store}: No main theme')
        return False
    
    theme_id = main[0]['id']
    theme_name = main[0]['name']
    
    # Read and encode logo
    with open(logo_path, 'rb') as f:
        logo_data = base64.b64encode(f.read()).decode()
    
    # Upload logo as theme asset
    asset_key = f'assets/logo.png'
    payload = {
        'asset': {
            'key': asset_key,
            'attachment': logo_data
        }
    }
    
    r = requests.put(f'{base}/themes/{theme_id}/assets.json', headers=hdrs, json=payload)
    time.sleep(0.5)
    
    if r.status_code in [200, 201]:
        print(f'{store.upper()}: Logo uploaded to {theme_name}')
        
        # Now update settings to use logo
        # Get current settings
        r2 = requests.get(f'{base}/themes/{theme_id}/assets.json', headers=hdrs,
            params={'asset[key]': 'config/settings_data.json'})
        
        if r2.status_code == 200:
            settings_content = r2.json().get('asset', {}).get('value', '{}')
            settings = json.loads(settings_content)
            
            # Update logo in current settings
            current = settings.get('current', {})
            
            # Different themes have different logo settings
            # Try to find and update logo settings
            updated = False
            for key in list(current.keys()):
                if 'logo' in key.lower() and 'height' not in key.lower():
                    current[key] = 'logo.png'
                    updated = True
            
            if updated:
                settings['current'] = current
                
                # Save settings
                save_payload = {
                    'asset': {
                        'key': 'config/settings_data.json',
                        'value': json.dumps(settings)
                    }
                }
                r3 = requests.put(f'{base}/themes/{theme_id}/assets.json', headers=hdrs, json=save_payload)
                time.sleep(0.5)
                if r3.status_code in [200, 201]:
                    print(f'  Settings updated')
                else:
                    print(f'  Settings error: {r3.status_code}')
        
        return True
    else:
        print(f'{store}: Upload error {r.status_code} - {r.text[:100]}')
        return False

if __name__ == '__main__':
    stores = ['japan', 'kaiqi', 'yokomar', 'bara', 'cbi', 'leo', 'mclmotos', 'duna', 'vitton']
    
    success = 0
    for store in stores:
        if upload_logo(store):
            success += 1
        time.sleep(1)
    
    print(f'\nDONE: {success}/{len(stores)} logos uploaded')
