#!/usr/bin/env python3
"""
Extractor de imagenes anti-basura para ARMOTOS
Filtros estrictos para descartar logos, banners, etc.
"""
import fitz
import os
from pathlib import Path
from PIL import Image
import io
import hashlib

PDF_PATH = "/opt/odi/data/ARMOTOS/catalogo/CATALOGO NOVIEMBRE V01-2025 NF.pdf"
OUTPUT_DIR = Path("/opt/odi/data/ARMOTOS/images")
OUTPUT_DIR.mkdir(exist_ok=True)

# Filtros anti-basura (dimensiones a descartar)
GARBAGE_SIZES = [
    (426, 209),   # Logo ARMOTOS
    (1024, 1024), # Simbolo R rojo
    (487, 61),    # Banners tabla
    (2639, 666),  # Headers/footers
]
GARBAGE_TOLERANCE = 5  # +/- pixels

MIN_SIZE = 100  # Minimo 100x100
MIN_BYTES = 10 * 1024  # Minimo 10KB
MAX_ASPECT = 4.0  # Maximo aspect ratio 4:1
COLOR_THRESHOLD = 0.80  # Maximo 80% un solo color

def is_garbage_size(w, h):
    for gw, gh in GARBAGE_SIZES:
        if abs(w - gw) <= GARBAGE_TOLERANCE and abs(h - gh) <= GARBAGE_TOLERANCE:
            return True
    return False

def is_solid_color(img_data):
    try:
        img = Image.open(io.BytesIO(img_data))
        if img.mode != "RGB":
            img = img.convert("RGB")
        colors = img.getcolors(maxcolors=1000)
        if colors:
            total = img.width * img.height
            dominant = max(c[0] for c in colors)
            if dominant / total > COLOR_THRESHOLD:
                return True
    except:
        pass
    return False

def extract_images():
    doc = fitz.open(PDF_PATH)
    print(f"PDF: {doc.page_count} paginas", flush=True)
    
    extracted = 0
    discarded = {"size": 0, "small": 0, "aspect": 0, "bytes": 0, "color": 0, "dup": 0}
    seen_hashes = set()
    
    for page_num in range(doc.page_count):
        page = doc[page_num]
        images = page.get_images()
        
        for img_idx, img in enumerate(images):
            xref = img[0]
            try:
                base = doc.extract_image(xref)
                img_data = base["image"]
                w, h = base["width"], base["height"]
                
                # Filtro 1: Tamanio basura conocido
                if is_garbage_size(w, h):
                    discarded["size"] += 1
                    continue
                
                # Filtro 2: Muy pequeno
                if w < MIN_SIZE or h < MIN_SIZE:
                    discarded["small"] += 1
                    continue
                
                # Filtro 3: Aspect ratio extremo
                aspect = max(w/h, h/w)
                if aspect > MAX_ASPECT:
                    discarded["aspect"] += 1
                    continue
                
                # Filtro 4: Muy pocos bytes
                if len(img_data) < MIN_BYTES:
                    discarded["bytes"] += 1
                    continue
                
                # Filtro 5: Color solido
                if is_solid_color(img_data):
                    discarded["color"] += 1
                    continue
                
                # Filtro 6: Duplicado
                img_hash = hashlib.md5(img_data).hexdigest()[:12]
                if img_hash in seen_hashes:
                    discarded["dup"] += 1
                    continue
                seen_hashes.add(img_hash)
                
                # Guardar imagen
                ext = base.get("ext", "png")
                filename = f"page_{page_num+1:03d}_img_{img_idx:02d}_{img_hash}.{ext}"
                filepath = OUTPUT_DIR / filename
                with open(filepath, "wb") as f:
                    f.write(img_data)
                extracted += 1
                
            except Exception as e:
                continue
        
        if (page_num + 1) % 20 == 0:
            print(f"  [{page_num+1}/{doc.page_count}] {extracted} imgs", flush=True)
    
    doc.close()
    
    print(f"\n=== RESULTADO ===", flush=True)
    print(f"Extraidas: {extracted}", flush=True)
    print(f"Descartadas:", flush=True)
    print(f"  - Tamano basura: {discarded[size]}", flush=True)
    print(f"  - Muy pequenas: {discarded[small]}", flush=True)
    print(f"  - Aspect ratio: {discarded[aspect]}", flush=True)
    print(f"  - Pocos bytes: {discarded[bytes]}", flush=True)
    print(f"  - Color solido: {discarded[color]}", flush=True)
    print(f"  - Duplicadas: {discarded[dup]}", flush=True)
    return extracted

if __name__ == "__main__":
    extract_images()
