#!/usr/bin/env python3
"""
ODI Knowledge Base Indexer v2
=============================
Indexa TODO el contenido de /mnt/volume_sfo3_01/profesion

Optimizado para el servidor de producción existente:
- Usa Redis ya corriendo (odi-redis)
- Guarda embeddings en /mnt/volume_sfo3_01/embeddings
- Notifica a n8n en localhost:5678

Uso:
    python odi_kb_indexer_v2.py --index-all
    python odi_kb_indexer_v2.py --watch
    python odi_kb_indexer_v2.py --stats
"""

import os
import sys
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass, asdict
import time
import argparse

# Third party
from dotenv import load_dotenv
import redis
import httpx

# LangChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

# Document loaders
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import markdown
    from bs4 import BeautifulSoup
except ImportError:
    markdown = None
    BeautifulSoup = None

# Load env from /opt/odi/.env
ENV_PATH = "/opt/odi/.env"
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

# ============================================
# CONFIGURACIÓN
# ============================================
CONFIG = {
    # Paths del servidor
    "profesion_path": "/mnt/volume_sfo3_01/profesion",
    "embeddings_path": "/mnt/volume_sfo3_01/embeddings/profesion_kb",
    "cache_path": "/opt/odi/kb_cache",
    "logs_path": "/opt/odi/logs",

    # OpenAI
    "embedding_model": "text-embedding-3-small",
    "chunk_size": 1000,
    "chunk_overlap": 200,

    # Redis (ya corriendo en Docker)
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_db": 0,

    # n8n webhook
    "n8n_webhook": "http://localhost:5678/webhook/odi-kb-indexed",

    # Extensiones soportadas
    "extensions": {".pdf", ".md", ".txt", ".json", ".csv", ".html", ".py", ".yaml", ".yml"}
}

