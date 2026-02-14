import os
import re
import json
import pandas as pd
from collections import defaultdict


# ==========================================
# 🔧 CONFIGURACIÓN
# ==========================================
INPUT_FILE  = r"C:\adsi\EXTRACTOR_V4\output\productos_llm.json"
OUT_JSON    = r"C:\adsi\EXTRACTOR_V4\output\productos_llm_clean.json"
OUT_CSV     = r"C:\adsi\EXTRACTOR_V4\output\productos_llm_clean.csv"
OUT_LOG     = r"C:\adsi\EXTRACTOR_V4\output\clean_llm_log.txt"


# ====================================================
# 🧠 UTILIDADES: Normalización y validaciones
# ====================================================
def clean_text(s):
    if not isinstance(s, str):
        return ""
    s = s.strip()
    s = s.replace("\n", " ").replace("\t", " ")
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_key(k):
    k = k.lower().strip()
    k = k.replace("í", "i").replace("ó", "o").replace("á", "a").replace("é", "e")
    return k


def safe_value(v):
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return v
    return clean_text(str(v))


# ====================================================
# 🧠 EXTRACCIÓN DE JSONS VÁLIDOS
# ====================================================
JSON_PATTERN = re.compile(r'\{.*?\}', re.DOTALL)


def extract_json_objects(raw_text):
    """Devuelve todos los objetos JSON detectados en el texto."""
    candidates = JSON_PATTERN.findall(raw_text)
    valid = []
    corrupted = []

    for c in candidates:
        try:
            obj = json.loads(c)
            valid.append(obj)
        except:
            corrupted.append(c)

    return valid, corrupted


# ====================================================
# 🧠 INTENTO DE REPARACIÓN SIMPLE DE JSONS
# ====================================================
def try_repair_json(broken):
    """
    Intenta corregir JSONs truncados:
      - Llaves sin cerrar
      - Comas faltantes
      - Strings rotos
    """
    txt = broken.strip()

    # Cerrar llave final si falta
    if txt.count("{") > txt.count("}"):
        txt += "}"

    # Reparar comas mal puestas
    txt = re.sub(r',\s*}', '}', txt)

    try:
        return json.loads(txt)
    except:
        return None


# ====================================================
# 🧠 UNIFICACIÓN DE CAMPOS
# ====================================================
FIELD_MAP = {
    "codigo": ["codigo", "cod", "sku", "id"],
    "descripcion": ["descripcion", "nombre", "titulo"],
    "empaque": ["empaque", "package", "pack"],
    "precio": ["precio", "precio_unit", "price"],
    "imagen": ["imagen", "img", "image", "file"],
    "marketing": ["marketing", "texto_marketing"],
    "tecnico": ["tecnico", "texto_tecnico"],
    "familia": ["familia", "categoria", "rubro"],
}


def normalize_object(obj):
    cleaned = {}

    for std_key, aliases in FIELD_MAP.items():
        for a in aliases:
            if a in obj:
                cleaned[std_key] = safe_value(obj[a])
                break

    return cleaned


# ====================================================
# 🧠 FUSIÓN DE PRODUCTOS (por código o descripción)
# ====================================================
def merge_products(products):
    by_code = defaultdict(dict)
    unnamed_counter = 0

    for p in products:
        code = p.get("codigo", "").strip()
        desc = p.get("descripcion", "").strip()

        if code:
            target = by_code[code]
        else:
            unnamed_counter += 1
            key = f"DESC-{unnamed_counter}-{desc[:20]}"
            target = by_code[key]

        for k, v in p.items():
            if v and not target.get(k):
                target[k] = v

    return list(by_code.values())


# ====================================================
# 🚀 PROCESO PRINCIPAL
# ====================================================
def main():
    print("=== FASE 17.1 — LIMPIEZA AVANZADA LLM JSON ===")
    print(f"Leyendo archivo: {INPUT_FILE}")

    with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    # 1. Extraer JSONs válidos
    print("Extrayendo JSONs válidos...")
    valid, corrupted = extract_json_objects(raw)

    print(f"   ✔ JSONs válidos: {len(valid)}")
    print(f"   ⚠ JSONs corruptos: {len(corrupted)}")

    # 2. Intentar reparar corruptos
    repaired = []
    for c in corrupted:
        obj = try_repair_json(c)
        if obj:
            repaired.append(obj)

    print(f"   ✔ JSONs reparados exitosamente: {len(repaired)}")

    all_objs = valid + repaired

    # 3. Normalizar
    print("Normalizando objetos...")
    normalized = [normalize_object(o) for o in all_objs]

    # 4. Fusionar productos
    print("Fusionando productos...")
    merged = merge_products(normalized)

    print(f"   ✔ Total productos finales: {len(merged)}")

    # 5. Guardar JSON limpio
    print(f"Guardando JSON limpio en {OUT_JSON}...")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    # 6. Guardar CSV
    print(f"Guardando CSV limpio en {OUT_CSV}...")
    pd.DataFrame(merged).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    # 7. Guardar log
    with open(OUT_LOG, "w", encoding="utf-8") as f:
        f.write("=== JSON VÁLIDOS ===\n")
        f.write(f"{len(valid)}\n\n")
        f.write("=== JSON CORRUPTOS ===\n")
        for c in corrupted[:200]:
            f.write(c + "\n\n")

    print("=== FASE 17.1 COMPLETADA ===")
    print(f"Archivos finales generados:\n - {OUT_JSON}\n - {OUT_CSV}\n - {OUT_LOG}")


if __name__ == "__main__":
    main()
