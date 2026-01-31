import cv2
import numpy as np

class OpenCVTableDetector:
    """
    Detector de tablas usando OpenCV – funciona para tablas marcadas,
    bordes fuertes, líneas continuas y cuadrículas típicas de catálogos.
    """

    def detect_tables(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return {"tables": [], "cells": []}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Umbral adaptativo para resaltar bordes
        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV,
            15, 8
        )

        # Líneas horizontales
        horiz = thresh.copy()
        horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horiz = cv2.morphologyEx(horiz, cv2.MORPH_OPEN, horiz_kernel)

        # Líneas verticales
        vert = thresh.copy()
        vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vert = cv2.morphologyEx(vert, cv2.MORPH_OPEN, vert_kernel)

        grid = cv2.add(horiz, vert)

        # Buscar contornos (bloques rectangulares)
        contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cells = []

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w < 40 or h < 25:
                continue

            cells.append({
                "x": int(x),
                "y": int(y),
                "w": int(w),
                "h": int(h)
            })

        return {
            "tables": [ { "cells": cells } ] if len(cells) > 3 else [],
            "cells": cells
        }
