from .pattern_rules import PatternRules


class Trainer:
    def __init__(self):
        self.rules = PatternRules()

    # Aprende familia corregida
    def learn_from_edit(self, old_product, new_product):
        old_desc = old_product["descripcion"]
        new_desc = new_product["descripcion"]

        # Corrección de descripción
        if old_desc != new_desc:
            self.rules.learn_description_fix(old_desc, new_desc)

        # Corrección de familia
        if old_product["familia"] != new_product["familia"]:
            self.rules.learn_family(new_desc, new_product["familia"])

        # Corrección de subfamilia
        if old_product["subfamilia"] != new_product["subfamilia"]:
            self.rules.learn_subfamilia(new_desc, new_product["subfamilia"])

        # Precio corregido
        if old_product["precio"] != new_product["precio"]:
            self.rules.learn_price_fix(old_product["precio"], new_product["precio"])

        return True
