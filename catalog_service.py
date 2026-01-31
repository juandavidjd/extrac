import os
import pandas as pd
import json

class CatalogService:
    def __init__(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.catalog_path = os.path.join(base, "output", "catalog", "catalogo_adsi_master.csv")

    def load_catalog(self):
        if not os.path.exists(self.catalog_path):
            return {"error": "Catálogo no generado todavía"}

        df = pd.read_csv(self.catalog_path)
        return df.to_dict("records")
