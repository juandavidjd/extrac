#!/usr/bin/env python3
"""Activate all draft products across remaining Shopify stores."""

import os
import requests
import time
import logging
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

API = "2024-01"
STORES = ["DUNA", "JAPAN", "LEO", "STORE", "VAISAND"]


def activate_all_drafts(store, shop, token):
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    activated = 0
    page = 0

    while True:
        page += 1
        url = f"https://{shop}/admin/api/{API}/products.json?status=draft&limit=250&fields=id"

        for attempt in range(5):
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", 2))
                log.warning("  Rate limited on GET, waiting %.1fs", wait)
                time.sleep(wait)
                continue
            break

        if r.status_code != 200:
            log.error("  GET error: %d", r.status_code)
            break

        products = r.json().get("products", [])
        if not products:
            break

        log.info("  [%s] Page %d: %d drafts to activate...", store, page, len(products))

        for p in products:
            pid = p["id"]
            for attempt in range(5):
                pr = requests.put(
                    f"https://{shop}/admin/api/{API}/products/{pid}.json",
                    headers=headers,
                    json={"product": {"id": pid, "status": "active"}},
                    timeout=30,
                )
                if pr.status_code == 429:
                    wait = float(pr.headers.get("Retry-After", 2))
                    log.warning("  Rate limited on PUT, waiting %.1fs", wait)
                    time.sleep(wait)
                    continue
                if pr.status_code == 200:
                    activated += 1
                    break
                else:
                    log.warning("  PUT error %d for product %d", pr.status_code, pid)
                    break
            time.sleep(0.3)

        log.info("  [%s] Running total: %d activated", store, activated)

    return activated


def main():
    log.info("=" * 60)
    log.info("  ACTIVAR DRAFTS → ACTIVE")
    log.info("=" * 60)

    results = {}
    for store in STORES:
        shop = os.getenv(f"{store}_SHOP", "")
        token = os.getenv(f"{store}_TOKEN", "")
        if not shop or not token:
            log.error("[%s] No credentials", store)
            results[store] = "NO_CREDS"
            continue

        headers = {"X-Shopify-Access-Token": token}
        draft = requests.get(
            f"https://{shop}/admin/api/{API}/products/count.json?status=draft",
            headers=headers, timeout=10
        ).json().get("count", 0)

        log.info("[%s] %d drafts in %s", store, draft, shop)
        if draft == 0:
            log.info("[%s] Nothing to activate", store)
            results[store] = 0
            continue

        n = activate_all_drafts(store, shop, token)
        results[store] = n
        log.info("[%s] DONE: %d activated", store, n)

    log.info("=" * 60)
    log.info("  RESUMEN")
    log.info("=" * 60)
    for store, count in results.items():
        log.info("  %s: %s", store, count)
    log.info("DONE")


if __name__ == "__main__":
    main()
