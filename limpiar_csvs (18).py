import os
import pandas as pd
from datetime import datetime

CRUDO_DIR = "../data/crudos"
ARCHIVOS = [f for f in os.listdir(CRUDO_DIR) if f.endswith(".csv")]

def limpiar_fecha(valor):
    try:
        return pd.to_datetime(valor, dayfirst=True).strftime("%Y-%m-%d")
    except:
        return valor  # Deja el valor original si falla

def limpiar_archivo(path, nombre):
    try:
        df = pd.read_csv(path)

        if "fecha" in df.columns:
            df["fecha"] = df["fecha"].apply(limpiar_fecha)

        if "numero" in df.columns:
            df["numero"] = df["numero"].astype(str).str.zfill(4)

        if "signo" in df.columns:
            df["signo"] = df["signo"].str.title()

        if "ganadores" in df.columns:
            df["ganadores"] = pd.to_numeric(df["ganadores"], errors="coerce").fillna(0).astype(int)

        if "premio_unit" in df.columns:
            df["premio_unit"] = pd.to_numeric(df["premio_unit"], errors="coerce").fillna(0)

        if "premio_total" in df.columns:
            df["premio_total"] = pd.to_numeric(df["premio_total"], errors="coerce").fillna(0)

        df.drop_duplicates(inplace=True)
        df.to_csv(path, index=False)
        print(f"Limpieza completada: {nombre}")
    except Exception as e:
        print(f"[ERROR] al limpiar {nombre}: {e}")

for archivo in ARCHIVOS:
    ruta = os.path.join(CRUDO_DIR, archivo)
    limpiar_archivo(ruta, archivo)
