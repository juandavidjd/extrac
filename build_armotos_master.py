import os
import json
import pandas as pd
import shutil
from tqdm import tqdm
import re
from smart_csv_loader import smart_load_csv

# ======================================
# CONFIGURACIÓN
# ======================================
BASE_DIR = r"C:\adsi\EXTRACTOR_V4"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

REBUILD_CSV = os.path.join(OUTPUT_DIR, "productos_llm_semantic.csv")
REBUILD_JSON = os.path.join(OUTPUT_DIR, "productos_llm_semantic.json")

CROP_DIR = os.path.join(OUTPUT_DIR, "images", "crops")

OUT_DB = r"C:\img\Base_Datos_Armotos.csv"
OUT_CAT = r"C:\img\catalogo_kaiqi_imagenes_Armotos.csv"
OUT_IMG = r"C:\img\FOTOS_COMPETENCIA_ARMOTOS"
OUT_MASTER = r"C:\img\ARMOTOS_MASTER_2025.xlsx"


# ======================================
# FUNCIONES AUXILIARES
# ======================================

def limpiar(t):
    if not isinstance(t, str): return ""
    t = t.lower()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def evitar_colision(path):
    base, ext = os.path.splitext(path)
    c = 1
    while os.path.exists(path):
        path = f"{base}-{c}{ext}"
        c += 1
    return path


# ======================================
# 1. CARGAR CSV ARMOTOS REBUILD (tolerante)
# ======================================
print("=== FASE 18.2 — ARMOTOS MASTER BUILDER ===")
print("Cargando CSV reconstruido...")

df_raw = smart_load_csv(REBUILD_CSV)

# Buscamos columnas por contenido semántico
def detectar_columna(nombre_parcial):
    for col in df_raw.columns:
        if nombre_parcial.lower() in str(df_raw[col].iloc[0]).lower():
            return col
    return None

# Mapear columnas
col_codigo = "col_0"
col_descripcion = "col_1"
col_filename = "col_2"
col_sistema = "col_3"
col_subsistema = "col_4"
col_componente = "col_5"

print(f"[INFO] Filas cargadas: {len(df_raw)}")


# ======================================
# 2. CREAR CARPETA DE IMÁGENES
# ======================================
if os.path.exists(OUT_IMG):
    shutil.rmtree(OUT_IMG)
os.makedirs(OUT_IMG, exist_ok=True)

imagenes_rows = []
db_rows = []

print("Asignando imágenes y construyendo catálogo final...")

for _, row in tqdm(df_raw.iterrows(), total=len(df_raw)):

    filename = str(row.get(col_filename, "")).strip()
    desc = str(row.get(col_descripcion, "Producto Sin Descripción")).strip()
    codigo = str(row.get(col_codigo, "")).strip()

    sistema = row.get(col_sistema, "")
    subsistema = row.get(col_subsistema, "")
    componente = row.get(col_componente, "")

    # ==================================
    # 2.1 Buscar imagen real
    # ==================================
    src = os.path.join(CROP_DIR, filename)
    img_final = ""

    if os.path.exists(src):
        ext = os.path.splitext(filename)[1].lower()
        new_name = f"{slugify(codigo if codigo else desc)}{ext}"
        dst = os.path.join(OUT_IMG, new_name)
        dst = evitar_colision(dst)
        shutil.copy2(src, dst)
        img_final = os.path.basename(dst)

    # ==================================
    # 2.2 Guardar catálogo de imágenes
    # ==================================
    imagenes_rows.append({
        "Filename": img_final,
        "Nombre_Comercial": desc,
        "Sistema": sistema,
        "Subsistema": subsistema,
        "Componente": componente
    })

    # ==================================
    # 2.3 Guardar Base de Datos principal
    # ==================================
    db_rows.append({
        "CODIGO": codigo,
        "DESCRIPCION": desc,
        "SISTEMA": sistema,
        "SUBSISTEMA": subsistema,
        "COMPONENTE": componente,
        "IMAGEN": img_final
    })


# ======================================
# 3. GUARDAR ARCHIVOS
# ======================================
print("Guardando archivos finales...")

pd.DataFrame(db_rows).to_csv(OUT_DB, index=False, encoding="utf-8-sig")
pd.DataFrame(imagenes_rows).to_csv(OUT_CAT, index=False, encoding="utf-8-sig")

with pd.ExcelWriter(OUT_MASTER, engine='xlsxwriter') as writer:
    pd.DataFrame(db_rows).to_excel(writer, sheet_name="Base_Datos", index=False)
    pd.DataFrame(imagenes_rows).to_excel(writer, sheet_name="Catalogo_Imagenes", index=False)

print("\n=== FASE 18.2 COMPLETADA ===")
print("Archivos generados:")
print(" -", OUT_DB)
print(" -", OUT_CAT)
print(" -", OUT_IMG)
print(" -", OUT_MASTER)
