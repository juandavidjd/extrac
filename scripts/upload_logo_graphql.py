#!/usr/bin/env python3
"""Upload logos to Shopify via GraphQL"""
import requests, json, os, time

LOGOS = '/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/logos_optimized'
BRANDS = '/opt/odi/data/brands'

LOGO_MAP = {
    'japan': 'Japan.png',
    'kaiqi': 'Kaiqi.png',
    'yokomar': 'Yokomar.png',
    'bara': 'Bara.png',
    'cbi': 'cbi.png',
    'leo': 'Leo.png',
    'mclmotos': 'mcll.png',
    'duna': 'Duna.png',
    'vitton': 'Vitton.png'
}

def upload_logo(store):
    logo_file = LOGO_MAP.get(store.lower())
    logo_path = f'{LOGOS}/{logo_file}'

    with open(f'{BRANDS}/{store.lower()}.json') as f:
        c = json.load(f)
    s = c.get('shopify', {})
    shop = s.get('shop_name', s.get('shop', ''))
    tok = s.get('access_token', s.get('token', ''))
    if not shop.endswith('.myshopify.com'):
        shop = f'{shop}.myshopify.com'

    hdrs = {'X-Shopify-Access-Token': tok, 'Content-Type': 'application/json'}
    graphql_url = f'https://{shop}/admin/api/2024-01/graphql.json'

    file_size = os.path.getsize(logo_path)

    # Create staged upload
    mutation = '''
    mutation {
        stagedUploadsCreate(input: [{
            filename: "logo.png",
            mimeType: "image/png",
            resource: FILE,
            fileSize: "%s",
            httpMethod: POST
        }]) {
            stagedTargets {
                url
                resourceUrl
                parameters {
                    name
                    value
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    ''' % file_size

    r = requests.post(graphql_url, headers=hdrs, json={'query': mutation})

    if r.status_code != 200:
        print(f'{store.upper()}: GraphQL error {r.status_code}')
        return False

    data = r.json()

    if 'errors' in data:
        print(f'{store.upper()}: {data["errors"]}')
        return False

    targets = data.get('data', {}).get('stagedUploadsCreate', {}).get('stagedTargets', [])
    user_errors = data.get('data', {}).get('stagedUploadsCreate', {}).get('userErrors', [])

    if user_errors:
        print(f'{store.upper()}: {user_errors}')
        return False

    if not targets:
        print(f'{store.upper()}: No staged targets')
        return False

    target = targets[0]
    upload_url = target['url']
    resource_url = target['resourceUrl']
    params = {p['name']: p['value'] for p in target['parameters']}

    # Upload file
    with open(logo_path, 'rb') as f:
        logo_data = f.read()

    files = {'file': ('logo.png', logo_data, 'image/png')}
    upload_r = requests.post(upload_url, data=params, files=files)

    if upload_r.status_code not in [200, 201, 204]:
        print(f'{store.upper()}: Upload failed {upload_r.status_code}')
        return False

    # Create file in Shopify
    create_mutation = '''
    mutation {
        fileCreate(files: [{
            originalSource: "%s",
            alt: "%s Logo",
            contentType: IMAGE
        }]) {
            files {
                id
                alt
                ... on MediaImage {
                    image {
                        url
                    }
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    ''' % (resource_url, store.upper())

    r2 = requests.post(graphql_url, headers=hdrs, json={'query': create_mutation})

    if r2.status_code != 200:
        print(f'{store.upper()}: File create error {r2.status_code}')
        return False

    result = r2.json()

    if 'errors' in result:
        print(f'{store.upper()}: {result["errors"]}')
        return False

    files_created = result.get('data', {}).get('fileCreate', {}).get('files', [])
    errors = result.get('data', {}).get('fileCreate', {}).get('userErrors', [])

    if errors:
        print(f'{store.upper()}: {errors}')
        return False

    if files_created:
        file_id = files_created[0]['id']
        print(f'{store.upper()}: Logo created with ID {file_id}')
        return True

    print(f'{store.upper()}: Unknown error')
    return False

if __name__ == '__main__':
    stores = ['japan', 'kaiqi', 'yokomar', 'bara', 'cbi', 'leo', 'mclmotos', 'duna', 'vitton']

    success = 0
    for store in stores:
        if upload_logo(store):
            success += 1
        time.sleep(1)

    print(f'\nDone: {success}/{len(stores)}')
