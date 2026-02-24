#!/usr/bin/env python3
"""
ODI PDF Grid Extractor (Tipo 2)
Para catalogos con layout de 3 columnas (ej: MCLMOTOS)
"""

import fitz
import re
import json
import os
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Tuple

# Regex para codigos MCLMOTOS
CODE_PATTERN = re.compile(r"\b(?:MC[A-Z]{2}|AG|GY6|BWS|CB|YBR|AX|DT|XTZ)-\d{2,3}(?:-\d+)?\b")
PRICE_PATTERN = re.compile(r"\$?\s*([\d.,]+)")

# Modelos conocidos (para deteccion)
KNOWN_MODELS = [
    "AYCO", "AGILITY", "CERONTE", "GY6", "BWS", "CRYPTON", "NMAX", "PCX",
    "SCOOTER", "AKT", "KYMCO", "YAMAHA", "HONDA", "SUZUKI", "KAWASAKI",
    "PULSAR", "BAJAJ", "TVS", "HERO", "VAISAND", "JIALING", "WUYANG",
    "SIGMA", "INVICTA", "CBF", "NAKED", "TWIST"
]

@dataclass
class ProductBlock:
    codigo: str
    descripcion: Optional[str]
    modelo: Optional[str]
    precio: Optional[int]
    precio_raw: Optional[str]
    page: int
    column: str
    y_min: float
    y_max: float
    lines_count: int
    image_idx: Optional[int] = None
    has_image: bool = False

