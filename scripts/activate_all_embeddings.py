#!/usr/bin/env python3
"""
Ingestar productos de TODAS las tiendas en ChromaDB odi_ind_motos.
BARA (698) ya está — este script ingesta las 13 restantes.

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

EMBED_PATH = "/mnt/volume_sfo3_01/embeddings/kb_embeddings"
COLLECTION = "odi_ind_motos"
JSON_PATH = "/opt/odi/data/orden_maestra_v6"
BATCH_SIZE = 100

# All stores EXCEPT BARA (already ingested)
STORES = [
    "YOKOMAR", "KAIQI", "DFG", "DUNA", "IMBRA", "JAPAN",
    "LEO", "STORE", "VAISAND",
    "ARMOTOS", "CBI", "MCLMOTOS", "OH_IMPORTACIONES", "VITTON",
]


def load_store_products(store: str) -> list[Document]:
    """Convert store products into searchable documents."""
    json_file = f"{JSON_PATH}/{store}_products.json"
    if not os.path.exists(json_file):
        log.warning("[%s] JSON not found: %s", store, json_file)
        return []

    with open(json_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    docs = []
    for p in products:
        sku = p.get("sku", "")
        title = p.get("title", "")
        price = p.get("price", 0) or 0
        system = p.get("system", "")
        category = p.get("category", "")
        vendor = p.get("vendor", store)

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
                "source": f"{store}/{sku}",
                "sku": sku,
                "price": price,
                "system": system,
                "category": category,
                "vendor": vendor,
                "type": "product",
                "store": store,
                "indexed_at": datetime.now().isoformat(),
            }
        ))
    return docs


def ingest_batch_with_retry(vs, batch, batch_num, total_batches, store):
    """Ingest a single batch with retry logic for rate limits."""
    for attempt in range(5):
        try:
            t0 = time.time()
            vs.add_documents(batch)
            elapsed = time.time() - t0
            log.info(
                "  [%s] Batch %d/%d: %d docs in %.1fs",
                store, batch_num, total_batches, len(batch), elapsed
            )
            return True
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                wait = 20 * (attempt + 1)
                log.warning(
                    "  [%s] Rate limited batch %d, waiting %ds (attempt %d/5)",
                    store, batch_num, wait, attempt + 1
                )
                time.sleep(wait)
            else:
                log.error("  [%s] Error on batch %d: %s", store, batch_num, e)
                return False
    log.error("  [%s] Failed batch %d after 5 attempts", store, batch_num)
    return False


def main():
    log.info("=" * 60)
    log.info("  INGESTAR TODAS LAS TIENDAS EN ChromaDB")
    log.info("=" * 60)

    if not os.getenv("OPENAI_API_KEY"):
        log.error("OPENAI_API_KEY not set")
        sys.exit(1)

    # Initialize embeddings and ChromaDB once
    log.info("Initializing embeddings (text-embedding-3-small)...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    log.info("Opening ChromaDB at %s, collection=%s", EMBED_PATH, COLLECTION)
    vs = Chroma(
        persist_directory=EMBED_PATH,
        embedding_function=embeddings,
        collection_name=COLLECTION,
    )
    existing = vs._collection.count()
    log.info("Existing docs in collection: %d", existing)

    # Check which stores are already ingested
    log.info("Checking which stores are already in the collection...")
    already_ingested = set()
    try:
        sample = vs._collection.get(
            where={"type": "product"},
            limit=10000,
            include=["metadatas"]
        )
        if sample and sample.get("metadatas"):
            for m in sample["metadatas"]:
                store_name = m.get("store") or m.get("vendor", "")
                if store_name:
                    already_ingested.add(store_name.upper())
    except Exception as e:
        log.warning("Could not check existing stores: %s", e)

    if already_ingested:
        log.info("Stores already in collection: %s", already_ingested)

    # Process each store
    results = {}
    total_ingested = 0

    for store in STORES:
        if store in already_ingested:
            log.info("[%s] Already ingested, skipping", store)
            results[store] = "SKIPPED"
            continue

        docs = load_store_products(store)
        if not docs:
            results[store] = "NO_DATA"
            continue

        log.info("[%s] Ingesting %d products...", store, len(docs))

        total_batches = (len(docs) + BATCH_SIZE - 1) // BATCH_SIZE
        store_ingested = 0

        for i in range(0, len(docs), BATCH_SIZE):
            batch = docs[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1

            success = ingest_batch_with_retry(vs, batch, batch_num, total_batches, store)
            if success:
                store_ingested += len(batch)

            # Pause between batches
            if i + BATCH_SIZE < len(docs):
                time.sleep(3)

        results[store] = store_ingested
        total_ingested += store_ingested
        log.info("[%s] DONE: %d products ingested", store, store_ingested)

    # Final count
    final_count = vs._collection.count()

    log.info("=" * 60)
    log.info("  RESUMEN")
    log.info("=" * 60)
    for store, count in results.items():
        log.info("  %s: %s", store, count)
    log.info("  ---")
    log.info("  Total ingested this run: %d", total_ingested)
    log.info("  Collection total: %d docs", final_count)
    log.info("=" * 60)

    # Restart Cortex to pick up new embeddings
    log.info("Restarting odi-cortex-query...")
    os.system("systemctl restart odi-cortex-query")
    time.sleep(5)

    # Verify with test queries
    log.info("Verifying with test queries...")
    tests = [
        "filtro de aceite honda cb 190",
        "kit de arrastre pulsar 200",
        "llanta 110-70-13",
        "pastillas de freno bajaj discover",
    ]
    for query in tests:
        results_q = vs.similarity_search(query, k=3)
        log.info("  Q: '%s'", query)
        for r in results_q:
            log.info("    -> [%s] %s", r.metadata.get("store", r.metadata.get("vendor", "?")), r.page_content[:80])

    log.info("DONE. Todas las tiendas ingested en odi_ind_motos.")


if __name__ == "__main__":
    main()
