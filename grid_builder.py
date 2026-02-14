import numpy as np

class GridBuilder:
    """
    Organiza celdas detectadas en una cuadrícula ordenada y coherente.

    Toma una lista de bounding boxes desordenados:
        {x, y, w, h}

    Y devuelve una estructura con filas y columnas ordenadas.
    """

    def __init__(self, row_threshold=20, col_threshold=20):
        """
        row_threshold: distancia vertical para considerar dos celdas en la misma fila
        col_threshold: distancia horizontal para considerar dos celdas en la misma columna
        """
        self.row_threshold = row_threshold
        self.col_threshold = col_threshold

    # -----------------------------------------------------------
    # Agrupar celdas en filas por coordenada Y
    # -----------------------------------------------------------
    def group_rows(self, cells):
        rows = []
        sorted_cells = sorted(cells, key=lambda c: (c["y"], c["x"]))

        for c in sorted_cells:
            placed = False

            for row in rows:
                # Comparación vertical
                if abs(c["y"] - row[0]["y"]) <= self.row_threshold:
                    row.append(c)
                    placed = True
                    break

            if not placed:
                rows.append([c])

        return rows

    # -----------------------------------------------------------
    # Ordenar columnas dentro de cada fila
    # -----------------------------------------------------------
    def sort_row_columns(self, rows):
        for row in rows:
            row.sort(key=lambda c: c["x"])
        return rows

    # -----------------------------------------------------------
    # Construir grilla final con índices row/col
    # -----------------------------------------------------------
    def build_grid(self, cells):
        if not cells:
            return []

        rows = self.group_rows(cells)
        rows = self.sort_row_columns(rows)

        # Construcción final
        grid = []
        for r_idx, row in enumerate(rows):
            for c_idx, cell in enumerate(row):
                grid.append({
                    "row": r_idx,
                    "col": c_idx,
                    "x": cell["x"],
                    "y": cell["y"],
                    "w": cell["w"],
                    "h": cell["h"]
                })

        return grid

    # -----------------------------------------------------------
    # Método principal
    # -----------------------------------------------------------
    def build(self, cells):
        """
        Entrada:
            cells = [{x,y,w,h}, ...]

        Salida:
            grid = [{row, col, x, y, w, h}, ...]
        """
        return self.build_grid(cells)
