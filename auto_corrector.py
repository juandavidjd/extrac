import pandas as pd
from .pattern_rules import PatternRules


class AutoCorrector:
    """
    Aplica reglas aprendidas para corregir el catálogo automáticamente.
    """

    def __init__(self):
        self.rules = PatternRules()

    def auto_fix(self, df):
        df = df.copy()

        for i in df.index:
            desc = df.at[i, "descripcion"]

            # Normalizar descripción
            fixed = self.rules.apply_description_rules(desc)
            fixed = self.rules.apply_synonyms(fixed)
            df.at[i, "descripcion"] = fixed

            # Aplicar familia aprendida
            fam = self.rules.apply_family_rules(desc)
            if fam:
                df.at[i, "familia"] = fam

            # Aplicar subfamilia aprendida
            sub = self.rules.apply_subfamily_rules(desc)
            if sub:
                df.at[i, "subfamilia"] = sub

            # Precio
            p = str(df.at[i, "precio"])
            df.at[i, "precio"] = self.rules.apply_price_rules(p)

        return df
