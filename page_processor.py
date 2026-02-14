import os
import json


class PageProcessor:
    """
    Procesa páginas individuales:
        1. Segmentación (tablas, bloques o híbrido)
        2. Recorte de celdas
        3. Exportación de JSON por página
        4. Producción de datos listos para LLM Vision
    """

    def __init__(self, page_segmenter, cell_extractor, output_dir="output/segments"):
        self.segmenter = page_segmenter
        self.cell_extractor = cell_extractor
        self.output_dir = output_dir

        os.makedirs(self.output_dir, exist_ok=True)

    # ---------------------------------------------------------
    # Procesar una sola página
    # ---------------------------------------------------------
    def process_page(self, image_path, page_index):
        page_name = os.path.basename(image_path)
        json_name = page_name.replace(".png", "").replace(".jpg", "") + ".json"
        json_path = os.path.join(self.output_dir, json_name)

        print(f"[PAGE] Segmentando → {page_name}")

        # 1) Segmentación: detectores + selector + grid
        seg = self.segmenter.process_page(image_path)

        # 2) Recorte de celdas en output/cells
        cells_dir = os.path.join(self.output_dir, "..", "cells")
        extracted_files = self.cell_extractor.extract_cells(
            image_path,
            seg["cells"],
            cells_dir
        )

        # 3) Guardar JSON de salida por página
        for i, c in enumerate(seg["cells"]):
            if i < len(extracted_files):
                c["file"] = extracted_files[i]

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(seg, f, indent=4)

        return seg

    # ---------------------------------------------------------
    # Procesar todas las páginas de un directorio
    # ---------------------------------------------------------
    def process_all(self, pages_dir):
        pages = sorted(os.listdir(pages_dir))
        results = []

        for idx, fname in enumerate(pages):
            if not fname.lower().endswith((".png", ".jpg", ".jpeg")):
                continue

            full_path = os.path.join(pages_dir, fname)
            result = self.process_page(full_path, idx)
            results.append(result)

        return results
