import json
import pandas as pd
import os
import re
from collections import Counter
from thefuzz import fuzz

INPUT_JSON = r"C:\adsi\EXTRACTOR_V4\output\productos_llm_semantic.json"
OUT_REPORT = r"C:\adsi\EXTRACTOR_V4\output\armotos_auditoria_report.txt"
OUT_DETALLADO = r"C:\adsi\EXTRACTOR_V4\output\armotos_auditoria_detallada.csv"
OUT_CLEAN_JSON = r"C:\adsi\EXTRACTOR_V4\output\armotos_productos_limpios_pre18.json"
OUT_CLEAN_CSV = r"C:\adsi\EXTRACTOR_V4\output\armotos_productos_limpios_pre18.csv"

def load_json_safely(path):
    if not os.path.exists(path):
        print("❌ Archivo no existe:", path)
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        # Cargar fallback
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()
        objs = []
        current = ""
        for line in txt.splitlines():
            if "{" in line:
                current = ""
            current += line
            if "}" in line:
                try: objs.append(json.loads(current))
                except: pass
        return objs

def normalize(x):
    if not isinstance(x, str):
        return ""
    x = x.lower().strip()
    x = re.sub(r'\s+', ' ', x)
    return x

print("=== FASE 17.4 — AUDITORÍA COMPLETA DEL ARCHIVO ===")
data = load_json_safely(INPUT_JSON)

df = pd.DataFrame(data)

report_lines = []
report = lambda x: report_lines.append(x)

report("=== INFORME DE AUDITORÍA ARMOTOS ===")
report(f"Total de productos cargados: {len(df)}")

# -------------------------------
# 1. CODIGOS DUPLICADOS
# -------------------------------
cod_col = None
for c in df.columns:
    if re.search(r'cod|sku|ref', c, re.IGNORECASE):
        cod_col = c
        break

if cod_col:
    codigos = df[cod_col].fillna("")
    dupl = codigos[codigos.duplicated()].unique()
    report(f"Códigos duplicados detectados: {len(dupl)}")
    if len(dupl) > 0:
        report("Ejemplos duplicados: " + ", ".join(dupl[:10]))

# -------------------------------
# 2. DESCRIPCIONES DUPLICADAS
# -------------------------------
desc_col = None
for c in df.columns:
    if re.search(r'desc|nombre|title', c, re.IGNORECASE):
        desc_col = c
        break

if desc_col:
    descs = df[desc_col].fillna("")
    dupl_desc = descs[descs.duplicated()].unique()
    report(f"Descripciones duplicadas: {len(dupl_desc)}")
    if len(dupl_desc) > 0:
        report("Ejemplos: " + ", ".join(dupl_desc[:10]))

# -------------------------------
# 3. CAMPOS VACÍOS
# -------------------------------
for col in df.columns:
    vacios = df[col].isna().sum()
    report(f"Column '{col}' tiene {vacios} vacíos.")

# -------------------------------
# 4. LONGITUD DE DESCRIPCIÓN
# -------------------------------
df["desc_norm"] = df[desc_col].apply(normalize)
df["desc_len"] = df["desc_norm"].apply(len)

desc_cortas = df[df["desc_len"] < 5]
report(f"Descripciones demasiado cortas (<5 chars): {len(desc_cortas)}")

# -------------------------------
# 5. IMÁGENES INEXISTENTES
# -------------------------------
img_col = None
for c in df.columns:
    if re.search(r'img|imagen|foto', c, re.IGNORECASE):
        img_col = c
        break

folder_img = r"C:\adsi\EXTRACTOR_V4\output\images\crops"

missing_imgs = 0
if img_col:
    for f in df[img_col]:
        if isinstance(f, str) and f.strip():
            if not os.path.exists(os.path.join(folder_img, f)):
                missing_imgs += 1

report(f"Imágenes faltantes: {missing_imgs}")

# -------------------------------
# 6. DUPLICADOS SOSPECHOSOS (Fuzzy)
# -------------------------------
suspects = []
names = df[desc_col].fillna("").tolist()

for i in range(len(names)-1):
    score = fuzz.token_set_ratio(names[i], names[i+1])
    if score > 92:
        suspects.append((names[i], names[i+1], score))

report(f"Posibles duplicados por similitud >92: {len(suspects)}")

# -------------------------------
# 7. GUARDADO
# -------------------------------
# Guardar informe
with open(OUT_REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))

# Guardar versión limpia (sin nulos peligrosos)
df_clean = df.fillna("")
df_clean.to_json(OUT_CLEAN_JSON, orient="records", indent=2, force_ascii=False)
df_clean.to_csv(OUT_CLEAN_CSV, index=False, encoding="utf-8-sig")

# Guardar CSV detallado
df.to_csv(OUT_DETALLADO, index=False, encoding="utf-8-sig")

print("=== FASE 17.4 COMPLETADA ===")
print("Archivos generados:")
print(" -", OUT_REPORT)
print(" -", OUT_DETALLADO)
print(" -", OUT_CLEAN_JSON)
print(" -", OUT_CLEAN_CSV)
