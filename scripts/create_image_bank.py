#!/usr/bin/env python3
"""
Fase 3: Crear índice de banco de imágenes por empresa
"""
import os
import json
from pathlib import Path
import hashlib

BASE_IMG = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Imagenes"
OUTPUT = "/opt/odi/data/identidad"

EMPRESAS = {
    "Bara": "BARA", "DFG": "DFG", "Duna": "DUNA", "Imbra": "IMBRA",
    "Japan": "JAPAN", "Kaiqi": "KAIQI", "Leo": "LEO", "Store": "STORE",
    "Vaisand": "VAISAND", "Yokomar": "YOKOMAR"
}

def analyze_image_name(filename):
    """Clasificar imagen por nombre"""
    name_lower = filename.lower()
    
    # Detectar tipo
    if any(x in name_lower for x in ["watermark", "marca", "logo_", "brand"]):
        img_type = "watermarked"
    elif any(x in name_lower for x in ["generic", "placeholder", "default"]):
        img_type = "generic"
    else:
        img_type = "product"
    
    # Extraer posible SKU del nombre
    # Formato común: SKU_nombre.jpg o SKU.jpg
    base = Path(filename).stem
    parts = base.split("_")
    sku = parts[0] if len(parts) > 0 else ""
    
    return {
        "filename": filename,
        "type": img_type,
        "potential_sku": sku,
        "usable": img_type != "watermarked"
    }

def create_image_bank(empresa, empresa_key):
    """Crear banco de imágenes para una empresa"""
    img_path = Path(BASE_IMG) / empresa
    out_dir = Path(OUTPUT) / empresa_key
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not img_path.exists():
        return {"total": 0, "usable": 0, "images": []}
    
    images = []
    for f in img_path.iterdir():
        if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            info = analyze_image_name(f.name)
            info["path"] = str(f)
            info["size"] = f.stat().st_size
            images.append(info)
    
    # Estadísticas
    usable = sum(1 for i in images if i["usable"])
    
    bank = {
        "empresa": empresa,
        "empresa_key": empresa_key,
        "total": len(images),
        "usable": usable,
        "by_type": {
            "product": sum(1 for i in images if i["type"] == "product"),
            "generic": sum(1 for i in images if i["type"] == "generic"),
            "watermarked": sum(1 for i in images if i["type"] == "watermarked")
        },
        "images": images
    }
    
    with open(out_dir / "image_bank.json", "w") as f:
        json.dump(bank, f, indent=2, ensure_ascii=False)
    
    return bank

if __name__ == "__main__":
    print("=" * 60)
    print("FASE 3: BANCO DE IMÁGENES")
    print("=" * 60)
    
    total_all = 0
    for empresa, key in EMPRESAS.items():
        bank = create_image_bank(empresa, key)
        total_all += bank["total"]
        print(f"{empresa:15} Total: {bank['total']:5}  Usables: {bank['usable']:5}  Productos: {bank['by_type']['product']:5}")
    
    print("=" * 60)
    print(f"TOTAL IMÁGENES: {total_all}")
