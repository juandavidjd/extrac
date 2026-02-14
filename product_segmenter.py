class ProductSegmenter:

    def __init__(self):
        pass

    def segment_products(self, blocks):
        """
        Convierte bloques del layout en filas lógicas tipo tabla.
        """

        # Ordenar bloques por posición vertical
        blocks = sorted(blocks, key=lambda b: b[1])

        rows = []
        current_row = []

        prev_y = None
        threshold = 40  # separa productos por altura

        for b in blocks:
            x, y, w, h = b

            if prev_y is None:
                current_row.append(b)
            else:
                if abs(y - prev_y) < threshold:
                    current_row.append(b)
                else:
                    rows.append(current_row)
                    current_row = [b]

            prev_y = y

        if current_row:
            rows.append(current_row)

        return rows
