#!/usr/bin/env python3
import sys
sys.path.insert(0, "/opt/odi/odi_production/extractors")
import os, json, warnings
from collections import Counter
from PIL import Image
from dotenv import load_dotenv
from pdf2image import convert_from_path

warnings.filterwarnings("ignore")
load_dotenv("/opt/odi/.env")

import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

PDF = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Armotos/CATALOGO NOVIEMBRE V01-2025 NF.pdf"
OUT = "/opt/odi/data/ARMOTOS"
global_skus = {}

PROMPT = """Analiza esta pagina de catalogo de repuestos de motos marca ARMOTOS.
Para CADA PRODUCTO visible, extrae JSON:
{"products": [{"name": "nombre", "normalized_title": "Pieza Modelo - Armotos", "sku": "codigo", "price": numero, "category": "cat", "compatible_models": [], "has_photo": true/false, "photo_bbox_pct": {"x1": 0, "y1": 0, "x2": 100, "y2": 100}}], "page_type": "A/B/C"}
REGLAS: SKU es codigo unico (no precio). Foto solo si es imagen real. Coordenadas en porcentaje 0-100."""

def validate_image(path):
    if os.path.getsize(path) < 10240:
        return False
    img = Image.open(path)
    w, h = img.size
    if w < 100 or h < 100:
        return False
    pixels = list(img.convert("RGB").getdata())[:2000]
    dominant_pct = Counter(pixels).most_common(1)[0][1] / len(pixels)
    if dominant_pct > 0.80:
        return False
    if max(w,h) / max(min(w,h),1) > 5:
        return False
    return True

def generate_ficha(prod):
    sku = prod.get("sku", "N/A")
    cat = prod.get("category", "Repuesto")
    models = ", ".join(prod.get("compatible_models", [])) or "Consultar"
    return f"<div class=ficha-360><h2>Descripcion</h2><p>Repuesto ARMOTOS. {cat}.</p><h2>Info</h2><table><tr><td>Ref</td><td>{sku}</td></tr><tr><td>Marca</td><td>ARMOTOS</td></tr></table><h2>Compatibilidad</h2><p>{models}</p><h2>Proveedor</h2><p>ARMOTOS</p></div>"

def extract_page(img, page_num):
    try:
        response = model.generate_content([PROMPT, img], generation_config={"temperature": 0.1, "max_output_tokens": 4096})
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except:
        return {"products": [], "page_type": "B"}

def main():
    global global_skus
    os.makedirs(f"{OUT}/images", exist_ok=True)
    os.makedirs(f"{OUT}/json", exist_ok=True)
    
    print("ARMOTOS EXTRACCION CALIDAD")
    print("=" * 50)
    
    from PyPDF2 import PdfReader
    total_pages = len(PdfReader(PDF).pages)
    print(f"PDF: {total_pages} paginas")
    
    all_products = []
    stats = {"A": 0, "B": 0, "C": 0, "img_ok": 0, "img_bad": 0, "dup": 0}
    
    for page_num in range(1, total_pages + 1):
        if page_num % 10 == 1:
            print(f"Paginas {page_num}-{min(page_num+9, total_pages)}...")
        
        pages = convert_from_path(PDF, dpi=200, first_page=page_num, last_page=page_num)
        page_img = pages[0]
        
        data = extract_page(page_img, page_num)
        pt = data.get("page_type", "C")
        if pt in stats:
            stats[pt] += 1
        
        for prod in data.get("products", []):
            sku = prod.get("sku", f"NOSKU-P{page_num:03d}")
            
            if sku in global_skus and not sku.startswith("NOSKU"):
                stats["dup"] += 1
                continue
            
            img_path = None
            if prod.get("has_photo") and prod.get("photo_bbox_pct"):
                bbox = prod["photo_bbox_pct"]
                w, h = page_img.size
                x1, y1 = int(bbox.get("x1",0)/100*w), int(bbox.get("y1",0)/100*h)
                x2, y2 = int(bbox.get("x2",100)/100*w), int(bbox.get("y2",100)/100*h)
                if x2 > x1 and y2 > y1:
                    crop = page_img.crop((x1, y1, x2, y2))
                    safe_sku = sku.replace("/","_").replace(" ","_")[:20]
                    fpath = f"{OUT}/images/ARM_p{page_num:03d}_{safe_sku}.png"
                    crop.save(fpath)
                    if validate_image(fpath):
                        img_path = fpath
                        stats["img_ok"] += 1
                    else:
                        os.remove(fpath)
                        stats["img_bad"] += 1
            
            final = {
                "title": prod.get("normalized_title", prod.get("name", "")),
                "sku": sku,
                "price": prod.get("price", 0),
                "body_html": generate_ficha(prod),
                "category": prod.get("category", ""),
                "tags": ",".join(prod.get("compatible_models", [])),
                "image_path": img_path,
                "page_num": page_num
            }
            global_skus[sku] = final
            all_products.append(final)
    
    with open(f"{OUT}/json/products_quality.json", "w") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    
    print()
    print("STATS:")
    print(f"  Productos unicos: {len(all_products)}")
    print(f"  Imagenes OK: {stats['img_ok']}")
    print(f"  Imagenes rechazadas: {stats['img_bad']}")
    print(f"  Duplicados: {stats['dup']}")
    print(f"  Con precio: {len([p for p in all_products if p.get('price', 0) > 0])}")

if __name__ == "__main__":
    main()
