#!/usr/bin/env python3
"""
KB Technical Indexer v1.1
Extrae texto de catálogos PDF con PyMuPDF e indexa en ChromaDB.
"""
import os
import json
import re
import time
import hashlib
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF
import chromadb

# Config
CATALOG_DIR = Path("/mnt/volume_sfo3_01/kb/IND_MOTOS/Catalogos")
CHECKPOINT_FILE = Path("/opt/odi/data/kb_chunks/catalogs/checkpoint_technical.json")
BATCH_SIZE = 10
CHROMA_HOST = 'localhost'
CHROMA_PORT = 8000
COLLECTION = 'odi_ind_motos'

def extract_model_from_filename(filename):
    """Extrae el modelo de moto del nombre del archivo."""
    name = filename.replace(".pdf", "").replace("-", " ").replace("_", " ")
    for prefix in ["CATALOGO", "PLANTILLA", "ACTUALIZADO", "DE PARTES", "FORMATO MOBILITY"]:
        name = re.sub(rf'\b{prefix}\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\d{1,2}\s*\d{1,2}\s*\d{2,4}', '', name)
    name = re.sub(r'MY\d{2,4}', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:60] if name else "MOTO"

def make_unique_id(filename, page_num):
    """Genera ID único basado en filename + página."""
    # Hash corto del filename para garantizar unicidad
    file_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
    return f"kb_tech_{file_hash}_p{page_num:03d}"

def detect_system(text):
    """Detecta el sistema basado en keywords."""
    text_lower = text.lower()
    systems = {
        "motor": ["cilindro", "piston", "biela", "cigueñal", "valvula", "culata", "carter", "arbol levas"],
        "transmision": ["embrague", "clutch", "cadena", "piñon", "engranaje", "caja cambios"],
        "frenos": ["freno", "disco", "pastilla", "caliper", "bomba freno"],
        "suspension": ["amortiguador", "horquilla", "tijera", "resorte"],
        "electrico": ["cdi", "bobina", "magneto", "bateria", "faro", "switch", "relay"],
        "carroceria": ["plastico", "carenado", "guardafango", "tanque", "asiento"],
        "escape": ["escape", "silenciador", "exosto"],
        "direccion": ["manubrio", "manillar", "direccion"],
    }
    for system, keywords in systems.items():
        for kw in keywords:
            if kw in text_lower:
                return system
    return "general"

def extract_part_numbers(text):
    """Extrae números de parte del texto."""
    patterns = [
        r'\b[A-Z]{1,3}[-]?\d{4,8}\b',
        r'\b\d{5,10}\b',
        r'\b[A-Z]\d{2,3}[-]\d{3,5}\b',
    ]
    parts = set()
    for pattern in patterns:
        matches = re.findall(pattern, text)
        parts.update(matches[:20])
    return list(parts)[:15]

def process_pdf(pdf_path):
    """Procesa un PDF y extrae chunks por página."""
    filename = pdf_path.name
    model_name = extract_model_from_filename(filename)
    chunks = []
    
    try:
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text()
            
            if len(text.strip()) < 50:
                continue
            
            text_clean = re.sub(r'\s+', ' ', text).strip()[:2000]
            system = detect_system(text_clean)
            parts = extract_part_numbers(text)
            
            chunk_text = f"Catálogo técnico {model_name}. Sistema: {system}. "
            if parts:
                chunk_text += f"Números de parte: {', '.join(parts[:10])}. "
            chunk_text += f"Contenido: {text_clean[:500]}"
            
            chunk_id = make_unique_id(filename, page_num + 1)
            
            chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "metadata": {
                    "type": "kb_technical",
                    "source": "catalog_pdf",
                    "model": model_name,
                    "system": system,
                    "page": page_num + 1,
                    "filename": filename,
                    "parts_count": len(parts)
                }
            })
        
        doc.close()
        return chunks, None
        
    except Exception as e:
        return [], str(e)

def index_to_chromadb(chunks):
    """Indexa chunks en ChromaDB."""
    if not chunks:
        return 0
    
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    col = client.get_or_create_collection(COLLECTION)
    
    for i in range(0, len(chunks), 100):
        batch = chunks[i:i+100]
        col.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[c["metadata"] for c in batch]
        )
    
    return len(chunks)

def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"processed": [], "total_chunks": 0, "errors": []}

def save_checkpoint(data):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2)

def main():
    print("="*60)
    print("KB TECHNICAL INDEXER v1.1 (PyMuPDF)")
    print("="*60)
    
    checkpoint = load_checkpoint()
    print(f"Checkpoint: {len(checkpoint['processed'])} procesados, {checkpoint['total_chunks']} chunks")
    
    catalogs = sorted(CATALOG_DIR.glob("*.pdf"))
    pending = [c for c in catalogs if c.name not in checkpoint["processed"]]
    print(f"Total: {len(catalogs)} | Pendientes: {len(pending)}")
    print("")
    
    batch_chunks = []
    batch_count = 0
    
    for i, pdf_path in enumerate(pending):
        print(f"[{i+1}/{len(pending)}] {pdf_path.name[:50]}...", end=" ", flush=True)
        
        chunks, error = process_pdf(pdf_path)
        
        if error:
            print(f"ERROR: {error}")
            checkpoint["errors"].append({"file": pdf_path.name, "error": error})
        elif chunks:
            batch_chunks.extend(chunks)
            print(f"OK ({len(chunks)} chunks)")
        else:
            print("SKIP (sin texto)")
        
        checkpoint["processed"].append(pdf_path.name)
        batch_count += 1
        
        if batch_count >= BATCH_SIZE and batch_chunks:
            indexed = index_to_chromadb(batch_chunks)
            checkpoint["total_chunks"] += indexed
            save_checkpoint(checkpoint)
            print(f"\n*** BATCH: {indexed} chunks indexados (total: {checkpoint['total_chunks']}) ***\n")
            batch_chunks = []
            batch_count = 0
            time.sleep(1)
    
    if batch_chunks:
        indexed = index_to_chromadb(batch_chunks)
        checkpoint["total_chunks"] += indexed
        save_checkpoint(checkpoint)
        print(f"\n*** FINAL: {indexed} chunks indexados ***")
    
    print(f"\n{'='*60}")
    print(f"COMPLETADO: {len(checkpoint['processed'])} catálogos")
    print(f"Total chunks: {checkpoint['total_chunks']}")
    print(f"Errores: {len(checkpoint['errors'])}")

if __name__ == "__main__":
    main()
