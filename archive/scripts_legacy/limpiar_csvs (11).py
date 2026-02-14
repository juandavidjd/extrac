#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
limpiar_csvs.py — versión estable para pipeline (2025-08-13-r2)

Objetivo:
- No romper el master si la carpeta de origen no existe o no tiene CSVs (RC=0).
- Limpiar CSVs crudos y dejarlos en data/limpio.
- Manejar delimitador automático (coma/punto y coma/tab), UTF-8/BOM.
- Conservar ceros a la izquierda (todo como texto).
- Mensajería clara para logs.

Uso típico (pipeline):
  python -X utf8 limpiar_csvs.py
Opcional:
  --src C:\RadarPremios\data\crudos
  --dst C:\RadarPremios\data\limpio
  --force-create-src  (crea la carpeta origen si no existe, vacía)
  --version
"""

from __future__ import annotations
import sys
import csv
import argparse
from pathlib import Path

# pandas es requerido por otras etapas del proyecto
import pandas as pd

VERSION = "2025-08-13-r2"


def info(msg: str) -> None:
    print(f"[INFO] {msg}")


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def err(msg: str) -> None:
    print(f"[ERROR] {msg}")


def infer_sep(text_sample: str) -> str | None:
    """
    Heurística simple por si el motor de pandas falla:
    Prioriza ';', luego ',', luego tab.
    """
    priorities = [';', ',', '\t', '|']
    counts = {sep: text_sample.count(sep) for sep in priorities}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else None


def read_csv_safe(path: Path) -> pd.DataFrame:
    """
    Lee un CSV con máxima tolerancia:
    - dtype=str para no perder ceros.
    - engine=python para permitir sep=None (autodetección).
    - si falla, intenta con una heurística de separador.
    """
    # 1) intento estándar con autodetección
    try:
        return pd.read_csv(
            path,
            sep=None,               # autodetecta (coma/;/\t/|)
            engine="python",
            dtype=str,
            encoding="utf-8",
            na_filter=False,        # no convertir en NaN (mantenemos texto)
            quoting=csv.QUOTE_MINIMAL,
            on_bad_lines="skip",    # salta líneas mal formadas
        )
    except Exception:
        # 2) fallback: heurística de separador
        try:
            sample = path.read_text(encoding="utf-8", errors="ignore")[:4000]
            sep = infer_sep(sample) or ","
            return pd.read_csv(
                path,
                sep=sep,
                engine="python",
                dtype=str,
                encoding="utf-8",
                na_filter=False,
                quoting=csv.QUOTE_MINIMAL,
                on_bad_lines="skip",
            )
        except Exception as e2:
            raise RuntimeError(f"no se pudo leer con pandas (fallback): {e2}") from e2


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    # recorta espacios de strings; elimina filas completamente vacías (por si vienen en blanco)
    if df.empty:
        return df
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    # Si alguna columna viene vacía con '' y usamos na_filter=False, dropna(how='all') no sirve.
    # Transformamos filas 'todo vacío' a None para poder filtrar.
    df = df.replace("", pd.NA)
    df = df.dropna(how="all")
    # devolvemos a string (para mantener consistencia) y reponemos '' en lugar de <NA>
    df = df.fillna("")
    return df


def write_csv_safe(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(
        out_path,
        index=False,
        encoding="utf-8-sig",      # BOM amigable para Excel
        quoting=csv.QUOTE_NONNUMERIC,  # celdas de texto entre comillas; números quedan libres
    )


def process_file(src: Path, dst: Path) -> bool:
    try:
        df = read_csv_safe(src)
        df = clean_df(df)
        write_csv_safe(df, dst)
        ok(f"{src.name} → {dst.name} ({len(df)} filas)")
        return True
    except Exception as e:
        err(f"{src.name}: {e}")
        return False


def default_paths() -> tuple[Path, Path]:
    # Estructura del repo: scripts está en C:\RadarPremios\scripts → base = padre
    base = Path(__file__).resolve().parents[1]  # C:\RadarPremios
    src = base / "data" / "crudos"
    dst = base / "data" / "limpio"
    return src, dst


def main() -> int:
    parser = argparse.ArgumentParser(description="Limpia CSVs de una carpeta a otra (tolerante y estable).")
    src_def, dst_def = default_paths()
    parser.add_argument("--src", default=str(src_def), help="Carpeta origen de CSVs crudos.")
    parser.add_argument("--dst", default=str(dst_def), help="Carpeta destino para CSVs limpios.")
    parser.add_argument("--force-create-src", action="store_true",
                        help="Si no existe --src, la crea vacía y sale con RC=0 (no rompe pipeline).")
    parser.add_argument("--version", action="store_true", help="Imprime la versión y sale.")
    args = parser.parse_args()

    if args.version:
        print(VERSION)
        return 0

    src = Path(args.src).resolve()
    dst = Path(args.dst).resolve()

    # Si no existe origen
    if not src.exists():
        if args.force-create-src:
            src.mkdir(parents=True, exist_ok=True)
            warn(f"Origen no existía, creado: {src}")
            info("Nada que limpiar. Saliendo (RC=0).")
            return 0
        else:
            info(f"Origen no existe: {src}")
            info("Nada que limpiar. Saliendo (RC=0).")
            return 0

    # Buscar CSVs
    files = sorted(src.glob("*.csv"))
    if not files:
        info(f"No hay CSVs en {src}. Nada que hacer. (RC=0)")
        # Aun así, aseguramos que la carpeta destino exista
        dst.mkdir(parents=True, exist_ok=True)
        return 0

    ok_count = 0
    for f in files:
        if process_file(f, dst / f.name):
            ok_count += 1

    total = len(files)
    print(f"[RESUMEN] {ok_count}/{total} limpiados.")

    # Si alguno falló, devolvemos RC=1 para detectar problemas en datos particulares,
    # pero el script ya hizo el mayor esfuerzo sin detener todo abruptamente.
    return 0 if ok_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
