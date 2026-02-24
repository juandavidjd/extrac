#!/usr/bin/env python3
"""
KB Catalog Extractor v1.0
Extrae chunks de conocimiento de catálogos PDF usando Gemini Vision.
Indexa directamente en ChromaDB.
"""
import os
import json
import re
import time
import base64
import io
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')

import google.generativeai as genai
from pdf2image import convert_from_path
from PIL import Image
import chromadb

# Config
CATALOG_DIR = Path("/mnt/volume_sfo3_01/kb/IND_MOTOS/Catalogos")
OUTPUT_DIR = Path("/opt/odi/data/kb_chunks/catalogs")
CHECKPOINT_FILE = OUTPUT_DIR / "checkpoint.json"
DPI = 150
BATCH_SIZE = 5  # PDFs por batch antes de indexar

# ChromaDB
CHROMA_HOST = 'localhost'
CHROMA_PORT = 8000
COLLECTION = 'odi_ind_motos'

# Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

def extract_model_from_filename(filename):
    """Extrae el modelo de moto del nombre del archivo."""
    name = filename.replace(".pdf", "").replace("-", " ").replace("_", " ")
    # Quitar prefijos comunes
    for prefix in ["CATALOGO", "PLANTILLA", "ACTUALIZADO", "DE PARTES", "FORMATO MOBILITY", "PDF"]:
        name = re.sub(rf'\b{prefix}\b', '', name, flags=re.IGNORECASE)
    # Limpiar fechas y versiones
    name = re.sub(r'\d{1,2}\s*\d{1,2}\s*\d{2,4}', '', name)
    name = re.sub(r'MY\d{2,4}', '', name)
    name = re.sub(r'V\d+', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:50] if name else "MOTO"

def image_to_base64(img, max_size=1024):
    """Convierte imagen PIL a base64."""
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode()

def extract_page_content(img, model_name, page_num):
    """Extrae contenido de una página usando Gemini Vision."""
    prompt = f"""Analiza esta página del catálogo de partes para {model_name}.

Extrae en JSON:
{{"sistema": "motor|transmision|frenos|suspension|electrico|carroceria|escape|direccion|ruedas|general",
"piezas": [{{"num": "ABC-123", "nombre": "Nombre pieza"}}],
"diagrama": "Descripción breve del diagrama si existe"}}

REGLAS:
- Extrae TODOS los números de parte visibles
- Si no hay piezas, devuelve lista vacía
- Solo JSON, sin explicaciones"""

    try:
        img_b64 = image_to_base64(img)
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": img_b64}
        ])
        
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        return json.loads(text)
    except Exception as e:
        return {"sistema": "general", "piezas": [], "diagrama": None}

def create_kb_chunk(model_name, page_num, content, filename):
    """Crea un chunk KB."""
    piezas_text = ", ".join([
        f"{p.get('num','')}: {p.get('nombre','')}" for p in content.get("piezas", [])
    ][:20]) or "Ver catálogo"
    
    text = f"Catálogo {model_name}. Sistema: {content.get('sistema', 'general')}. Piezas: {piezas_text}."
    if content.get("diagrama"):
        text += f" Diagrama: {content['diagrama']}."
    
    chunk_id = f"kb_cat_{re.sub(r'[^a-zA-Z0-9]', '_', model_name)[:30]}_{page_num:03d}"
    
    return {
        "id": chunk_id,
        "text": text,
        "metadata": {
            "type": "kb_catalog",
            "source": "catalog_pdf",
            "model": model_name,
            "system": content.get("sistema", "general"),
            "page": page_num,
            "filename": filename,
            "parts_count": len(content.get("piezas", []))
        }
    }

def index_to_chromadb(chunks):
    """Indexa chunks en ChromaDB."""
    if not chunks:
        return 0
    
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    col = client.get_or_create_collection(COLLECTION)
    
    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    
    col.upsert(ids=ids, documents=texts, metadatas=metadatas)
    return len(chunks)

def load_checkpoint():
    """Carga checkpoint."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"processed": [], "total_chunks": 0}

def save_checkpoint(data):
    """Guarda checkpoint."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f)

def process_catalog(pdf_path, checkpoint):
    """Procesa un catálogo PDF."""
    filename = pdf_path.name
    if filename in checkpoint["processed"]:
        return []
    
    model_name = extract_model_from_filename(filename)
    print(f"  Modelo: {model_name}")
    
    chunks = []
    try:
        pages = convert_from_path(str(pdf_path), dpi=DPI, first_page=1, last_page=80)
        print(f"  Páginas: {len(pages)}")
        
        for i, page_img in enumerate(pages):
            page_num = i + 1
            content = extract_page_content(page_img, model_name, page_num)
            
            if content.get("piezas") or content.get("diagrama"):
                chunk = create_kb_chunk(model_name, page_num, content, filename)
                chunks.append(chunk)
                print(f"    Pág {page_num}: {len(content.get('piezas', []))} piezas")
            
            time.sleep(0.3)  # Rate limit
            del page_img
        
    except Exception as e:
        print(f"  ERROR: {e}")
    
    return chunks

def main():
    print("="*60)
    print("KB CATALOG EXTRACTOR v1.0")
    print("="*60)
    
    checkpoint = load_checkpoint()
    print(f"Checkpoint: {len(checkpoint['processed'])} procesados, {checkpoint['total_chunks']} chunks")
    
    catalogs = sorted(CATALOG_DIR.glob("*.pdf"))
    pending = [c for c in catalogs if c.name not in checkpoint["processed"]]
    print(f"Total: {len(catalogs)} | Pendientes: {len(pending)}")
    
    batch_chunks = []
    
    for i, pdf_path in enumerate(pending):
        print(f"\n[{i+1}/{len(pending)}] {pdf_path.name}")
        
        chunks = process_catalog(pdf_path, checkpoint)
        
        if chunks:
            batch_chunks.extend(chunks)
            checkpoint["processed"].append(pdf_path.name)
            print(f"  -> {len(chunks)} chunks")
        
        # Indexar cada BATCH_SIZE PDFs
        if (i + 1) % BATCH_SIZE == 0 and batch_chunks:
            indexed = index_to_chromadb(batch_chunks)
            checkpoint["total_chunks"] += indexed
            save_checkpoint(checkpoint)
            print(f"\n*** BATCH INDEXADO: {indexed} chunks (total: {checkpoint['total_chunks']}) ***\n")
            batch_chunks = []
            time.sleep(2)  # Pausa entre batches
    
    # Indexar chunks restantes
    if batch_chunks:
        indexed = index_to_chromadb(batch_chunks)
        checkpoint["total_chunks"] += indexed
        save_checkpoint(checkpoint)
        print(f"\n*** FINAL INDEXADO: {indexed} chunks ***")
    
    print(f"\n{'='*60}")
    print(f"COMPLETADO: {len(checkpoint['processed'])} catálogos, {checkpoint['total_chunks']} chunks")

if __name__ == "__main__":
    main()
