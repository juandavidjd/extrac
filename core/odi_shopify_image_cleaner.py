#!/usr/bin/env python3
"""
ODI V24.1 - Shopify Image Cleaner
Elimina todas las imagenes de productos activos.
Generico para cualquier tienda con imagenes basura.
"""
import json
import requests
import time
from pathlib import Path

# V25: Middleware
try:
    import sys
    sys.path.insert(0, "/opt/odi/core")
    from odi_organismo_middleware import get_middleware
    _MW = get_middleware()
except:
    _MW = None
BRANDS_DIR = Path("/opt/odi/data/brands")


def load_brand_config(empresa: str):
    path = BRANDS_DIR / f"{empresa.lower()}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def clean_all_images(empresa: str, domain: str = None, token: str = None, dry_run: bool = True):
    # V25 Middleware PRE
    if _MW:
        pre = _MW.pre_operacion({"operacion": "image_clean", "empresa": empresa, "tipo": "image_clean"})
        if not pre.get("permitido", True):
            return {"blocked": True, "reason": pre.get("motivo")}
    """Elimina todas las imagenes de productos activos."""
    config = load_brand_config(empresa)
    shop_config = config.get("shopify", {})
    shop = domain or shop_config.get("shop")
    token = token or shop_config.get("token")

    if not shop or not token:
        print("[ERROR] Missing credentials")
        return {"error": "missing_credentials"}

    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"

    headers = {"X-Shopify-Access-Token": token}
    
    # Get all products with images
    products = []
    url = f"https://{shop}/admin/api/2024-10/products.json"
    params = {"status": "active", "fields": "id,title,images", "limit": 250}
    
    while url:
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=60)
            if resp.status_code != 200:
                break
            data = resp.json()
            for p in data.get("products", []):
                if p.get("images"):
                    products.append({"id": p["id"], "title": p["title"], "images": p["images"]})
            link = resp.headers.get("Link", "")
            url = None
            params = {}
            if "rel=\"next\"" in link:
                for part in link.split(","):
                    if "rel=\"next\"" in part:
                        url = part.split(";")[0].strip().strip("<>")
                        break
            time.sleep(0.3)
        except Exception as e:
            print(f"[ERROR] {e}")
            break

    total_images = sum(len(p["images"]) for p in products)
    print(f"[CLEAN] {empresa}: {len(products)} productos con {total_images} imagenes")

    if dry_run:
        print("[DRY RUN] No se eliminaron imagenes")
        return {"products": len(products), "images": total_images, "deleted": 0, "dry_run": True}

    deleted = 0
    for p in products:
        product_id = p["id"]
        for img in p["images"]:
            image_id = img["id"]
            try:
                del_url = f"https://{shop}/admin/api/2024-10/products/{product_id}/images/{image_id}.json"
                resp = requests.delete(del_url, headers=headers, timeout=30)
                if resp.status_code == 200:
                    deleted += 1
                time.sleep(0.3)
            except:
                pass
        print(f"  [{p['id']}] {len(p['images'])} imagenes eliminadas")

    print(f"\n[COMPLETE] Deleted: {deleted} imagenes")
    return {"products": len(products), "images": total_images, "deleted": deleted}


def main():
    import sys
    if len(sys.argv) < 2:
        print("Uso: python odi_shopify_image_cleaner.py <EMPRESA> [--clean | --dry-run]")
        sys.exit(1)
    empresa = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--dry-run"
    dry_run = mode != "--clean"
    clean_all_images(empresa, dry_run=dry_run)


if __name__ == "__main__":
    main()
