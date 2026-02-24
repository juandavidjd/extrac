#!/usr/bin/env python3
"""
ODI IMBRA Processor
Special V19 processing for IMBRA store with long ALL CAPS titles.
Extracts product type + compatibility properly.
"""
import json
import logging
import os
import re
import time
import psycopg2
from typing import Dict, List, Optional, Tuple
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": "172.18.0.8",
    "port": 5432,
    "database": "odi",
    "user": "odi_user",
    "password": "odi_secure_password"
}

BRANDS_DIR = "/opt/odi/data/brands"


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_shopify_config():
    """Get IMBRA Shopify config."""
    with open(os.path.join(BRANDS_DIR, "imbra.json")) as f:
        data = json.load(f)
        return data.get("shopify", data)


def split_title_and_compatibility(raw_title: str) -> Tuple[str, List[str]]:
    """
    Split a long title into product type and compatibility list.
    Example: "BANDA DE FRENO FZ 16 ST FAZER-FZ 16-YBR 125"
    Returns: ("Banda de Freno", ["FZ 16 ST Fazer", "FZ 16", "YBR 125"])
    """
    if not raw_title:
        return "", []

    title = raw_title.strip()

    # Product type keywords that mark end of product name
    product_markers = [
        r"^(PASTILLAS?\s+DE\s+FRENO(?:\s+CERAMICA)?(?:\s+(?:DEL(?:ANTERAS?)?|TRAS(?:ERAS?)?))?\s*)",
        r"^(DISCO\s+DE\s+FRENO\s+(?:DELANTERO|TRASERO)\s*)",
        r"^(BANDA\s+DE\s+FRENO\s*)",
        r"^(SOSTENEDOR\s+(?:CENTRO\s+)?DE\s+CLUTCH\s*)",
        r"^(LLAVE\s+AJUSTE\s+AMORTIGUADORES\s*)",
        r"^(KIT\s+DE\s+(?:ARRASTRE|CLUTCH|EMBRAGUE|TRANSMISION)\s*)",
        r"^(PINON\s+(?:DELANTERO|TRASERO|DE\s+ARRASTRE)\s*)",
        r"^(CADENA\s+(?:DE\s+ARRASTRE|RK|DID)?\s*)",
        r"^(CORONA\s+(?:TRASERA)?\s*)",
        r"^(BUJIA(?:\s+DE\s+ENCENDIDO)?\s*)",
        r"^(FILTRO\s+DE\s+(?:ACEITE|AIRE|COMBUSTIBLE)\s*)",
        r"^(MANIGUETA(?:S)?\s+(?:DE\s+FRENO|DE\s+CLUTCH)?\s*)",
        r"^(TENSOR\s+DE\s+CADENA\s*)",
        r"^(ZAPATA(?:S)?\s+DE\s+FRENO\s*)",
        r"^(CABLE\s+DE\s+(?:VELOCIMETRO|FRENO|CLUTCH|ACELERADOR)\s*)",
        r"^(EMPAQUE(?:S)?\s+(?:DE\s+MOTOR|COMPLETO)?\s*)",
        r"^(RETEN(?:ES)?\s+(?:DE\s+MOTOR)?\s*)",
        r"^(RODAMIENTO(?:S)?\s*)",
        r"^(BALINERA(?:S)?\s*)",
    ]

    product_type = ""
    rest = title

    for pattern in product_markers:
        match = re.match(pattern, title, re.IGNORECASE)
        if match:
            product_type = match.group(1).strip()
            rest = title[len(product_type):].strip()
            break

    if not product_type:
        # Try to find first model reference as split point
        brand_pattern = r"(HONDA|YAMAHA|BAJAJ|SUZUKI|KAWASAKI|TVS|AKT|KTM|BENELLI|HERO|VICTORY|CF\s*MOTO|KYMCO)"
        match = re.search(brand_pattern, title, re.IGNORECASE)
        if match:
            product_type = title[:match.start()].strip(" -")
            rest = title[match.start():].strip()
        else:
            # Split at first hyphen
            if " - " in title:
                parts = title.split(" - ", 1)
                product_type = parts[0].strip()
                rest = parts[1].strip() if len(parts) > 1 else ""
            elif "-" in title and title.index("-") > 10:
                idx = title.index("-")
                product_type = title[:idx].strip()
                rest = title[idx+1:].strip()
            else:
                product_type = title
                rest = ""

    # Parse compatibility list
    compatibility = []
    if rest:
        # Split by common separators
        parts = re.split(r"[-/]|\s*,\s*|\s+(?=[A-Z]{2,})", rest)
        for part in parts:
            part = part.strip(" -,")
            if part and len(part) > 2:
                clean = normalize_model_name(part)
                if clean and clean not in compatibility:
                    compatibility.append(clean)

    # Normalize product type to Title Case
    product_type = normalize_product_type(product_type)

    return product_type, compatibility


