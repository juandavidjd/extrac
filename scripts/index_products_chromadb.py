#!/usr/bin/env python3
"""Index all products from orden_maestra_v6 to ChromaDB (with dedup)."""
import json
import chromadb
from pathlib import Path

# Connect to ChromaDB
client = chromadb.HttpClient(host='localhost', port=8000)
collection = client.get_or_create_collection('odi_ind_motos')

# Path to product JSONs
JSON_PATH = Path('/opt/odi/data/orden_maestra_v6')

# Get all JSON files
json_files = list(JSON_PATH.glob('*_products.json'))
print(f'Found {len(json_files)} JSON files')

total_indexed = 0
total_skipped = 0

for json_file in sorted(json_files):
    empresa = json_file.stem.replace('_products', '').upper()
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        print(f'\n{empresa}: {len(products)} products')
        
        # Prepare batch data with deduplication
        seen_ids = set()
        ids = []
        documents = []
        metadatas = []
        
        for idx, p in enumerate(products):
            sku = str(p.get('sku', '')) or f'IDX-{idx}'
            base_id = f'{empresa}_{sku}'
            
            # Handle duplicates by adding index suffix
            unique_id = base_id
            counter = 1
            while unique_id in seen_ids:
                unique_id = f'{base_id}_{counter}'
                counter += 1
            seen_ids.add(unique_id)
            
            title = p.get('title', '') or ''
            description = p.get('body_html', '') or p.get('description', '') or ''
            price = p.get('price', 0)
            vendor = p.get('vendor', empresa)
            tags = p.get('tags', '')
            
            # Create document text for search
            doc_text = f"{title}. {description[:500]}. SKU: {sku}. Marca: {vendor}"
            
            ids.append(unique_id)
            documents.append(doc_text)
            metadatas.append({
                'sku': sku,
                'title': title[:200],
                'empresa': empresa,
                'vendor': vendor,
                'price': float(price) if price else 0,
                'type': 'product',
                'tags': str(tags)[:200] if tags else ''
            })
        
        # Upsert in batches of 500
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            
            collection.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_meta
            )
        
        total_indexed += len(ids)
        print(f'  ✓ {empresa}: {len(ids)} indexed')
        
    except Exception as e:
        print(f'  ✗ {empresa}: Error - {e}')

print(f'\n{"="*50}')
print(f'TOTAL INDEXED: {total_indexed}')
print(f'Collection count: {collection.count()}')
