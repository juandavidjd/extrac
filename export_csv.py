import csv
import os

class CSVExporter:

    def __init__(self, out_dir):
        self.out_dir = out_dir

    def export(self, productos):

        path = os.path.join(self.out_dir, "catalogo_adsi_master.csv")

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)

            w.writerow([
                "codigo", "descripcion", "descripcion_tecnica",
                "descripcion_marketing", "precio", "empaque",
                "familia", "subfamilia", "color",
                "modelo_moto", "padre", "variante", "imagen"
            ])

            for p in productos:
                w.writerow([
                    p.codigo,
                    p.descripcion,
                    p.descripcion_tecnica,
                    p.descripcion_marketing,
                    p.precio,
                    p.empaque,
                    p.familia,
                    p.subfamilia,
                    p.color,
                    p.modelo_moto,
                    p.padre,
                    p.variante,
                    p.imagen
                ])

        print(f"CSV generado: {path}")
