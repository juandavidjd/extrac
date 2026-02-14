import os
import re
import pandas as pd
from pdf2image import convert_from_path
from PIL import Image
import pytesseract

# ================================================
# CONFIGURACIONES
# ================================================
BASE_DIR = r"C:\scrap"
PDF_FILE = "CATALOGO NOVIEMBRE V01-2025 NF.pdf"
OUTPUT_DIR = os.path.join(BASE_DIR, "EXTRA_ARMOTOS")

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "pages"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "crops"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "imagenes_por_codigo"), exist_ok=True)

# ================================================
# PATRONES
# ================================================
REGEX_COD = re.compile(r"(COD[: ]{0,3}|CÓDIGO[: ]{0,3})?(\d{4,5})")
REGEX_PRECIO = re.compile(r"\$[\s]*([\d\.\,]+)")
REGEX_CATEGORIA_MAYUS = re.compile(r"^[A-ZÁÉÍÓÚÑ\s]{5,}$")

def limpiar_precio(p):
    p = p.replace(".", "").replace(",", "").replace(" ", "")
    try:
        return int(p)
    except:
        return None

# ================================================
# PROCESAR PDF → IMÁGENES
# ================================================
print("📄 Convirtiendo PDF a imágenes...")
pages = convert_from_path(os.path.join(BASE_DIR, PDF_FILE), dpi=200)

page_paths = []

for i, page in enumerate(pages):
    out_path = os.path.join(OUTPUT_DIR, "pages", f"page_{i+1}.png")
    page.save(out_path, "PNG")
    page_paths.append(out_path)

print(f"✔ {len(page_paths)} páginas convertidas.")

# ================================================
# EXTRAER TEXTO + BLOQUES
# ================================================
productos = []
variantes = []
bloque_actual = {
    "categoria": None,
    "productos": []
}

def procesar_bloque(bloque):
    for pr in bloque["productos"]:
        productos.append(pr)

for page_num, img_path in enumerate(page_paths, start=1):
    print(f"🔍 OCR página {page_num}...")

    img = Image.open(img_path)
    texto = pytesseract.image_to_string(img, lang="spa")

    lineas = [l.strip() for l in texto.split("\n") if l.strip()]

    categoria_detectada = None
    productos_pagina = []

    for linea in lineas:

        # -----------------------
        # Detectar categoría
        # -----------------------
        if REGEX_CATEGORIA_MAYUS.match(linea) and len(linea.split()) <= 6:
            categoria_detectada = linea
            continue

        # -----------------------
        # Detectar códigos
        # -----------------------
        cod_match = REGEX_COD.search(linea)
        precio_match = REGEX_PRECIO.search(linea)

        if cod_match:
            codigo = cod_match.group(2)

            productos_pagina.append({
                "codigo": codigo,
                "descripcion": linea,
                "precio": None,
                "categoria": categoria_detectada,
                "pagina": page_num,
                "imagen": None
            })
            continue

        # -----------------------
        # Detectar precios
        # -----------------------
        if precio_match and productos_pagina:
            precio_raw = precio_match.group(1)
            precio = limpiar_precio(precio_raw)

            productos_pagina[-1]["precio"] = precio
            continue

        # -----------------------
        # Descripción extendida
        # -----------------------
        if productos_pagina and not cod_match and not precio_match:
            productos_pagina[-1]["descripcion"] += " " + linea

    # Guardar página
    for pr in productos_pagina:
        productos.append(pr)

# ================================================
# GUARDAR CSV
# ================================================
df = pd.DataFrame(productos)
df.to_csv(os.path.join(OUTPUT_DIR, "Catalogo_ARMOTOS_MASTER.csv"), index=False, encoding="utf-8-sig")

print("\n✨ PROCESO COMPLETADO")
print(f"Total productos detectados: {len(df)}")
print(f"Archivo generado: {OUTPUT_DIR}\\Catalogo_ARMOTOS_MASTER.csv")
