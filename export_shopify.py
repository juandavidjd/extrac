import csv
import os

class ShopifyExporter:

    def __init__(self, out_dir):
        self.out_dir = out_dir

    def export(self, productos):

        path = os.path.join(self.out_dir, "shopify_import.csv")

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)

            w.writerow([
                "Handle", "Title", "Body (HTML)", "Vendor", "Type",
                "Tags", "Variant Price", "Image Src", "Variant SKU"
            ])

            for p in productos:

                handle = p.codigo.lower().replace(" ", "-")

                w.writerow([
                    handle,
                    p.descripcion,
                    p.descripcion_tecnica,
                    "ARMOTOS",
                    p.familia,
                    f"{p.subfamilia},{p.color},{p.modelo_moto}",
                    p.precio,
                    p.imagen,
                    p.codigo
                ])

        print(f"Shopify CSV generado: {path}")
