"""
ODI PriceRescue — Lookup de precios desde Cross-Audit v3.0
Fuentes: price_assignment_report.json, sku_exact_matches.json
Tres niveles O(1): empresa:sku → sku global → título normalizado
"""

import json
import os
import re
import logging

logger = logging.getLogger("odi.price_rescue")

class PriceRescue:
    def __init__(self, data_dir="/opt/odi/data/reports"):
        self.data_dir = data_dir
        self.by_empresa_sku = {}
        self.by_sku = {}
        self.by_title = {}
        self.loaded = False
        self.stats = {"total": 0, "sources": {}}

    def load(self):
        sources = [
            ("price_assignment_report.json", 0.85),
            ("rescue_sync_final.json", 0.85),
            ("sku_exact_matches.json", 0.80),
            ("fuzzy_title_matches.json", 0.65),
        ]

        for filename, confidence in sources:
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.exists(filepath):
                continue

            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                count = self._ingest(data, confidence, filename)
                self.stats["sources"][filename] = count
                print(f"  Cargado: {filename} → {count} precios")
            except Exception as e:
                print(f"  Error cargando {filename}: {e}")

        self.stats["total"] = len(self.by_empresa_sku) + len(self.by_sku) + len(self.by_title)
        self.loaded = True
        return self

    def _ingest(self, data, confidence, source):
        count = 0

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    if any(isinstance(v, (dict, int, float)) for v in value.values()):
                        for sku, info in value.items():
                            precio = self._extract_price(info)
                            if precio and precio > 0:
                                empresa = key.upper()
                                sku_clean = self._normalize_code(sku)
                                entry = {"precio": precio, "confidence": confidence, 
                                        "source": source, "method": f"empresa:{empresa}+sku"}
                                self.by_empresa_sku[f"{empresa}:{sku_clean}"] = entry
                                if sku_clean not in self.by_sku:
                                    self.by_sku[sku_clean] = entry
                                count += 1
                elif isinstance(value, (int, float)):
                    sku_clean = self._normalize_code(key)
                    entry = {"precio": float(value), "confidence": confidence,
                            "source": source, "method": "sku_direct"}
                    self.by_sku[sku_clean] = entry
                    count += 1

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    sku = item.get("codigo") or item.get("sku") or item.get("code", "")
                    precio = self._extract_price(item)
                    empresa = (item.get("empresa") or item.get("store") or "").upper()
                    titulo = item.get("titulo") or item.get("title") or item.get("descripcion", "")

                    if precio and precio > 0 and sku:
                        sku_clean = self._normalize_code(sku)
                        entry = {"precio": precio, "confidence": confidence,
                                "source": source, "method": "list_item"}
                        if empresa:
                            self.by_empresa_sku[f"{empresa}:{sku_clean}"] = entry
                        if sku_clean not in self.by_sku:
                            self.by_sku[sku_clean] = entry
                        if titulo:
                            title_key = self._normalize_title(titulo)
                            if title_key not in self.by_title:
                                self.by_title[title_key] = entry
                        count += 1

        return count

    def _extract_price(self, info):
        if isinstance(info, (int, float)):
            return float(info)
        if isinstance(info, dict):
            for key in ["precio", "price", "precio_cop", "valor", "cost"]:
                if key in info:
                    try:
                        val = info[key]
                        if isinstance(val, str):
                            val = re.sub(r'[^\d.]', '', val)
                        return float(val)
                    except (ValueError, TypeError):
                        continue
        if isinstance(info, str):
            try:
                return float(re.sub(r'[^\d.]', '', info))
            except ValueError:
                return None
        return None

    def _normalize_code(self, code):
        return re.sub(r'[^A-Z0-9]', '', str(code).upper())

    def _normalize_title(self, title):
        return re.sub(r'\s+', ' ', re.sub(r'[^A-Z0-9 ]', '', str(title).upper())).strip()

    def get_price(self, sku, empresa="", titulo=""):
        sku_clean = self._normalize_code(sku)

        if empresa:
            key = f"{empresa.upper()}:{sku_clean}"
            if key in self.by_empresa_sku:
                return self.by_empresa_sku[key]

        if sku_clean in self.by_sku:
            return self.by_sku[sku_clean]

        if titulo:
            title_key = self._normalize_title(titulo)
            if title_key in self.by_title:
                return self.by_title[title_key]

        return None

    def get_stats(self):
        return self.stats


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    rescue = PriceRescue()
    rescue.load()

    print(f"\n=== PriceRescue Stats ===")
    print(f"Total entradas: {rescue.stats['total']}")
    print(f"Por empresa:sku: {len(rescue.by_empresa_sku)}")
    print(f"Por sku global: {len(rescue.by_sku)}")
    print(f"Por título: {len(rescue.by_title)}")

    if len(sys.argv) > 1:
        code = sys.argv[1]
        empresa = sys.argv[2] if len(sys.argv) > 2 else "ARMOTOS"
        result = rescue.get_price(code, empresa)
        print(f"\nLookup {empresa}:{code} → {result}")
