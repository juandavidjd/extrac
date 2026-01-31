import pytesseract
import cv2
import numpy as np

class OCRReader:

    def __init__(self, lang="spa"):
        self.lang = lang

    def read_region(self, img, bbox):
        """
        Extrae texto de una región determinada.
        bbox = (x, y, w, h)
        """
        x, y, w, h = bbox
        crop = img[y:y+h, x:x+w]

        # Limpieza OCR
        crop = cv2.GaussianBlur(crop, (3, 3), 0)
        crop = cv2.threshold(crop, 0, 255,
                             cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

        text = pytesseract.image_to_string(
            crop,
            lang=self.lang,
            config="--psm 6 --oem 3"
        )

        return text.strip()

    def clean_text(self, text):
        """
        Normaliza texto: rompe saltos, remove basura.
        """
        text = text.replace("\n", " ")
        text = " ".join(text.split())
        return text
