#!/usr/bin/env python3
"""KB Otros Indexer - Procesa PDFs en /Otros/ como kb_technical"""
import os, json, re, time, hashlib
from pathlib import Path
import fitz
import chromadb

OTROS_DIR = Path("/mnt/volume_sfo3_01/kb/IND_MOTOS/Otros")
CHECKPOINT_FILE = Path("/opt/odi/data/kb_chunks/otros/checkpoint.json")
BATCH_SIZE = 10

def extract_model(filename):
    name = filename.replace(".pdf", "").replace("-", " ").replace("_", " ")
    name = re.sub(r'Actualizado|actualizada|copiaa|MY\d+|final|\d{2}\s*\d{2}\s*\d{2,4}', '', name, flags=re.I)
    return re.sub(r'\s+', ' ', name).strip()[:60] or "MOTO"

def make_id(filename, page):
    return f"kb_tech_{hashlib.md5(filename.encode()).hexdigest()[:8]}_p{page:03d}"

def detect_system(text):
    tl = text.lower()
    for sys, kws in {"motor":["cilindro","piston","biela"],"transmision":["embrague","cadena"],"frenos":["freno","disco","pastilla"],"suspension":["amortiguador","horquilla"],"electrico":["cdi","bobina","bateria"]}.items():
        if any(k in tl for k in kws): return sys
    return "general"

def process_pdf(path):
    filename, model = path.name, extract_model(path.name)
    chunks = []
    try:
        doc = fitz.open(str(path))
        for i in range(len(doc)):
            text = doc[i].get_text()
            if len(text.strip()) < 50: continue
            text_clean = re.sub(r'\s+', ' ', text).strip()[:2000]
            chunks.append({
                "id": make_id(filename, i+1),
                "text": f"Catálogo técnico {model}. Sistema: {detect_system(text_clean)}. Contenido: {text_clean[:600]}",
                "metadata": {"type":"kb_technical","source":"otros_pdf","model":model,"page":i+1,"filename":filename}
            })
        doc.close()
        return chunks, None
    except Exception as e:
        return [], str(e)

def index_chromadb(chunks):
    if not chunks: return 0
    client = chromadb.HttpClient("localhost", 8000)
    col = client.get_or_create_collection("odi_ind_motos")
    for i in range(0, len(chunks), 100):
        b = chunks[i:i+100]
        col.upsert(ids=[c["id"] for c in b], documents=[c["text"] for c in b], metadatas=[c["metadata"] for c in b])
    return len(chunks)

def load_cp():
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f: return json.load(f)
    return {"processed":[], "total_chunks":0, "errors":[]}

def save_cp(d):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f: json.dump(d, f)

def main():
    print("="*50)
    print("KB OTROS INDEXER v1.0")
    print("="*50)
    cp = load_cp()
    pdfs = sorted(OTROS_DIR.glob("*.pdf"))
    pending = [p for p in pdfs if p.name not in cp["processed"]]
    print(f"Total: {len(pdfs)} | Pendientes: {len(pending)}\n")
    
    batch, bc = [], 0
    for i, pdf in enumerate(pending):
        print(f"[{i+1}/{len(pending)}] {pdf.name[:45]}...", end=" ", flush=True)
        chunks, err = process_pdf(pdf)
        if err:
            print(f"ERROR: {err}")
            cp["errors"].append({"file":pdf.name,"error":err})
        elif chunks:
            batch.extend(chunks)
            print(f"OK ({len(chunks)})")
        else:
            print("SKIP")
        cp["processed"].append(pdf.name)
        bc += 1
        if bc >= BATCH_SIZE and batch:
            n = index_chromadb(batch)
            cp["total_chunks"] += n
            save_cp(cp)
            print(f"\n*** BATCH: {n} chunks (total: {cp['total_chunks']}) ***\n")
            batch, bc = [], 0
            time.sleep(1)
    
    if batch:
        n = index_chromadb(batch)
        cp["total_chunks"] += n
        save_cp(cp)
        print(f"\n*** FINAL: {n} chunks ***")
    
    print(f"\n{'='*50}")
    print(f"COMPLETADO: {len(cp['processed'])} PDFs, {cp['total_chunks']} chunks, {len(cp['errors'])} errores")

if __name__ == "__main__":
    main()
