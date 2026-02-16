#!/usr/bin/env python3
"""
KB Manual Indexer v1.0
Extrae texto de manuales de servicio PDF e indexa en ChromaDB.
"""
import os
import json
import re
import time
import hashlib
from pathlib import Path
import fitz  # PyMuPDF
import chromadb

# Config
MANUAL_DIR = Path("/mnt/volume_sfo3_01/kb/IND_MOTOS/Manuales")
CHECKPOINT_FILE = Path("/opt/odi/data/kb_chunks/manuals/checkpoint.json")
BATCH_SIZE = 10
CHROMA_HOST = 'localhost'
CHROMA_PORT = 8000
COLLECTION = 'odi_ind_motos'

def extract_model_from_filename(filename):
    """Extrae el modelo de moto del nombre del archivo."""
    name = filename.replace(".pdf", "").replace("-", " ").replace("_", " ")
    for prefix in ["MANUAL", "SERVICIO", "SERVICE", "TALLER", "DESPIECE"]:
        name = re.sub(rf'\b{prefix}\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:60] if name else "MOTO"

def make_unique_id(filename, page_num):
    file_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
    return f"kb_man_{file_hash}_p{page_num:03d}"

def detect_procedure(text):
    """Detecta el tipo de procedimiento."""
    text_lower = text.lower()
    procedures = {
        "mantenimiento": ["mantenimiento", "maintenance", "service", "revision", "inspeccion"],
        "desmontaje": ["desmontaje", "desmontar", "removal", "quitar", "extraer"],
        "montaje": ["montaje", "montar", "installation", "instalar", "colocar"],
        "ajuste": ["ajuste", "adjustment", "calibrar", "torque", "apriete"],
        "diagnostico": ["diagnostico", "diagnosis", "falla", "problema", "solucion"],
        "electrico": ["cableado", "wiring", "circuito", "fusible", "bateria"],
        "especificaciones": ["especificacion", "specification", "dimension", "capacidad"],
    }
    for proc, keywords in procedures.items():
        for kw in keywords:
            if kw in text_lower:
                return proc
    return "general"

def extract_torques(text):
    """Extrae valores de torque del texto."""
    patterns = [
        r'\d+[\s-]*[Nn][·\.]?[Mm]',  # 25 N·m, 25 Nm
        r'\d+[\s-]*kgf?[\s·-]*[cm]m',  # 2.5 kgf·cm
        r'\d+[\s-]*lb[\s·-]*ft',  # 18 lb·ft
    ]
    torques = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        torques.extend(matches[:5])
    return torques[:5]

def process_pdf(pdf_path):
    """Procesa un PDF de manual."""
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
            procedure = detect_procedure(text_clean)
            torques = extract_torques(text)
            
            chunk_text = f"Manual de servicio {model_name}. Procedimiento: {procedure}. "
            if torques:
                chunk_text += f"Torques: {', '.join(torques)}. "
            chunk_text += f"Contenido: {text_clean[:500]}"
            
            chunk_id = make_unique_id(filename, page_num + 1)
            
            chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "metadata": {
                    "type": "kb_manual",
                    "source": "manual_pdf",
                    "model": model_name,
                    "procedure": procedure,
                    "page": page_num + 1,
                    "filename": filename,
                    "has_torques": len(torques) > 0
                }
            })
        
        doc.close()
        return chunks, None
        
    except Exception as e:
        return [], str(e)

def index_to_chromadb(chunks):
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
    print("KB MANUAL INDEXER v1.0 (PyMuPDF)")
    print("="*60)
    
    checkpoint = load_checkpoint()
    print(f"Checkpoint: {len(checkpoint['processed'])} procesados, {checkpoint['total_chunks']} chunks")
    
    manuals = sorted(MANUAL_DIR.glob("*.pdf"))
    pending = [m for m in manuals if m.name not in checkpoint["processed"]]
    print(f"Total: {len(manuals)} | Pendientes: {len(pending)}")
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
            print(f"\n*** BATCH: {indexed} chunks (total: {checkpoint['total_chunks']}) ***\n")
            batch_chunks = []
            batch_count = 0
            time.sleep(1)
    
    if batch_chunks:
        indexed = index_to_chromadb(batch_chunks)
        checkpoint["total_chunks"] += indexed
        save_checkpoint(checkpoint)
        print(f"\n*** FINAL: {indexed} chunks ***")
    
    print(f"\n{'='*60}")
    print(f"COMPLETADO: {len(checkpoint['processed'])} manuales")
    print(f"Total chunks: {checkpoint['total_chunks']}")
    print(f"Errores: {len(checkpoint['errors'])}")

if __name__ == "__main__":
    main()
