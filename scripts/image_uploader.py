#!/usr/bin/env python3
"""
Fase 3B: Upload Controlado de Imagenes a Shopify
- Rate limit: 2 concurrentes, 300ms entre requests
- Skip si producto ya tiene imagen
- Log completo de resultados
"""
import os
import sys
import json
import time
import base64
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

DATA_DIR = Path("/opt/odi/data")
REPORTS_DIR = DATA_DIR / "reports"
VALIDATED_QUEUE = REPORTS_DIR / "validated_upload_queue_v2.json"
RESULTS_FILE = REPORTS_DIR / "upload_results_v1.json"

# Rate limiting
MAX_CONCURRENT = 2
REQUEST_DELAY_MS = 300

# Orden de procesamiento
UPLOAD_ORDER = ["DUNA", "BARA", "DFG", "ARMOTOS"]

# Store credentials
STORES = {
    "DFG": ("DFG_SHOP", "DFG_TOKEN"),
    "ARMOTOS": ("ARMOTOS_SHOP", "ARMOTOS_TOKEN"),
    "DUNA": ("DUNA_SHOP", "DUNA_TOKEN"),
    "BARA": ("BARA_SHOP", "BARA_TOKEN"),
}

# Thread-safe rate limiter
rate_lock = Lock()
last_request_time = 0

def rate_limit():
    """Aplica rate limiting entre requests"""
    global last_request_time
    with rate_lock:
        now = time.time()
        elapsed = (now - last_request_time) * 1000  # ms
        if elapsed < REQUEST_DELAY_MS:
            time.sleep((REQUEST_DELAY_MS - elapsed) / 1000)
        last_request_time = time.time()

def get_shopify_credentials(store):
    """Obtiene credenciales de una tienda"""
    if store not in STORES:
        return None, None
    shop_env, token_env = STORES[store]
    return os.getenv(shop_env), os.getenv(token_env)

