#!/usr/bin/env python3
"""
ODI Knowledge Base Indexer
==========================
Indexa documentos de /mnt/volume_sfo3_01/profesion en embeddings vectoriales.

Soporta:
- PDF (texto + OCR si es necesario)
- Markdown (.md)
- Text (.txt)
- JSON (extrae campos de texto)
- CSV (extrae columnas de texto)

Uso:
    python odi_kb_indexer.py --index          # Indexar todo
    python odi_kb_indexer.py --watch          # Modo watch (detecta cambios)
    python odi_kb_indexer.py --reindex        # Reindexar desde cero
    python odi_kb_indexer.py --stats          # Mostrar estadisticas
"""

import os
import sys
import json
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass, asdict
import time

# Third party
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import redis

# LangChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

# Document loaders
import pdfplumber
import markdown
from bs4 import BeautifulSoup

# Setup
console = Console()
load_dotenv("/opt/odi/config/.env")

# Configuration
CONFIG = {
    "profesion_path": os.getenv("PROFESION_PATH", "/mnt/volume_sfo3_01/profesion"),
    "embeddings_path": os.getenv("EMBEDDINGS_PATH", "/opt/odi/embeddings"),
    "cache_path": os.getenv("CACHE_PATH", "/opt/odi/cache"),
    "logs_path": os.getenv("LOGS_PATH", "/opt/odi/logs"),
    "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
    "chunk_size": int(os.getenv("CHUNK_SIZE", "1000")),
    "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "200")),
    "redis_host": os.getenv("REDIS_HOST", "localhost"),
    "redis_port": int(os.getenv("REDIS_PORT", "6379")),
    "redis_db": int(os.getenv("REDIS_DB", "0")),
}

# Logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"{CONFIG['logs_path']}/indexer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Supported file types
SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt", ".json", ".csv", ".html"}


@dataclass
class DocumentChunk:
    """Representa un chunk de documento indexado."""
    content: str
    metadata: Dict[str, Any]
    doc_id: str
    chunk_index: int
    file_path: str
    file_hash: str
    timestamp: str


class FileHashCache:
    """Cache de hashes de archivos para detectar cambios."""

    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.hashes: Dict[str, str] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r") as f:
                self.hashes = json.load(f)

    def _save(self):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(self.hashes, f, indent=2)

    def get_hash(self, file_path: str) -> Optional[str]:
        return self.hashes.get(file_path)

    def set_hash(self, file_path: str, file_hash: str):
        self.hashes[file_path] = file_hash
        self._save()

    def file_changed(self, file_path: str, current_hash: str) -> bool:
        stored = self.get_hash(file_path)
        return stored != current_hash

    def remove(self, file_path: str):
        if file_path in self.hashes:
            del self.hashes[file_path]
            self._save()


