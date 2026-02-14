#!/usr/bin/env python3
"""
ODI Inventory Audit P1 — Shopify Store Scanner (READ-ONLY)
==========================================================
Escanea productos via Shopify GraphQL Admin API.
Calcula NAV (Net Asset Value) de inventario en draft.
Genera reporte de calidad y redflags.

Modo: ESTRICTAMENTE READ-ONLY. No modifica nada en Shopify.

Uso:
    python3 inventory_audit_p1.py --store MCLMOTOS
    python3 inventory_audit_p1.py --store BARA
    python3 inventory_audit_p1.py --store ALL

Versión: 1.0.0 — 14 Feb 2026
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("odi.audit.p1")

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

REPORTS_DIR = Path("/opt/odi/data/reports")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")

# Known store env var patterns: {NAME}_SHOP, {NAME}_TOKEN
# Auto-detected from /opt/odi/config/.env
KNOWN_STORES = [
    "BARA", "YOKOMAR", "KAIQI", "DFG", "DUNA", "IMBRA",
    "JAPAN", "LEO", "STORE", "VAISAND", "ARMOTOS", "VITTON",
    "CBI", "MCLMOTOS", "OH",
]

GRAPHQL_QUERY = """
query ($cursor: String) {
  products(first: 50, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        title
        status
        productType
        vendor
        tags
        images(first: 1) {
          edges {
            node {
              url
            }
          }
        }
        variants(first: 100) {
          edges {
            node {
              id
              sku
              price
              inventoryQuantity
              title
            }
          }
        }
      }
    }
  }
}
"""


# ══════════════════════════════════════════════════════════════════════════════
# STORE DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def detect_store_credentials(store_name: str) -> tuple:
    """
    Detect Shopify store domain and token from environment variables.
    Tries: {NAME}_SHOP / {NAME}_TOKEN, then SHOPIFY_STORE_{NAME} / SHOPIFY_TOKEN_{NAME}.
    Returns (domain, token) or raises ValueError.
    """
    name = store_name.upper()

    # Pattern 1: NAME_SHOP / NAME_TOKEN
    domain = os.getenv(f"{name}_SHOP")
    token = os.getenv(f"{name}_TOKEN")

    if domain and token:
        log.info("Credentials found: %s_SHOP / %s_TOKEN", name, name)
        return domain, token

    # Pattern 2: SHOPIFY_STORE_NAME / SHOPIFY_TOKEN_NAME
    domain = os.getenv(f"SHOPIFY_STORE_{name}")
    token = os.getenv(f"SHOPIFY_TOKEN_{name}")

    if domain and token:
        log.info("Credentials found: SHOPIFY_STORE_%s / SHOPIFY_TOKEN_%s", name, name)
        return domain, token

    raise ValueError(
        f"No credentials found for store '{name}'. "
        f"Expected env vars: {name}_SHOP + {name}_TOKEN"
    )


def list_available_stores() -> list:
    """List stores that have credentials configured."""
    available = []
    for name in KNOWN_STORES:
        try:
            detect_store_credentials(name)
            available.append(name)
        except ValueError:
            pass
    return available


# ══════════════════════════════════════════════════════════════════════════════
# SHOPIFY GRAPHQL CLIENT (READ-ONLY)
# ══════════════════════════════════════════════════════════════════════════════

def graphql_request(domain: str, token: str, query: str, variables: dict = None) -> dict:
    """Execute a GraphQL query against Shopify Admin API."""
    url = f"https://{domain}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": token,
        },
        method="POST",
    )

    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))

                # Check for throttling
                extensions = data.get("extensions", {})
                cost = extensions.get("cost", {})
                throttle = cost.get("throttleStatus", {})
                available = throttle.get("currentlyAvailable", 1000)

                if available < 100:
                    wait = max(1, (100 - available) / 50)
                    log.warning("Throttled: available=%d, waiting %.1fs", available, wait)
                    time.sleep(wait)

                if "errors" in data:
                    log.error("GraphQL errors: %s", data["errors"])
                    return data

                return data

        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** (attempt + 1)
                log.warning("Rate limited (429), backoff %ds (attempt %d/4)", wait, attempt + 1)
                time.sleep(wait)
                continue
            raise
        except urllib.error.URLError as e:
            if attempt < 3:
                wait = 2 ** (attempt + 1)
                log.warning("Network error: %s, retry in %ds", e, wait)
                time.sleep(wait)
                continue
            raise

    raise RuntimeError("Max retries exceeded for GraphQL request")


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT SCANNER
# ══════════════════════════════════════════════════════════════════════════════

def scan_store(store_name: str) -> dict:
    """
    Scan all products in a Shopify store via GraphQL cursor pagination.
    Returns audit summary dict.
    """
    domain, token = detect_store_credentials(store_name)
    log.info("Scanning store: %s (%s)", store_name, domain)

    # Counters
    total_products = 0
    total_variants = 0
    drafts = 0
    actives = 0
    archived = 0
    with_stock = 0
    with_price = 0
    with_sku = 0
    with_images = 0
    ready_for_sale = 0

    capital_draft = 0.0
    capital_activable = 0.0

    redflags = []
    cursor = None
    batch = 0

    while True:
        batch += 1
        variables = {"cursor": cursor} if cursor else {}
        result = graphql_request(domain, token, GRAPHQL_QUERY, variables)

        products_data = result.get("data", {}).get("products", {})
        edges = products_data.get("edges", [])
        page_info = products_data.get("pageInfo", {})

        if not edges:
            log.info("No more products (batch %d)", batch)
            break

        for edge in edges:
            node = edge["node"]
            total_products += 1

            product_id = node["id"]
            title = node.get("title", "")
            status = node.get("status", "UNKNOWN").upper()
            product_type = node.get("productType", "")
            vendor = node.get("vendor", "")
            has_images = len(node.get("images", {}).get("edges", [])) > 0

            if status == "DRAFT":
                drafts += 1
            elif status == "ACTIVE":
                actives += 1
            elif status == "ARCHIVED":
                archived += 1

            if has_images:
                with_images += 1

            # Process variants
            product_stock = 0
            product_max_price = 0.0
            product_has_sku = False

            for v_edge in node.get("variants", {}).get("edges", []):
                v = v_edge["node"]
                total_variants += 1

                v_price = float(v.get("price", 0) or 0)
                v_stock = int(v.get("inventoryQuantity", 0) or 0)
                v_sku = (v.get("sku") or "").strip()

                if v_price > 0:
                    product_max_price = max(product_max_price, v_price)
                if v_stock > 0:
                    product_stock += v_stock
                if v_sku:
                    product_has_sku = True

            # Aggregate counters
            if product_stock > 0:
                with_stock += 1
            if product_max_price > 0:
                with_price += 1
            if product_has_sku:
                with_sku += 1

            # Capital calculation
            product_value = product_max_price * product_stock
            if status == "DRAFT":
                capital_draft += product_value

            # Gating: ready for sale = stock>0, price>0, sku, image
            passes_gating = (
                product_stock > 0
                and product_max_price > 0
                and product_has_sku
                and has_images
            )
            if passes_gating:
                ready_for_sale += 1
                if status == "DRAFT":
                    capital_activable += product_value

            # Redflags
            if product_stock > 0 and not has_images:
                redflags.append({
                    "product_id": product_id,
                    "title": title[:80],
                    "vendor": vendor,
                    "status": status,
                    "stock": product_stock,
                    "price": product_max_price,
                    "flag": "STOCK_NO_IMAGE",
                })
            if product_stock > 0 and product_max_price <= 0:
                redflags.append({
                    "product_id": product_id,
                    "title": title[:80],
                    "vendor": vendor,
                    "status": status,
                    "stock": product_stock,
                    "price": product_max_price,
                    "flag": "STOCK_NO_PRICE",
                })
            if product_stock > 0 and not product_has_sku:
                redflags.append({
                    "product_id": product_id,
                    "title": title[:80],
                    "vendor": vendor,
                    "status": status,
                    "stock": product_stock,
                    "price": product_max_price,
                    "flag": "STOCK_NO_SKU",
                })

        log.info(
            "Batch %d: %d products scanned so far (this batch: %d)",
            batch, total_products, len(edges),
        )

        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

        # Small delay between pages to be respectful
        time.sleep(0.3)

    summary = {
        "store": store_name,
        "domain": domain,
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "api_version": SHOPIFY_API_VERSION,
        "total_products_scanned": total_products,
        "total_variants_scanned": total_variants,
        "by_status": {
            "draft": drafts,
            "active": actives,
            "archived": archived,
        },
        "quality": {
            "with_stock": with_stock,
            "with_price": with_price,
            "with_sku": with_sku,
            "with_images": with_images,
            "ready_for_sale": ready_for_sale,
        },
        "nav": {
            "capital_total_draft_cop": round(capital_draft, 2),
            "capital_activable_cop": round(capital_activable, 2),
            "currency": "COP",
        },
        "redflags_count": len(redflags),
        "redflags_by_type": {
            "STOCK_NO_IMAGE": sum(1 for r in redflags if r["flag"] == "STOCK_NO_IMAGE"),
            "STOCK_NO_PRICE": sum(1 for r in redflags if r["flag"] == "STOCK_NO_PRICE"),
            "STOCK_NO_SKU": sum(1 for r in redflags if r["flag"] == "STOCK_NO_SKU"),
        },
    }

    return summary, redflags


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT
# ══════════════════════════════════════════════════════════════════════════════

def save_results(store_name: str, summary: dict, redflags: list):
    """Save audit results to JSON and CSV."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    name_lower = store_name.lower()

    # Summary JSON
    summary_path = REPORTS_DIR / f"p1_audit_summary_{name_lower}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    log.info("Summary saved: %s", summary_path)

    # Also save as the generic name for backward compat
    generic_path = REPORTS_DIR / "p1_audit_summary.json"
    with open(generic_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Redflags CSV
    csv_path = REPORTS_DIR / f"p1_quality_redflags_{name_lower}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["product_id", "title", "vendor", "status", "stock", "price", "flag"],
        )
        writer.writeheader()
        writer.writerows(redflags)
    log.info("Redflags CSV saved: %s (%d rows)", csv_path, len(redflags))

    # Generic name
    generic_csv = REPORTS_DIR / "p1_quality_redflags.csv"
    with open(generic_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["product_id", "title", "vendor", "status", "stock", "price", "flag"],
        )
        writer.writeheader()
        writer.writerows(redflags)

    return summary_path, csv_path


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ODI Inventory Audit P1 — Shopify Store Scanner (READ-ONLY)",
    )
    parser.add_argument(
        "--store",
        required=True,
        help="Store name (e.g., MCLMOTOS, BARA, ALL)",
    )
    parser.add_argument(
        "--env-file",
        default="/opt/odi/config/.env",
        help="Path to .env file (default: /opt/odi/config/.env)",
    )
    args = parser.parse_args()

    # Load .env file manually (no dependency on python-dotenv)
    env_path = Path(args.env_file)
    if env_path.exists():
        log.info("Loading env from: %s", env_path)
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Don't override existing env vars
                if key not in os.environ:
                    os.environ[key] = value
    else:
        log.warning("Env file not found: %s", env_path)

    store_name = args.store.upper()

    if store_name == "ALL":
        stores = list_available_stores()
        log.info("Scanning ALL available stores: %s", stores)
    else:
        stores = [store_name]

    for store in stores:
        log.info("=" * 60)
        log.info("AUDIT P1: %s", store)
        log.info("=" * 60)

        try:
            summary, redflags = scan_store(store)
            summary_path, csv_path = save_results(store, summary, redflags)

            # Print summary
            print()
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            print()
            log.info(
                "DONE: %s — %d products, %d ready for sale, NAV draft=%s COP, NAV activable=%s COP, %d redflags",
                store,
                summary["total_products_scanned"],
                summary["quality"]["ready_for_sale"],
                f"{summary['nav']['capital_total_draft_cop']:,.0f}",
                f"{summary['nav']['capital_activable_cop']:,.0f}",
                summary["redflags_count"],
            )
        except ValueError as e:
            log.error("SKIP %s: %s", store, e)
        except Exception as e:
            log.exception("FAIL %s: %s", store, e)


if __name__ == "__main__":
    main()
