import os
import json
import re
import pandas as pd
from collections import defaultdict


# ==========================================
# CONFIG
# ==========================================
RAW_FILE      = r"C:\adsi\EXTRACTOR_V4\output\productos_llm.json"
CLEAN_FILE    = r"C:\adsi\EXTRACTOR_V4\output\productos_llm_clean.json"
OUT_REBUILT   = r"C:\adsi\EXTRACTOR_V4\output\productos_llm_rebuild.json"
OUT_REBUILT_CSV = r"C:\adsi\EXTRACTOR_V4\output\productos_llm_rebuild.csv"
LOG_FILE      = r"C:\adsi\EXTRACTOR_V4\output\rebuild_log.txt"


# ==========================================
# UTILIDADES GENERALES
# ==========================================
def normalize_text(s):
    if not isinstance(s, str): return ""
    s = s.replace("\n", " ").replace("\t", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def try_json_load(fragment):
    try:
        return json.loads(fragment)
    except:
        return None


# ==========================================
# 1) SEPARAR OBJETOS JSON PEGADOS
# ==========================================
def split_json_objects(raw):
    """
    Usa una estrategia ultra agresiva:
    - Insertar saltos entre '}{'
    - Insertar saltos entre '}\n{'
    - Insertar saltos entre '}{\s*"'
    """
    temp = raw.replace("}{", "}\n{")
    temp = temp.replace("}\n\n{", "}\n{")
    temp = re.sub(r'\}\s*\{', '}\n{', temp)
    return temp.split("\n")


# ==========================================
# 2) RECONSTRUCCIÓN: UNIFICAR FRAGMENTOS
# ==========================================
def reconstruct_fragments(lines):
    """
    Junta líneas hasta formar un JSON válido.
    """
    buffer = ""
    reconstructed = []

    for line in lines:
        line = line.strip()
        if not line: continue

        # Agregar al buffer
        buffer += " " + line

        # Intentar cargar
        obj = try_json_load(buffer.strip())
        if obj:
            reconstructed.append(obj)
            buffer = ""

        # Si el JSON empieza pero no termina, seguimos acumulando
        elif buffer.count("{") > buffer.count("}"):
            continue

        # Si tiene algo que no es JSON, limpiamos
        elif not buffer.strip().startswith("{"):
            buffer = ""

    return reconstructed


# ==========================================
# 3) LIMPIEZA Y NORMALIZACIÓN
# ==========================================
CANONICAL_KEYS = {
    "codigo": ["codigo","cod","id","sku","ref"],
    "descripcion": ["descripcion","nombre","title","producto"],
    "precio": ["precio","valor","price"],
    "empaque": ["empaque","package"],
    "imagen": ["image","img","foto","filename"],
    "familia": ["familia","categoria"],
    "marketing": ["marketing","texto_marketing"],
    "tecnico": ["tecnico","texto_tecnico"],
}


def extract_value(obj, keys):
    for k in keys:
        if k in obj:
            return normalize_text(str(obj[k]))
    return ""


def normalize_obj(o):
    clean = {}
    for canon, alias_list in CANONICAL_KEYS.items():
        clean[canon] = extract_value(o, alias_list)
    return clean


# ==========================================
# 4) AGRUPACIÓN DE PRODUCTOS
# ==========================================
def group_products(products):
    grouped = defaultdict(dict)

    for p in products:
        code = p.get("codigo")
        desc = p.get("descripcion")

        key = code if code else f"DESC-{desc[:20]}".upper()

        for k,v in p.items():
            if v and not grouped[key].get(k):
                grouped[key][k] = v

    return list(grouped.values())


# ==========================================
# PROCESO PRINCIPAL
# ==========================================
def main():

    print("=== FASE 17.2 — REBUILD MODE (Reconstrucción Avanzada) ===")
    print(f"Leyendo archivo bruto: {RAW_FILE}")

    raw = open(RAW_FILE, "r", encoding="utf-8", errors="ignore").read()

    # 1) Separar bloques grandes
    print("[1] Separando bloques JSON...")
    lines = split_json_objects(raw)
    print(f"    → {len(lines)} fragmentos detectados")

    # 2) Reconstruir JSONs válidos
    print("[2] Reconstruyendo fragmentos...")
    objs = reconstruct_fragments(lines)
    print(f"    → {len(objs)} objetos reconstruidos")

    # 3) Limpiar / normalizar
    print("[3] Normalizando objetos...")
    clean_objs = [normalize_obj(o) for o in objs]

    # 4) Fusionar
    print("[4] Agrupando productos...")
    merged = group_products(clean_objs)
    print(f"    → {len(merged)} productos finales reconstruidos")

    # 5) Exportar JSON
    print("[5] Guardando JSON final...")
    with open(OUT_REBUILT, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    # 6) Exportar CSV
    print("[6] Guardando CSV final...")
    pd.DataFrame(merged).to_csv(OUT_REBUILT_CSV, index=False, encoding="utf-8-sig")

    # 7) LOG
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("=== REBUILD MODE LOG ===\n")
        f.write(f"Fragmentos leídos: {len(lines)}\n")
        f.write(f"Objetos reconstruidos: {len(objs)}\n")
        f.write(f"Productos finales: {len(merged)}\n")

    print("\n=== FASE 17.2 COMPLETADA ===")
    print(f"Archivo reconstruido: {OUT_REBUILT}")
    print(f"CSV final: {OUT_REBUILT_CSV}")


if __name__ == "__main__":
    main()
