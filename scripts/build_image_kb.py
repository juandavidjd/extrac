#!/usr/bin/env python3
"""
Build Image Knowledge Base v1.0
Crea indice de hashes perceptuales para todas las imagenes del ecosistema ODI.
"""
import os, sys, json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import imagehash
    from PIL import Image
except ImportError:
    print("ERROR: pip install imagehash pillow")
    sys.exit(1)

DATA_DIR = Path("/opt/odi/data")
ORDEN_MAESTRA = DATA_DIR / "orden_maestra_v6"
KB_OUTPUT = DATA_DIR / "image_kb"
KB_FILE = KB_OUTPUT / "image_hashes.json"

STORES = ["DFG","ARMOTOS","OH_IMPORTACIONES","DUNA","IMBRA","YOKOMAR",
          "JAPAN","BARA","MCLMOTOS","CBI","VITTON","KAIQI","LEO","STORE","VAISAND"]

def compute_hashes(image_path):
    """Calcula hashes perceptuales para una imagen local"""
    try:
        img = Image.open(image_path)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return {
            "phash": str(imagehash.phash(img)),
            "dhash": str(imagehash.dhash(img)),
            "ahash": str(imagehash.average_hash(img)),
        }
    except:
        return None

def load_products():
    """Carga productos con imagenes de orden_maestra_v6"""
    products = []
    for store in STORES:
        json_file = ORDEN_MAESTRA / f"{store}_products.json"
        if not json_file.exists():
            continue
        try:
            with open(json_file) as f:
                data = json.load(f)
            items = data if isinstance(data, list) else data.get("products", [])
            for p in items:
                img = p.get("image") or ""
                if img and img.startswith("/"):
                    products.append({
                        "store": store,
                        "sku": p.get("sku", ""),
                        "title": p.get("title", ""),
                        "image_path": img,
                        "price": p.get("price", 0)
                    })
        except Exception as e:
            print(f"  Error {store}: {e}")
    return products

def build_kb(max_workers=8, limit=None):
    """Construye el KB"""
    print("=" * 60)
    print("BUILD IMAGE KB v1.0")
    print("=" * 60)
    
    print("[1/2] Cargando productos...")
    products = load_products()
    print(f"      {len(products)} productos con imagen")
    
    KB_OUTPUT.mkdir(parents=True, exist_ok=True)
    
    if limit:
        products = products[:limit]
    
    print(f"\n[2/2] Calculando hashes ({len(products)} imagenes)...")
    entries = []
    ok = failed = 0
    
    def process(p):
        h = compute_hashes(p["image_path"])
        if h:
            return {**p, "hashes": h}
        return None
    
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(process, p): p for p in products}
        for f in as_completed(futures):
            r = f.result()
            if r:
                entries.append(r)
                ok += 1
            else:
                failed += 1
            total = ok + failed
            if total % 500 == 0:
                print(f"      {total}/{len(products)} ({ok} ok, {failed} failed)")
    
    print(f"      Completado: {ok} ok, {failed} failed")
    
    # Stats por tienda
    by_store = {}
    for e in entries:
        s = e["store"]
        by_store[s] = by_store.get(s, 0) + 1
    
    kb = {
        "version": "1.0",
        "created": datetime.now().isoformat(),
        "stats": {"total": len(entries), "by_store": by_store},
        "entries": entries
    }
    
    with open(KB_FILE, "w") as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Total:  {len(entries)}")
    for s in sorted(by_store.keys()):
        print(f"  {s:20} {by_store[s]:5}")
    print(f"\nOutput: {KB_FILE}")

def show_stats():
    if not KB_FILE.exists():
        print("KB no existe")
        return
    with open(KB_FILE) as f:
        kb = json.load(f)
    print("IMAGE KB STATS")
    print(f"Total: {kb[stats][total]}")
    for s, c in kb[stats][by_store].items():
        print(f"  {s}: {c}")

if __name__ == "__main__":
    if "--stats" in sys.argv:
        show_stats()
    elif "--test" in sys.argv:
        build_kb(limit=100)
    else:
        build_kb()
