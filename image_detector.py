import cv2

class ImageDetector:

    def __init__(self):
        pass

    def detect_images(self, img):
        """
        Detecta bloques que son fotos utilizando bordes + densidad de píxeles.
        """
        edges = cv2.Canny(img, 80, 200)

        cnts, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        image_blocks = []

        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)

            # Filtrar bloques sospechosos de ser imágenes
            if w > 100 and h > 100:
                aspect = w / h
                if 0.2 < aspect < 6.0:
                    image_blocks.append((x, y, w, h))

        return image_blocks
