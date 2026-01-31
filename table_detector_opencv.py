import cv2
import numpy as np


class OpenCVTableDetector:

    def __init__(self):
        pass

    def preprocess(self, image):
        # Convertir a gris
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Binarizar (Otsu)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Quitar ruido pequeño
        kernel = np.ones((2,2), np.uint8)
        clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

        return clean

    def detect_lines(self, binary):
        # Lineas horizontales
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)

        # Lineas verticales
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

        # Tabla = unión de horizontales + verticales
        table_mask = cv2.add(horizontal, vertical)

        return horizontal, vertical, table_mask

    def detect_table_boxes(self, image):
        """
        Devuelve bounding boxes de celdas detectadas.
        Si no detecta estructura suficiente → se devuelve lista vacía.
        """
        binary = self.preprocess(image)
        horizontal, vertical, mask = self.detect_lines(binary)

        # Dilatar para unir celdas
        kernel = np.ones((3,3), np.uint8)
        dilated = cv2.dilate(mask, kernel, iterations=2)

        cnts, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes = []

        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if w > 30 and h > 20:   # filtro de tamaño mínimo de celda
                boxes.append((x, y, x+w, y+h))

        # Si detectó menos de 3 celdas → tabla inválida
        if len(boxes) < 3:
            return []

        return boxes
