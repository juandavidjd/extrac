class VariantBuilder:

    def __init__(self):
        pass

    def assign_variants(self, products):
        """
        Cada código puede ser variante si comparte descripción + foto con otros.
        """

        groups = {}

        for p in products:
            key = p.descripcion[:25].upper()  # clave por similitud
            if key not in groups:
                groups[key] = []
            groups[key].append(p)

        # Construir relaciones padre-hijo
        for g in groups.values():
            if len(g) == 1:
                continue

            padre = g[0].codigo
            for p in g[1:]:
                p.padre = padre
                p.variante = True

        return products
