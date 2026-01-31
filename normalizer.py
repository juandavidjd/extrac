import re
import json
import os


class ADSINormalizer:
    def __init__(self):
        rules_path = os.path.join("rules", "rules_adsi.json")
        if os.path.exists(rules_path):
            with open(rules_path, "r", encoding="utf-8") as f:
                self.rules = json.load(f)
        else:
            self.rules = {}

    def normalize_price(self, value):
        if not value:
            return ""
        value = value.replace("$", "").replace(".", "").replace(",", "")
        return value.strip()

    def normalize_code(self, value):
        if not value:
            return ""
        return re.sub(r"[^0-9A-Za-z]", "", value).strip()

    def normalize_text(self, text):
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def normalize(self, data):
        if "error" in data:
            return data

        data["codigo"] = self.normalize_code(data.get("codigo"))
        data["descripcion"] = self.normalize_text(data.get("descripcion"))
        data["precio"] = self.normalize_price(data.get("precio"))
        data["empaque"] = self.normalize_text(data.get("empaque"))

        if "variantes" in data and isinstance(data["variantes"], list):
            for v in data["variantes"]:
                v["codigo"] = self.normalize_code(v.get("codigo", ""))
                v["color"] = self.normalize_text(v.get("color", ""))

        return data
