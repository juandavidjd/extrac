#!/usr/bin/env python3
"""V18 Image Upload Script"""
import sys
import os
import time
sys.path.insert(0, '/opt/odi')
from core.odi_image_mapper import ImageMapper

def upload_store(store):
    print(f'Starting upload for {store}...')
    start = time.time()
    
    mapper = ImageMapper(store)
    result = mapper.map_images()
    mapper.save_report(result)
    
    print(f'{store}: {result.matched} images to upload')
    
    if result.matched == 0:
        print(f'{store}: No images to upload')
        return
    
    # Real upload (no dry run)
    stats = mapper.upload_matched(result, dry_run=False, delay=0.8)
    
    elapsed = time.time() - start
    print(f'{store} DONE: {stats["success"]}/{stats["attempted"]} uploaded in {elapsed:.1f}s')
    
    if stats['errors']:
        print(f'{store} ERRORS: {len(stats["errors"])}')
        for err in stats['errors'][:5]:
            print(f'  - {err}')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python v18_upload_images.py <STORE>')
        sys.exit(1)
    upload_store(sys.argv[1].upper())
