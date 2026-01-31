import csv
import os

class DropiExporter:

    def __init__(self, out_dir):
        self.out_dir = out_dir

    def export(self, productos):

        path = os.path.join(self.out_dir, "dropi_provider.csv")

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)

            w.writerow([
                "sku", "nombre_producto", "descripcion", "precio",
                "inventario", "categoria", "imagen"
            ])

            for p in productos:

                w.writerow([
                    p.codigo,
                    p.descripcion,
                    p.descripcion_tecnica,
                    p.precio,
                    999,  # inventario estimado
                    p.familia,
                    p.imagen
                ])

        print(f"Dropi provider CSV generado: {path}")
