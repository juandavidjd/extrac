#!/usr/bin/env python3
"""
Activar productos Shopify: draft → active en todas las tiendas ODI
+ Subir YOKOMAR (0 productos en Shopify, 1000 en JSON)

Usa Shopify Admin REST API 2024-01
"""

import os
import sys
import json
import time
import requests
import logging
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

API_VERSION = "2024-01"
JSON_PATH = "/opt/odi/data/orden_maestra_v6"

# Stores that need draft→active activation
ACTIVATE_STORES = ["DUNA", "IMBRA", "JAPAN", "LEO", "STORE", "VAISAND"]

# Stores that need full upload (0 products in Shopify)
UPLOAD_STORES = ["YOKOMAR"]


def get_creds(store):
    shop = os.getenv(f"{store}_SHOP", "")
    token = os.getenv(f"{store}_TOKEN", "")
    return shop, token


def api_call(shop, token, method, endpoint, data=None):
    url = f"https://{shop}/admin/api/{API_VERSION}/{endpoint}"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    for attempt in range(5):
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                r = requests.post(url, headers=headers, json=data, timeout=60)
            elif method == "PUT":
                r = requests.put(url, headers=headers, json=data, timeout=30)
            else:
                return None
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", 2))
                log.warning("  Rate limited, waiting %.1fs (attempt %d/5)", wait, attempt + 1)
                time.sleep(wait)
                continue
            return r
        except Exception as e:
            if attempt < 4:
                time.sleep(2)
            else:
                log.error("  API call failed after 5 attempts: %s", e)
    return None


def get_all_draft_ids(shop, token):
    """Fetch all draft product IDs (paginated)."""
    ids = []
    url_params = "status=draft&limit=250&fields=id"
    while True:
        r = api_call(shop, token, "GET", f"products.json?{url_params}")
        if not r or r.status_code != 200:
            break
        products = r.json().get("products", [])
        if not products:
            break
        ids.extend([p["id"] for p in products])

        # Check for pagination via Link header
        link = r.headers.get("Link", "")
        if 'rel="next"' in link:
            # Extract next page URL
            next_url = link.split("<")[1].split(">")[0]
            # Extract page_info param
            if "page_info=" in next_url:
                page_info = next_url.split("page_info=")[1].split("&")[0]
                url_params = f"limit=250&fields=id&page_info={page_info}"
            else:
                break
        else:
            break
        time.sleep(0.3)
    return ids


def activate_drafts(store, shop, token):
    """Set all draft products to active."""
    log.info("[%s] Fetching draft product IDs...", store)
    draft_ids = get_all_draft_ids(shop, token)
    total = len(draft_ids)
    log.info("[%s] Found %d draft products to activate", store, total)

    if total == 0:
        return 0, 0

    activated = 0
    errors = 0
    for i, pid in enumerate(draft_ids):
        r = api_call(shop, token, "PUT", f"products/{pid}.json", {
            "product": {"id": pid, "status": "active"}
        })
        if r and r.status_code == 200:
            activated += 1
        else:
            errors += 1
            status = r.status_code if r else "NO_RESPONSE"
            log.warning("  Failed to activate %d: %s", pid, status)

        if (i + 1) % 50 == 0:
            log.info("  [%s] Progress: %d/%d activated", store, activated, total)
        time.sleep(0.25)

    log.info("[%s] Done: %d activated, %d errors", store, activated, errors)
    return activated, errors


def upload_products(store, shop, token):
    """Upload products from JSON file."""
    json_file = f"{JSON_PATH}/{store}_products.json"
    if not os.path.exists(json_file):
        log.error("[%s] JSON not found: %s", store, json_file)
        return 0, 0

    with open(json_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    total = len(products)
    log.info("[%s] Uploading %d products from JSON...", store, total)

    uploaded = 0
    errors = 0
    for i, p in enumerate(products):
        title = p.get("title", "Sin titulo")
        price = p.get("price", 0) or 0
        sku = p.get("sku", "")

        images = []
        for img in p.get("images", []):
            if isinstance(img, dict) and img.get("src"):
                images.append({"src": img["src"]})
            elif isinstance(img, str) and img.startswith("http"):
                images.append({"src": img})

        product_data = {
            "product": {
                "title": title,
                "status": "active",
                "variants": [{
                    "sku": sku,
                    "price": str(price),
                    "inventory_management": "shopify",
                    "inventory_quantity": 10,
                }],
            }
        }
        if images:
            product_data["product"]["images"] = images

        r = api_call(shop, token, "POST", "products.json", product_data)
        if r and r.status_code == 201:
            uploaded += 1
        else:
            errors += 1
            status = r.status_code if r else "NO_RESPONSE"
            if errors <= 5:
                log.warning("  Failed to upload '%s': %s", title[:40], status)

        if (i + 1) % 100 == 0:
            log.info("  [%s] Progress: %d/%d (%d ok, %d err)", store, i + 1, total, uploaded, errors)
        time.sleep(0.25)

    log.info("[%s] Done: %d uploaded, %d errors", store, uploaded, errors)
    return uploaded, errors


def main():
    log.info("=" * 60)
    log.info("  ACTIVAR TODAS LAS TIENDAS SHOPIFY")
    log.info("=" * 60)

    results = []

    # Phase 1: Activate drafts
    log.info("\n--- FASE 1: Activar drafts (draft → active) ---")
    for store in ACTIVATE_STORES:
        shop, token = get_creds(store)
        if not shop or not token:
            log.error("[%s] No credentials found", store)
            results.append({"store": store, "action": "activate", "status": "NO_CREDS"})
            continue
        activated, errors = activate_drafts(store, shop, token)
        results.append({
            "store": store, "action": "activate",
            "activated": activated, "errors": errors
        })

    # Phase 2: Upload missing stores
    log.info("\n--- FASE 2: Subir tiendas vacías ---")
    for store in UPLOAD_STORES:
        shop, token = get_creds(store)
        if not shop or not token:
            log.error("[%s] No credentials found", store)
            results.append({"store": store, "action": "upload", "status": "NO_CREDS"})
            continue
        uploaded, errors = upload_products(store, shop, token)
        results.append({
            "store": store, "action": "upload",
            "uploaded": uploaded, "errors": errors
        })

    # Summary
    log.info("\n" + "=" * 60)
    log.info("  RESUMEN FINAL")
    log.info("=" * 60)
    for r in results:
        if "status" in r and r["status"] == "NO_CREDS":
            log.info("  %s: NO CREDS", r["store"])
        elif r["action"] == "activate":
            log.info("  %s: %d activados, %d errores", r["store"], r["activated"], r["errors"])
        elif r["action"] == "upload":
            log.info("  %s: %d subidos, %d errores", r["store"], r["uploaded"], r["errors"])

    log.info("=" * 60)
    log.info("  DONE")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