def product_has_images(shop, token, product_id):
    """Verifica si un producto ya tiene imagenes"""
    rate_limit()
    url = f"https://{shop}/admin/api/2024-01/products/{product_id}.json"
    try:
        resp = requests.get(
            url,
            headers={"X-Shopify-Access-Token": token},
            params={"fields": "id,images"},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            images = data.get("product", {}).get("images", [])
            return len(images) > 0
        return False
    except:
        return False

def upload_image_to_product(shop, token, product_id, image_path):
    """Sube una imagen a un producto de Shopify"""
    rate_limit()

    # Leer y codificar imagen
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return {"success": False, "error": f"read_error: {e}"}

    # Determinar tipo MIME
    ext = Path(image_path).suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }
    mime = mime_types.get(ext, "image/jpeg")

    # Upload via Shopify API
    url = f"https://{shop}/admin/api/2024-01/products/{product_id}/images.json"
    payload = {
        "image": {
            "attachment": image_data,
            "filename": Path(image_path).name
        }
    }

    try:
        resp = requests.post(
            url,
            headers={
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )

        if resp.status_code in [200, 201]:
            data = resp.json()
            image_id = data.get("image", {}).get("id")
            return {"success": True, "image_id": image_id}
        else:
            return {
                "success": False,
                "error": f"http_{resp.status_code}",
                "detail": resp.text[:200]
            }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def process_upload(item, shop, token):
    """Procesa un upload individual"""
    product_id = item["product_id"]
    image_path = item["image_path"]

    # Verificar si ya tiene imagen
    if product_has_images(shop, token, product_id):
        return {
            "product_id": product_id,
            "status": "skipped",
            "reason": "already_has_image"
        }

    # Verificar que existe el archivo
    if not os.path.exists(image_path):
        return {
            "product_id": product_id,
            "status": "error",
            "reason": "file_not_found"
        }

    # Upload
    result = upload_image_to_product(shop, token, product_id, image_path)

    if result["success"]:
        return {
            "product_id": product_id,
            "status": "success",
            "image_id": result.get("image_id"),
            "image_path": image_path
        }
    else:
        return {
            "product_id": product_id,
            "status": "error",
            "reason": result.get("error"),
            "detail": result.get("detail", "")
        }

def main():
    print("=" * 70)
    print("FASE 3B: UPLOAD CONTROLADO DE IMAGENES")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Rate limit: {MAX_CONCURRENT} concurrentes, {REQUEST_DELAY_MS}ms delay")
    print(f"Orden: {' -> '.join(UPLOAD_ORDER)}")
    print()

    # Cargar queue validado
    print("[1/3] Cargando queue validado...")
    if not VALIDATED_QUEUE.exists():
        print(f"ERROR: {VALIDATED_QUEUE} no existe")
        sys.exit(1)

    with open(VALIDATED_QUEUE) as f:
        all_items = json.load(f)
    print(f"      {len(all_items)} items en queue")

    # Dividir por tienda
    by_store = {}
    for item in all_items:
        store = item["store"]
        if store not in by_store:
            by_store[store] = []
        by_store[store].append(item)

    print("\n      Por tienda:")
    for store in UPLOAD_ORDER:
        count = len(by_store.get(store, []))
        print(f"        {store}: {count}")

    # Procesar en orden
    print("\n[2/3] Ejecutando uploads...")
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "max_concurrent": MAX_CONCURRENT,
            "delay_ms": REQUEST_DELAY_MS
        },
        "summary": {},
        "details": []
    }

    total_success = 0
    total_error = 0
    total_skipped = 0

    for store in UPLOAD_ORDER:
        items = by_store.get(store, [])
        if not items:
            print(f"\n  [{store}] Sin items, saltando...")
            continue

        shop, token = get_shopify_credentials(store)
        if not shop or not token:
            print(f"\n  [{store}] Sin credenciales, saltando...")
            continue

        print(f"\n  [{store}] Procesando {len(items)} items...")

        store_results = {
            "success": 0,
            "error": 0,
            "skipped": 0,
            "items": []
        }

        processed = 0

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
            futures = {
                executor.submit(process_upload, item, shop, token): item
                for item in items
            }

            for future in as_completed(futures):
                result = future.result()
                store_results["items"].append(result)

                if result["status"] == "success":
                    store_results["success"] += 1
                    total_success += 1
                elif result["status"] == "skipped":
                    store_results["skipped"] += 1
                    total_skipped += 1
                else:
                    store_results["error"] += 1
                    total_error += 1

                processed += 1
                if processed % 50 == 0:
                    print(f"      Progreso: {processed}/{len(items)} "
                          f"(OK:{store_results['success']} Skip:{store_results['skipped']} Err:{store_results['error']})")

        print(f"      Completado: OK:{store_results['success']} "
              f"Skip:{store_results['skipped']} Err:{store_results['error']}")

        all_results["summary"][store] = {
            "total": len(items),
            "success": store_results["success"],
            "skipped": store_results["skipped"],
            "error": store_results["error"]
        }
        all_results["details"].extend(store_results["items"])

    # Guardar resultados
    print("\n[3/3] Guardando resultados...")

    all_results["totals"] = {
        "processed": total_success + total_error + total_skipped,
        "success": total_success,
        "skipped": total_skipped,
        "error": total_error
    }

    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # Reporte final
    print()
    print("=" * 70)
    print("REPORTE FINAL")
    print("=" * 70)
    print(f"Total procesados:    {total_success + total_error + total_skipped}")
    print(f"Exitosos:            {total_success}")
    print(f"Saltados (ya tiene): {total_skipped}")
    print(f"Errores:             {total_error}")
    print()

    print("Por tienda:")
    print(f"{'Tienda':15} {'Total':>8} {'OK':>8} {'Skip':>8} {'Err':>8} {'%OK':>8}")
    print("-" * 60)
    for store in UPLOAD_ORDER:
        if store in all_results["summary"]:
            s = all_results["summary"][store]
            pct = (s["success"] / s["total"] * 100) if s["total"] > 0 else 0
            print(f"{store:15} {s['total']:>8} {s['success']:>8} {s['skipped']:>8} {s['error']:>8} {pct:>7.1f}%")

    print()
    print(f"Resultados guardados en: {RESULTS_FILE}")
    print("=" * 70)

    # Mostrar errores si hay
    errors = [r for r in all_results["details"] if r["status"] == "error"]
    if errors:
        print(f"\nPrimeros 10 errores:")
        for e in errors[:10]:
            print(f"  Product {e['product_id']}: {e.get('reason', 'unknown')}")

if __name__ == "__main__":
    main()