# Logging
os.makedirs(CONFIG["logs_path"], exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"{CONFIG['logs_path']}/kb_indexer_v2.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================
# DOCUMENT LOADER
# ============================================
class DocumentLoader:
    """Carga documentos de diferentes formatos."""

    @staticmethod
    def compute_hash(file_path: str) -> str:
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def load_pdf(file_path: str) -> str:
        if not pdfplumber:
            logger.warning("pdfplumber not installed, skipping PDF")
            return ""
        text_parts = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
        except Exception as e:
            logger.error(f"Error loading PDF {file_path}: {e}")
        return "\n\n".join(text_parts)

    @staticmethod
    def load_text(file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading text {file_path}: {e}")
            return ""

    @staticmethod
    def load_json(file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            def extract_strings(obj, depth=0) -> List[str]:
                if depth > 10:
                    return []
                texts = []
                if isinstance(obj, str) and len(obj) > 20:
                    texts.append(obj)
                elif isinstance(obj, dict):
                    for v in obj.values():
                        texts.extend(extract_strings(v, depth + 1))
                elif isinstance(obj, list):
                    for item in obj:
                        texts.extend(extract_strings(item, depth + 1))
                return texts

            return "\n\n".join(extract_strings(data))
        except Exception as e:
            logger.error(f"Error loading JSON {file_path}: {e}")
            return ""

    @staticmethod
    def load_markdown(file_path: str) -> str:
        if not markdown or not BeautifulSoup:
            return DocumentLoader.load_text(file_path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            html = markdown.markdown(md_content)
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text(separator="\n")
        except Exception as e:
            logger.error(f"Error loading Markdown {file_path}: {e}")
            return ""

    @staticmethod
    def load_csv(file_path: str) -> str:
        try:
            import csv
            texts = []
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_text = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
                    if row_text:
                        texts.append(row_text)
            return "\n".join(texts[:500])  # Limit rows
        except Exception as e:
            logger.error(f"Error loading CSV {file_path}: {e}")
            return ""

    @classmethod
    def load(cls, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        loaders = {
            ".pdf": cls.load_pdf,
            ".md": cls.load_markdown,
            ".txt": cls.load_text,
            ".json": cls.load_json,
            ".csv": cls.load_csv,
            ".py": cls.load_text,
            ".yaml": cls.load_text,
            ".yml": cls.load_text,
            ".html": cls.load_text,
        }
        loader = loaders.get(ext, cls.load_text)
        return loader(file_path)


# ============================================
# HASH CACHE
# ============================================
class FileHashCache:
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.hashes: Dict[str, str] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    self.hashes = json.load(f)
            except:
                self.hashes = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(self.hashes, f, indent=2)

    def needs_update(self, file_path: str, current_hash: str) -> bool:
        return self.hashes.get(file_path) != current_hash

    def set_hash(self, file_path: str, file_hash: str):
        self.hashes[file_path] = file_hash
        self._save()


# ============================================
# MAIN INDEXER
# ============================================
class ODIKBIndexerV2:
    def __init__(self):
        self.profesion_path = Path(CONFIG["profesion_path"])
        self.embeddings_path = Path(CONFIG["embeddings_path"])
        self.cache_file = Path(CONFIG["cache_path"]) / "file_hashes_v2.json"

        # Validate paths
        if not self.profesion_path.exists():
            logger.error(f"Profesion path not found: {self.profesion_path}")
            sys.exit(1)

        # Create directories
        self.embeddings_path.mkdir(parents=True, exist_ok=True)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize cache
        self.hash_cache = FileHashCache(str(self.cache_file))

        # Text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CONFIG["chunk_size"],
            chunk_overlap=CONFIG["chunk_overlap"],
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        # OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment")
            sys.exit(1)

        self.embeddings = OpenAIEmbeddings(
            model=CONFIG["embedding_model"],
            openai_api_key=api_key
        )

        # Vector store
        self.vectorstore = Chroma(
            persist_directory=str(self.embeddings_path),
            embedding_function=self.embeddings,
            collection_name="odi_profesion_kb"
        )

        # Redis
        try:
            self.redis = redis.Redis(
                host=CONFIG["redis_host"],
                port=CONFIG["redis_port"],
                db=CONFIG["redis_db"]
            )
            self.redis.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            self.redis = None

        # Stats
        self.stats = {
            "files_found": 0,
            "files_processed": 0,
            "files_skipped": 0,
            "chunks_created": 0,
            "errors": 0
        }

    def discover_files(self) -> Generator[Path, None, None]:
        """Descubre todos los archivos indexables."""
        for ext in CONFIG["extensions"]:
            for file_path in self.profesion_path.rglob(f"*{ext}"):
                if file_path.is_file():
                    # Skip hidden files and __pycache__
                    if any(part.startswith('.') or part == '__pycache__'
                           for part in file_path.parts):
                        continue
                    yield file_path

    def index_file(self, file_path: Path, force: bool = False) -> int:
        """Indexa un archivo individual."""
        try:
            # Check hash
            current_hash = DocumentLoader.compute_hash(str(file_path))
            if not force and not self.hash_cache.needs_update(str(file_path), current_hash):
                self.stats["files_skipped"] += 1
                return 0

            # Load content
            content = DocumentLoader.load(str(file_path))
            if not content or len(content) < 50:
                logger.debug(f"Skipping (insufficient content): {file_path}")
                return 0

            # Metadata
            relative_path = file_path.relative_to(self.profesion_path)
            metadata = {
                "source": str(relative_path),
                "file_name": file_path.name,
                "file_type": file_path.suffix.lower(),
                "category": str(relative_path.parent) if str(relative_path.parent) != "." else "root",
                "indexed_at": datetime.now().isoformat(),
                "file_hash": current_hash
            }

            # Split into chunks
            chunks = self.text_splitter.split_text(content)

            # Create documents
            documents = []
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        **metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }
                )
                documents.append(doc)

            # Add to vectorstore
            if documents:
                self.vectorstore.add_documents(documents)
                self.hash_cache.set_hash(str(file_path), current_hash)
                self.stats["files_processed"] += 1
                self.stats["chunks_created"] += len(documents)

                # Publish to Redis
                if self.redis:
                    self.redis.publish("odi:kb:indexed", json.dumps({
                        "file": str(relative_path),
                        "chunks": len(documents),
                        "timestamp": datetime.now().isoformat()
                    }))

                logger.info(f"✓ {relative_path} ({len(documents)} chunks)")
                return len(documents)

            return 0

        except Exception as e:
            logger.error(f"Error indexing {file_path}: {e}")
            self.stats["errors"] += 1
            return 0

    def index_all(self, force: bool = False):
        """Indexa todo el directorio profesion."""
        logger.info("=" * 60)
        logger.info("ODI Knowledge Base Indexer v2")
        logger.info(f"Source: {self.profesion_path}")
        logger.info(f"Embeddings: {self.embeddings_path}")
        logger.info("=" * 60)

        # Discover files
        files = list(self.discover_files())
        self.stats["files_found"] = len(files)
        logger.info(f"Found {len(files)} files to process")

        if not files:
            logger.warning("No files found!")
            return

        # Process files
        for i, file_path in enumerate(files, 1):
            logger.info(f"[{i}/{len(files)}] Processing: {file_path.name}")
            self.index_file(file_path, force=force)

        # Persist
        logger.info("Persisting vector store...")
        self.vectorstore.persist()

        # Notify n8n
        self._notify_n8n()

        # Save stats
        self._save_stats()

        # Summary
        logger.info("=" * 60)
        logger.info("INDEXING COMPLETE")
        logger.info(f"  Files found:     {self.stats['files_found']}")
        logger.info(f"  Files processed: {self.stats['files_processed']}")
        logger.info(f"  Files skipped:   {self.stats['files_skipped']}")
        logger.info(f"  Chunks created:  {self.stats['chunks_created']}")
        logger.info(f"  Errors:          {self.stats['errors']}")
        logger.info("=" * 60)

    def _notify_n8n(self):
        """Notifica a n8n que se completó la indexación."""
        try:
            webhook_url = CONFIG.get("n8n_webhook")
            if not webhook_url:
                return

            response = httpx.post(
                webhook_url,
                json={
                    "event": "kb_indexed",
                    "stats": self.stats,
                    "timestamp": datetime.now().isoformat(),
                    "source": "odi_kb_indexer_v2"
                },
                timeout=10.0
            )
            logger.info(f"n8n notified: {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not notify n8n: {e}")

    def _save_stats(self):
        """Guarda estadísticas."""
        stats_file = Path(CONFIG["cache_path"]) / "indexer_stats_v2.json"
        self.stats["last_run"] = datetime.now().isoformat()
        with open(stats_file, "w") as f:
            json.dump(self.stats, f, indent=2)

        # Also save to Redis
        if self.redis:
            self.redis.set("odi:kb:stats", json.dumps(self.stats))

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas."""
        try:
            collection = self.vectorstore._collection
            doc_count = collection.count()
        except:
            doc_count = 0

        stats_file = Path(CONFIG["cache_path"]) / "indexer_stats_v2.json"
        if stats_file.exists():
            with open(stats_file, "r") as f:
                saved = json.load(f)
        else:
            saved = {}

        return {
            **saved,
            "total_documents_in_index": doc_count,
            "profesion_path": str(self.profesion_path),
            "profesion_exists": self.profesion_path.exists()
        }

    def watch(self):
        """Modo watch - detecta cambios."""
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        logger.info(f"Watching {self.profesion_path} for changes...")

        class Handler(FileSystemEventHandler):
            def __init__(self, indexer):
                self.indexer = indexer

            def on_modified(self, event):
                if not event.is_directory:
                    ext = Path(event.src_path).suffix.lower()
                    if ext in CONFIG["extensions"]:
                        logger.info(f"Change detected: {event.src_path}")
                        self.indexer.index_file(Path(event.src_path), force=True)

            def on_created(self, event):
                self.on_modified(event)

        observer = Observer()
        observer.schedule(Handler(self), str(self.profesion_path), recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


# ============================================
# MAIN
# ============================================
def main():
    parser = argparse.ArgumentParser(description="ODI KB Indexer v2")
    parser.add_argument("--index-all", action="store_true", help="Index all files")
    parser.add_argument("--reindex", action="store_true", help="Force reindex all")
    parser.add_argument("--watch", action="store_true", help="Watch mode")
    parser.add_argument("--stats", action="store_true", help="Show stats")

    args = parser.parse_args()
    indexer = ODIKBIndexerV2()

    if args.stats:
        stats = indexer.get_stats()
        print("\nODI KB Stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
    elif args.reindex:
        indexer.index_all(force=True)
    elif args.watch:
        indexer.index_all(force=False)
        indexer.watch()
    else:
        indexer.index_all(force=False)


if __name__ == "__main__":
    main()
