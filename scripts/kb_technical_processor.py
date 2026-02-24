#!/usr/bin/env python3
"""
KB Technical PDF Processor v1.0
Extrae texto de PDFs técnicos y genera chunks para ChromaDB.
Usa PyMuPDF (fitz) - sin Vision AI.
"""
import os
import sys
import re
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import fitz  # PyMuPDF
import chromadb

# Paths
KB_DIR = Path("/mnt/volume_sfo3_01/kb/IND_MOTOS")
CATALOGOS_DIR = KB_DIR / "Catalogos"
MANUALES_DIR = KB_DIR / "Manuales"
OTROS_DIR = KB_DIR / "Otros"
ENCICLOPEDIA_DIR = KB_DIR / "Enciclopedia"

CHROMADB_HOST = "localhost"
CHROMADB_PORT = 8000
COLLECTION_NAME = "odi_ind_motos"

# Chunking config
CHUNK_SIZE = 600  # palabras target
CHUNK_OVERLAP = 100  # palabras overlap
MIN_PAGE_CHARS = 50  # mínimo caracteres para considerar página
MAX_GARBAGE_RATIO = 0.3  # máximo 30% caracteres raros

BATCH_SIZE = 10


class TextChunker:
    """Divide texto en chunks con overlap"""

    def __init__(self, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text, metadata=None):
        """Divide texto en chunks de ~chunk_size palabras"""
        words = text.split()
        chunks = []

        if len(words) <= self.chunk_size:
            # Texto corto, un solo chunk
            if len(words) > 20:  # mínimo 20 palabras
                chunks.append({
                    "text": text,
                    "word_count": len(words),
                    "metadata": metadata or {}
                })
            return chunks

        # Dividir en chunks con overlap
        start = 0
        chunk_num = 0

        while start < len(words):
            end = start + self.chunk_size
            chunk_words = words[start:end]

            if len(chunk_words) > 20:  # mínimo 20 palabras
                chunk_text = " ".join(chunk_words)
                chunks.append({
                    "text": chunk_text,
                    "word_count": len(chunk_words),
                    "chunk_num": chunk_num,
                    "metadata": metadata or {}
                })
                chunk_num += 1

            start = end - self.overlap

            # Evitar loop infinito
            if start >= len(words) - self.overlap:
                break

        return chunks


