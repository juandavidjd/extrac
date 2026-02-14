import os
import json
import pandas as pd


class Exporter:
    """
    Exporta el catálogo final en múltiples formatos:
    - CSV maestro
    - Excel con pestañas
    - JSON completo
    - Shopify CSV
    - SRM CSV
    """

    def __init__(self, output_dir="output/catalog"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # ----------------------------------------------------------------------
    # Guardar CSV normal
    # ----------------------------------------------------------------------
    def export_csv(self, df):
        path = os.path.join(self.output_dir, "catalogo_adsi_master.csv")
        df.to_csv(path, index=False, encoding="utf-8")
        print("✔ CSV maestro generado:", path)

    # ----------------------------------------------------------------------
    # Guardar JSON
    # ----------------------------------------------------------------------
    def export_json(self, df):
        path = os.path.join(self.output_dir, "catalogo_adsi_master.json")
        df.to_json(path, orient="records", force_ascii=False, indent=2)
        print("✔ JSON generado:", path)

    # ----------------------------------------------------------------------
    # Guardar Excel estructurado
    # ----------------------------------------------------------------------
    def export_excel(self, df):
        path = os.path.join(self.output_dir, "catalogo_adsi_master.xlsx")
        with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Productos")

            # Variantes (padre → hijo)
            variants = df[df["parent_uid"] != ""]
            variants.to_excel(writer, index=False, sheet_name="Variantes")

            # Inventario
            inv = df[["sku", "descripcion", "precio"]]
            inv.to_excel(writer, index=False, sheet_name="Inventario")

            # Índice por familias
            fam_groups = df.groupby("familia").size().reset_index(name="cantidad")
            fam_groups.to_excel(writer, index=False, sheet_name="Familias")

            # Reporte calidad
            issues = df[df["descripcion"].str.contains("SIN", na=False)]
            issues.to_excel(writer, index=False, sheet_name="Calidad")

        print("✔ Excel maestro generado:", path)

    # ----------------------------------------------------------------------
    # Exportación específica Shopify
    # ----------------------------------------------------------------------
    def export_shopify(self, df):
        shopify = pd.DataFrame()

        shopify["Handle"] = df["sku"].str.lower()
        shopify["Title"] = df["descripcion"]
        shopify["Body (HTML)"] = df["marketing"] + "<br>" + df["tecnico"]
        shopify["Vendor"] = "ARMOTOS"
        shopify["Product Category"] = df["familia"]
        shopify["Tags"] = df["subfamilia"]
        shopify["Variant Price"] = df["precio"]
        shopify["Image Src"] = df["imagenes"].str.split(",").str[0].fillna("")

        path = os.path.join(self.output_dir, "shopify_import.csv")
        shopify.to_csv(path, index=False, encoding="utf-8")
        print("✔ Shopify CSV generado:", path)

    # ----------------------------------------------------------------------
    # Exportación compacta SRM
    # ----------------------------------------------------------------------
    def export_srm(self, df):
        """
        Formato optimizado para SRM-QK / ADSI Marketplace:
        SKU | CODIGO | NOMBRE | PRECIO | FAMILIA | IMG
        """
        srm = pd.DataFrame()

        srm["SKU"] = df["sku"]
        srm["CODIGO"] = df["codigo"]
        srm["NOMBRE"] = df["descripcion"]
        srm["PRECIO"] = df["precio"]
        srm["FAMILIA"] = df["familia"]
        srm["IMG"] = df["imagenes"].str.split(",").str[0].fillna("")

        path = os.path.join(self.output_dir, "catalogo_srm.csv")
        srm.to_csv(path, index=False, encoding="utf-8")
        print("✔ SRM CSV generado:", path)

    # ----------------------------------------------------------------------
    # Método maestro
    # ----------------------------------------------------------------------
    def export_all(self, df):
        print("📦 Exportando catálogo en formatos múltiples...")

        self.export_csv(df)
        self.export_json(df)
        self.export_excel(df)
        self.export_shopify(df)
        self.export_srm(df)

        print("🎉 EXPORTACIÓN COMPLETA")
