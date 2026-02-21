#!/usr/bin/env python3
import os, re, json, unicodedata
from typing import Dict, List, Tuple
from datetime import datetime
import sys
sys.path.insert(0, "/opt/odi/core")
from odi_title_normalizer import TitleNormalizer

class ProductCorrector:
    def __init__(self, store, max_title_len=60, max_handle_len=80):
        self.store = store.upper()
        self.store_lower = store.lower()
        self.max_title_len = max_title_len
        self.max_handle_len = max_handle_len
        self.title_normalizer = TitleNormalizer(store, max_title_len)
        self.min_price, self.max_price = 500, 5000000
        self.stats = dict(titles_corrected=0, handles_regenerated=0, prices_flagged=0, duplicates_removed=0, images_missing=0, total_processed=0)
        self.compression_rules = [("Para ", " "), ("De ", " "), ("Con ", " "), ("Set Kit", "Kit"), ("Delantera", "Del"), ("Trasera", "Tras"), ("Izquierda", "Izq"), ("Derecha", "Der"), ("Universal", "Univ")]

    def _get_sku(self, p):
        sku = p.get("codigo", p.get("sku", ""))
        if isinstance(sku, list):
            return sku[0] if sku else ""
        return str(sku) if sku else ""

    def normalize_title(self, title):
        if not title: return title
        result = self.title_normalizer.normalize(title)
        if len(result) > self.max_title_len:
            for pat, rep in self.compression_rules:
                result = result.replace(pat, rep)
        if len(result) > self.max_title_len:
            result = result[:self.max_title_len].rsplit(" ", 1)[0]
        return result.strip().title()

    def generate_handle(self, title, sku=""):
        # V22 fix: require valid SKU, no generic handles
        if not sku or sku in ('None', 'null', ''):
            return None  # Skip products without valid SKU
        if not title: return f"producto-{sku}-{self.store_lower}"
        text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii").lower()
        text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
        handle = f"{text}-{self.store_lower}"
        if len(handle) > self.max_handle_len:
            text = text[:self.max_handle_len - len(self.store_lower) - 1].rsplit("-", 1)[0]
            handle = f"{text}-{self.store_lower}"
        return handle

    def validate_price(self, price, sku=""):
        try:
            s = str(price).strip() if price else ""
            if not s: return 0, "invalid"
            # Quitar $ y espacios
            s = s.replace("$", "").replace(" ", "")
            # El punto es separador de miles en COP, no decimal
            # "203.805" = 203805, "$5.710" = 5710
            s = s.replace(".", "")
            p = float(s)
        except:
            return 0, "invalid"
        if p < self.min_price:
            if 0 < p < 500: return p * 1000, "multiplied"
            return p, "too_low"
        if p > self.max_price: return p, "too_high"
        return p, "ok"

    def detect_duplicates(self, products):
        seen, unique, dups = {}, [], []
        for p in products:
            sku = self._get_sku(p)
            if not sku:
                unique.append(p)
                continue
            if sku in seen:
                if len(json.dumps(p)) > len(json.dumps(seen[sku])):
                    dups.append(seen[sku])
                    seen[sku] = p
                    for i, u in enumerate(unique):
                        if self._get_sku(u) == sku:
                            unique[i] = p
                            break
                else:
                    dups.append(p)
            else:
                seen[sku] = p
                unique.append(p)
        return unique, dups

    def check_image(self, sku, images_dir):
        import glob
        # Buscar patron page_XXX_sku_YYYYY.png
        pattern = os.path.join(images_dir, f"*_sku_{sku}.png")
        matches = glob.glob(pattern)
        if matches:
            return True, matches[0]
        # Fallback patrones simples
        for pat in [f"{sku}.png", f"{sku.upper()}.png"]:
            path = os.path.join(images_dir, pat)
            if os.path.exists(path): return True, path
        return False, None

    def condense_desc(self, p):
        t = p.get("nombre", p.get("title", ""))
        s = self._get_sku(p)
        c = p.get("compatibilidad", "")
        if isinstance(c, list): c = ", ".join(c)
        return f"<div><h3>Descripcion</h3><p>{t} - Codigo: {s}</p><h3>Compatibilidad</h3><p>{c or 'Consultar'}</p></div>"

    def correct_product(self, p, images_dir=""):
        c = p.copy()
        orig = p.get("nombre", p.get("title", ""))
        sku = self._get_sku(p)
        price = p.get("precio", p.get("price", 0))
        c["title"] = self.normalize_title(orig)
        c["title_original"] = orig
        if c["title"] != orig: self.stats["titles_corrected"] += 1
        c["handle"] = self.generate_handle(c["title"], sku)
        self.stats["handles_regenerated"] += 1
        c["price"], c["price_status"] = self.validate_price(price, sku)
        if c["price_status"] != "ok": self.stats["prices_flagged"] += 1
        c["body_html"] = self.condense_desc(p)
        if images_dir:
            c["has_image"], c["image_path"] = self.check_image(sku, images_dir)
            if not c["has_image"]: self.stats["images_missing"] += 1
        c["sku"], c["vendor"], c["status"] = sku, p.get("vendor", p.get("marca", self.store)), "active"  # V22 fix: preserve vendor
        self.stats["total_processed"] += 1
        return c

    def run_pipeline(self, input_path, output_path=None, images_dir=""):
        with open(input_path) as f: data = json.load(f)
        products = data if isinstance(data, list) else data.get("products", [])
        print(f"Loaded {len(products)} products")
        unique, dups = self.detect_duplicates(products)
        self.stats["duplicates_removed"] = len(dups)
        print(f"Removed {len(dups)} duplicates, {len(unique)} unique")
        corrected = [self.correct_product(p, images_dir) for p in unique]
        result = dict(timestamp=datetime.now().isoformat(), store=self.store, stats=self.stats, products=corrected, duplicates=dups)
        if output_path:
            with open(output_path, "w") as f: json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Saved to {output_path}")
        return result

    def get_examples(self, prods, n=5):
        import random
        samples = random.sample(prods, min(n, len(prods)))
        return [dict(sku=p["sku"], before=p.get("title_original","")[:40], after=p["title"], price=p["price"], status=p["price_status"]) for p in samples]

    def get_price_issues(self, prods):
        return [dict(sku=p["sku"], title=p["title"], price=p["price"], status=p["price_status"]) for p in prods if p.get("price_status") != "ok"]
