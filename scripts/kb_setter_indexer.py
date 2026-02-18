#!/usr/bin/env python3
"""
KB Setter/Closer Indexer - Chunking Inteligente con Metadata Rica
"""
import os
import re
import fitz  # PyMuPDF
import chromadb
from pathlib import Path
from typing import List, Dict
import hashlib

# Config
BASE_PATH = Path("/mnt/volume_sfo3_01/profesion/Setter, Closer, Servicio al Cliente")
COLLECTION = "odi_ind_motos"
CHUNK_SIZE = 500  # palabras por chunk
CHUNK_OVERLAP = 50  # palabras de overlap

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extrae texto de un PDF."""
    try:
        doc = fitz.open(str(pdf_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"  ERROR extracting {pdf_path.name}: {e}")
        return ""

def extract_metadata_from_filename(filename: str) -> Dict:
    """Extrae metadata del nombre del archivo."""
    meta = {
        "domain": "ventas",
        "tags": []
    }
    
    fn_lower = filename.lower()
    
    # Detectar modulo/leccion
    module_match = re.search(r"m[oó]dulo\s*(\d+)", fn_lower)
    if module_match:
        meta["module"] = int(module_match.group(1))
        meta["tags"].append(f"modulo_{module_match.group(1)}")
    
    lesson_match = re.search(r"lecci[oó]n\s*(\d+)", fn_lower)
    if lesson_match:
        meta["lesson"] = int(lesson_match.group(1))
        meta["tags"].append(f"leccion_{lesson_match.group(1)}")
    
    dia_match = re.search(r"d[ií]a\s*(\d+)", fn_lower)
    if dia_match:
        meta["day"] = int(dia_match.group(1))
        meta["tags"].append(f"dia_{dia_match.group(1)}")
    
    # Detectar rol
    if "setter" in fn_lower:
        meta["role"] = "setter"
        meta["tags"].append("setter")
    elif "closer" in fn_lower:
        meta["role"] = "closer"
        meta["tags"].append("closer")
    elif "cs" in fn_lower or "servicio" in fn_lower:
        meta["role"] = "customer_service"
        meta["tags"].append("customer_service")
    
    # Detectar temas
    topics = {
        "linkedin": "linkedin",
        "crm": "crm",
        "prospección": "prospeccion",
        "objeciones": "objeciones",
        "cierre": "cierre",
        "seguimiento": "seguimiento",
        "agendamiento": "agendamiento",
        "coaching": "coaching",
        "ventas": "ventas",
        "whatsapp": "whatsapp"
    }
    for keyword, tag in topics.items():
        if keyword in fn_lower:
            meta["tags"].append(tag)
    
    meta["tags"] = ",".join(meta["tags"]) if meta["tags"] else "general"
    return meta

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Divide texto en chunks por palabras con overlap."""
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

def main():
    print("=" * 60)
    print("KB SETTER/CLOSER INDEXER - CHUNKING INTELIGENTE")
    print("=" * 60)
    
    # Connect to ChromaDB
    client = chromadb.HttpClient(host="localhost", port=8000)
    col = client.get_or_create_collection(COLLECTION)
    
    # Delete old kb_sales_training chunks
    print("\n[1] Eliminando chunks viejos de kb_sales_training...")
    try:
        old_data = col.get(where={"type": "kb_sales_training"}, limit=10000)
        if old_data["ids"]:
            col.delete(ids=old_data["ids"])
            print(f"    Eliminados: {len(old_data[ids])} chunks")
    except Exception as e:
        print(f"    Error eliminando: {e}")
    
    # Find all PDFs
    pdfs = list(BASE_PATH.rglob("*.pdf"))
    print(f"\n[2] Procesando {len(pdfs)} PDFs...")
    
    all_ids = []
    all_docs = []
    all_metas = []
    
    for i, pdf_path in enumerate(pdfs):
        print(f"\n  [{i+1}/{len(pdfs)}] {pdf_path.name[:60]}...")
        
        # Extract text
        text = extract_text_from_pdf(pdf_path)
        if not text or len(text) < 100:
            print(f"    SKIP: texto muy corto ({len(text)} chars)")
            continue
        
        # Extract metadata from filename
        file_meta = extract_metadata_from_filename(pdf_path.name)
        
        # Chunk text
        chunks = chunk_text(text)
        print(f"    Chunks: {len(chunks)} | Palabras: {len(text.split())}")
        
        # Prepare documents
        for chunk_num, chunk in enumerate(chunks):
            doc_id = f"kb_setter_{hashlib.md5((pdf_path.name + str(chunk_num)).encode()).hexdigest()[:12]}"
            
            metadata = {
                "type": "kb_sales_training",
                "domain": file_meta.get("domain", "ventas"),
                "source": "setter_closer_course",
                "source_file": str(pdf_path),
                "filename": pdf_path.name,
                "folder": "Setter, Closer, Servicio al Cliente",
                "chunk_num": chunk_num,
                "total_chunks": len(chunks),
                "word_count": len(chunk.split()),
                "tags": file_meta.get("tags", "general"),
            }
            
            # Add optional metadata
            if "role" in file_meta:
                metadata["role"] = file_meta["role"]
            if "module" in file_meta:
                metadata["module"] = file_meta["module"]
            if "lesson" in file_meta:
                metadata["lesson"] = file_meta["lesson"]
            if "day" in file_meta:
                metadata["day"] = file_meta["day"]
            
            all_ids.append(doc_id)
            all_docs.append(f"[VENTAS] {chunk}")
            all_metas.append(metadata)
    
    # Upsert to ChromaDB
    print(f"\n[3] Insertando {len(all_ids)} chunks en ChromaDB...")
    
    # Batch upsert (ChromaDB limit is ~5000 per batch)
    batch_size = 500
    for start in range(0, len(all_ids), batch_size):
        end = min(start + batch_size, len(all_ids))
        col.upsert(
            ids=all_ids[start:end],
            documents=all_docs[start:end],
            metadatas=all_metas[start:end]
        )
        print(f"    Batch {start//batch_size + 1}: {end - start} chunks")
    
    print("\n" + "=" * 60)
    print(f"COMPLETADO: {len(all_ids)} chunks indexados")
    print(f"PDFs procesados: {len(pdfs)}")
    print(f"Promedio chunks/PDF: {len(all_ids) / len(pdfs):.1f}")
    print("=" * 60)
    
    # Verify
    verify = col.get(where={"type": "kb_sales_training"}, limit=5)
    print("\nVerificacion - Muestra de metadata:")
    for m in verify["metadatas"][:3]:
        print(f"  {m}")

if __name__ == "__main__":
    main()
