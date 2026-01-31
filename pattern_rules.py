import re
import json
import os


class PatternRules:
    def __init__(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.memory_file = os.path.join(base, "learning", "correction_memory.json")

        if os.path.exists(self.memory_file):
            with open(self.memory_file, "r", encoding="utf-8") as f:
                self.memory = json.load(f)
        else:
            self.memory = {
                "familia_corrections": {},
                "subfamilia_corrections": {},
                "descripcion_replacements": {},
                "precio_fix_rules": {},
                "sku_patterns": {},
                "synonyms": {}
            }

    # Guardar memoria
    def save(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------
    # AGREGAR CORRECCIONES MANUALES
    # ------------------------------------------------------

    def learn_family(self, descripcion, familia):
        self.memory["familia_corrections"][descripcion.upper()] = familia
        self.save()

    def learn_subfamilia(self, descripcion, subfamilia):
        self.memory["subfamilia_corrections"][descripcion.upper()] = subfamilia
        self.save()

    def learn_description_fix(self, old, new):
        self.memory["descripcion_replacements"][old.upper()] = new
        self.save()

    def learn_synonym(self, word, synonym):
        self.memory["synonyms"][word.upper()] = synonym
        self.save()

    def learn_price_fix(self, pattern, corrected):
        self.memory["precio_fix_rules"][pattern] = corrected
        self.save()

    def learn_sku_pattern(self, code_prefix, family):
        self.memory["sku_patterns"][code_prefix] = family
        self.save()

    # ------------------------------------------------------
    # APLICAR REGLAS APRENDIDAS
    # ------------------------------------------------------

    def apply_description_rules(self, desc):
        d = desc.upper()
        for wrong, correct in self.memory["descripcion_replacements"].items():
            if wrong in d:
                d = d.replace(wrong, correct)
        return d

    def apply_synonyms(self, text):
        t = text.upper()
        for w, s in self.memory["synonyms"].items():
            t = t.replace(w, s)
        return t

    def apply_family_rules(self, desc):
        d = desc.upper()
        if d in self.memory["familia_corrections"]:
            return self.memory["familia_corrections"][d]
        return None

    def apply_subfamily_rules(self, desc):
        d = desc.upper()
        if d in self.memory["subfamilia_corrections"]:
            return self.memory["subfamilia_corrections"][d]
        return None

    def apply_price_rules(self, price_text):
        for pattern, corrected in self.memory["precio_fix_rules"].items():
            if re.search(pattern, price_text):
                return corrected
        return price_text
