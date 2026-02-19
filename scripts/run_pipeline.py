#!/usr/bin/env python3
"""Run pipeline for a store."""
import asyncio
import sys
import json

sys.path.insert(0, '/opt/odi')
from core.odi_pipeline_service import PipelineExecutor, PipelineRequest

async def main():
    store = sys.argv[1] if len(sys.argv) > 1 else 'DFG'
    source_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Load brand config
    with open(f'/opt/odi/data/brands/{store.lower()}.json') as f:
        brand = json.load(f)
    
    # Determine source file
    if not source_file:
        # Try JSON first, then CSV
        json_path = f'/opt/odi/data/orden_maestra_v6/{store.upper()}_products.json'
        csv_path = brand.get('data_sources', {}).get('base_csv', '')
        
        import os
        if os.path.exists(json_path):
            source_file = json_path
        elif os.path.exists(csv_path):
            source_file = csv_path
        else:
            print(f'No source file found for {store}')
            return
    
    print(f'Running pipeline for {store}')
    print(f'  Source: {source_file}')
    print(f'  Shop: {brand["shopify"]["shop"]}')
    
    executor = PipelineExecutor()
    
    request = PipelineRequest(
        job_id=f'{store.lower()}_v15_{int(asyncio.get_event_loop().time())}',
        empresa=store.upper(),
        shop_key=store.upper(),
        source_file=source_file,
        images_folder=brand.get('data_sources', {}).get('images_dir', '')
    )
    
    job = await executor.execute(request)
    
    print(f'Pipeline complete!')
    print(f'  Stage: {job.stage}')
    print(f'  Products: {len(job.products)}')
    print(f'  Errors: {len(job.errors)}')
    if job.errors:
        for e in job.errors[:5]:
            print(f'    - {e}')

if __name__ == '__main__':
    asyncio.run(main())
