import cv2
import numpy as np


class FallbackDetector:
    """
    Detector de bloques cuando NO hay tablas visibles.
    Este módulo busca:

        - Zonas con texto denso
        - Clusters de imágenes
        - Cuadros con precio o descripción
        - Regiones grandes que OpenCV o LayoutParser no clasificaron

    Es especialmente útil para páginas tipo mosaico (muy comunes en ARMOTOS).
    """

    def detect_blocks(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Suavizar ruido
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        # Detección de bordes
        edges = cv2.Canny(blur, 50, 150)

        # Dilatar bordes para agrupar
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(edges, kernel, iterations=2)

        # Buscar contornos
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        blocks = []

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)

            # Filtro básico
            if w < 80 or h < 60:
                continue

            blocks.append({
                "x": int(x),
                "y": int(y),
                "w": int(w),
                "h": int(h)
            })

        # Ordenar bloques por posición visual (arriba → abajo)
        blocks.sort(key=lambda b: (b["y"], b["x"]))

        return blocks

    # ---------------------------------------------------------
    # Método principal
    # ---------------------------------------------------------
    def detect(self, image_path):
        """
        Devuelve:
            { "blocks": [ {x,y,w,h}, ... ] }
        """
        blocks = self.detect_blocks(image_path)

        return {
            "blocks": blocks
        }
