import cv2
import os

class ImageCropper:

    def __init__(self):
        self.out_dir = "output/images/crops/"
        os.makedirs(self.out_dir, exist_ok=True)

    def crop_blocks(self, img, image_blocks, page_name):
        """
        Corta y exporta cada foto detectada.
        """
        saved = []

        for i, (x, y, w, h) in enumerate(image_blocks):

            crop = img[y:y+h, x:x+w]

            filename = f"{page_name.replace('.png','')}_img_{i}.png"
            cv_path = os.path.join(self.out_dir, filename)
            cv2.imwrite(cv_path, crop)

            saved.append({
                "file": cv_path,
                "bbox": (x, y, w, h)
            })

        return saved
