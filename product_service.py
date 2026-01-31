import os
import pandas as pd

class ProductService:
    def __init__(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        path = os.path.join(base, "output", "catalog", "catalogo_adsi_master.csv")
        self.df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

    # Buscar por SKU exacto
    def get_product_by_sku(self, sku):
        f = self.df[self.df["sku"] == sku]
        if not f.empty:
            return f.to_dict("records")[0]
        return None

    # Búsqueda global
    def search(self, q, limit=50):
        q = q.upper()

        df = self.df[
            self.df["descripcion"].str.upper().str.contains(q, na=False) |
            self.df["codigo"].astype(str).str.contains(q, na=False) |
            self.df["sku"].astype(str).str.contains(q, na=False)
        ]

        return df.head(limit).to_dict("records")
