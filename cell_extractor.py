import os
import cv2


class CellExtractor:
    """
    Recorta cada celda/bloque detectado por PageSegmenter
    y la guarda como imagen PNG individual.

    Nombre de archivo recomendado:
        page_10_row_3_col_2.png
    """

    def __init__(self, margin=4):
        self.margin = margin

    def extract_cells(self, image_path, cells, output_dir):
        """
        Recorta y guarda todas las celdas detectadas.

        image_path: imagen de la página
        cells: lista de dicts con {row, col, x, y, w, h}
        output_dir: carpeta donde guardar los PNG
        """
        os.makedirs(output_dir, exist_ok=True)

        img = cv2.imread(image_path)
        if img is None:
            print("[ERROR] No se pudo cargar la imagen:", image_path)
            return []

        extracted_files = []

        for cell in cells:
            x, y, w, h = cell["x"], cell["y"], cell["w"], cell["h"]

            # Expandir un poco el recorte para no cortar texto
            x0 = max(0, x - self.margin)
            y0 = max(0, y - self.margin)
            x1 = min(img.shape[1], x + w + self.margin)
            y1 = min(img.shape[0], y + h + self.margin)

            crop = img[y0:y1, x0:x1]

            # Nombre de archivo
            page = os.path.splitext(os.path.basename(image_path))[0]
            fname = f"{page}_row{cell['row']}_col{cell['col']}.png"
            out_path = os.path.join(output_dir, fname)

            cv2.imwrite(out_path, crop)

            cell["file"] = out_path
            extracted_files.append(out_path)

        return extracted_files
