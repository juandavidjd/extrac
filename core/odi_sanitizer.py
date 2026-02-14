"""
ODI Sanitizer - Validacion y sanitizacion de datos del pipeline
===============================================================
Previene inyeccion de prompt via PDF, XSS via Shopify, y datos invalidos.
"""
import re
import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger("odi.sanitizer")

ALLOWED_TAGS = {"p", "br", "strong", "em", "b", "i", "ul", "ol", "li", "h1", "h2", "h3", "h4", "span", "div"}
DANGEROUS_ATTRS = re.compile(r'\s(on\w+|srcdoc|style|formaction|data-\w+)\s*=', re.IGNORECASE)
XSS_PATTERNS = [
    re.compile(r'<\s*script', re.IGNORECASE),
    re.compile(r'javascript\s*:', re.IGNORECASE),
    re.compile(r'<\s*iframe', re.IGNORECASE),
    re.compile(r'<\s*object', re.IGNORECASE),
    re.compile(r'<\s*embed', re.IGNORECASE),
    re.compile(r'<\s*form', re.IGNORECASE),
    re.compile(r'<\s*svg.*?on\w+', re.IGNORECASE),
    re.compile(r'<\s*img.*?onerror', re.IGNORECASE),
    re.compile(r'expression\s*\(', re.IGNORECASE),
]


def sanitize_html(raw_html: str) -> str:
    """Sanitiza HTML para Shopify body_html. Elimina XSS vectors."""
    if not raw_html:
        return ""
    text = str(raw_html)
    for pattern in XSS_PATTERNS:
        if pattern.search(text):
            log.warning(f"XSS pattern detected and removed: {pattern.pattern[:40]}")
            text = pattern.sub("", text)
    text = DANGEROUS_ATTRS.sub(" ", text)

    def strip_tag(match):
        tag = match.group(1).lower().split()[0]
        if tag.lstrip("/") in ALLOWED_TAGS:
            return match.group(0)
        return ""

    text = re.sub(r'<(/?\w[^>]*)>', strip_tag, text)
    if len(text) > 32000:
        text = text[:32000] + "..."
        log.warning("body_html truncated to 32KB")
    return text.strip()


PRICE_MIN_COP = 500
PRICE_MAX_COP = 50_000_000
MAX_TITLE_LENGTH = 255
MAX_SKU_LENGTH = 64
MAX_TAG_LENGTH = 255


def validate_product(product: Dict[str, Any]) -> Dict[str, Any]:
    """Valida y sanitiza un producto. Raises ValueError si irrecuperable."""
    sanitized = dict(product)

    title = sanitized.get("title", "")
    if not title or len(title.strip()) < 3:
        raise ValueError(f"Title invalido o vacio: {repr(title)}")
    title = re.sub(r'[\x00-\x1f\x7f]', '', title)
    sanitized["title"] = title[:MAX_TITLE_LENGTH].strip()

    sku = sanitized.get("sku", "")
    sku = re.sub(r'[^a-zA-Z0-9\-_]', '', str(sku))
    sanitized["sku"] = sku[:MAX_SKU_LENGTH]

    price = sanitized.get("price")
    if price is not None:
        try:
            price_f = float(price)
            if price_f < PRICE_MIN_COP or price_f > PRICE_MAX_COP:
                log.warning(f"Price out of range ({price_f}), SKU: {sku}")
                sanitized["price"] = None
            else:
                sanitized["price"] = price_f
        except (ValueError, TypeError):
            sanitized["price"] = None

    desc = sanitized.get("description", "")
    sanitized["description"] = sanitize_html(desc)

    tags = sanitized.get("compatibility", [])
    if isinstance(tags, list):
        sanitized["compatibility"] = [
            re.sub(r'[<>"\'\\]', '', str(t))[:MAX_TAG_LENGTH]
            for t in tags[:50]
        ]

    brand = sanitized.get("brand", "")
    sanitized["brand"] = re.sub(r'[<>"\'\\]', '', str(brand))[:100]

    category = sanitized.get("category", "")
    sanitized["category"] = re.sub(r'[<>"\'\\]', '', str(category))[:100]

    return sanitized


def validate_llm_products(raw_products: list) -> List[Dict[str, Any]]:
    """Valida lista de productos del LLM. Filtra invalidos, sanitiza validos."""
    if not isinstance(raw_products, list):
        log.error(f"LLM returned non-list type: {type(raw_products)}")
        return []

    valid = []
    for i, p in enumerate(raw_products):
        if not isinstance(p, dict):
            log.warning(f"Product {i} is not a dict, skipping")
            continue
        try:
            sanitized = validate_product(p)
            valid.append(sanitized)
        except ValueError as e:
            log.warning(f"Product {i} validation failed: {e}")

    rejected = len(raw_products) - len(valid)
    if rejected > 0:
        log.info(f"Validated {len(valid)}/{len(raw_products)} products ({rejected} rejected)")

    return valid
