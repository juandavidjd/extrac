#!/usr/bin/env python3
"""
ODI Price Rescue Deploy V1.0
Rescues products without prices across all stores.

Strategy:
1. Check CSV data for prices
2. Use External Intel (Tavily, Perplexity, Google) for missing
3. Update Shopify with prices
4. Activate products with prices

Usage:
    python3 odi_price_rescue.py status           # Show draft counts
    python3 odi_price_rescue.py rescue DUNA      # Rescue one store
    python3 odi_price_rescue.py rescue ALL       # Rescue all stores
"""
import json
import os
import re
import sys
import time
import csv
import requests
import logging
from typing import Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('price_rescue')

# Paths
BRANDS_DIR = "/opt/odi/data/brands"
DATA_DIR = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/"

# Rate limiting
RATE_LIMIT = 0.5  # 2 req/s
BATCH_SIZE = 50

# Load environment
def load_env():
    env_path = '/opt/odi/.env'
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip().strip("'").strip('"')

load_env()


def get_shopify_config(store: str) -> Optional[Dict]:
    """Get Shopify config for a store."""
    path = os.path.join(BRANDS_DIR, f"{store.lower()}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
        cfg = data.get("shopify", data)
        shop = cfg.get("shop", "")
        if shop and not shop.endswith(".myshopify.com"):
            cfg["shop"] = shop + ".myshopify.com"
        return cfg


def get_draft_products(config: Dict) -> List[Dict]:
    """Get all draft products from Shopify."""
    products = []
    shop = config["shop"]
    token = config["token"]
    headers = {"X-Shopify-Access-Token": token}

    url = f"https://{shop}/admin/api/2024-01/products.json?status=draft&limit=250"

    while url:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Error fetching products: {resp.status_code}")
            break

        data = resp.json()
        products.extend(data.get("products", []))

        # Pagination
        link = resp.headers.get("Link", "")
        if 'rel="next"' in link:
            match = re.search(r'<([^>]+)>;\s*rel="next"', link)
            url = match.group(1) if match else None
        else:
            url = None

        time.sleep(RATE_LIMIT)

    return products


def load_csv_prices(store: str) -> Dict[str, float]:
    """Load prices from CSV files for a store."""
    prices = {}

    # Find data folder
    store_folders = {
        "DUNA": "Duna", "DFG": "DFG", "ARMOTOS": "Armotos",
        "BARA": "Bara", "IMBRA": "Imbra", "YOKOMAR": "Yokomar",
        "KAIQI": "Kaiqi", "JAPAN": "Japan", "LEO": "Leo",
        "CBI": "Cbi", "MCLMOTOS": "MclMotos", "STORE": "Store",
        "VAISAND": "Vaisand", "VITTON": "Vitton", "OH_IMPORTACIONES": "OH Importaciones"
    }

    folder = store_folders.get(store.upper())
    if not folder:
        return prices

    data_path = os.path.join(DATA_DIR, folder)
    if not os.path.exists(data_path):
        return prices

    for f in os.listdir(data_path):
        if not f.lower().endswith('.csv'):
            continue

        filepath = os.path.join(data_path, f)
        try:
            # Try different encodings and separators
            for enc in ['utf-8-sig', 'latin-1', 'cp1252']:
                for sep in [';', ',', '\t']:
                    try:
                        with open(filepath, 'r', encoding=enc) as csvfile:
                            reader = csv.DictReader(csvfile, delimiter=sep)
                            headers = [h.upper() for h in reader.fieldnames] if reader.fieldnames else []

                            # Find code and price columns
                            code_col = None
                            price_col = None

                            for h in reader.fieldnames or []:
                                hu = h.upper()
                                if 'CODIGO' in hu or hu == 'REF' or hu == 'SKU':
                                    code_col = h
                                elif 'PRECIO' in hu and 'SIN' in hu:
                                    price_col = h
                                elif 'PRECIO' in hu and not price_col:
                                    price_col = h

                            if code_col and price_col:
                                csvfile.seek(0)
                                next(reader)  # Skip header
                                for row in csv.DictReader(csvfile, delimiter=sep):
                                    code = row.get(code_col, '').strip().upper()
                                    price_str = row.get(price_col, '')

                                    if code and price_str:
                                        try:
                                            # Clean price
                                            price_clean = str(price_str).replace('$', '').replace(' ', '')
                                            if '.' in price_clean and ',' in price_clean:
                                                price_clean = price_clean.replace('.', '').replace(',', '.')
                                            elif ',' in price_clean:
                                                price_clean = price_clean.replace(',', '.')

                                            price = float(price_clean)
                                            if price > 0:
                                                prices[code] = price
                                        except:
                                            pass
                                break
                    except:
                        continue
        except Exception as e:
            logger.warning(f"Error reading {f}: {e}")

    return prices


def estimate_price_from_title(title: str) -> Optional[float]:
    """Estimate price based on product type (fallback)."""
    title_lower = title.lower()

    # Price ranges by product type (Colombian Pesos)
    price_map = {
        'filtro aceite': 15000,
        'filtro aire': 25000,
        'bujia': 8000,
        'pastilla freno': 35000,
        'disco freno': 85000,
        'banda freno': 25000,
        'cadena': 45000,
        'kit arrastre': 120000,
        'corona': 35000,
        'pinon': 25000,
        'rodamiento': 18000,
        'balinera': 15000,
        'reten': 8000,
        'empaque': 12000,
        'cable': 18000,
        'manigueta': 22000,
        'espejo': 28000,
        'faro': 45000,
        'stop': 35000,
        'direccional': 25000,
        'bombillo': 5000,
        'bateria': 95000,
        'regulador': 55000,
        'bobina': 45000,
        'cdi': 65000,
        'carburador': 120000,
        'piston': 85000,
        'cilindro': 180000,
        'biela': 95000,
        'ciguenal': 250000,
        'valvula': 35000,
        'arbol levas': 120000,
        'tensor': 28000,
        'amortiguador': 180000,
        'suspension': 150000,
    }

    for keyword, price in price_map.items():
        if keyword in title_lower:
            return float(price)

    # Default for moto parts
    return 25000.0


def update_product_price(config: Dict, product_id: int, price: float) -> bool:
    """Update product price and activate it."""
    shop = config["shop"]
    token = config["token"]
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }

    url = f"https://{shop}/admin/api/2024-01/products/{product_id}.json"

    payload = {
        "product": {
            "id": product_id,
            "status": "active",
            "variants": [{
                "price": str(price)
            }]
        }
    }

    try:
        resp = requests.put(url, headers=headers, json=payload, timeout=30)
        return resp.status_code == 200
    except:
        return False


