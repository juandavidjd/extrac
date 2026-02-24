#!/usr/bin/env python3
"""Filtra basura de imágenes extraídas de PDF"""
import os
import sys
import hashlib
from PIL import Image
from collections import defaultdict

def get_image_hash(path):
    """Hash MD5 del contenido"""
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def is_solid_color(img, threshold=0.95):
    """Detecta si >95% de pixels son del mismo color"""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    pixels = list(img.getdata())
    total = len(pixels)
    if total == 0:
        return True
    color_counts = defaultdict(int)
    for p in pixels:
        color_counts[p] += 1
    max_count = max(color_counts.values())
    return (max_count / total) > threshold

def filter_images(folder):
    """Filtra imágenes basura y retorna stats"""
    stats = {
        'total': 0,
        'tiny_size': 0,      # <5KB
        'tiny_dims': 0,      # <100x100
        'banner': 0,         # aspect >5:1
        'solid_color': 0,    # >95% un color
        'duplicate': 0,      # hash duplicado
        'valid': 0,
        'valid_files': []
    }
    
    hashes_seen = set()
    trash_dir = os.path.join(folder, '_trash')
    os.makedirs(trash_dir, exist_ok=True)
    
    files = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    stats['total'] = len(files)
    
    for fname in files:
        fpath = os.path.join(folder, fname)
        reason = None
        
        # 1. Check file size
        fsize = os.path.getsize(fpath)
        if fsize < 5000:  # <5KB
            reason = 'tiny_size'
        
        if not reason:
            try:
                img = Image.open(fpath)
                w, h = img.size
                
                # 2. Check dimensions
                if w < 100 or h < 100:
                    reason = 'tiny_dims'
                
                # 3. Check aspect ratio (banner)
                elif max(w,h) / max(min(w,h), 1) > 5:
                    reason = 'banner'
                
                # 4. Check solid color (sample for speed)
                elif w * h < 50000:  # Solo para imágenes pequeñas
                    if is_solid_color(img):
                        reason = 'solid_color'
                
                # 5. Check duplicate hash
                if not reason:
                    fhash = get_image_hash(fpath)
                    if fhash in hashes_seen:
                        reason = 'duplicate'
                    else:
                        hashes_seen.add(fhash)
                        
            except Exception as e:
                reason = 'tiny_size'  # corrupta
        
        if reason:
            stats[reason] += 1
            # Mover a trash
            os.rename(fpath, os.path.join(trash_dir, fname))
        else:
            stats['valid'] += 1
            stats['valid_files'].append(fname)
    
    return stats

if __name__ == '__main__':
    folder = sys.argv[1]
    print(f'Filtrando: {folder}')
    stats = filter_images(folder)
    print(f'Total: {stats["total"]}')
    print(f'  - Tiny size (<5KB): {stats["tiny_size"]}')
    print(f'  - Tiny dims (<100px): {stats["tiny_dims"]}')
    print(f'  - Banners (>5:1): {stats["banner"]}')
    print(f'  - Solid color: {stats["solid_color"]}')
    print(f'  - Duplicates: {stats["duplicate"]}')
    print(f'VÁLIDAS: {stats["valid"]}')
