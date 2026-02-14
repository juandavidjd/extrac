#!/usr/bin/env python3
"""
Fase 2: Extracción de Identidad Corporativa
Genera /opt/odi/data/identidad/{EMPRESA}/brand.json
"""
import os
import json
from pathlib import Path
from PIL import Image
import colorsys

BASE = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI"
OUTPUT = "/opt/odi/data/identidad"

EMPRESAS = [
    "Armotos", "Bara", "CBI", "DFG", "Duna", "Imbra", "Japan", 
    "Kaiqi", "Leo", "MclMotos", "OH Importaciones", "Store", 
    "Vaisand", "Vitton", "Yokomar"
]

def extract_colors_from_image(img_path, n_colors=5):
    """Extraer colores dominantes de imagen"""
    try:
        img = Image.open(img_path).convert("RGB")
        img = img.resize((100, 100))
        pixels = list(img.getdata())
        
        # Contar colores
        color_counts = {}
        for pixel in pixels:
            # Simplificar a menos variaciones
            simplified = (pixel[0]//32*32, pixel[1]//32*32, pixel[2]//32*32)
            color_counts[simplified] = color_counts.get(simplified, 0) + 1
        
        # Top colores (excluyendo blancos y negros puros)
        sorted_colors = sorted(color_counts.items(), key=lambda x: -x[1])
        result = []
        for color, count in sorted_colors:
            if color not in [(0,0,0), (32,32,32), (224,224,224), (255,255,255), (192,192,192)]:
                hex_color = "#{:02x}{:02x}{:02x}".format(*color)
                result.append(hex_color)
                if len(result) >= n_colors:
                    break
        return result
    except:
        return []

def classify_empresa(data_path):
    """Clasificar tipo de empresa según productos"""
    files = os.listdir(data_path) if os.path.exists(data_path) else []
    file_str = " ".join(files).lower()
    
    if "catalogo" in file_str or "catálogo" in file_str:
        if "freno" in file_str or "brake" in file_str:
            return "fabricante"
        return "importador"
    return "distribuidor"

def generate_brand(empresa):
    """Generar brand.json para una empresa"""
    empresa_key = empresa.upper().replace(" ", "_")
    out_dir = Path(OUTPUT) / empresa_key
    out_dir.mkdir(parents=True, exist_ok=True)
    
    brand = {
        "nombre": empresa,
        "nombre_comercial": empresa,
        "nombre_key": empresa_key,
        "descripcion": f"Distribuidor de repuestos para motocicletas - {empresa}",
        "colores": {"primario": "#1a1a2e", "secundario": "#16213e", "acento": "#e94560"},
        "logo_png": None,
        "logo_svg": None,
        "logo_url": None,
        "web": None,
        "redes_sociales": {},
        "telefono": None,
        "direccion": None,
        "categoria": "distribuidor",
        "tiene_imagenes": False,
        "total_imagenes": 0
    }
    
    # Buscar logo
    logo_base = f"{BASE}/logos_optimized/{empresa}"
    if os.path.exists(f"{logo_base}.png"):
        brand["logo_png"] = f"{logo_base}.png"
        colors = extract_colors_from_image(f"{logo_base}.png")
        if len(colors) >= 3:
            brand["colores"]["primario"] = colors[0]
            brand["colores"]["secundario"] = colors[1]
            brand["colores"]["acento"] = colors[2]
        elif len(colors) >= 1:
            brand["colores"]["primario"] = colors[0]
    
    if os.path.exists(f"{logo_base}.svg"):
        brand["logo_svg"] = f"{logo_base}.svg"
    
    # Contar imagenes
    img_path = f"{BASE}/Imagenes/{empresa}"
    if os.path.exists(img_path):
        img_count = len([f for f in os.listdir(img_path) if f.lower().endswith((".jpg",".jpeg",".png",".webp"))])
        brand["tiene_imagenes"] = img_count > 0
        brand["total_imagenes"] = img_count
    
    # Clasificar empresa
    data_path = f"{BASE}/Data/{empresa}"
    brand["categoria"] = classify_empresa(data_path)
    
    # Guardar
    with open(out_dir / "brand.json", "w") as f:
        json.dump(brand, f, indent=2, ensure_ascii=False)
    
    return brand

if __name__ == "__main__":
    print("=" * 60)
    print("FASE 2: EXTRACCIÓN DE IDENTIDAD CORPORATIVA")
    print("=" * 60)
    
    for empresa in EMPRESAS:
        brand = generate_brand(empresa)
        logo = "✓" if brand["logo_png"] else "✗"
        imgs = brand["total_imagenes"]
        color = brand["colores"]["primario"]
        print(f"{empresa:20} Logo:{logo} Imgs:{imgs:4} Color:{color}")
    
    print("=" * 60)
    print(f"Generados: {len(EMPRESAS)} brand.json")
