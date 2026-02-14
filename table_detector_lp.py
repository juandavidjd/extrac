import layoutparser as lp
import cv2
import numpy as np


class LayoutParserTableDetector:
    """
    Detector de tablas basado en deep learning con LayoutParser.
    Utiliza el modelo PrimaLayout o PubLayNet para detectar estructuras:

        - Table
        - Table Row
        - Table Cell
        - Text Block

    Este módulo es más flexible que el detector OpenCV
    y detecta tablas incluso sin bordes visibles.
    """

    def __init__(self, model_name="lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config"):
        try:
            self.model = lp.AutoLayoutModel(model_name)
            self.enabled = True
        except Exception as e:
            print("[WARN] LayoutParser no disponible:", e)
            self.enabled = False

    def detect_tables(self, image_path):
        if not self.enabled:
            return {
                "tables": [],
                "cells": []
            }

        image = cv2.imread(image_path)
        if image is None:
            return {"tables": [], "cells": []}

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Detect layout components
        layout = self.model.detect(image_rgb)

        tables = []
        cells = []

        # --- Filtrar SOLO los bloques que nos sirven ---
        table_blocks = [b for b in layout if b.type in ("Table", "table")]
        cell_blocks = [b for b in layout if b.type in ("Table Cell", "Cell")]

        # Convertir celdas a diccionarios
        for blk in cell_blocks:
            x1, y1, x2, y2 = map(int, blk.block)
            w = x2 - x1
            h = y2 - y1

            if w < 30 or h < 20:
                continue

            cells.append({
                "x": x1,
                "y": y1,
                "w": w,
                "h": h
            })

        # Convertir tablas
        for blk in table_blocks:
            tables.append({
                "bbox": list(map(int, blk.block)),
                "cells": cells  # LayoutParser no separa celdas por tabla
            })

        # Si detecta celdas sin tabla, igual lo registramos
        if len(tables) == 0 and len(cells) > 3:
            tables.append({"bbox": None, "cells": cells})

        return {
            "tables": tables,
            "cells": cells
        }
