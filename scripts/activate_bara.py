#!/usr/bin/env python3
"""
Activar BARA en producción — Poblar odi_ind_motos en ChromaDB
=============================================================
1. Ingesta 2,553 chunks de manuales/catálogos (kb_text JSON)
2. Ingesta 698 productos BARA como documentos buscables
3. Verifica que Cortex puede consultar el lobe

Usa: text-embedding-3-small (OpenAI)
Target: /mnt/volume_sfo3_01/embeddings/kb_embeddings collection=odi_ind_motos
"""

import json
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# Config
EMBED_PATH = "/mnt/volume_sfo3_01/embeddings/kb_embeddings"
COLLECTION = "odi_ind_motos"
KB_JSON = "/mnt/volume_sfo3_01/embeddings/kb_embeddings/kb_text_20260127_232312.json"
BARA_JSON = "/opt/odi/data/orden_maestra_v6/BARA_products.json"
BATCH_SIZE = 100  # docs per batch to avoid rate limits


def load_kb_chunks() -> list[Document]:
    """Load 2,553 knowledge chunks from manuals/catalogs."""
    log.info("Loading KB chunks from %s", KB_JSON)
    with open(KB_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data.get("chunks", [])
    docs = []
    for chunk in chunks:
        content = chunk.get("content", "").strip()
        if len(content) < 20:
            continue
        docs.append(Document(
            page_content=content,
            metadata={
                "source": chunk.get("source_name", "unknown"),
                "source_path": chunk.get("source", ""),
                "chunk_id": chunk.get("chunk_id", 0),
                "type": "manual_catalog",
                "indexed_at": datetime.now().isoformat(),
            }
        ))
    log.info("Loaded %d KB chunks (from %d raw)", len(docs), len(chunks))
    return docs


def load_bara_products() -> list[Document]:
    """Convert 698 BARA products into searchable documents."""
    log.info("Loading BARA products from %s", BARA_JSON)
    with open(BARA_JSON, "r", encoding="utf-8") as f:
        products = json.load(f)

    docs = []
    for p in products:
        sku = p.get("sku", "")
        title = p.get("title", "")
        price = p.get("price", 0)
        system = p.get("system", "")
        category = p.get("category", "")
        vendor = p.get("vendor", "BARA")

        # Build searchable text
        content = (
            f"Producto: {title}\n"
            f"SKU: {sku}\n"
            f"Precio: ${price:,.0f} COP\n"
            f"Sistema: {system}\n"
            f"Categoria: {category}\n"
            f"Proveedor: {vendor}"
        )

        docs.append(Document(
            page_content=content,
            metadata={
                "source": f"BARA/{sku}",
                "sku": sku,
                "price": price,
                "system": system,
                "category": category,
                "vendor": vendor,
                "type": "product",
                "indexed_at": datetime.now().isoformat(),
            }
        ))
    log.info("Loaded %d BARA products", len(docs))
    return docs


def ingest_to_chroma(docs: list[Document], skip_batches: int = 0):
    """Embed and store documents in ChromaDB with rate-limit resilience."""
    log.info("Initializing embeddings (text-embedding-3-small)...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    log.info("Opening ChromaDB at %s, collection=%s", EMBED_PATH, COLLECTION)
    os.makedirs(EMBED_PATH, exist_ok=True)

    # Open existing collection
    vs = Chroma(
        persist_directory=EMBED_PATH,
        embedding_function=embeddings,
        collection_name=COLLECTION,
    )
    existing = vs._collection.count()
    log.info("Existing docs in collection: %d", existing)

    # Process in batches
    total = len(docs)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    log.info("Ingesting %d documents in batches of %d (skipping first %d)...",
             total, BATCH_SIZE, skip_batches)

    for i in range(0, total, BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        if batch_num <= skip_batches:
            continue

        batch = docs[i:i + BATCH_SIZE]

        # Retry loop for rate limits
        for attempt in range(5):
            try:
                t0 = time.time()
                vs.add_documents(batch)
                elapsed = time.time() - t0
                log.info(
                    "  Batch %d/%d: %d docs in %.1fs (%.0f docs/s)",
                    batch_num, total_batches, len(batch), elapsed,
                    len(batch) / elapsed if elapsed > 0 else 0
                )
                break
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    wait = 15 * (attempt + 1)
                    log.warning("  Rate limited on batch %d, waiting %ds (attempt %d/5)...",
                                batch_num, wait, attempt + 1)
                    time.sleep(wait)
                else:
                    raise

        # Pause between batches to stay under TPM
        if i + BATCH_SIZE < total:
            time.sleep(3)

    return vs


def verify(vs):
    """Verify the collection works with a test query."""
    log.info("Verifying with test queries...")

    tests = [
        "pastillas de freno yamaha fz 2020",
        "filtro aceite honda cb 190",
        "kit arrastre pulsar 200",
    ]

    for query in tests:
        results = vs.similarity_search(query, k=3)
        log.info("  Q: '%s'", query)
        for r in results:
            log.info("    -> %s (type=%s)", r.page_content[:80], r.metadata.get("type"))

    # Final count
    count = vs._collection.count()
    log.info("Collection '%s' now has %d documents", COLLECTION, count)
    return count


def main():
    log.info("=" * 60)
    log.info("  ACTIVAR BARA — Poblar odi_ind_motos")
    log.info("=" * 60)

    # Check OpenAI key
    if not os.getenv("OPENAI_API_KEY"):
        log.error("OPENAI_API_KEY not set")
        sys.exit(1)

    # Load documents
    kb_docs = load_kb_chunks()
    bara_docs = load_bara_products()
    all_docs = kb_docs + bara_docs
    log.info("Total documents to ingest: %d (KB: %d, BARA: %d)",
             len(all_docs), len(kb_docs), len(bara_docs))

    # Check existing and calculate skip
    import chromadb
    client = chromadb.PersistentClient(path=EMBED_PATH)
    try:
        col = client.get_collection(COLLECTION)
        existing = col.count()
    except Exception:
        existing = 0
    skip_batches = existing // BATCH_SIZE
    log.info("Existing docs: %d, skipping first %d batches", existing, skip_batches)

    # Ingest (resume from where we left off)
    vs = ingest_to_chroma(all_docs, skip_batches=skip_batches)

    # Verify
    count = verify(vs)

    log.info("=" * 60)
    log.info("  BARA ACTIVADA — %d docs en odi_ind_motos", count)
    log.info("=" * 60)

    # Restart Cortex to pick up new embeddings
    log.info("Restarting odi-cortex-query to load new embeddings...")
    os.system("systemctl restart odi-cortex-query")
    time.sleep(5)

    # Verify Cortex health
    import httpx
    try:
        r = httpx.get("http://127.0.0.1:8803/health", timeout=10)
        health = r.json()
        log.info("Cortex health: %s v%s", health.get("status"), health.get("version"))
    except Exception as e:
        log.warning("Cortex health check failed: %s (may still be starting)", e)

    log.info("DONE. BARA esta activa en produccion.")


if __name__ == "__main__":
    main()
