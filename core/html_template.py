#!/usr/bin/env python3
"""
Generador de body_html profesional con colores corporativos
"""
import json
from pathlib import Path

IDENTITY_PATH = Path("/opt/odi/data/identidad")

def load_brand(empresa_key):
    brand_file = IDENTITY_PATH / empresa_key / "brand.json"
    if brand_file.exists():
        with open(brand_file) as f:
            return json.load(f)
    return {"nombre": empresa_key, "colores": {"primario": "#1a1a2e", "secundario": "#16213e", "acento": "#e94560"}}

def generate_body_html(product, empresa_key):
    brand = load_brand(empresa_key)
    colors = brand.get("colores", {})
    primary = colors.get("primario", "#1a1a2e")
    secondary = colors.get("secundario", "#16213e")
    accent = colors.get("acento", "#e94560")
    
    title = product.get("title", "Producto")
    sku = product.get("sku", "")
    categoria = product.get("category", "Repuesto")
    sistema = product.get("sistema", "General")
    compat = product.get("compatibilidad", "")
    vendor = brand.get("nombre", empresa_key)
    
    compat_section = ""
    if compat:
        compat_section = f"<p><strong>Compatible con:</strong> {compat}</p>"
    
    html = f"""<div style="font-family:Arial,sans-serif;">
<div style="background:{primary};color:white;padding:12px;border-radius:5px;">
<h3 style="margin:0;">{title}</h3>
<span style="font-size:12px;">SKU: {sku}</span>
</div>
<div style="padding:12px;">
<span style="background:#eee;padding:4px 8px;border-radius:3px;font-size:12px;margin-right:5px;">{categoria}</span>
<span style="background:#eee;padding:4px 8px;border-radius:3px;font-size:12px;">{sistema}</span>
{compat_section}
<p style="margin-top:15px;color:#666;font-size:12px;">Distribuido por <strong>{vendor}</strong></p>
</div>
</div>"""
    return html

if __name__ == "__main__":
    product = {"title": "Kit Cadena 14T/44T", "sku": "KC-YAM-110", "category": "Transmision", "sistema": "transmision", "compatibilidad": "Yamaha Libero 110"}
    print(generate_body_html(product, "DFG"))