class KBTechnicalProcessor:
    """Procesa PDFs técnicos y los indexa en ChromaDB"""

    def __init__(self):
        self.client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        self.collection = self.client.get_collection(COLLECTION_NAME)
        self.chunker = TextChunker()
        self.stats = {
            "pdfs_processed": 0,
            "pdfs_failed": 0,
            "pdfs_skipped": 0,
            "chunks_created": 0,
            "pages_processed": 0,
            "pages_skipped": 0,
        }
        self.log_lines = []

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        self.log_lines.append(line)

    def extract_model_from_filename(self, filename):
        """Extrae modelo de moto del nombre del archivo"""
        name = Path(filename).stem

        # Limpiar prefijos comunes
        cleanups = [
            r'^CATALOGO[-_\s]*DE[-_\s]*PARTES[-_\s]*',
            r'^CATALOGO[-_\s]*ACTUALIZADO[-_\s]*',
            r'^CATALOGO[-_\s]*',
            r'^PLANTILLA[-_\s]*CATALOGO[-_\s]*',
            r'^MANUAL[-_\s]*DE[-_\s]*SERVICIO[-_\s]*',
            r'^MANUAL[-_\s]*',
            r'^REPUESTOS[-_\s]*',
        ]

        for pattern in cleanups:
            name = re.sub(pattern, '', name, flags=re.I)

        # Limpiar sufijos
        suffixes = [
            r'[-_\s]*FORMATO[-_\s]*MOBILITY.*$',
            r'[-_\s]*\d{1,2}[-_]\d{1,2}[-_]\d{2,4}.*$',
            r'[-_\s]*MY\d{2,4}.*$',
            r'[-_\s]*ABRIL[-_\s]*\d{4}.*$',
            r'[-_\s]*MARZO[-_\s]*\d{4}.*$',
            r'[-_\s]*\d+[-_\s]*\d*$',
            r'[-_\s]*V\d+.*$',
        ]

        for pattern in suffixes:
            name = re.sub(pattern, '', name, flags=re.I)

        # Normalizar
        name = name.replace('-', ' ').replace('_', ' ')
        name = ' '.join(name.split())

        return name.strip() if name else "General"

    def is_garbage_text(self, text):
        """Detecta si el texto es basura (demasiados caracteres raros)"""
        if not text:
            return True

        # Contar caracteres válidos vs raros
        valid_chars = sum(1 for c in text if c.isalnum() or c.isspace() or c in '.,;:!?()-$%')
        total_chars = len(text)

        if total_chars == 0:
            return True

        ratio = valid_chars / total_chars
        return ratio < (1 - MAX_GARBAGE_RATIO)

    def extract_text_from_pdf(self, pdf_path):
        """Extrae texto de un PDF usando PyMuPDF"""
        try:
            doc = fitz.open(pdf_path)
            pages_text = []

            for page_num, page in enumerate(doc, 1):
                text = page.get_text()

                # Skip páginas con poco texto
                if len(text.strip()) < MIN_PAGE_CHARS:
                    self.stats["pages_skipped"] += 1
                    continue

                # Skip texto basura
                if self.is_garbage_text(text):
                    self.stats["pages_skipped"] += 1
                    continue

                # Limpiar texto
                text = self.clean_text(text)

                if len(text.strip()) > MIN_PAGE_CHARS:
                    pages_text.append({
                        "page": page_num,
                        "text": text
                    })
                    self.stats["pages_processed"] += 1

            doc.close()
            return pages_text

        except Exception as e:
            self.log(f"    Error extrayendo PDF: {e}")
            return []

    def clean_text(self, text):
        """Limpia texto extraído"""
        # Normalizar espacios y saltos de línea
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)

        # Remover caracteres de control
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

        # Unir líneas que parecen continuación
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

        return text.strip()

    def generate_chunk_id(self, category, filename, chunk_num):
        """Genera ID único para chunk"""
        base = f"{category}_{filename}_{chunk_num}"
        hash_part = hashlib.md5(base.encode()).hexdigest()[:8]
        return f"kb_tech_{hash_part}_{chunk_num}"

    def process_pdf(self, pdf_path, category):
        """Procesa un PDF y genera chunks"""
        filename = Path(pdf_path).name
        model = self.extract_model_from_filename(filename)

        # Extraer texto
        pages = self.extract_text_from_pdf(pdf_path)

        if not pages:
            self.stats["pdfs_skipped"] += 1
            return []

        # Combinar todo el texto con marcadores de página
        all_text = ""
        page_ranges = []
        current_start = 1

        for p in pages:
            all_text += f"\n{p['text']}\n"
            page_ranges.append(p['page'])

        # Generar chunks
        chunks = self.chunker.chunk_text(all_text)

        # Crear documentos para ChromaDB
        docs = []
        page_start = page_ranges[0] if page_ranges else 1
        page_end = page_ranges[-1] if page_ranges else 1

        for i, chunk in enumerate(chunks):
            chunk_id = self.generate_chunk_id(category, filename, i)

            # Enriquecer texto con contexto
            enriched_text = f"[{category.upper()}] {model}. {chunk['text']}"

            docs.append({
                "id": chunk_id,
                "text": enriched_text,
                "metadata": {
                    "type": "kb_technical",
                    "source": "technical_pdf",
                    "filename": filename,
                    "category": category,
                    "model": model,
                    "page_start": page_start,
                    "page_end": page_end,
                    "chunk_num": i,
                    "word_count": chunk["word_count"],
                }
            })

        return docs

    def index_batch(self, docs):
        """Indexa batch de documentos en ChromaDB"""
        if not docs:
            return

        ids = [d["id"] for d in docs]
        texts = [d["text"] for d in docs]
        metadatas = [d["metadata"] for d in docs]

        self.collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )

        self.stats["chunks_created"] += len(docs)

    def process_directory(self, directory, category):
        """Procesa todos los PDFs de un directorio"""
        if not directory.exists():
            self.log(f"Directorio no existe: {directory}")
            return

        pdf_files = sorted(directory.glob("*.pdf")) + sorted(directory.glob("*.PDF"))

        if not pdf_files:
            self.log(f"No hay PDFs en {directory}")
            return

        self.log(f"\n{'='*60}")
        self.log(f"PROCESANDO: {category.upper()} ({len(pdf_files)} PDFs)")
        self.log(f"{'='*60}")

        batch_docs = []
        batch_count = 0

        for i, pdf_path in enumerate(pdf_files, 1):
            filename = pdf_path.name
            self.log(f"  [{i}/{len(pdf_files)}] {filename[:50]}...")

            try:
                docs = self.process_pdf(pdf_path, category)

                if docs:
                    batch_docs.extend(docs)
                    self.stats["pdfs_processed"] += 1
                    self.log(f"    → {len(docs)} chunks ({len([p for p in self.extract_text_from_pdf(pdf_path)])} páginas)")
                else:
                    self.log(f"    → SKIP (sin texto útil)")

            except Exception as e:
                self.stats["pdfs_failed"] += 1
                self.log(f"    → ERROR: {e}")

            # Indexar cada BATCH_SIZE PDFs
            batch_count += 1
            if batch_count >= BATCH_SIZE:
                if batch_docs:
                    self.log(f"  >> Indexando batch: {len(batch_docs)} chunks")
                    self.index_batch(batch_docs)
                    batch_docs = []
                batch_count = 0

        # Indexar último batch
        if batch_docs:
            self.log(f"  >> Indexando batch final: {len(batch_docs)} chunks")
            self.index_batch(batch_docs)

    def run(self):
        """Ejecuta procesamiento completo"""
        self.log("="*60)
        self.log("KB TECHNICAL PDF PROCESSOR v1.0")
        self.log("="*60)
        self.log(f"Timestamp: {datetime.now().isoformat()}")

        # Estado inicial
        initial_count = self.collection.count()
        self.log(f"ChromaDB inicial: {initial_count} docs")

        # Procesar en orden
        self.process_directory(CATALOGOS_DIR, "catalog")
        self.process_directory(MANUALES_DIR, "manual")
        self.process_directory(OTROS_DIR, "other")
        self.process_directory(ENCICLOPEDIA_DIR, "encyclopedia")

        # Estado final
        final_count = self.collection.count()

        self.log("\n" + "="*60)
        self.log("REPORTE FINAL")
        self.log("="*60)
        self.log(f"PDFs procesados:    {self.stats['pdfs_processed']}")
        self.log(f"PDFs fallidos:      {self.stats['pdfs_failed']}")
        self.log(f"PDFs sin texto:     {self.stats['pdfs_skipped']}")
        self.log(f"Páginas procesadas: {self.stats['pages_processed']}")
        self.log(f"Páginas saltadas:   {self.stats['pages_skipped']}")
        self.log(f"Chunks creados:     {self.stats['chunks_created']}")
        self.log(f"")
        self.log(f"ChromaDB inicial:   {initial_count}")
        self.log(f"ChromaDB final:     {final_count}")
        self.log(f"Nuevos docs:        {final_count - initial_count}")
        self.log("="*60)

        # Test query
        self.log("\n[TEST] Query: 'partes motor Agility 125'")
        results = self.collection.query(
            query_texts=["partes motor Agility 125"],
            n_results=5
        )

        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            doc_type = meta.get("type", "?")
            if doc_type == "kb_technical":
                self.log(f"  [TECH] {meta.get('model','?')[:30]} - {meta.get('filename','?')[:30]}")
            elif doc_type == "product":
                self.log(f"  [PROD] {meta.get('store','?')} - {meta.get('title','?')[:40]}")
            else:
                self.log(f"  [{doc_type}] {doc[:50]}...")


if __name__ == "__main__":
    processor = KBTechnicalProcessor()
    processor.run()