def normalize_product_type(product_type: str) -> str:
    """Convert ALL CAPS product type to Title Case."""
    if not product_type:
        return ""

    upper_count = sum(1 for c in product_type if c.isupper())
    total_alpha = sum(1 for c in product_type if c.isalpha())

    if total_alpha > 0 and upper_count / total_alpha > 0.6:
        lowercase_words = {"de", "del", "la", "el", "los", "las", "para", "con", "sin", "en", "y", "o", "a", "al", "por"}
        words = product_type.lower().split()
        result = []

        for i, word in enumerate(words):
            if i == 0:
                result.append(word.capitalize())
            elif word in lowercase_words:
                result.append(word)
            else:
                result.append(word.capitalize())

        return " ".join(result)

    return product_type


def normalize_model_name(model: str) -> str:
    """Normalize a model name like 'FZ 16 ST FAZER' to 'FZ 16 ST Fazer'."""
    if not model:
        return ""

    model = model.strip()

    # Remove trailing years/versions like (17-UP) or (MOD 2019)
    model = re.sub(r"\s*\(.*?\)\s*$", "", model)

    if len(model) < 3 or model.isdigit():
        return ""

    # Known models that should stay uppercase
    uppercase_models = {"FZ", "YBR", "XTZ", "CBR", "CB", "CBF", "NS", "RS", "AS", "NXR", "CG",
                       "BWS", "MT", "SZ", "RR", "ABS", "FI", "GT", "ED", "ST", "PRO", "CBS",
                       "AK", "TVS", "KTM", "RC", "TNT", "TRK", "BN", "GLH", "NXG"}

    words = model.split()
    result = []

    for word in words:
        word_upper = word.upper()
        if word_upper in uppercase_models:
            result.append(word_upper)
        elif word.isdigit() or re.match(r"^\d+[A-Za-z]*$", word):
            result.append(word.upper())
        elif len(word) <= 2:
            result.append(word.upper())
        else:
            result.append(word.capitalize())

    return " ".join(result)


def build_short_title(product_type: str, compatibility: List[str]) -> str:
    """Build a short title (max 60 chars) with product type + store suffix."""
    base = product_type if product_type else "Repuesto"

    # Add first 1-2 models if space permits
    if compatibility and len(base) < 40:
        models_str = ", ".join(compatibility[:2])
        if len(base) + len(models_str) < 50:
            base = f"{base} {models_str}"

    # Add store suffix
    title = f"{base} - Imbra"

    if len(title) > 60:
        title = title[:57] + "..."

    return title


def build_compatibility_html(compatibility: List[str]) -> str:
    """Build HTML for compatibility section."""
    if not compatibility:
        return "<p>Consultar compatibilidad</p>"

    items = ["<ul>"]
    for model in compatibility[:15]:
        items.append(f"  <li>{model}</li>")
    if len(compatibility) > 15:
        items.append(f"  <li>Y {len(compatibility) - 15} modelos mas...</li>")
    items.append("</ul>")

    return "\n".join(items)


def build_ficha_html(short_title: str, sku: str, product_type: str, compatibility: List[str]) -> str:
    """Build complete V19 ficha HTML."""
    compat_html = build_compatibility_html(compatibility)

    return f"""<div class="ficha-360-imbra">
  <h2>{short_title}</h2>

  <div class="producto-info">
    <p><strong>Codigo:</strong> {sku}</p>
    <p><strong>Tipo:</strong> {product_type}</p>
    <p><strong>Marca:</strong> Imbra</p>
  </div>

  <div class="compatibilidad">
    <h3>Compatibilidad</h3>
    {compat_html}
  </div>

  <div class="garantia">
    <p><strong>Garantia:</strong> 6 meses por defecto de fabrica</p>
    <p><strong>Envio:</strong> A toda Colombia</p>
  </div>
</div>"""


