#!/usr/bin/env python3
"""
Image Matcher v4.0 - Fuzzy matching by title/description
Solves: DFG images named 'aceite-20w-50-4t.jpg' vs SKU '14007'
"""

import os
import re
import json
from pathlib import Path
from difflib import SequenceMatcher

def normalize_for_match(text):
    """Normaliza texto para matching: lowercase, sin acentos, solo alfanum"""
    if not text:
        return ''
    text = str(text).lower()
    # Remover acentos
    replacements = {'á':'a','é':'e','í':'i','ó':'o','ú':'u','ñ':'n','ü':'u'}
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Solo alfanuméricos y espacios
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    # Normalizar espacios
    text = ' '.join(text.split())
    return text

def extract_keywords(text):
    """Extrae keywords significativas (3+ chars)"""
    normalized = normalize_for_match(text)
    words = normalized.split()
    # Filtrar palabras muy cortas y stopwords
    stopwords = {'para', 'con', 'sin', 'los', 'las', 'del', 'por', 'que', 'una', 'uno'}
    return [w for w in words if len(w) >= 3 and w not in stopwords]

def similarity_score(text1, text2):
    """Calcula similitud entre dos textos"""
    norm1 = normalize_for_match(text1)
    norm2 = normalize_for_match(text2)
    
    if not norm1 or not norm2:
        return 0
    
    # Score por SequenceMatcher
    seq_score = SequenceMatcher(None, norm1, norm2).ratio()
    
    # Score por keywords compartidos
    kw1 = set(extract_keywords(text1))
    kw2 = set(extract_keywords(text2))
    if kw1 and kw2:
        common = kw1 & kw2
        kw_score = len(common) / max(len(kw1), len(kw2))
    else:
        kw_score = 0
    
    # Combinar scores
    return (seq_score * 0.4) + (kw_score * 0.6)

def match_image_to_product(product_title, image_bank, threshold=0.3):
    """
    Busca la mejor imagen para un producto usando fuzzy matching
    Returns: (image_path, score) or (None, 0)
    """
    best_match = None
    best_score = 0
    
    for img_name, img_path in image_bank.items():
        # Extraer nombre base de imagen (sin extensión)
        base_name = os.path.splitext(img_name)[0]
        # Convertir guiones a espacios para matching
        img_text = base_name.replace('-', ' ').replace('_', ' ')
        
        score = similarity_score(product_title, img_text)
        
        if score > best_score:
            best_score = score
            best_match = img_path
    
    if best_score >= threshold:
        return best_match, best_score
    return None, 0

def load_image_bank(store_path):
    """Carga banco de imágenes de una tienda"""
    images = {}
    img_dir = os.path.join(store_path, 'imagenes')
    
    if not os.path.exists(img_dir):
        return images
    
    for root, dirs, files in os.walk(img_dir):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                full_path = os.path.join(root, f)
                # Key: nombre en mayúsculas sin extensión
                key = os.path.splitext(f)[0].upper()
                images[key] = full_path
    
    return images

# Test
if __name__ == '__main__':
    # Test con DFG
    store = '/mnt/volume_sfo3_01/profesion/ecosistema_odi/DFG'
    images = load_image_bank(store)
    
    test_products = [
        'ACEITE 20W-50 4T MOTO SL 1L',
        'RODAMIENTO 6005 2RS',
        'LLANTA 90/90-18 TUBELESS',
        'FILTRO DE ACEITE HONDA CB150',
        'CADENA 428 X 120'
    ]
    
    print('=== TEST FUZZY MATCHER DFG ===')
    print(f'Banco: {len(images)} imagenes')
    print()
    
    for title in test_products:
        img, score = match_image_to_product(title, images)
        if img:
            print(f'[{score:.2f}] {title}')
            print(f'        -> {os.path.basename(img)}')
        else:
            print(f'[NONE] {title}')
        print()