class DocumentLoader:
    """Carga y extrae texto de diferentes tipos de documentos."""

    @staticmethod
    def compute_hash(file_path: str) -> str:
        """Computa hash MD5 de un archivo."""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def load_pdf(file_path: str) -> str:
        """Extrae texto de PDF."""
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
    def load_markdown(file_path: str) -> str:
        """Extrae texto de Markdown."""
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
    def load_text(file_path: str) -> str:
        """Carga archivo de texto."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading text {file_path}: {e}")
            return ""

    @staticmethod
    def load_json(file_path: str) -> str:
        """Extrae texto de JSON."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            def extract_strings(obj, depth=0) -> List[str]:
                if depth > 10:  # Prevent infinite recursion
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
    def load_csv(file_path: str) -> str:
        """Extrae texto de CSV."""
        try:
            import csv
            texts = []
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_text = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
                    if row_text:
                        texts.append(row_text)
            return "\n".join(texts)
        except Exception as e:
            logger.error(f"Error loading CSV {file_path}: {e}")
            return ""

    @staticmethod
    def load_html(file_path: str) -> str:
        """Extrae texto de HTML."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
            return soup.get_text(separator="\n")
        except Exception as e:
            logger.error(f"Error loading HTML {file_path}: {e}")
            return ""

    @classmethod
    def load(cls, file_path: str) -> str:
        """Carga un documento segun su extension."""
        ext = Path(file_path).suffix.lower()

        loaders = {
            ".pdf": cls.load_pdf,
            ".md": cls.load_markdown,
            ".txt": cls.load_text,
            ".json": cls.load_json,
            ".csv": cls.load_csv,
            ".html": cls.load_html,
        }

        loader = loaders.get(ext)
        if loader:
            return loader(file_path)
        return ""


class ODIKnowledgeBaseIndexer:
    """Indexador principal de Knowledge Base para ODI."""

    def __init__(self):
        self.profesion_path = Path(CONFIG["profesion_path"])
        self.embeddings_path = Path(CONFIG["embeddings_path"])
        self.cache_file = Path(CONFIG["cache_path"]) / "file_hashes.json"

        # Initialize components
        self.hash_cache = FileHashCache(str(self.cache_file))
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CONFIG["chunk_size"],
            chunk_overlap=CONFIG["chunk_overlap"],
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        # OpenAI Embeddings
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "sk-your-key-here":
            logger.error("OPENAI_API_KEY no configurada en /opt/odi/config/.env")
            sys.exit(1)

        self.embeddings = OpenAIEmbeddings(
            model=CONFIG["embedding_model"],
            openai_api_key=api_key
        )

        # Vector store
        self.embeddings_path.mkdir(parents=True, exist_ok=True)
        self.vectorstore = Chroma(
            persist_directory=str(self.embeddings_path),
            embedding_function=self.embeddings,
            collection_name="odi_knowledge_base"
        )

        # Redis for real-time updates
        try:
            self.redis = redis.Redis(
                host=CONFIG["redis_host"],
                port=CONFIG["redis_port"],
                db=CONFIG["redis_db"]
            )
            self.redis.ping()
            logger.info("Conectado a Redis")
        except Exception as e:
            logger.warning(f"Redis no disponible: {e}")
            self.redis = None

        # Stats
        self.stats = {
            "files_processed": 0,
            "chunks_created": 0,
            "errors": 0,
            "last_run": None
        }

    def discover_files(self) -> Generator[Path, None, None]:
        """Descubre archivos soportados en el directorio profesion."""
        if not self.profesion_path.exists():
            logger.error(f"Directorio no existe: {self.profesion_path}")
            return

        for ext in SUPPORTED_EXTENSIONS:
            for file_path in self.profesion_path.rglob(f"*{ext}"):
                if file_path.is_file():
                    yield file_path

    def should_index(self, file_path: Path) -> bool:
        """Determina si un archivo necesita ser indexado."""
        current_hash = DocumentLoader.compute_hash(str(file_path))
        return self.hash_cache.file_changed(str(file_path), current_hash)

    def index_file(self, file_path: Path) -> int:
        """Indexa un archivo individual."""
        try:
            # Load document
            content = DocumentLoader.load(str(file_path))
            if not content or len(content) < 50:
                logger.warning(f"Contenido insuficiente: {file_path}")
                return 0

            # Compute hash
            file_hash = DocumentLoader.compute_hash(str(file_path))

            # Extract metadata
            relative_path = file_path.relative_to(self.profesion_path)
            metadata = {
                "source": str(relative_path),
                "file_name": file_path.name,
                "file_type": file_path.suffix.lower(),
                "file_hash": file_hash,
                "indexed_at": datetime.now().isoformat(),
                "category": str(relative_path.parent) if relative_path.parent != Path(".") else "root"
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
                self.hash_cache.set_hash(str(file_path), file_hash)

                # Publish to Redis
                if self.redis:
                    self.redis.publish("odi:indexed", json.dumps({
                        "file": str(relative_path),
                        "chunks": len(documents),
                        "timestamp": datetime.now().isoformat()
                    }))

            logger.info(f"Indexado: {relative_path} ({len(documents)} chunks)")
            return len(documents)

        except Exception as e:
            logger.error(f"Error indexando {file_path}: {e}")
            self.stats["errors"] += 1
            return 0

    def index_all(self, force: bool = False) -> Dict[str, Any]:
        """Indexa todos los documentos."""
        console.print("\n[bold blue]ODI Knowledge Base Indexer[/bold blue]\n")

        files = list(self.discover_files())
        console.print(f"Encontrados: [cyan]{len(files)}[/cyan] archivos\n")

        if not files:
            console.print("[yellow]No se encontraron archivos para indexar[/yellow]")
            return self.stats

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Indexando...", total=len(files))

            for file_path in files:
                if force or self.should_index(file_path):
                    chunks = self.index_file(file_path)
                    self.stats["files_processed"] += 1
                    self.stats["chunks_created"] += chunks
                else:
                    logger.debug(f"Sin cambios: {file_path}")

                progress.update(task, advance=1)

        self.stats["last_run"] = datetime.now().isoformat()

        # Persist
        self.vectorstore.persist()

        # Save stats
        stats_file = Path(CONFIG["cache_path"]) / "indexer_stats.json"
        with open(stats_file, "w") as f:
            json.dump(self.stats, f, indent=2)

        # Summary
        console.print("\n[bold green]Indexacion completada![/bold green]")
        table = Table(title="Resumen")
        table.add_column("Metrica", style="cyan")
        table.add_column("Valor", style="green")
        table.add_row("Archivos procesados", str(self.stats["files_processed"]))
        table.add_row("Chunks creados", str(self.stats["chunks_created"]))
        table.add_row("Errores", str(self.stats["errors"]))
        console.print(table)

        return self.stats

    def watch(self):
        """Modo watch: detecta cambios y reindexar automaticamente."""
        console.print("[bold blue]ODI Indexer - Modo Watch[/bold blue]")
        console.print(f"Observando: {self.profesion_path}\n")

        class ChangeHandler(FileSystemEventHandler):
            def __init__(self, indexer):
                self.indexer = indexer

            def on_modified(self, event):
                if not event.is_directory:
                    ext = Path(event.src_path).suffix.lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        logger.info(f"Cambio detectado: {event.src_path}")
                        self.indexer.index_file(Path(event.src_path))

            def on_created(self, event):
                if not event.is_directory:
                    ext = Path(event.src_path).suffix.lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        logger.info(f"Nuevo archivo: {event.src_path}")
                        self.indexer.index_file(Path(event.src_path))

        observer = Observer()
        observer.schedule(ChangeHandler(self), str(self.profesion_path), recursive=True)
        observer.start()

        console.print("[green]Watching... (Ctrl+C para detener)[/green]")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()

        observer.join()

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadisticas del indice."""
        stats_file = Path(CONFIG["cache_path"]) / "indexer_stats.json"

        if stats_file.exists():
            with open(stats_file, "r") as f:
                saved_stats = json.load(f)
        else:
            saved_stats = {}

        # Collection stats
        try:
            collection = self.vectorstore._collection
            doc_count = collection.count()
        except:
            doc_count = 0

        return {
            **saved_stats,
            "total_documents_in_index": doc_count,
            "profesion_path": str(self.profesion_path),
            "embeddings_path": str(self.embeddings_path),
            "profesion_exists": self.profesion_path.exists()
        }


def main():
    parser = argparse.ArgumentParser(description="ODI Knowledge Base Indexer")
    parser.add_argument("--index", action="store_true", help="Indexar documentos nuevos/modificados")
    parser.add_argument("--reindex", action="store_true", help="Reindexar todo desde cero")
    parser.add_argument("--watch", action="store_true", help="Modo watch (detecta cambios)")
    parser.add_argument("--stats", action="store_true", help="Mostrar estadisticas")

    args = parser.parse_args()

    indexer = ODIKnowledgeBaseIndexer()

    if args.stats:
        stats = indexer.get_stats()
        console.print("\n[bold]ODI KB Stats[/bold]")
        for key, value in stats.items():
            console.print(f"  {key}: [cyan]{value}[/cyan]")
    elif args.reindex:
        indexer.index_all(force=True)
    elif args.watch:
        # Initial index
        indexer.index_all(force=False)
        # Then watch
        indexer.watch()
    else:
        indexer.index_all(force=False)


if __name__ == "__main__":
    main()
