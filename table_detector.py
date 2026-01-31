import cv2

class TableDetector:

    def __init__(self):
        pass

    def find_tables(self, img):
        """
        Detección inicial de tablas por líneas horizontales/verticales.
        En Fase 1 solo devuelve una lista vacía para evitar errores.
        Las versiones avanzadas se activarán en Fase 2 y 3.
        """

        # Conversión a binario (detección de contornos básicos)
        thresh = cv2.adaptiveThreshold(
            img, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            15, 8
        )

        # Detección de contornos
        cnts, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        tables = []

        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)

            # Heurística básica de tabla: anchas y semi-altas
            if w > 300 and h > 80:
                tables.append((x, y, w, h))

        return tables
