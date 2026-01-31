#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
build_armotos_catalog.py

Toma el resultado de FASE 8 (productos_llm.json) y genera:

1) C:\img\Base_Datos_Armotos.csv
   → Base de datos estructurada por producto

2) C:\img\catalogo_kaiqi_imagenes_Armotos.csv
   → Mapeo CODIGO ↔ IMAGEN final para SRM/KAIQI

3) C:\img\FOTOS_COMPETENCIA_ARMOTOS\
   → Imágenes finales recortadas y renombradas

No modifica el pipeline ni los módulos V5.
"""

import os
import json
import csv
import shutil
from collections import defaultdict

# --------------------------------------------------------------------
# RUTAS BASE (ajusta si algo cambia en tu máquina)
# --------------------------------------------------------------------
BASE_DIR = r"C:\adsi\EXTRACTOR_V4"
LLM_JSON = os.path.join(BASE_DIR, "output", "productos_llm.json")

CROPS_DIR = os.path.join(BASE_DIR, "output", "images", "crops")  # donde están los recortes
IMG_BASE_DIR = r"C:\img"
ARMOTOS_IMG_DIR = os.path.join(IMG_BASE_DIR, "FOTOS_COMPETENCIA_ARMOTOS")

BASE_DATOS_ARMOTOS = os.path.join(IMG_BASE_DIR, "Base_Datos_Armotos.csv")
CATALOGO_IMAGENES_ARMOTOS = os.path.join(IMG_BASE_DIR, "catalogo_kaiqi_imagenes_Armotos.csv")


# --------------------------------------------------------------------
# UTILIDADES
# --------------------------------------------------------------------
def safe_get(d, key, default=""):
    """get seguro que nunca rompe si falta la clave."""
    v = d.get(key, default)
    if v is None:
        return default
    return str(v).strip()


def normalize_code(code):
    """Normaliza el código para usarlo en nombre de archivo."""
    code = str(code).strip()
    if not code or code.lower() in ("none", "nan", "sin_codigo"):
        return ""
    return code.replace(" ", "").replace("/", "-").upper()


def normalize_desc(desc):
    if not desc:
        return ""
    d = " ".join(str(desc).split())
    return d


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


# --------------------------------------------------------------------
# 1) CARGAR productos_llm.json
# --------------------------------------------------------------------
def load_llm_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encontró productos_llm.json en: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("El JSON esperado debe ser una lista de objetos.")

    print(f"[INFO] Fragmentos totales en JSON LLM: {len(data)}")
    return data


# --------------------------------------------------------------------
# 2) AGRUPACIÓN POR PRODUCTO
# --------------------------------------------------------------------
def group_fragments_by_product(fragments):
    """
    Intenta reconstruir productos:

    Regla:
    - Si tiene 'codigo' → agrupar por 'codigo'
    - Si NO tiene 'codigo' pero sí 'descripcion' → agrupar por descripción
    - Si no tiene nada útil → se ignora
    """

    productos = defaultdict(lambda: {
        "codigo": "",
        "descripcion": "",
        "precio": "",
        "empaque": "",
        "familia": "",
        "subfamilia": "",
        "marketing": [],
        "tecnico": [],
        "observaciones": [],
        "imagenes": set(),
        "origenes": set(),
    })

    sin_codigo_count = 0

    for frag in fragments:
        codigo = safe_get(frag, "codigo", "")
        desc = safe_get(frag, "descripcion", "")
        tipo = safe_get(frag, "tipo", "")  # por si el LLM marcó tipo: producto/tabla/etc.
        img_path = safe_get(frag, "image_path", frag.get("file", ""))

        if not codigo and not desc:
            # Fragmento demasiado pobre, lo saltamos
            continue

        # Clave de agrupación
        if codigo:
            key = ("COD", normalize_code(codigo))
        else:
            key = ("DESC", normalize_desc(desc))
            sin_codigo_count += 1

        p = productos[key]

        # Unificar datos
        if codigo and not p["codigo"]:
            p["codigo"] = normalize_code(codigo)

        if desc and not p["descripcion"]:
            p["descripcion"] = normalize_desc(desc)

        precio = safe_get(frag, "precio", "")
        if precio and not p["precio"]:
            p["precio"] = precio

        empaque = safe_get(frag, "empaque", "")
        if empaque and not p["empaque"]:
            p["empaque"] = empaque

        familia = safe_get(frag, "familia", "")
        if familia and not p["familia"]:
            p["familia"] = familia

        subfamilia = safe_get(frag, "subfamilia", "")
        if subfamilia and not p["subfamilia"]:
            p["subfamilia"] = subfamilia

        mk = safe_get(frag, "marketing", "")
        if mk:
            p["marketing"].append(mk)

        tec = safe_get(frag, "tecnico", "")
        if tec:
            p["tecnico"].append(tec)

        obs = safe_get(frag, "observaciones", "")
        if obs:
            p["observaciones"].append(obs)

        if img_path:
            p["imagenes"].add(img_path)

        origen = safe_get(frag, "page", "") or safe_get(frag, "source", "")
        if origen:
            p["origenes"].add(origen)

    print(f"[INFO] Productos agrupados: {len(productos)}")
    print(f"[INFO] Productos creados solo por descripción (sin código): {sin_codigo_count}")
    return productos


# --------------------------------------------------------------------
# 3) COPIAR Y RENOMBRAR IMÁGENES A FOTOS_COMPETENCIA_ARMOTOS
# --------------------------------------------------------------------
def export_images(productos):
    ensure_dir(ARMOTOS_IMG_DIR)

    mapping = []  # para catalogo_kaiqi_imagenes_Armotos.csv

    for key, p in productos.items():
        codigo = p["codigo"]
        desc = p["descripcion"]

        if codigo:
            base_name = normalize_code(codigo)
        else:
            # fallback a descripción recortada
            base_name = normalize_desc(desc)[:40].replace(" ", "_").upper() or "SIN_CODIGO"

        imagenes = list(p["imagenes"])

        if not imagenes:
            # no hay imagen asociada, igual registramos en mapping con IMG vacía
            mapping.append({
                "CODIGO": codigo or "",
                "IMAGEN_FINAL": "",
                "RUTA_FINAL": "",
                "DESCRIPCION": desc
            })
            continue

        # Primera imagen = principal
        for idx, img_rel in enumerate(imagenes):
            # Algunos paths vienen relativos a output, otros absolutos
            if os.path.isabs(img_rel):
                src = img_rel
            else:
                # asumimos que vienen de CROPS_DIR
                src = os.path.join(CROPS_DIR, os.path.basename(img_rel))

            if not os.path.exists(src):
                # Intento adicional: por si el JSON trae solo nombre
                alt = os.path.join(CROPS_DIR, img_rel)
                if os.path.exists(alt):
                    src = alt
                else:
                    print(f"[WARN] No encuentro imagen fuente: {img_rel}")
                    continue

            # Nombre destino
            if idx == 0:
                dst_name = f"{base_name}.png"
            else:
                dst_name = f"{base_name}_EXTRA_{idx}.png"

            dst_path = os.path.join(ARMOTOS_IMG_DIR, dst_name)

            try:
                shutil.copyfile(src, dst_path)
            except Exception as e:
                print(f"[ERROR] Al copiar {src} → {dst_path}: {e}")
                continue

            # Registrar solo primera como principal para mapping
            if idx == 0:
                mapping.append({
                    "CODIGO": codigo or "",
                    "IMAGEN_FINAL": dst_name,
                    "RUTA_FINAL": dst_path,
                    "DESCRIPCION": desc
                })

    print(f"[INFO] Imágenes exportadas a: {ARMOTOS_IMG_DIR}")
    return mapping


# --------------------------------------------------------------------
# 4) GENERAR Base_Datos_Armotos.csv
# --------------------------------------------------------------------
def export_base_datos(productos):
    """
    Estructura base (ajustable):
    MARCA, CODIGO, DESCRIPCION, PRECIO, EMPAQUE, FAMILIA, SUBFAMILIA,
    MARKETING, TECNICO, OBSERVACIONES, IMAGENES_ORIGEN, ORIGENES
    """
    rows = []

    for key, p in productos.items():
        rows.append({
            "MARCA": "ARMOTOS",
            "CODIGO": p["codigo"],
            "DESCRIPCION": p["descripcion"],
            "PRECIO": p["precio"],
            "EMPAQUE": p["empaque"],
            "FAMILIA": p["familia"],
            "SUBFAMILIA": p["subfamilia"],
            "MARKETING": " | ".join(p["marketing"]),
            "TECNICO": " | ".join(p["tecnico"]),
            "OBSERVACIONES": " | ".join(p["observaciones"]),
            "IMAGENES_ORIGEN": ", ".join(sorted(p["imagenes"])),
            "ORIGENES": ", ".join(sorted(p["origenes"])),
        })

    fieldnames = [
        "MARCA", "CODIGO", "DESCRIPCION", "PRECIO", "EMPAQUE",
        "FAMILIA", "SUBFAMILIA",
        "MARKETING", "TECNICO", "OBSERVACIONES",
        "IMAGENES_ORIGEN", "ORIGENES"
    ]

    with open(BASE_DATOS_ARMOTOS, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"[OK] Base_Datos_Armotos.csv generado en: {BASE_DATOS_ARMOTOS}")


# --------------------------------------------------------------------
# 5) GENERAR catalogo_kaiqi_imagenes_Armotos.csv
# --------------------------------------------------------------------
def export_catalogo_imagenes(mapping):
    """
    Estructura:
    CODIGO,IMAGEN_FINAL,RUTA_FINAL,DESCRIPCION
    (Puedes ajustarla para que se parezca a tus otros catalogo_kaiqi_imagenes_*.csv)
    """

    fieldnames = ["CODIGO", "IMAGEN_FINAL", "RUTA_FINAL", "DESCRIPCION"]

    with open(CATALOGO_IMAGENES_ARMOTOS, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in mapping:
            writer.writerow(m)

    print(f"[OK] catalogo_kaiqi_imagenes_Armotos.csv generado en: {CATALOGO_IMAGENES_ARMOTOS}")


# --------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------
def main():
    print("=== ARMOTOS BUILDER — ADSI V5 ===")
    print(f"Usando JSON LLM: {LLM_JSON}")

    fragments = load_llm_json(LLM_JSON)
    productos = group_fragments_by_product(fragments)

    print("\n[1] Exportando imágenes finales ARMOTOS...")
    mapping = export_images(productos)

    print("\n[2] Generando Base_Datos_Armotos.csv...")
    export_base_datos(productos)

    print("\n[3] Generando catalogo_kaiqi_imagenes_Armotos.csv...")
    export_catalogo_imagenes(mapping)

    print("\n🎉 PROCESO ARMOTOS COMPLETADO (nivel catálogo + imágenes)")
    print("   - Revisa C:\\img\\Base_Datos_Armotos.csv")
    print("   - Revisa C:\\img\\catalogo_kaiqi_imagenes_Armotos.csv")
    print("   - Revisa C:\\img\\FOTOS_COMPETENCIA_ARMOTOS\\")


if __name__ == "__main__":
    main()
