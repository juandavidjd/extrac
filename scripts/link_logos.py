#!/usr/bin/env python3
"""Link uploaded logos to theme settings"""
import requests, json, time

BRANDS = '/opt/odi/data/brands'

# MediaImage GIDs from previous upload
LOGO_GIDS = {
    'japan': 'gid://shopify/MediaImage/31697045913700',
    'kaiqi': 'gid://shopify/MediaImage/70560886358097',
    'yokomar': 'gid://shopify/MediaImage/34841282281655',
    'bara': 'gid://shopify/MediaImage/31697045946468',
    'cbi': 'gid://shopify/MediaImage/40906293248259',
    'leo': 'gid://shopify/MediaImage/59633499766968',
    'mclmotos': 'gid://shopify/MediaImage/26594032844905',
    'duna': 'gid://shopify/MediaImage/41561422430426',
    'vitton': 'gid://shopify/MediaImage/27097063391293'
}

def get_image_url(store, hdrs, graphql_url):
    """Get the actual image URL from the MediaImage GID"""
    gid = LOGO_GIDS.get(store.lower())

    query = '''
    query {
        node(id: "%s") {
            ... on MediaImage {
                image {
                    url
                }
            }
        }
    }
    ''' % gid

    r = requests.post(graphql_url, headers=hdrs, json={'query': query})
    if r.status_code == 200:
        data = r.json()
        return data.get('data', {}).get('node', {}).get('image', {}).get('url')
    return None

def link_logo(store):
    with open(f'{BRANDS}/{store.lower()}.json') as f:
        c = json.load(f)
    s = c.get('shopify', {})
    shop = s.get('shop_name', s.get('shop', ''))
    tok = s.get('access_token', s.get('token', ''))
    if not shop.endswith('.myshopify.com'):
        shop = f'{shop}.myshopify.com'

    hdrs = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    base = f'https://{shop}/admin/api/2024-01'
    graphql_url = f'{base}/graphql.json'

    # Get main theme
    r = requests.get(f'{base}/themes.json', headers=hdrs)
    themes = r.json().get('themes', [])
    main = [t for t in themes if t.get('role') == 'main']
    if not main:
        print(f'{store.upper()}: No main theme')
        return False

    theme_id = main[0]['id']

    # Get image URL
    image_url = get_image_url(store, hdrs, graphql_url)
    if not image_url:
        print(f'{store.upper()}: Could not get image URL')
        return False

    print(f'{store.upper()}: Image URL = {image_url[:60]}...')

    # Get current settings
    r2 = requests.get(f'{base}/themes/{theme_id}/assets.json', headers=hdrs,
        params={'asset[key]': 'config/settings_data.json'})

    if r2.status_code != 200:
        print(f'{store.upper()}: Could not get settings')
        return False

    settings = json.loads(r2.json()['asset']['value'])
    current = settings.get('current', {})

    # Try to set logo using shopify:// URL format
    gid = LOGO_GIDS.get(store.lower())
    # Extract numeric ID from GID
    numeric_id = gid.split('/')[-1]
    shopify_url = f'shopify://shop_images/{numeric_id}'

    # Update logo settings
    current['logo'] = shopify_url
    current['logo_inverse'] = shopify_url

    settings['current'] = current

    # Save settings
    payload = {
        'asset': {
            'key': 'config/settings_data.json',
            'value': json.dumps(settings)
        }
    }

    r3 = requests.put(f'{base}/themes/{theme_id}/assets.json', headers=hdrs, json=payload)

    if r3.status_code in [200, 201]:
        print(f'{store.upper()}: Settings updated!')
        return True
    else:
        # Try with direct CDN URL
        current['logo'] = image_url
        current['logo_inverse'] = image_url
        settings['current'] = current
        payload['asset']['value'] = json.dumps(settings)

        r4 = requests.put(f'{base}/themes/{theme_id}/assets.json', headers=hdrs, json=payload)
        if r4.status_code in [200, 201]:
            print(f'{store.upper()}: Settings updated with CDN URL!')
            return True
        else:
            print(f'{store.upper()}: Settings failed {r4.status_code}')
            return False

if __name__ == '__main__':
    stores = ['japan', 'kaiqi', 'yokomar', 'bara', 'cbi', 'leo', 'mclmotos', 'duna', 'vitton']

    success = 0
    for store in stores:
        if link_logo(store):
            success += 1
        time.sleep(1)

    print(f'\nDone: {success}/{len(stores)}')
