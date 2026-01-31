import json
import os

class JSONExporter:

    def __init__(self, out_dir):
        self.out_dir = out_dir

    def export(self, productos):

        path = os.path.join(self.out_dir, "catalogo_adsi_master.json")

        data = [p.to_dict() for p in productos]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"JSON generado: {path}")
