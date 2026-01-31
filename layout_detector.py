import cv2

class LayoutDetector:

    def detect(self, img):
        thresh = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                       cv2.THRESH_BINARY_INV, 25, 15)

        cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)

        blocks = []

        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if h > 50 and w > 50:
                blocks.append((x, y, w, h))

        return blocks
