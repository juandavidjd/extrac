class ImageAssigner:

    def __init__(self):
        pass

    def assign(self, productos, image_blocks):
        """
        Asigna bloques de imágenes a productos basados en cercanía vertical.
        """
        productos_con_fotos = []

        for prod in productos:
            prod_y = prod["y"]

            # Buscar imagen más cercana en Y
            closest = None
            min_dist = 99999

            for img in image_blocks:
                (x, y, w, h) = img["bbox"]
                dist = abs(y - prod_y)

                if dist < min_dist:
                    min_dist = dist
                    closest = img["file"]

            prod["imagen"] = closest
            productos_con_fotos.append(prod)

        return productos_con_fotos
