#!/usr/bin/env python3
"""
KB General Indexer - Para carpetas pendientes con Metadata Rica
"""
import os
import re
import fitz
import chromadb
from pathlib import Path
from typing import List, Dict
import hashlib
import sys

COLLECTION = "odi_ind_motos"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Mapeo carpeta -> tipo KB
FOLDER_TYPE_MAP = {
    "Certificacion systeme.io": ("kb_tutorial", "marketing_automation", "systeme.io,embudos,automatizacion"),
    "Comprador de medios": ("kb_marketing", "media_buying", "ads,media_buyer,clientes"),
    "Dropi": ("kb_tutorial", "dropshipping", "dropi,ecommerce,proveedor"),
}

def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        doc = fitz.open(str(pdf_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"  ERROR: {e}")
        return ""

def extract_text_from_txt(txt_path: Path) -> str:
    try:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        print(f"  ERROR: {e}")
        return ""

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    words = text.split()
    if len(words) <= chunk_size:
        return [text] if text.strip() else []
    
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks

def process_folder(folder_name: str, base_path: str = "/mnt/volume_sfo3_01/profesion"):
    folder_path = Path(base_path) / folder_name
    
    if not folder_path.exists():
        print(f"ERROR: Carpeta no existe: {folder_path}")
        return
    
    kb_type, domain, tags = FOLDER_TYPE_MAP.get(folder_name, ("kb_general", "general", ""))
    
    print("=" * 60)
    print(f"INDEXANDO: {folder_name}")
    print(f"Tipo: {kb_type} | Dominio: {domain}")
    print("=" * 60)
    
    client = chromadb.HttpClient(host="localhost", port=8000)
    col = client.get_or_create_collection(COLLECTION)
    
    # Find files
    pdfs = list(folder_path.rglob("*.pdf"))
    txts = list(folder_path.rglob("*.txt"))
    all_files = pdfs + txts
    
    print(f"\nArchivos: {len(pdfs)} PDFs, {len(txts)} TXTs")
    
    all_ids = []
    all_docs = []
    all_metas = []
    
    for i, file_path in enumerate(all_files):
        print(f"\n  [{i+1}/{len(all_files)}] {file_path.name[:50]}...")
        
        if file_path.suffix.lower() == ".pdf":
            text = extract_text_from_pdf(file_path)
        else:
            text = extract_text_from_txt(file_path)
        
        if not text or len(text) < 100:
            print(f"    SKIP: texto muy corto")
            continue
        
        chunks = chunk_text(text)
        print(f"    Chunks: {len(chunks)}")
        
        for chunk_num, chunk in enumerate(chunks):
            doc_id = f"kb_{folder_name[:10]}_{hashlib.md5((file_path.name + str(chunk_num)).encode()).hexdigest()[:12]}"
            
            metadata = {
                "type": kb_type,
                "domain": domain,
                "source": "educational_content",
                "source_file": str(file_path),
                "filename": file_path.name,
                "folder": folder_name,
                "chunk_num": chunk_num,
                "total_chunks": len(chunks),
                "word_count": len(chunk.split()),
                "tags": tags,
            }
            
            prefix = f"[{domain.upper()}]" if domain else "[KB]"
            all_ids.append(doc_id)
            all_docs.append(f"{prefix} {chunk}")
            all_metas.append(metadata)
    
    print(f"\n[INSERTING] {len(all_ids)} chunks...")
    
    batch_size = 500
    for start in range(0, len(all_ids), batch_size):
        end = min(start + batch_size, len(all_ids))
        col.upsert(
            ids=all_ids[start:end],
            documents=all_docs[start:end],
            metadatas=all_metas[start:end]
        )
        print(f"  Batch: {end - start} chunks")
    
    print(f"\nCOMPLETADO: {len(all_ids)} chunks de {folder_name}")
    return len(all_ids)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 kb_general_indexer.py <carpeta>")
        print("Carpetas disponibles:", list(FOLDER_TYPE_MAP.keys()))
        sys.exit(1)
    
    folder = sys.argv[1]
    process_folder(folder)
