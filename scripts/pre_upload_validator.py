#!/usr/bin/env python3
"""
Fase 3A v2: Validacion Pre-Upload
Criterios actualizados:
- Resolucion minima: 400px ancho
- Tamano minimo: 25KB
- Deduplicacion pHash <= 5, priorizando mayor resolucion
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

try:
    import imagehash
    from PIL import Image
except ImportError:
    print("ERROR: pip install imagehash pillow")
    sys.exit(1)

DATA_DIR = Path("/opt/odi/data")
REPORTS_DIR = DATA_DIR / "reports"
IMAGE_KB = DATA_DIR / "image_kb/image_hashes.json"
SKU_MATCHES = REPORTS_DIR / "sku_exact_matches.json"

# Criterios v2
MIN_WIDTH = 400  # Reducido de 600
MIN_FILE_SIZE = 25 * 1024  # 25KB en bytes
PHASH_THRESHOLD = 5

def get_image_info(image_path):
    """Obtiene resolucion y tamano de una imagen"""
    try:
        file_size = os.path.getsize(image_path)
        with Image.open(image_path) as img:
            width, height = img.size
        return width, height, file_size
    except:
        return 0, 0, 0

def hash_distance(hash1, hash2):
    """Calcula distancia Hamming entre dos hashes"""
    try:
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2
    except:
        return 999

def main():
    print("=" * 70)
    print("FASE 3A v2: VALIDACION PRE-UPLOAD (CRITERIOS RELAJADOS)")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("Modo: READ-ONLY (no sube imagenes)")
    print()
    print(f"Criterios de validacion v2:")
    print(f"  - Resolucion minima: {MIN_WIDTH}px ancho")
    print(f"  - Tamano minimo: {MIN_FILE_SIZE // 1024}KB")
    print(f"  - Duplicados pHash: distancia <= {PHASH_THRESHOLD}")
    print(f"  - Prioridad: mayor resolucion si hay duplicados")
    print()

    # Cargar matches
    print("[1/4] Cargando matches...")
    if not SKU_MATCHES.exists():
        print(f"ERROR: {SKU_MATCHES} no existe.")
        sys.exit(1)

    with open(SKU_MATCHES) as f:
        matches = json.load(f)
    print(f"      {len(matches)} productos con match SKU")

    # Cargar KB para hashes
    print("\n[2/4] Cargando Image KB...")
    with open(IMAGE_KB) as f:
        kb = json.load(f)

    path_to_hash = {}
    for entry in kb["entries"]:
        path_to_hash[entry["image_path"]] = entry["hashes"]["phash"]
    print(f"      {len(path_to_hash)} imagenes indexadas")

    # Validar cada match
    print("\n[3/4] Validando imagenes...")

    validated = []
    rejected = []
    stats = {
        "total_matches": len(matches),
        "checked": 0,
        "valid": 0,
        "rejected_low_res": 0,
        "rejected_small_file": 0,
        "rejected_missing": 0,
        "duplicates_removed": 0
    }

    # Para deduplicacion global - phash -> mejor candidato
    # Estructura: {phash: {"entry": validated_entry, "resolution": width*height}}
    phash_best = {}

    for match in matches:
        stats["checked"] += 1

        product_id = match["product_id"]
        store = match["store"]
        title = match["title"]
        sku = match["sku"]
        image_candidates = match.get("matches", [])

        if not image_candidates:
            rejected.append({
                "product_id": product_id,
                "store": store,
                "title": title,
                "sku": sku,
                "reason": "no_candidates"
            })
            stats["rejected_missing"] += 1
            continue

        # Evaluar cada candidato - buscar el mejor
        best_candidate = None
        best_resolution = 0
        rejection_reason = None

        for candidate in image_candidates:
            img_path = candidate.get("image_path", "")

            if not img_path or not os.path.exists(img_path):
                rejection_reason = "file_not_found"
                continue

            width, height, file_size = get_image_info(img_path)

            if width < MIN_WIDTH:
                rejection_reason = f"low_resolution_{width}px"
                continue

            if file_size < MIN_FILE_SIZE:
                rejection_reason = f"small_file_{file_size // 1024}KB"
                stats["rejected_small_file"] += 1
                continue

            resolution = width * height
            if resolution > best_resolution:
                best_resolution = resolution
                best_candidate = {
                    "image_path": img_path,
                    "width": width,
                    "height": height,
                    "file_size": file_size,
                    "phash": candidate.get("phash") or path_to_hash.get(img_path, ""),
                    "source_store": candidate.get("store", "")
                }

        if not best_candidate:
            rejected.append({
                "product_id": product_id,
                "store": store,
                "title": title,
                "sku": sku,
                "reason": rejection_reason or "no_valid_candidate"
            })
            if "low_resolution" in str(rejection_reason):
                stats["rejected_low_res"] += 1
            continue

        # Crear entrada validada
        entry = {
            "product_id": product_id,
            "store": store,
            "title": title,
            "sku": sku,
            "image_path": best_candidate["image_path"],
            "width": best_candidate["width"],
            "height": best_candidate["height"],
            "file_size_kb": best_candidate["file_size"] // 1024,
            "phash": best_candidate["phash"],
            "source_store": best_candidate["source_store"]
        }

        phash = best_candidate["phash"]
        resolution = best_resolution

        # Verificar duplicados por pHash
        if phash:
            is_duplicate = False
            duplicate_key = None

            for existing_phash in list(phash_best.keys()):
                dist = hash_distance(phash, existing_phash)
                if dist <= PHASH_THRESHOLD:
                    # Encontrado duplicado
                    existing = phash_best[existing_phash]
                    if resolution > existing["resolution"]:
                        # Este es mejor - reemplazar
                        # Mover el anterior a rechazados
                        stats["duplicates_removed"] += 1
                        duplicate_key = existing_phash
                    else:
                        # El existente es mejor
                        is_duplicate = True
                        stats["duplicates_removed"] += 1
                    break

            if duplicate_key:
                del phash_best[duplicate_key]

            if not is_duplicate:
                phash_best[phash] = {"entry": entry, "resolution": resolution}
        else:
            # Sin phash, agregar directamente
            validated.append(entry)
            stats["valid"] += 1

        if stats["checked"] % 1000 == 0:
            print(f"      Progreso: {stats['checked']}/{len(matches)}")

    # Agregar todos los mejores de phash_best a validated
    for data in phash_best.values():
        validated.append(data["entry"])
        stats["valid"] += 1

    # Guardar resultados
    print("\n[4/4] Guardando resultados...")

    with open(REPORTS_DIR / "validated_upload_queue_v2.json", "w") as f:
        json.dump(validated, f, indent=2, ensure_ascii=False)

    with open(REPORTS_DIR / "rejected_low_quality_v2.json", "w") as f:
        json.dump(rejected, f, indent=2, ensure_ascii=False)

    # Reporte final
    prev_valid = 1819  # v1 result
    increment = stats["valid"] - prev_valid
    increment_pct = (increment / prev_valid * 100) if prev_valid > 0 else 0

    print()
    print("=" * 70)
    print("REPORTE FINAL v2")
    print("=" * 70)
    print(f"Total matches evaluados:       {stats['total_matches']}")
    print(f"Validados para upload:         {stats['valid']}")
    print(f"Rechazados (baja resolucion):  {stats['rejected_low_res']}")
    print(f"Rechazados (archivo pequeno):  {stats['rejected_small_file']}")
    print(f"Rechazados (imagen faltante):  {stats['rejected_missing']}")
    print(f"Duplicados removidos:          {stats['duplicates_removed']}")
    print()
    print(f"--- COMPARACION CON v1 ---")
    print(f"Validados v1:                  {prev_valid}")
    print(f"Validados v2:                  {stats['valid']}")
    print(f"Incremento:                    +{increment} ({increment_pct:+.1f}%)")
    print()

    coverage = (stats['valid'] / stats['total_matches'] * 100) if stats['total_matches'] > 0 else 0
    print(f"Tasa de validacion:            {coverage:.1f}%")
    print()
    print("Archivos generados:")
    print(f"  {REPORTS_DIR / 'validated_upload_queue_v2.json'}")
    print(f"  {REPORTS_DIR / 'rejected_low_quality_v2.json'}")
    print("=" * 70)

    # Desglose por tienda
    print("\nDesglose por tienda:")
    by_store = defaultdict(lambda: {"valid": 0, "rejected": 0})

    for v in validated:
        by_store[v["store"]]["valid"] += 1
    for r in rejected:
        by_store[r["store"]]["rejected"] += 1

    print(f"{'Tienda':20} {'Valid':>8} {'Rejected':>8} {'Pct':>8}")
    print("-" * 50)
    for store in sorted(by_store.keys()):
        v = by_store[store]["valid"]
        r = by_store[store]["rejected"]
        t = v + r
        pct = (v / t * 100) if t > 0 else 0
        print(f"{store:20} {v:>8} {r:>8} {pct:>7.1f}%")

    # Distribucion de resoluciones
    print("\nDistribucion de resoluciones validadas:")
    res_buckets = {"400-600": 0, "600-800": 0, "800-1000": 0, "1000-1500": 0, "1500+": 0}
    for v in validated:
        w = v["width"]
        if w < 600:
            res_buckets["400-600"] += 1
        elif w < 800:
            res_buckets["600-800"] += 1
        elif w < 1000:
            res_buckets["800-1000"] += 1
        elif w < 1500:
            res_buckets["1000-1500"] += 1
        else:
            res_buckets["1500+"] += 1

    for bucket, count in res_buckets.items():
        pct = (count / len(validated) * 100) if validated else 0
        bar = "#" * int(pct / 2)
        print(f"  {bucket:>10}px: {count:>5} ({pct:>5.1f}%) {bar}")

    # Distribucion de tamanos
    print("\nDistribucion de tamanos de archivo:")
    size_buckets = {"25-50KB": 0, "50-100KB": 0, "100-250KB": 0, "250-500KB": 0, "500KB+": 0}
    for v in validated:
        s = v["file_size_kb"]
        if s < 50:
            size_buckets["25-50KB"] += 1
        elif s < 100:
            size_buckets["50-100KB"] += 1
        elif s < 250:
            size_buckets["100-250KB"] += 1
        elif s < 500:
            size_buckets["250-500KB"] += 1
        else:
            size_buckets["500KB+"] += 1

    for bucket, count in size_buckets.items():
        pct = (count / len(validated) * 100) if validated else 0
        bar = "#" * int(pct / 2)
        print(f"  {bucket:>10}: {count:>5} ({pct:>5.1f}%) {bar}")

if __name__ == "__main__":
    main()
