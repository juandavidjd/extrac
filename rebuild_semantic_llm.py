# -*- coding: utf-8 -*-
"""
FASE 17.3 — SEMANTIC REBUILD MODE
Reconstrucción semántica completa del archivo productos_llm.json
by ADSI Extractor V5

Objetivo:
    - Recuperar productos a partir de texto libre NO estructurado
    - Detectar códigos, descripciones, variantes
    - Asignar imágenes padre
    - Construir objetos limpios para FASE 18
"""

import re
import json
import os
import pandas as pd

INPUT_FILE = r"C:\adsi\EXTRACTOR_V4\output\productos_llm.json"
OUT_JSON = r"C:\adsi\EXTRACTOR_V4\output\productos_llm_semantic.json"
OUT_CSV  = r"C:\adsi\EXTRACTOR_V4\output\productos_llm_semantic.csv"

# =============================== 
# 🔍 Reglas de detección
# ===============================

REGEX_CODE = re.compile(
    r"\b(?:[A-Z0-9]{3,8}|[0-9]{3,6})\b"
)

REGEX_COLOR = re.compile(
    r"\b(negro|azul|rojo|verde|gris|dorado|amarillo|naranja|plateado|blanco)\b",
    re.IGNORECASE
)

REGEX_EMPAQUE = re.compile(
    r"(empaque\s*[: ]?\s*x?\d{1,3})",
    re.IGNORECASE
)

REGEX_IMG = re.compile(
    r"(page_\d+_(?:img|block)_\d+\.png)",
    re.IGNORECASE
)

# =============================== 
# 🔧 Funciones auxiliares
# ===============================

def limpiar_texto(txt):
    if not txt: 
        return ""
    txt = txt.strip()
    txt = txt.replace("•", " ")
    txt = txt.replace("–", "-")
    txt = txt.replace("=", " ")
    return txt


def extraer_productos_de_linea(linea):
    """
    Detecta múltiples productos en una misma línea.
    Devuelve una lista de dicts.
    """
    productos = []
    codes = REGEX_CODE.findall(linea)

    if not codes:
        return []

    # Dividir por códigos detectados
    parts = REGEX_CODE.split(linea)
    parts = [p.strip(" -:") for p in parts if p.strip()]

    if len(parts) != len(codes):
        # Caso: "AZUL 02905 ROJO 02906 VERDE 02907"
        # reconstrucción secuencial
        productos = []
        tokens = linea.split()
        for i, token in enumerate(tokens):
            if REGEX_CODE.fullmatch(token):
                desc = " ".join(tokens[max(0, i-5):i])
                productos.append({
                    "codigo": token,
                    "descripcion": desc.strip(),
                })
        return productos

    # Caso normal 1:1
    for desc, code in zip(parts, codes):
        productos.append({
            "codigo": code,
            "descripcion": desc.strip(),
        })

    return productos


# =============================== 
# 🚀 PROCESO PRINCIPAL
# ===============================

print("=== FASE 17.3 — SEMANTIC REBUILD MODE ===")
print(f"Leyendo archivo: {INPUT_FILE}")

with open(INPUT_FILE, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

productos = []
current_img = None

for i, line in enumerate(lines):
    line = limpiar_texto(line)

    if not line or len(line) < 3:
        continue

    # ¿Esta línea menciona una imagen?
    img = REGEX_IMG.findall(line)
    if img:
        current_img = img[-1]

    # ¿Contiene productos?
    encontrados = extraer_productos_de_linea(line)

    for prod in encontrados:
        desc = prod["descripcion"].lower()

        color = None
        match_color = REGEX_COLOR.search(desc)
        if match_color:
            color = match_color.group(1).strip()

        empaque = None
        match_emp = REGEX_EMPAQUE.search(line)
        if match_emp:
            empaque = match_emp.group(1)

        productos.append({
            "codigo": prod["codigo"],
            "descripcion": prod["descripcion"],
            "color": color,
            "empaque": empaque,
            "imagen": current_img,
            "linea": i
        })

# ===============================
# 🧹 Limpieza y normalización final
# ===============================

# Eliminar repetidos
productos_unicos = { (p["codigo"], p["descripcion"]): p for p in productos }
productos_final = list(productos_unicos.values())

print(f"[INFO] Productos detectados: {len(productos_final)}")

# Guardar JSON
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(productos_final, f, ensure_ascii=False, indent=2)

# Guardar CSV
pd.DataFrame(productos_final).to_csv(OUT_CSV, index=False, encoding='utf-8-sig')

print("=== FASE 17.3 COMPLETADA ===")
print(f"JSON final: {OUT_JSON}")
print(f"CSV final:  {OUT_CSV}")
