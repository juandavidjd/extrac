#!/usr/bin/env python3
"""
Fuzzy Title Matching - Cross-Store Image Matching
Busca imagenes por similitud de titulo del producto.
"""
import os
import sys
import json
import re
import requests
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

DATA_DIR = Path("/opt/odi/data")
REPORTS_DIR = DATA_DIR / "reports"
IMAGE_KB = DATA_DIR / "image_kb/image_hashes.json"

STORES = {
    "DFG": ("DFG_SHOP", "DFG_TOKEN"),
    "ARMOTOS": ("ARMOTOS_SHOP", "ARMOTOS_TOKEN"),
    "OH_IMPORTACIONES": ("OH_IMPORTACIONES_SHOP", "OH_IMPORTACIONES_TOKEN"),
    "DUNA": ("DUNA_SHOP", "DUNA_TOKEN"),
    "IMBRA": ("IMBRA_SHOP", "IMBRA_TOKEN"),
    "YOKOMAR": ("YOKOMAR_SHOP", "YOKOMAR_TOKEN"),
    "JAPAN": ("JAPAN_SHOP", "JAPAN_TOKEN"),
    "BARA": ("BARA_SHOP", "BARA_TOKEN"),
    "MCLMOTOS": ("MCLMOTOS_SHOP", "MCLMOTOS_TOKEN"),
    "CBI": ("CBI_SHOP", "CBI_TOKEN"),
    "VITTON": ("VITTON_SHOP", "VITTON_TOKEN"),
    "KAIQI": ("KAIQI_SHOP", "KAIQI_TOKEN"),
    "LEO": ("LEO_SHOP", "LEO_TOKEN"),
    "STORE": ("STORE_SHOP", "STORE_TOKEN"),
    "VAISAND": ("VAISAND_SHOP", "VAISAND_TOKEN"),
}

# Threshold de similitud (0.0 - 1.0)
SIMILARITY_THRESHOLD = 0.65

def normalize_title(text):
    """Normaliza titulo para matching"""
    if not text:
        return ""
    text = str(text).lower()
    # Remover acentos
    replacements = {'á':'a','é':'e','í':'i','ó':'o','ú':'u','ñ':'n','ü':'u'}
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Solo alfanumericos y espacios
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    # Normalizar espacios
    text = ' '.join(text.split())
    return text

def extract_keywords(text):
    """Extrae keywords significativas"""
    normalized = normalize_title(text)
    words = normalized.split()
    stopwords = {'para', 'con', 'sin', 'los', 'las', 'del', 'por', 'que', 'una', 'uno', 'de', 'la', 'el', 'en', 'y'}
    return set(w for w in words if len(w) >= 3 and w not in stopwords)

def similarity_score(text1, text2):
    """Calcula similitud entre dos titulos"""
    norm1 = normalize_title(text1)
    norm2 = normalize_title(text2)

    if not norm1 or not norm2:
        return 0

    # Score por SequenceMatcher
    seq_score = SequenceMatcher(None, norm1, norm2).ratio()

    # Score por keywords compartidos
    kw1 = extract_keywords(text1)
    kw2 = extract_keywords(text2)
    if kw1 and kw2:
        common = kw1 & kw2
        kw_score = len(common) / max(len(kw1), len(kw2))
    else:
        kw_score = 0

    # Combinar scores
    return (seq_score * 0.4) + (kw_score * 0.6)

def get_credentials(store):
    if store not in STORES:
        return None, None
    shop_env, token_env = STORES[store]
    return os.getenv(shop_env), os.getenv(token_env)

