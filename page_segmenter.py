import os
import cv2
import json


class PageSegmenter:
    """
    Motor maestro de segmentación por página.

    Aporta:
        - Detección híbrida (CV + LP + Fallback)
        - Selección inteligente del modo
        - Reconstrucción de la cuadrícula con GridBuilder
        - Salida ordenada lista para recortes y LLM
    """

    def __init__(self, cv_detector, lp_detector, fallback_detector,
                 grid_builder, selector):
        self.cv_detector = cv_detector
        self.lp_detector = lp_detector
        self.fallback_detector = fallback_detector
        self.grid_builder = grid_builder
        self.selector = selector

    # --------------------------------------------------------
    # Procesar una sola página
    # --------------------------------------------------------
    def process_page(self, image_path, output_json=None):
        page_name = os.path.basename(image_path)

        # 1 — Ejecutar detectores
        cv_res = self.cv_detector.detect_tables(image_path)
        lp_res = self.lp_detector.detect_tables(image_path)
        fb_res = self.fallback_detector.detect(image_path)

        # 2 — Seleccionar modo
        selection = self.selector.select(cv_res, lp_res, fb_res)
        mode = selection["mode"]
        raw_cells = selection["cells"]

        # 3 — Construir la cuadrícula final
        grid = self.grid_builder.build(raw_cells)

        result = {
            "page": page_name,
            "mode": mode,
            "cells": grid,
            "raw_cells": raw_cells
        }

        # 4 — Guardar resultado JSON
        if output_json:
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4)

        return result

    # --------------------------------------------------------
    # Procesar todas las páginas de un directorio
    # --------------------------------------------------------
    def process_all(self, pages_dir, output_dir="output/segments"):
        os.makedirs(output_dir, exist_ok=True)

        pages = sorted(os.listdir(pages_dir))
        results = []

        for p in pages:
            if not p.lower().endswith((".png", ".jpg", ".jpeg")):
                continue

            image_path = os.path.join(pages_dir, p)
            json_path = os.path.join(output_dir, f"{os.path.splitext(p)[0]}.json")

            print(f"[PAGE] Segmentando {p} ...")

            res = self.process_page(image_path, json_path)
            results.append(res)

        return results
