#!/usr/bin/env python3
"""
ODI KB Daemon v2 - Multi-Lobe Architecture
==========================================
Observa múltiples rutas y escribe en vector stores separados.

Lóbulos:
- profesion_kb: Conocimiento general (ADSI, empresas, estrategia)
- kb_embeddings: Conocimiento técnico (motos, catálogos, manuales)

Uso:
    python3 odi_kb_daemon_v2.py          # Correr en foreground
    systemctl start odi-kb-daemon        # Correr como servicio
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

# ============================================
# CONFIGURACIÓN MULTI-LÓBULO
# ============================================
LOBES = {
    "profesion": {
        "path": "/mnt/volume_sfo3_01/profesion",
        "embeddings": "/mnt/volume_sfo3_01/embeddings/profesion_kb",
        "collection": "odi_profesion",
        "cache": "/opt/odi/kb_cache/profesion_indexed.txt",
        "description": "Conocimiento general: ADSI, empresas, estrategia"
    },
    "ind_motos": {
        "path": "/mnt/volume_sfo3_01/kb/IND_MOTOS",
        "embeddings": "/mnt/volume_sfo3_01/embeddings/kb_embeddings",
        "collection": "odi_ind_motos",
        "cache": "/opt/odi/kb_cache/ind_motos_indexed.txt",
        "description": "Conocimiento técnico: motos, catálogos, manuales, fitment"
    }
}

LOG_FILE = "/opt/odi/logs/kb_daemon_v2.log"
BATCH_SIZE = 10
SLEEP_BETWEEN = 5

# Extensions
EXTENSIONS = {".pdf", ".txt", ".md", ".json", ".csv", ".py", ".yaml", ".yml"}

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


class LobeIndexer:
    """Indexador para un lóbulo específico."""

    def __init__(self, lobe_name: str, config: dict):
        self.name = lobe_name
        self.config = config
        self.path = Path(config["path"])
        self.embeddings_path = config["embeddings"]
        self.collection_name = config["collection"]
        self.cache_file = Path(config["cache"])

        # Create directories
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        os.makedirs(self.embeddings_path, exist_ok=True)

        # Load cache
        self.indexed = self._load_cache()

        # Initialize components
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        log.info(f"Lobe [{self.name}] initialized: {len(self.indexed)} files indexed")

    def _load_cache(self) -> set:
        if self.cache_file.exists():
            content = self.cache_file.read_text().strip()
            return set(content.split("\n")) if content else set()
        return set()

    def _save_to_cache(self, filepath: str):
        with open(self.cache_file, "a") as f:
            f.write(filepath + "\n")
        self.indexed.add(filepath)

    def _read_file(self, filepath: Path) -> str:
        ext = filepath.suffix.lower()
        try:
            if ext == ".pdf":
                import pdfplumber
                with pdfplumber.open(filepath) as pdf:
                    return "\n".join((p.extract_text() or "")[:3000] for p in pdf.pages[:15])
            else:
                return filepath.read_text(errors="ignore")[:15000]
        except Exception as e:
            log.error(f"[{self.name}] Error reading {filepath}: {e}")
            return ""

    def index_file(self, filepath: Path) -> bool:
        """Indexa un archivo en este lóbulo."""
        if str(filepath) in self.indexed:
            return False

        try:
            log.info(f"[{self.name}] Indexing: {filepath.name}")

            text = self._read_file(filepath)
            if len(text) < 50:
                log.warning(f"[{self.name}] Skipping (too short): {filepath.name}")
                self._save_to_cache(str(filepath))
                return False

            chunks = self.splitter.split_text(text)[:25]
            if not chunks:
                self._save_to_cache(str(filepath))
                return False

            # Metadata con origen del lóbulo
            docs = [Document(
                page_content=c,
                metadata={
                    "source": filepath.name,
                    "folder": filepath.parent.name,
                    "path": str(filepath.relative_to(self.path)),
                    "lobe": self.name,  # Identificador del lóbulo
                    "indexed_at": datetime.now().isoformat()
                }
            ) for c in chunks]

            # Guardar en vector store
            vs = Chroma(
                persist_directory=self.embeddings_path,
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
            vs.add_documents(docs)
            vs.persist()
            del vs

            self._save_to_cache(str(filepath))
            log.info(f"[{self.name}] ✓ {filepath.name} ({len(docs)} chunks)")

            gc.collect()
            return True

        except Exception as e:
            log.error(f"[{self.name}] Error indexing {filepath}: {e}")
            return False

    def get_pending_files(self) -> list:
        """Obtiene archivos pendientes de indexar."""
        if not self.path.exists():
            log.warning(f"[{self.name}] Path not found: {self.path}")
            return []

        pending = []
        for ext in EXTENSIONS:
            for f in self.path.rglob(f"*{ext}"):
                if f.is_file() and str(f) not in self.indexed:
                    pending.append(f)
        return pending

    def process_batch(self) -> int:
        """Procesa un lote de archivos."""
        pending = self.get_pending_files()

        if not pending:
            return 0

        log.info(f"[{self.name}] Pending files: {len(pending)}")
        processed = 0

        for f in pending[:BATCH_SIZE]:
            if self.index_file(f):
                processed += 1
            time.sleep(SLEEP_BETWEEN)

        return processed


class MultiLobeHandler(FileSystemEventHandler):
    """Handler para detectar cambios en múltiples lóbulos."""

    def __init__(self, lobes: dict):
        self.lobes = lobes  # {path: LobeIndexer}

    def _get_lobe_for_path(self, path: str) -> LobeIndexer:
        for lobe_path, indexer in self.lobes.items():
            if path.startswith(lobe_path):
                return indexer
        return None

    def on_created(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix.lower() in EXTENSIONS:
            indexer = self._get_lobe_for_path(event.src_path)
            if indexer:
                log.info(f"New file detected in [{indexer.name}]: {path.name}")
                time.sleep(2)
                indexer.index_file(path)

    def on_modified(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix.lower() in EXTENSIONS:
            indexer = self._get_lobe_for_path(event.src_path)
            if indexer and str(path) in indexer.indexed:
                log.info(f"File modified in [{indexer.name}], re-indexing: {path.name}")
                indexer.indexed.discard(str(path))
                time.sleep(2)
                indexer.index_file(path)


def main():
    log.info("=" * 70)
    log.info("ODI KB Daemon v2 - Multi-Lobe Architecture")
    log.info("=" * 70)

    # Inicializar lóbulos
    lobe_indexers = {}
    path_to_lobe = {}

    for lobe_name, config in LOBES.items():
        indexer = LobeIndexer(lobe_name, config)
        lobe_indexers[lobe_name] = indexer
        path_to_lobe[config["path"]] = indexer
        log.info(f"  [{lobe_name}] {config['path']}")
        log.info(f"    → {config['description']}")

    log.info("=" * 70)

    # Procesar archivos pendientes
    log.info("Processing pending files in all lobes...")
    for name, indexer in lobe_indexers.items():
        while True:
            processed = indexer.process_batch()
            if processed == 0:
                break
            log.info(f"[{name}] Batch complete: {processed} files")
            time.sleep(10)
        log.info(f"[{name}] All pending files processed")

    log.info("Starting watch mode on all lobes...")

    # Configurar watchers
    handler = MultiLobeHandler(path_to_lobe)
    observer = Observer()

    for config in LOBES.values():
        if Path(config["path"]).exists():
            observer.schedule(handler, config["path"], recursive=True)
            log.info(f"Watching: {config['path']}")

    observer.start()

    try:
        while True:
            time.sleep(60)
            # Verificar periódicamente
            for name, indexer in lobe_indexers.items():
                pending = indexer.get_pending_files()
                if pending:
                    log.info(f"[{name}] Found {len(pending)} new files, processing...")
                    indexer.process_batch()
    except KeyboardInterrupt:
        observer.stop()
        log.info("Daemon stopped")

    observer.join()


if __name__ == "__main__":
    main()