def get_all_products(store_name):
    """Obtiene todos los productos de una tienda"""
    shop, token = get_credentials(store_name)
    if not shop or not token:
        return []

    products = []
    url = f"https://{shop}/admin/api/2024-01/products.json"
    params = {"limit": 250, "fields": "id,title,variants,images"}

    while url:
        try:
            resp = requests.get(url, headers={"X-Shopify-Access-Token": token}, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for p in data.get("products", []):
                sku = ""
                if p.get("variants"):
                    sku = p["variants"][0].get("sku", "")

                has_image = len(p.get("images", [])) > 0
                image_url = p["images"][0]["src"] if has_image else None

                products.append({
                    "id": p["id"],
                    "title": p["title"],
                    "title_normalized": normalize_title(p["title"]),
                    "keywords": extract_keywords(p["title"]),
                    "sku": sku,
                    "has_image": has_image,
                    "image_url": image_url,
                    "store": store_name
                })

            params = {}
            link = resp.headers.get("Link", "")
            if "next" in link:
                for part in link.split(","):
                    if "next" in part:
                        url = part.split(";")[0].strip().strip("<>")
                        break
            else:
                url = None
        except Exception as e:
            print(f"    Error {store_name}: {e}")
            break

    return products

def load_image_kb():
    """Carga el KB de imagenes local"""
    if not IMAGE_KB.exists():
        return []

    with open(IMAGE_KB) as f:
        kb = json.load(f)

    images = []
    for entry in kb["entries"]:
        images.append({
            "title": entry.get("title", ""),
            "title_normalized": normalize_title(entry.get("title", "")),
            "keywords": extract_keywords(entry.get("title", "")),
            "image_path": entry["image_path"],
            "store": entry["store"],
            "source": "local_kb"
        })

    return images

def find_best_match(product, image_sources, threshold=SIMILARITY_THRESHOLD):
    """Encuentra la mejor imagen para un producto"""
    best_match = None
    best_score = 0

    prod_keywords = product["keywords"]

    for img in image_sources:
        # Skip si es de la misma tienda (ya la tendria)
        if img.get("store") == product["store"]:
            continue

        # Primero filtro rapido por keywords
        img_keywords = img.get("keywords", set())
        if prod_keywords and img_keywords:
            common = prod_keywords & img_keywords
            if len(common) < 2:  # Al menos 2 keywords en comun
                continue

        # Calcular similitud completa
        score = similarity_score(product["title"], img["title"])

        if score > best_score and score >= threshold:
            best_score = score
            best_match = {
                "source_title": img["title"],
                "source_store": img["store"],
                "source_type": img.get("source", "shopify"),
                "image_url": img.get("image_url"),
                "image_path": img.get("image_path"),
                "score": score
            }

    return best_match

def main():
    print("=" * 70)
    print("FUZZY TITLE MATCHING - CROSS-STORE")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Threshold de similitud: {SIMILARITY_THRESHOLD}")
    print()

    # Paso 1: Cargar Image KB local
    print("[1/4] Cargando Image KB local...")
    kb_images = load_image_kb()
    print(f"      {len(kb_images)} imagenes en KB local")

    # Paso 2: Obtener todos los productos
    print("\n[2/4] Obteniendo productos de todas las tiendas...")
    all_products = []
    products_with_image = []
    products_without_image = []

    for store_name in STORES.keys():
        print(f"      {store_name}...", end=" ", flush=True)
        products = get_all_products(store_name)

        with_img = [p for p in products if p["has_image"]]
        without_img = [p for p in products if not p["has_image"]]

        print(f"{len(products)} ({len(with_img)} con img)")

        products_with_image.extend(with_img)
        products_without_image.extend(without_img)
        all_products.extend(products)

    print(f"\n      Total sin imagen: {len(products_without_image)}")

    # Paso 3: Crear pool de imagenes disponibles
    print("\n[3/4] Creando pool de imagenes...")

    # Combinar Shopify + KB local
    image_sources = []

    # Agregar productos de Shopify con imagen
    for p in products_with_image:
        image_sources.append({
            "title": p["title"],
            "title_normalized": p["title_normalized"],
            "keywords": p["keywords"],
            "image_url": p["image_url"],
            "store": p["store"],
            "source": "shopify"
        })

    # Agregar KB local
    image_sources.extend(kb_images)

    print(f"      {len(image_sources)} imagenes disponibles para matching")

    # Paso 4: Buscar matches
    print("\n[4/4] Buscando matches fuzzy...")
    print(f"      Procesando {len(products_without_image)} productos...")

    matches = []
    no_match = []
    processed = 0

    for product in products_without_image:
        match = find_best_match(product, image_sources)

        if match:
            matches.append({
                "target_store": product["store"],
                "target_product_id": product["id"],
                "target_title": product["title"],
                "target_sku": product["sku"],
                "source_store": match["source_store"],
                "source_title": match["source_title"],
                "source_type": match["source_type"],
                "image_url": match.get("image_url"),
                "image_path": match.get("image_path"),
                "similarity_score": round(match["score"], 3)
            })
        else:
            no_match.append({
                "store": product["store"],
                "product_id": product["id"],
                "title": product["title"]
            })

        processed += 1
        if processed % 1000 == 0:
            print(f"      Progreso: {processed}/{len(products_without_image)} ({len(matches)} matches)")

    # Guardar resultados
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(REPORTS_DIR / "fuzzy_title_matches.json", "w") as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)

    with open(REPORTS_DIR / "fuzzy_no_match.json", "w") as f:
        json.dump(no_match, f, indent=2, ensure_ascii=False)

    # Reporte
    print()
    print("=" * 70)
    print("REPORTE FINAL")
    print("=" * 70)
    print(f"Productos sin imagen:          {len(products_without_image)}")
    print(f"Matches fuzzy encontrados:     {len(matches)}")
    print(f"Sin match:                     {len(no_match)}")
    print(f"Cobertura potencial:           {len(matches) / len(products_without_image) * 100:.1f}%")
    print()

    # Por tienda
    print("Por tienda destino:")
    by_store = defaultdict(list)
    for m in matches:
        by_store[m["target_store"]].append(m)

    print(f"{'Tienda':20} {'SinImg':>8} {'Match':>8} {'%':>8} {'AvgScore':>10}")
    print("-" * 60)

    for store in sorted(STORES.keys()):
        sin_img = sum(1 for p in products_without_image if p["store"] == store)
        store_matches = by_store.get(store, [])
        match_count = len(store_matches)
        pct = (match_count / sin_img * 100) if sin_img > 0 else 0
        avg_score = sum(m["similarity_score"] for m in store_matches) / len(store_matches) if store_matches else 0

        if sin_img > 0:
            print(f"{store:20} {sin_img:>8} {match_count:>8} {pct:>7.1f}% {avg_score:>9.2f}")

    # Distribucion de scores
    print("\nDistribucion de scores de similitud:")
    score_buckets = {"0.65-0.70": 0, "0.70-0.80": 0, "0.80-0.90": 0, "0.90-1.00": 0}
    for m in matches:
        s = m["similarity_score"]
        if s < 0.70:
            score_buckets["0.65-0.70"] += 1
        elif s < 0.80:
            score_buckets["0.70-0.80"] += 1
        elif s < 0.90:
            score_buckets["0.80-0.90"] += 1
        else:
            score_buckets["0.90-1.00"] += 1

    for bucket, count in score_buckets.items():
        pct = (count / len(matches) * 100) if matches else 0
        bar = "#" * int(pct / 2)
        print(f"  {bucket}: {count:>6} ({pct:>5.1f}%) {bar}")

    # Top fuentes
    print("\nTop fuentes de imagenes:")
    by_source = defaultdict(int)
    for m in matches:
        by_source[m["source_store"]] += 1

    for store, count in sorted(by_source.items(), key=lambda x: -x[1])[:5]:
        print(f"  {store}: {count}")

    print()
    print("Archivos generados:")
    print(f"  {REPORTS_DIR / 'fuzzy_title_matches.json'}")
    print(f"  {REPORTS_DIR / 'fuzzy_no_match.json'}")
    print("=" * 70)

    # Ejemplos de matches
    print("\nEjemplos de matches (top 10 por score):")
    top_matches = sorted(matches, key=lambda x: -x["similarity_score"])[:10]
    for m in top_matches:
        print(f"  [{m['similarity_score']:.2f}] {m['target_title'][:40]}")
        print(f"         -> {m['source_title'][:40]} ({m['source_store']})")

if __name__ == "__main__":
    main()
