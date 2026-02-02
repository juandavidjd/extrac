#!/usr/bin/env python3
"""
ODI KB Daemon - Servicio permanente de indexación
Corre como servicio systemd, procesa automáticamente nuevos archivos

Características:
- Procesa archivos pendientes al iniciar (en lotes de 10)
- Detecta nuevos archivos automáticamente (watchdog)
- Re-indexa si un archivo se modifica
- Se reinicia automáticamente si falla
- Logs en /opt/odi/logs/kb_daemon.log

Uso:
    python3 odi_kb_daemon.py          # Correr en foreground
    systemctl start odi-kb-daemon     # Correr como servicio
"""
import os
import sys
import gc
import time
import logging
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# Config
PROFESION = Path("/mnt/volume_sfo3_01/profesion")
EMBED_PATH = "/mnt/volume_sfo3_01/embeddings/profesion_kb"
CACHE_FILE = "/opt/odi/kb_cache/indexed_files.txt"
LOG_FILE = "/opt/odi/logs/kb_daemon.log"
BATCH_SIZE = 10
SLEEP_BETWEEN = 5  # segundos entre archivos

# Logging
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# Extensions
EXTENSIONS = {".pdf", ".txt", ".md", ".json", ".csv", ".py", ".yaml", ".yml"}


class KBIndexer:
    def __init__(self):
        self.cache_file = Path(CACHE_FILE)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.indexed = self._load_cache()

        self.splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        log.info(f"Indexer initialized. Already indexed: {len(self.indexed)} files")

    def _load_cache(self):
        if self.cache_file.exists():
            return set(self.cache_file.read_text().strip().split("\n"))
        return set()

    def _save_to_cache(self, filepath):
        with open(self.cache_file, "a") as f:
            f.write(str(filepath) + "\n")
        self.indexed.add(str(filepath))

    def _read_file(self, filepath):
        ext = filepath.suffix.lower()
        try:
            if ext == ".pdf":
                import pdfplumber
                with pdfplumber.open(filepath) as pdf:
                    return "\n".join((p.extract_text() or "")[:3000] for p in pdf.pages[:15])
            else:
                return filepath.read_text(errors="ignore")[:15000]
        except Exception as e:
            log.error(f"Error reading {filepath}: {e}")
            return ""

    def index_file(self, filepath):
        """Indexa un solo archivo"""
        if str(filepath) in self.indexed:
            return False

        try:
            log.info(f"Indexing: {filepath.name}")

            text = self._read_file(filepath)
            if len(text) < 50:
                log.warning(f"Skipping (too short): {filepath.name}")
                self._save_to_cache(filepath)
                return False

            chunks = self.splitter.split_text(text)[:25]
            if not chunks:
                self._save_to_cache(filepath)
                return False

            docs = [Document(
                page_content=c,
                metadata={
                    "source": filepath.name,
                    "folder": filepath.parent.name,
                    "path": str(filepath.relative_to(PROFESION)),
                    "indexed_at": datetime.now().isoformat()
                }
            ) for c in chunks]

            vs = Chroma(
                persist_directory=EMBED_PATH,
                embedding_function=self.embeddings,
                collection_name="odi_kb"
            )
            vs.add_documents(docs)
            vs.persist()
            del vs

            self._save_to_cache(filepath)
            log.info(f"✓ {filepath.name} ({len(docs)} chunks)")

            gc.collect()
            return True

        except Exception as e:
            log.error(f"Error indexing {filepath}: {e}")
            return False

    def get_pending_files(self):
        """Obtiene archivos pendientes de indexar"""
        pending = []
        for ext in EXTENSIONS:
            for f in PROFESION.rglob(f"*{ext}"):
                if f.is_file() and str(f) not in self.indexed:
                    pending.append(f)
        return pending

    def process_batch(self):
        """Procesa un lote de archivos pendientes"""
        pending = self.get_pending_files()

        if not pending:
            return 0

        log.info(f"Pending files: {len(pending)}")
        processed = 0

        for f in pending[:BATCH_SIZE]:
            if self.index_file(f):
                processed += 1
            time.sleep(SLEEP_BETWEEN)

        return processed


class NewFileHandler(FileSystemEventHandler):
    """Detecta nuevos archivos"""
    def __init__(self, indexer):
        self.indexer = indexer
        self.pending_queue = []

    def on_created(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix.lower() in EXTENSIONS:
            log.info(f"New file detected: {path.name}")
            # Esperar a que termine de escribirse
            time.sleep(2)
            self.indexer.index_file(path)

    def on_modified(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix.lower() in EXTENSIONS and str(path) in self.indexer.indexed:
            log.info(f"File modified, re-indexing: {path.name}")
            self.indexer.indexed.discard(str(path))
            time.sleep(2)
            self.indexer.index_file(path)


def main():
    log.info("="*60)
    log.info("ODI KB Daemon starting...")
    log.info(f"Watching: {PROFESION}")
    log.info(f"Embeddings: {EMBED_PATH}")
    log.info("="*60)

    indexer = KBIndexer()

    # Procesar archivos pendientes primero
    log.info("Processing pending files...")
    while True:
        processed = indexer.process_batch()
        if processed == 0:
            break
        log.info(f"Batch complete: {processed} files. Continuing...")
        time.sleep(10)  # Pausa entre lotes

    log.info("All pending files processed. Starting watch mode...")

    # Iniciar watcher
    handler = NewFileHandler(indexer)
    observer = Observer()
    observer.schedule(handler, str(PROFESION), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(60)
            # Verificar periódicamente si hay archivos nuevos
            pending = indexer.get_pending_files()
            if pending:
                log.info(f"Found {len(pending)} new files, processing...")
                indexer.process_batch()
    except KeyboardInterrupt:
        observer.stop()
        log.info("Daemon stopped")

    observer.join()


if __name__ == "__main__":
    main()