class GridExtractor:
    """Extractor para PDFs con layout de grilla (3 columnas)"""

    # Column boundaries
    COL_L_MAX = 180
    COL_C_MAX = 380

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.products: List[ProductBlock] = []

    def close(self):
        self.doc.close()

    def get_column(self, x: float) -> str:
        """Determina columna por posicion X"""
        if x < self.COL_L_MAX:
            return "L"
        elif x < self.COL_C_MAX:
            return "C"
        else:
            return "R"

    def get_column_x_range(self, col: str) -> Tuple[float, float]:
        """Retorna rango X para una columna"""
        if col == "L":
            return (0, self.COL_L_MAX)
        elif col == "C":
            return (self.COL_L_MAX, self.COL_C_MAX)
        else:
            return (self.COL_C_MAX, 600)

    def extract_page_text(self, page_num: int) -> List[Dict]:
        """Extrae texto con coordenadas de una pagina"""
        page = self.doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        text_items = []
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    bbox = span["bbox"]
                    text_items.append({
                        "text": text,
                        "x0": bbox[0],
                        "y0": bbox[1],
                        "x1": bbox[2],
                        "y1": bbox[3],
                        "col": self.get_column(bbox[0])
                    })

        # Sort by Y then X
        text_items.sort(key=lambda t: (t["y0"], t["x0"]))
        return text_items

    def extract_page_images(self, page_num: int) -> List[Dict]:
        """Extrae imagenes con sus bboxes"""
        page = self.doc[page_num]
        images = []

        for img_idx, img in enumerate(page.get_images()):
            xref = img[0]
            try:
                rects = page.get_image_rects(xref)
                if rects:
                    rect = rects[0]
                    center_x = (rect.x0 + rect.x1) / 2
                    images.append({
                        "idx": img_idx,
                        "xref": xref,
                        "x0": rect.x0,
                        "y0": rect.y0,
                        "x1": rect.x1,
                        "y1": rect.y1,
                        "center_x": center_x,
                        "col": self.get_column(center_x)
                    })
            except:
                pass

        return images

    def find_blocks_in_column(self, items: List[Dict], column: str, images: List[Dict]) -> List[ProductBlock]:
        """Encuentra bloques de producto en una columna"""
        # Filter items for this column
        col_items = [item for item in items if item["col"] == column]
        if not col_items:
            return []

        # Filter images for this column
        col_images = [img for img in images if img["col"] == column]

        # Find all code positions
        code_positions = []
        for i, item in enumerate(col_items):
            match = CODE_PATTERN.search(item["text"])
            if match:
                code_positions.append({
                    "idx": i,
                    "code": match.group(),
                    "y": item["y0"],
                    "item": item
                })

        if not code_positions:
            return []

        blocks = []
        col_x_range = self.get_column_x_range(column)

        for pos_idx, code_pos in enumerate(code_positions):
            start_idx = code_pos["idx"]
            code = code_pos["code"]

            # End index: next code or end of column
            if pos_idx + 1 < len(code_positions):
                end_idx = code_positions[pos_idx + 1]["idx"]
            else:
                end_idx = len(col_items)

            # Also limit by Y delta (safety: 120px max gap)
            block_items = []
            last_y = code_pos["y"]
            for i in range(start_idx, end_idx):
                item = col_items[i]
                if item["y0"] - last_y > 120 and i > start_idx:
                    break
                block_items.append(item)
                last_y = item["y0"]

            if not block_items:
                continue

            # Parse block attributes
            y_min = min(item["y0"] for item in block_items)
            y_max = max(item["y1"] for item in block_items)

            # Description: first meaningful line after code
            descripcion = None
            for item in block_items[1:]:  # Skip code line
                text = item["text"]
                if len(text) > 5 and "MODELO" not in text.upper() and "PRECIO" not in text.upper():
                    if not CODE_PATTERN.search(text):
                        descripcion = text[:60]
                        break

            # Model detection
            modelo = None
            for item in block_items:
                text = item["text"].upper()
                if "MODELO:" in text:
                    modelo = item["text"].split(":")[-1].strip()
                    break
                for known in KNOWN_MODELS:
                    if known in text and len(item["text"]) > 3:
                        modelo = item["text"]
                        break
                if modelo:
                    break

            # Price: last PRECIO match in block
            precio = None
            precio_raw = None
            for item in reversed(block_items):
                text = item["text"]
                if "PRECIO" in text.upper() or "$" in text:
                    price_text = text.replace("PRECIO:", "").replace("PRECIO", "").strip()
                    match = PRICE_PATTERN.search(price_text)
                    if match:
                        precio_raw = match.group(1)
                        # Normalize: remove dots (thousands sep), parse int
                        try:
                            precio = int(precio_raw.replace(".", "").replace(",", ""))
                        except:
                            pass
                        break

            # Image assignment: find image with best Y overlap in same column
            best_img = None
            best_overlap = 0
            for img in col_images:
                # Check if image center_x is within column range
                if not (col_x_range[0] <= img["center_x"] <= col_x_range[1]):
                    continue
                # Calculate Y overlap
                overlap_start = max(y_min, img["y0"])
                overlap_end = min(y_max, img["y1"])
                overlap = max(0, overlap_end - overlap_start)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_img = img

            # FIX 1: Si modelo == descripcion, limpiar
            if modelo and descripcion and modelo == descripcion:
                modelo = None
            
            # FIX 2: Si modelo coincide con regex de codigo, limpiar
            if modelo and CODE_PATTERN.search(modelo):
                modelo = None

            blocks.append(ProductBlock(
                codigo=code,
                descripcion=descripcion,
                modelo=modelo,
                precio=precio,
                precio_raw=precio_raw,
                page=0,  # Will be set later
                column=column,
                y_min=y_min,
                y_max=y_max,
                lines_count=len(block_items),
                image_idx=best_img["idx"] if best_img else None,
                has_image=best_img is not None
            ))

        return blocks

    def process_page(self, page_num: int) -> List[ProductBlock]:
        """Procesa una pagina completa (1-indexed input)"""
        idx = page_num - 1  # Convert to 0-indexed
        if idx < 0 or idx >= len(self.doc):
            return []

        text_items = self.extract_page_text(idx)
        images = self.extract_page_images(idx)

        # Process each column
        all_blocks = []
        for col in ["L", "C", "R"]:
            blocks = self.find_blocks_in_column(text_items, col, images)
            for block in blocks:
                block.page = page_num
                all_blocks.append(block)

        # Sort by Y
        all_blocks.sort(key=lambda b: (b.y_min, b.column))
        return all_blocks

    def process_pages(self, pages: List[int]) -> List[ProductBlock]:
        """Procesa multiples paginas"""
        all_products = []
        for page in pages:
            products = self.process_page(page)
            all_products.extend(products)
            self.products.extend(products)
        return all_products


