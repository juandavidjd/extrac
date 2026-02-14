#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
limpiar_csvs.py — robusto/flexible/actualizado
- Limpia todos los CSV de --src y guarda en --dst.
- Si --src no existe o no hay CSVs, sale RC=0 (no rompe el pipeline).
- Quita filas vacías, recorta espacios, conserva todo como texto.
- Acepta punto y coma o coma automáticamente.
"""

import sys
import argparse
import csv
from pathlib import Path
import pandas as pd

VERSION = "2025-08-13-r1"

def leer_csv_cauto(path: Path) -> pd.DataFrame:
    # sep=None + engine="python" infiere delimitador; dtype=str para no perder ceros a la izquierda
    return pd.read_csv(path, sep=None, engine="python", encoding="utf-8", dtype=str)

def limpiar_df(df: pd.DataFrame) -> pd.DataFrame:
    # Recorta strings y elimina filas totalmente vacías
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.dropna(how="all")
    return df

def procesar_archivo(origen: Path, destino: Path) -> bool:
    try:
        df = leer_csv_cauto(origen)
        df = limpiar_df(df)
        destino.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(destino, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_NONNUMERIC)
        print(f"[OK] {origen.name} → {destino.name} ({len(df)} filas)")
        return True
    except Exception as e:
        print(f"[ERROR] {origen.name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Limpia CSVs de una carpeta y guarda en otra.")
    base = Path(__file__).resolve().parents[1]  # C:\RadarPremios
    parser.add_argument("--src", default=str(base / "data" / "crudos"), help="Carpeta origen (CSVs crudos)")
    parser.add_argument("--dst", default=str(base / "data" / "limpio"), help="Carpeta destino (CSVs limpios)")
    parser.add_argument("--version", action="store_true", help="Imprime versión y sale")
    args = parser.parse_args()

    if args.version:
        print(VERSION)
        sys.exit(0)

    src = Path(args.src).resolve()
    dst = Path(args.dst).resolve()

    if not src.exists():
        print(f"[INFO] Origen no existe: {src}")
        print("[INFO] Nada que limpiar. Saliendo (RC=0).")
        sys.exit(0)

    archivos = sorted(src.glob("*.csv"))
    if not archivos:
        print(f"[INFO] No hay CSV en {src}. Nada que hacer. (RC=0)")
        sys.exit(0)

    ok = 0
    for a in archivos:
        if procesar_archivo(a, dst / a.name):
            ok += 1

    print(f"[RESUMEN] {ok}/{len(archivos)} limpiados.")
    sys.exit(0 if ok == len(archivos) else 1)

if __name__ == "__main__":
    main()
