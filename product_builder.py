import re
import uuid
from collections import defaultdict


class ProductBuilder:
    """
    Reconstruye productos a partir de múltiples fragmentos del VisionExtractor.
    """

    def __init__(self):
        # Registros temporales para agrupación
        self.by_code = defaultdict(list)
        self.by_name = defaultdict(list)
        self.products = []


    # ---------------------------------------------------------
    # Detectar códigos típicos ARMOTOS (02xxx, 04xxx, etc.)
    # ---------------------------------------------------------
    def extract_code(self, text):
        if not text:
            return None
        m = re.findall(r"\b\d{3,6}\b", text)
        if m:
            return m[0]
        return None


    # ---------------------------------------------------------
    # Normalizar descripción
    # ---------------------------------------------------------
    def normalize_name(self, text):
        if not text:
            return ""
        t = text.upper().strip()
        t = t.replace("  ", " ").strip()
        return t


    # ---------------------------------------------------------
    # Añadir fragmento del LLM
    # ---------------------------------------------------------
    def add_fragment(self, data):
        """
        data = {
            "codigo": "",
            "descripcion": "",
            "precio": "",
            "empaque": "",
            "marketing": "",
            "tecnico": "",
            "familia": "",
            "subfamilia": "",
            "observaciones": "",
            "file": "page_55_img_01.png"
        }
        """

        code = data.get("codigo")
        desc = self.normalize_name(data.get("descripcion"))

        # 1) Agrupar por código (si existe)
        if code and code != "SIN_CODIGO":
            self.by_code[code].append(data)

        # 2) También agrupar por nombre (otro ancla)
        if desc:
            key = desc[:25]  # clave corta (reduce ruido)
            self.by_name[key].append(data)


    # ---------------------------------------------------------
    # Combinar fragmentos dentro de un mismo código/producto
    # ---------------------------------------------------------
    def merge_records(self, records):
        """
        Une múltiples fragmentos del mismo producto en un solo dict.
        """
        final = {
            "codigo": "",
            "descripcion": "",
            "precio": "",
            "empaque": "",
            "marketing": "",
            "tecnico": "",
            "familia": "",
            "subfamilia": "",
            "observaciones": "",
            "imagenes": [],
            "uid": str(uuid.uuid4())
        }

        for r in records:
            if r.get("codigo") and r["codigo"] != "SIN_CODIGO":
                final["codigo"] = r["codigo"]

            if r.get("descripcion"):
                final["descripcion"] = r["descripcion"]

            if r.get("precio"):
                final["precio"] = r["precio"]

            if r.get("empaque"):
                final["empaque"] = r["empaque"]

            if r.get("marketing"):
                final["marketing"] += r["marketing"] + " | "

            if r.get("tecnico"):
                final["tecnico"] += r["tecnico"] + " | "

            if r.get("familia"):
                final["familia"] = r["familia"]

            if r.get("subfamilia"):
                final["subfamilia"] = r["subfamilia"]

            if r.get("observaciones"):
                final["observaciones"] += r["observaciones"] + " | "

            if r.get("file"):
                final["imagenes"].append(r["file"])

        # limpieza
        final["marketing"] = final["marketing"].strip(" |")
        final["tecnico"] = final["tecnico"].strip(" |")
        final["observaciones"] = final["observaciones"].strip(" |")

        # fallback
        if not final["descripcion"]:
            final["descripcion"] = "PRODUCTO SIN DESCRIPCIÓN"

        return final


    # ---------------------------------------------------------
    # Construir productos finales
    # ---------------------------------------------------------
    def build(self):
        """
        Convierte todos los fragmentos en productos consolidados.
        """

        # 1) Primero agrupamos por códigos reales
        for code, items in self.by_code.items():
            product = self.merge_records(items)
            self.products.append(product)

        # 2) Luego agrupamos por nombres cuando no hay código
        for key, items in self.by_name.items():
            # Si ya existe un producto con este código, saltar
            codes = [i.get("codigo") for i in items if i.get("codigo") != "SIN_CODIGO"]
            if codes:
                continue  # ya procesado en grupo 1

            product = self.merge_records(items)
            self.products.append(product)

        return self.products
