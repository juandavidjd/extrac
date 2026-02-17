#!/usr/bin/env python3
"""
Catalog Link Generator for WhatsApp Integration
Generates direct links to catalog pages with highlighted products
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any

CATALOG_BASE_URL = "https://api.liveodi.com/armotos"
HOTSPOT_DATA_DIR = Path("/opt/odi/data")

# Cache for hotspot data
_hotspot_cache: Dict[str, Any] = {}

def load_hotspots(store: str) -> Dict[str, Any]:
    """Load hotspot data for a store"""
    if store in _hotspot_cache:
        return _hotspot_cache[store]
    
    hotspot_file = HOTSPOT_DATA_DIR / store / "hotspot_map_sample.json"
    if not hotspot_file.exists():
        return {}
    
    with open(hotspot_file) as f:
        data = json.load(f)
    
    # Build SKU -> page mapping
    sku_to_page = {}
    for page_key, page_data in data.get('hotspots', {}).items():
        page_num = page_data.get('page', 0)
        for product in page_data.get('products', []):
            sku = str(product.get('codigo', ''))
            if sku:
                sku_to_page[sku] = {
                    'page': page_num,
                    'bbox': product.get('bbox', {})
                }
    
    _hotspot_cache[store] = {
        'raw': data,
        'sku_to_page': sku_to_page
    }
    return _hotspot_cache[store]

def get_catalog_link(store: str, sku: str) -> Optional[str]:
    """Generate a catalog link for a specific product"""
    data = load_hotspots(store)
    sku_map = data.get('sku_to_page', {})
    
    if sku in sku_map:
        page = sku_map[sku]['page']
        return f"{CATALOG_BASE_URL}?page={page}&sku={sku}"
    return None

def get_page_link(page: int) -> str:
    """Generate a link to a specific catalog page"""
    return f"{CATALOG_BASE_URL}?page={page}"

def enrich_product_response(store: str, products: list) -> list:
    """Add catalog links to product list for WhatsApp responses"""
    data = load_hotspots(store)
    sku_map = data.get('sku_to_page', {})
    
    for product in products:
        sku = str(product.get('codigo', product.get('sku', '')))
        if sku in sku_map:
            page = sku_map[sku]['page']
            product['catalog_link'] = f"{CATALOG_BASE_URL}?page={page}&sku={sku}"
            product['catalog_page'] = page
    
    return products

def format_whatsapp_product(product: dict, include_link: bool = True) -> str:
    """Format a product for WhatsApp message"""
    name = product.get('nombre', product.get('title', 'Producto'))
    price = product.get('precio', product.get('price', 0))
    sku = product.get('codigo', product.get('sku', ''))
    store = product.get('tienda', product.get('store', ''))
    
    # Format price
    if isinstance(price, (int, float)) and price > 0:
        price_str = f"${price:,.0f}"
    else:
        price_str = "Consultar"
    
    msg = f"*{name}*\n"
    msg += f"Precio: {price_str}\n"
    msg += f"Ref: {sku}"
    
    if include_link and 'catalog_link' in product:
        msg += f"\n\nVer en catalogo: {product['catalog_link']}"
    
    return msg

# Test
if __name__ == '__main__':
    data = load_hotspots('ARMOTOS')
    print(f"SKUs mapeados: {len(data.get('sku_to_page', {}))}" )
    
    # Test with a sample SKU
    sample_sku = list(data.get('sku_to_page', {}).keys())[:3]
    for sku in sample_sku:
        link = get_catalog_link('ARMOTOS', sku)
        print(f"{sku} -> {link}")
