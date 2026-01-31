import os
from modules.export_csv import CSVExporter
from modules.export_json import JSONExporter
from modules.export_shopify import ShopifyExporter
from modules.export_dropi import DropiExporter

class ExportManager:

    def __init__(self, out_dir="output/csv/"):
        os.makedirs(out_dir, exist_ok=True)
        self.out_dir = out_dir

        self.csv_exp = CSVExporter(out_dir)
        self.json_exp = JSONExporter(out_dir)
        self.shopify_exp = ShopifyExporter(out_dir)
        self.dropi_exp = DropiExporter(out_dir)

    def export_all(self, productos):
        print("→ Exportando CSV maestro...")
        self.csv_exp.export(productos)

        print("→ Exportando JSON estructurado...")
        self.json_exp.export(productos)

        print("→ Exportando CSV Shopify...")
        self.shopify_exp.export(productos)

        print("→ Exportando archivo Dropi...")
        self.dropi_exp.export(productos)