def update_shopify_product(config: Dict, product_id: int, title: str, body_html: str) -> bool:
    """Update a Shopify product."""
    shop = config.get("shop")
    token = config.get("token")

    url = f"https://{shop}/admin/api/2024-01/products/{product_id}.json"
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }

    payload = {
        "product": {
            "id": product_id,
            "title": title,
            "body_html": body_html
        }
    }

    try:
        resp = requests.put(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return True
        else:
            logger.error(f"Shopify error {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Request error: {e}")
        return False


def process_imbra_products(limit: int = 100, dry_run: bool = False) -> Dict:
    """Process IMBRA products with V19 normalization."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Get IMBRA products with Shopify IDs
    cur.execute("""
        SELECT p.id, p.codigo_proveedor, p.titulo_raw, p.shopify_product_id
        FROM productos p
        JOIN empresas e ON p.empresa_id = e.id
        WHERE e.codigo = 'IMBRA'
        AND p.shopify_product_id IS NOT NULL
        ORDER BY p.id
        LIMIT %s
    """, (limit,))

    products = cur.fetchall()
    logger.info(f"Processing {len(products)} IMBRA products")

    config = get_shopify_config()

    stats = {
        "processed": 0,
        "updated": 0,
        "errors": 0,
        "skipped": 0,
        "samples": []
    }

    for prod_id, sku, raw_title, shopify_id in products:
        stats["processed"] += 1

        # Split title
        product_type, compatibility = split_title_and_compatibility(raw_title or "")

        # Build short title
        short_title = build_short_title(product_type, compatibility)

        # Build ficha HTML
        body_html = build_ficha_html(short_title, sku, product_type, compatibility)

        # Sample first 5
        if len(stats["samples"]) < 5:
            stats["samples"].append({
                "sku": sku,
                "original": (raw_title[:80] + "...") if raw_title and len(raw_title) > 80 else raw_title,
                "new_title": short_title,
                "compatibility": compatibility[:5]
            })

        if dry_run:
            stats["updated"] += 1
            continue

        # Update Shopify
        success = update_shopify_product(config, shopify_id, short_title, body_html)

        if success:
            stats["updated"] += 1
            # Update PostgreSQL
            cur.execute("""
                UPDATE productos
                SET titulo_raw = %s, status = 'active'
                WHERE id = %s
            """, (short_title, prod_id))
        else:
            stats["errors"] += 1

        # Rate limit
        if stats["processed"] % 2 == 0:
            time.sleep(0.5)

        if stats["processed"] % 50 == 0:
            conn.commit()
            logger.info(f"Progress: {stats['processed']}/{len(products)}, updated: {stats['updated']}, errors: {stats['errors']}")

    conn.commit()
    cur.close()
    conn.close()

    return stats


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 odi_imbra_processor.py dry-run [limit]    # Preview")
        print("  python3 odi_imbra_processor.py process [limit]    # Execute")
        print("  python3 odi_imbra_processor.py test               # Test parsing")
        sys.exit(1)

    cmd = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    if cmd == "test":
        samples = [
            "BANDA DE FRENO FZ 16 ST FAZER-FZ 16-YBR 125 ED-FZ 16 2.0-YBR 125 E-LIBERO 125-SZ 16 R-AEROX 155-SZ RR 150",
            "PASTILLA DE FRENO TRAS  HONDA CBR 250 R(11-17)-CB300F(13-24)-CBR400RR(88-94)-CB500F(13-22)",
            "DISCO DE FRENO DELANTERO SUZUKI GIXXER 150(15-17) - GIXXER 150 FI (21-23) - GIXXER SF 150 ABS (23-24)",
        ]

        for title in samples:
            print(f"\n{'='*60}")
            print(f"Original: {title[:70]}...")
            product_type, compat = split_title_and_compatibility(title)
            short = build_short_title(product_type, compat)
            print(f"Product Type: {product_type}")
            print(f"Compatibility: {compat[:5]}")
            print(f"Short Title: {short}")

    elif cmd == "dry-run":
        result = process_imbra_products(limit=limit, dry_run=True)
        print(json.dumps(result, indent=2, default=str))

    elif cmd == "process":
        result = process_imbra_products(limit=limit, dry_run=False)
        print(json.dumps(result, indent=2, default=str))

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