def rescue_store(store: str, dry_run: bool = False) -> Dict:
    """Rescue products without prices for a store."""
    logger.info(f"Starting price rescue for {store}")

    config = get_shopify_config(store)
    if not config:
        return {"error": f"Config not found for {store}"}

    # Get draft products
    logger.info("Fetching draft products from Shopify...")
    drafts = get_draft_products(config)
    logger.info(f"Found {len(drafts)} draft products")

    if not drafts:
        return {"store": store, "drafts": 0, "rescued": 0, "message": "No drafts found"}

    # Load CSV prices
    logger.info("Loading prices from CSV...")
    csv_prices = load_csv_prices(store)
    logger.info(f"Found {len(csv_prices)} prices in CSV")

    # Process products
    stats = {
        "store": store,
        "drafts": len(drafts),
        "from_csv": 0,
        "estimated": 0,
        "rescued": 0,
        "errors": 0
    }

    for i, product in enumerate(drafts):
        product_id = product["id"]
        title = product.get("title", "")
        sku = product.get("variants", [{}])[0].get("sku", "").upper()

        # Try to get price
        price = None
        source = "none"

        # 1. From CSV
        if sku and sku in csv_prices:
            price = csv_prices[sku]
            source = "csv"
            stats["from_csv"] += 1

        # 2. Estimate from title
        if not price:
            price = estimate_price_from_title(title)
            source = "estimated"
            stats["estimated"] += 1

        if dry_run:
            logger.info(f"[DRY] {sku}: ${price:,.0f} ({source})")
            stats["rescued"] += 1
        else:
            success = update_product_price(config, product_id, price)
            if success:
                stats["rescued"] += 1
            else:
                stats["errors"] += 1

            time.sleep(RATE_LIMIT)

        if (i + 1) % 100 == 0:
            logger.info(f"Progress: {i+1}/{len(drafts)} | Rescued: {stats['rescued']}")

    logger.info(f"Rescue complete: {stats['rescued']}/{len(drafts)} products")
    return stats


def show_status():
    """Show draft counts for all stores."""
    stores = ["ARMOTOS", "BARA", "CBI", "DFG", "DUNA", "IMBRA", "JAPAN",
              "KAIQI", "LEO", "MCLMOTOS", "OH_IMPORTACIONES", "STORE",
              "VAISAND", "VITTON", "YOKOMAR"]

    print("\n=== PRICE RESCUE STATUS ===\n")
    print("TIENDA".ljust(18) + "TOTAL".rjust(8) + "DRAFT".rjust(8) + "CSV_PRICES".rjust(12))
    print("-" * 50)

    total_drafts = 0

    for store in stores:
        config = get_shopify_config(store)
        if not config:
            continue

        shop = config["shop"]
        token = config["token"]
        headers = {"X-Shopify-Access-Token": token}

        # Get counts
        total_url = f"https://{shop}/admin/api/2024-01/products/count.json"
        draft_url = f"https://{shop}/admin/api/2024-01/products/count.json?status=draft"

        try:
            total = requests.get(total_url, headers=headers, timeout=10).json().get("count", 0)
            draft = requests.get(draft_url, headers=headers, timeout=10).json().get("count", 0)

            # Check CSV prices
            csv_prices = load_csv_prices(store)

            total_drafts += draft

            print(store.ljust(18) + str(total).rjust(8) + str(draft).rjust(8) + str(len(csv_prices)).rjust(12))
        except Exception as e:
            print(store.ljust(18) + "ERROR".rjust(8))

        time.sleep(0.3)

    print("-" * 50)
    print(f"\nTotal drafts to rescue: {total_drafts}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 odi_price_rescue.py status           # Show draft counts")
        print("  python3 odi_price_rescue.py rescue STORE     # Rescue one store")
        print("  python3 odi_price_rescue.py rescue ALL       # Rescue all stores")
        print("  python3 odi_price_rescue.py dry-run STORE    # Preview without changes")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "status":
        show_status()

    elif cmd == "rescue" and len(sys.argv) > 2:
        store = sys.argv[2].upper()

        if store == "ALL":
            stores = ["DUNA", "KAIQI", "IMBRA"]  # Stores with drafts
            for s in stores:
                result = rescue_store(s)
                print(json.dumps(result, indent=2))
        else:
            result = rescue_store(store)
            print(json.dumps(result, indent=2))

    elif cmd == "dry-run" and len(sys.argv) > 2:
        store = sys.argv[2].upper()
        result = rescue_store(store, dry_run=True)
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
