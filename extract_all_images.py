#!/usr/bin/env python3
"""
ARMOTOS - Extracción completa de imágenes
Procesa TODAS las 256 páginas en batches pequeños
"""
import sys
sys.path.insert(0, "/opt/odi/odi_production/extractors")

import os
import json
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[
        logging.FileHandler("/opt/odi/logs/extract_images.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("extract")

PDF = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Armotos/CATALOGO NOVIEMBRE V01-2025 NF.pdf"
OUT = "/opt/odi/data/ARMOTOS/images"
PROGRESS_FILE = "/opt/odi/data/ARMOTOS/extraction_progress.json"

os.makedirs(OUT, exist_ok=True)

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"last_page": 1, "total_images": 0, "pages_done": []}

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f)

def main():
    import warnings
    warnings.filterwarnings("ignore")
    
    from odi_vision_extractor_v3 import VisionProductDetector
    from pdf2image import convert_from_path
    
    log.info("=" * 50)
    log.info("EXTRACCIÓN COMPLETA DE IMÁGENES - ARMOTOS")
    log.info("=" * 50)
    
    progress = load_progress()
    start_page = progress["last_page"] + 1
    
    log.info(f"Continuando desde página {start_page}")
    log.info(f"Imágenes previas: {progress[total_images]}")
    
    detector = VisionProductDetector(use_gemini=True)
    
    # Procesar de 5 en 5 páginas
    BATCH_SIZE = 5
    TOTAL_PAGES = 256
    
    for batch_start in range(start_page, TOTAL_PAGES + 1, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE - 1, TOTAL_PAGES)
        
        log.info(f"Batch: páginas {batch_start}-{batch_end}")
        
        try:
            # Convertir páginas a imágenes
            pages = convert_from_path(
                PDF, 
                dpi=200,
                first_page=batch_start,
                last_page=batch_end
            )
            
            batch_images = 0
            
            for i, page_img in enumerate(pages):
                page_num = batch_start + i
                
                if page_num in progress["pages_done"]:
                    continue
                
                page_path = f"{OUT}/page_{page_num:03d}.png"
                page_img.save(page_path)
                
                try:
                    # Detectar productos con Vision AI
                    products = detector.detect(page_path)
                    
                    if products:
                        # Recortar productos
                        crops = detector.crop_products(
                            page_path, products, OUT, "ARMOTOS", page_num
                        )
                        batch_images += len(crops)
                        progress["total_images"] += len(crops)
                        log.info(f"  Pág {page_num}: {len(crops)} productos")
                    else:
                        log.info(f"  Pág {page_num}: 0 productos")
                    
                    progress["pages_done"].append(page_num)
                    progress["last_page"] = page_num
                    
                except Exception as e:
                    log.error(f"  Pág {page_num} error detección: {e}")
                
                # Limpiar página temporal
                if os.path.exists(page_path):
                    os.remove(page_path)
                
                # Pequeña pausa para evitar rate limit
                time.sleep(0.5)
            
            # Guardar progreso después de cada batch
            save_progress(progress)
            log.info(f"  Batch completado: {batch_images} imágenes (total: {progress[total_images]})")
            
            # Pausa entre batches
            time.sleep(2)
            
        except Exception as e:
            log.error(f"Error en batch {batch_start}-{batch_end}: {e}")
            save_progress(progress)
            time.sleep(5)
            continue
    
    log.info("=" * 50)
    log.info(f"EXTRACCIÓN COMPLETADA")
    log.info(f"Total imágenes: {progress[total_images]}")
    log.info(f"Páginas procesadas: {len(progress[pages_done])}")
    log.info("=" * 50)
    
    # Guardar índice final
    all_images = []
    for f in os.listdir(OUT):
        if f.startswith("ARMOTOS_") and f.endswith(".png"):
            all_images.append(f)
    
    with open("/opt/odi/data/ARMOTOS/images_index.json", "w") as f:
        json.dump({"images": sorted(all_images), "count": len(all_images)}, f, indent=2)
    
    log.info(f"Índice guardado: {len(all_images)} imágenes")

if __name__ == "__main__":
    main()