def test_extraction():
    """Test en 4 paginas de MCLMOTOS"""
    pdf_path = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/MclMotos/REPUESTOS CATÁLOGO 2025 ACTUALIZADO  16 DE DICIEMBRE.pdf"

    print("=" * 70)
    print("MCLMOTOS GRID EXTRACTOR - TEST (4 PAGINAS)")
    print("=" * 70)

    extractor = GridExtractor(pdf_path)
    test_pages = [5, 15, 30, 50]

    all_products = []

    for page in test_pages:
        products = extractor.process_page(page)
        all_products.extend(products)

        # Stats for this page
        with_code = len(products)
        with_price = sum(1 for p in products if p.precio)
        with_desc = sum(1 for p in products if p.descripcion)
        with_model = sum(1 for p in products if p.modelo)
        with_image = sum(1 for p in products if p.has_image)

        print("")
        print("-" * 70)
        print(f"PAGINA {page}: {len(products)} productos")
        print("-" * 70)
        print(f"  Con codigo:      {with_code} (100%)")
        print(f"  Con precio:      {with_price} ({with_price*100//max(1,with_code)}%)")
        print(f"  Con descripcion: {with_desc} ({with_desc*100//max(1,with_code)}%)")
        print(f"  Con modelo:      {with_model} ({with_model*100//max(1,with_code)}%)")
        print(f"  Con imagen:      {with_image} ({with_image*100//max(1,with_code)}%)")

        # Show 2 examples
        print("")
        print("  EJEMPLOS:")
        for p in products[:2]:
            price_str = f"${p.precio:,}" if p.precio else "NO_PRICE"
            desc_str = (p.descripcion[:30] + "...") if p.descripcion and len(p.descripcion) > 30 else (p.descripcion or "NO_DESC")
            model_str = (p.modelo[:18] + "...") if p.modelo and len(p.modelo) > 18 else (p.modelo or "NO_MODEL")
            img_str = "HAS_IMAGE" if p.has_image else "NO_IMAGE"
            print(f"    {p.codigo:<12} | {price_str:<12} | {desc_str:<33} | {model_str:<20} | {img_str}")

    extractor.close()

    # Overall summary
    total = len(all_products)
    total_with_price = sum(1 for p in all_products if p.precio)
    total_with_desc = sum(1 for p in all_products if p.descripcion)
    total_with_model = sum(1 for p in all_products if p.modelo)
    total_with_image = sum(1 for p in all_products if p.has_image)

    print("")
    print("=" * 70)
    print("RESUMEN TOTAL (4 PAGINAS)")
    print("=" * 70)
    print(f"  Total productos:     {total}")
    print(f"  Con precio:          {total_with_price} ({total_with_price*100//max(1,total)}%)")
    print(f"  Con descripcion:     {total_with_desc} ({total_with_desc*100//max(1,total)}%)")
    print(f"  Con modelo:          {total_with_model} ({total_with_model*100//max(1,total)}%)")
    print(f"  Con imagen:          {total_with_image} ({total_with_image*100//max(1,total)}%)")
    print("")
    print(f"  Promedio/pagina:     {total/4:.1f}")
    print(f"  Estimado 67 paginas: {int(total/4 * 67)}")

    # Save sample JSON
    output_dir = "/opt/odi/data/MCLMOTOS"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "mclmotos_products_sample.json")

    # Convert to dict for JSON
    products_dict = []
    for p in all_products:
        products_dict.append({
            "codigo": p.codigo,
            "descripcion": p.descripcion,
            "modelo": p.modelo,
            "precio": p.precio,
            "precio_raw": p.precio_raw,
            "page": p.page,
            "column": p.column,
            "has_image": p.has_image
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(products_dict, f, ensure_ascii=False, indent=2)

    print("")
    print(f"  JSON guardado: {output_path}")


if __name__ == "__main__":
    test_extraction()
