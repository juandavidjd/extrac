import cv2
import numpy as np
import layoutparser as lp


class LayoutParserTableDetector:

    def __init__(self):
        """
        Modelo preentrenado de detección de layout
        'PrimaLayout' es el mejor para tablas complejas,
        usado en digitalización editorial y documentos con tablas irregulares.
        """
        print("[LP] Cargando modelo LayoutParser PrimaLayout...")
        self.model = lp.Detectron2LayoutModel(
            config_path="lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config",
            label_map={1: "Text", 2: "Title", 3: "List", 4: "Table", 5: "Figure"},
            extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.5]
        )

    def detect_tables(self, image):
        """
        Devuelve bounding boxes de tablas encontradas.
        """
        layout = self.model.detect(image)
        tables = [b for b in layout if b.type == "Table"]
        boxes = []

        for t in tables:
            x1, y1, x2, y2 = t.block.x_1, t.block.y_1, t.block.x_2, t.block.y_2
            boxes.append((int(x1), int(y1), int(x2), int(y2)))

        return boxes

    def extract_table_region(self, image, table_box):
        """
        Recorta la región donde existe la tabla detectada por LayoutParser.
        """
        x1, y1, x2, y2 = table_box
        return image[y1:y2, x1:x2]

    def detect_table_cells(self, table_image):
        """
        Detecta filas y columnas dentro de la tabla usando
        LayoutParser's built-in TableStructureRecognitionModel.
        """
        print("[LP] Ejecutando Table Structure Recognition...")
        ts_model = lp.TableStructureRecognitionModel(
            config_path="lp://TableBank/faster_rcnn_R_101_FPN_3x/config",
            label_map={"table row": 0, "table column": 1},
        )

        # Detectar filas y columnas
        structure = ts_model.detect(table_image)

        rows = [b for b in structure if b.type == "table row"]
        cols = [b for b in structure if b.type == "table column"]

        # Convertir bounding boxes en formato estándar
        row_boxes = [(int(r.block.x_1), int(r.block.y_1), int(r.block.x_2), int(r.block.y_2)) for r in rows]
        col_boxes = [(int(c.block.x_1), int(c.block.y_1), int(c.block.x_2), int(c.block.y_2)) for c in cols]

        return row_boxes, col_boxes

    def build_grid(self, table_image, row_boxes, col_boxes):
        """
        Construye la matriz de celdas combinando intersecciones
        de filas y columnas detectadas por LayoutParser.
        """
        grid = []

        for ry1, rx1, ry2, rx2 in row_boxes:
            row_cells = []
            for cy1, cx1, cy2, cx2 in col_boxes:
                cell_x1 = max(ry1, cy1)
                cell_y1 = max(rx1, cx1)
                cell_x2 = min(ry2, cy2)
                cell_y2 = min(rx2, cy2)

                if cell_x2 > cell_x1 and cell_y2 > cell_y1:
                    row_cells.append((cell_x1, cell_y1, cell_x2, cell_y2))

            if row_cells:
                grid.append(row_cells)

        return grid
