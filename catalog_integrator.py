import re
import uuid
import pandas as pd


class CatalogIntegrator:
    """
    Unifica, normaliza y prepara los productos finales
    para exportación (CSV/Excel/Shopify/SRM).

    Entrada: productos del ProductBuilder
    Salida: dataframe limpio y homologado
    """

    def __init__(self):
        pass

    # -------------------------------------------------------------------
    # Normalizar precio
    # -------------------------------------------------------------------
    def normalize_price(self, price):
        if not price:
            return ""

        p = str(price)

        # Quitar caracteres basura
        p = p.replace("$", "").replace(",", "").replace(" ", "").strip()

        # Detectar números sueltos tipo "3425"
        m = re.findall(r"\d+", p)
        if m:
            return int(m[0])

        return ""

    # -------------------------------------------------------------------
    # Crear SKU único si falta
    # -------------------------------------------------------------------
    def assign_sku(self, p):
        if p["codigo"] and p["codigo"] != "SIN_CODIGO":
            return p["codigo"]
        return "SKU-" + uuid.uuid4().hex[:10].upper()

    # -------------------------------------------------------------------
    # Normalizar familia
    # -------------------------------------------------------------------
    def normalize_family(self, desc):
        """
        Reglas generales basadas en patrones del catálogo ARMOTOS.
        """
        if not desc:
            return "OTROS"

        d = desc.upper()

        # Patrones comunes del PDF ARMOTOS
        if "LLAVE" in d or "HERRAMIENT" in d:
            return "Herramientas"

        if "CAUCHO" in d:
            return "Cauchos"

        if "GUARDABARRO" in d:
            return "Guardabarros"

        if "KIT" in d and "CAUCHO" in d:
            return "Kit Cauchos"

        if "DIAFRAGMA" in d or "CARBURADOR" in d:
            return "Carburación"

        if "TAPA" in d or "CUBIERTA" in d:
            return "Tapa Motor"

        if "SOPORTE" in d:
            return "Soportes"

        if "MANILAR" in d or "EMPUNADURA" in d:
            return "Manilares"

        return "General"

    # -------------------------------------------------------------------
    # Normalizar subfamilia
    # -------------------------------------------------------------------
    def normalize_subfamily(self, desc):
        if not desc:
            return ""

        d = desc.upper()

        if "TRASERO" in d:
            return "Trasero"

        if "DELANTERO" in d:
            return "Delantero"

        if "UNIVERSAL" in d:
            return "Universal"

        if "PLANO" in d and "PULPO" in d:
            return "Pulpo Plano"

        if "PASTA" in d and "METAL" in d:
            return "Pasta Metálica"

        return ""

    # -------------------------------------------------------------------
    # Marcar producto padre / variaciones
    # (ej. CAUCHO CRANK multicolor)
    # -------------------------------------------------------------------
    def detect_variants(self, df):
        """
        Agrupa productos por descripción base.
        """
        df["parent_uid"] = ""

        groups = df.groupby("descripcion")

        for desc, g in groups:
            if len(g) > 1:
                parent_id = "PARENT-" + uuid.uuid4().hex[:8]
                df.loc[g.index, "parent_uid"] = parent_id

        return df

    # -------------------------------------------------------------------
    # Integración principal
    # -------------------------------------------------------------------
    def integrate(self, products):
        """
        Convierte lista de dicts en dataframe limpio y uniforme.
        """

        rows = []

        for p in products:
            row = {}

            # Código / SKU
            row["sku"] = self.assign_sku(p)
            row["codigo"] = p.get("codigo", "")
            row["uid"] = p.get("uid", "")

            # Nombre
            desc = p.get("descripcion", "")
            row["descripcion"] = desc

            # Familia / Subfamilia
            row["familia"] = p.get("familia") or self.normalize_family(desc)
            row["subfamilia"] = p.get("subfamilia") or self.normalize_subfamily(desc)

            # Precio
            row["precio"] = self.normalize_price(p.get("precio"))

            # Empaque
            row["empaque"] = p.get("empaque", "")

            # Información técnica
            row["marketing"] = p.get("marketing", "")
            row["tecnico"] = p.get("tecnico", "")
            row["observaciones"] = p.get("observaciones", "")

            # Imágenes asociadas
            row["imagenes"] = ", ".join(p.get("imagenes", []))

            rows.append(row)

        # Crear dataframe
        df = pd.DataFrame(rows)

        # Detectar productos padre (variantes)
        df = self.detect_variants(df)

        # Ordenar catálogo
        df = df.sort_values(["familia", "subfamilia", "descripcion"]).reset_index(drop=True)

        return df
