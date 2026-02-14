#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
completar_figuras.py
- Lee la plantilla (plantilla_fig.xlsx o plantilla_fig.csv) con columnas: figura, a, b, c, d, e, f.
- Aprende el diseño de una figura a partir del primer bloque (o del más pequeño), y en particular
  sigue la pista de la fila 4 relativa (como tu referencia de C4–F4) si existe.
- Detecta automáticamente:
    * ALTURA del bloque (número de filas que componen cada figura)
    * celdas de DÍGITO (hasta 4 posiciones) — detectadas por '*', dígitos, o fila 4 (C..F)
    * celdas de DECORACIÓN (no vacías, no dígitos, fuera de posiciones de dígito)
- Completa figuras hasta N=100 copiando el mismo esqueleto y poniendo PLACEHOLDER en las posiciones de dígito.
- Respeta las figuras existentes en el archivo destino (todo_fig.xlsx/csv) si ya existen.
- Salida: todo_fig.csv y todo_fig.xlsx

Requiere pandas + openpyxl solo para .xlsx; CSV se genera siempre.
"""

import csv
import sys
import argparse
import re
from pathlib import Path
from collections import Counter

# --- Opcional XLSX ---
try:
    import pandas as pd
except Exception:
    pd = None

IN_TPL_XLSX = Path("plantilla_fig.xlsx")
IN_TPL_CSV  = Path("plantilla_fig.csv")
OUT_FIG_CSV = Path("todo_fig.csv")
OUT_FIG_XLSX= Path("todo_fig.xlsx")

COLS = ["figura", "a", "b", "c", "d", "e", "f"]
NUM_RE = re.compile(r"^\d+$")

def read_csv_rows(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.reader(f):
            rows.append([c.strip() for c in r])
    return rows

def write_csv_rows(path: Path, header, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def write_xlsx_rows(path: Path, header, rows, col_widths=None):
    if pd is None:
        print(f"⚠️ No se creó '{path.name}' (falta pandas).")
        return None
    try:
        import openpyxl  # noqa
    except Exception:
        print(f"⚠️ No se creó '{path.name}' (falta openpyxl).")
        return None
    df = pd.DataFrame(rows, columns=header)
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        sheet = path.stem
        df.to_excel(w, index=False, sheet_name=sheet)
        ws = w.sheets[sheet]
        # anchos
        try:
            from openpyxl.utils import get_column_letter
            for i, c in enumerate(header, start=1):
                width = (col_widths or {}).get(c)
                if width is None:
                    width = max(8, min(20, max(len(c), *(len(str(x)) for x in df[c].head(400))) + 2))
                ws.column_dimensions[get_column_letter(i)].width = width
        except Exception:
            pass
        return ws

def read_table(path_xlsx: Path, path_csv: Path):
    """Lee la tabla 'figura,a..f'. Prefiere XLSX; si no, CSV."""
    rows = None
    if path_xlsx.exists() and pd is not None:
        try:
            df = pd.read_excel(path_xlsx, dtype=str).fillna("")
            cols = list(df.columns)
            if cols:
                cols[0] = "figura"
                df.columns = cols
            for c in COLS:
                if c not in df.columns:
                    df[c] = ""
            df = df[COLS]
            rows = [[str(v) for v in r] for _, r in df.iterrows()]
        except Exception:
            rows = None
    if rows is None:
        rows = read_csv_rows(path_csv)
        if rows:
            head = [h.lower() for h in rows[0]]
            # si hay encabezado, quítalo
            if "figura" in head:
                rows = rows[1:]
    return rows or []

def group_figures(rows):
    """Convierte lista de filas (figura,a..f) en dict fig -> grid (lista de filas [a..f])."""
    figs = {}
    cur = None
    for r in rows:
        r = (r + [""]*7)[:7]
        head = (r[0] or "").strip()
        a_f  = [(r[i] or "").strip() for i in range(1, 7)]
        if head and head.isdigit():
            cur = int(head)
            figs.setdefault(cur, [])
            figs[cur].append(a_f)
        else:
            if cur is None:
                continue
            figs[cur].append(a_f)
    # recorta filas finales vacías
    for k, g in list(figs.items()):
        while g and all(c == "" for c in g[-1]):
            g.pop()
        if not g:
            figs.pop(k, None)
    return figs

def learn_design_from_smallest(figs):
    """
    Aprende diseño del bloque de figura 'más pequeño' (menos filas),
    como molde. Intenta detectar:
      - alto (rows_needed)
      - posiciones de dígito (digit_coords) — hasta 4
      - posiciones de decor (decor_coords)
    Si existe fila 4 (index 3), prioriza C..F en esa fila (tu referencia C4–F4).
    """
    if not figs:
        # fallback: 3 filas, dígitos en (1,2)(1,3)(2,2)(2,3); decor en marco suave
        return {
            "rows_needed": 3,
            "digit_coords": [(1,2),(1,3),(2,2),(2,3)],
            "decor_coords": {(0,1),(0,4),(2,1),(2,4),(1,0),(1,5)}
        }

    # el bloque más bajo (menos filas) suele ser el más "puro"
    candidate = min(figs.values(), key=lambda g: len(g))
    g = [(row + [""]*6)[:6] for row in candidate]
    rows_needed = len(g)
    if rows_needed < 3:
        rows_needed = 3
        while len(g) < 3:
            g.append([""]*6)

    # 1) si hay fila 4 (índice 3), priorizar columnas no vacías entre C..F
    digit_coords = []
    if rows_needed >= 4:
        row4 = g[3]
        for ci in range(2, 6):  # C..F
            if (row4[ci] or "").strip() != "":
                digit_coords.append((3, ci))

    # 2) si no obtuvimos 4, detectar por frecuencia de celdas con '*' o dígitos
    if len(digit_coords) < 4:
        cnt = Counter()
        for ri, row in enumerate(g):
            for ci, val in enumerate(row):
                s = (val or "").strip()
                if not s:
                    continue
                if s == "*" or NUM_RE.match(s):
                    cnt[(ri, ci)] += 1
        for p, _ in cnt.most_common(4 - len(digit_coords)):
            if p not in digit_coords:
                digit_coords.append(p)

    # 3) completar hasta 4 con un minicuadro centrado (C–D)
    while len(digit_coords) < 4:
        for p in [(1,2),(1,3),(2,2),(2,3)]:
            if p not in digit_coords:
                digit_coords.append(p)
            if len(digit_coords) == 4:
                break

    # 4) decor = no vacías fuera de posiciones dígito
    dset = set(digit_coords)
    decor_coords = set()
    for ri, row in enumerate(g):
        for ci, val in enumerate(row):
            s = (val or "").strip()
            if s and (ri, ci) not in dset and not NUM_RE.match(s) and s != "*":
                decor_coords.add((ri, ci))

    return {
        "rows_needed": rows_needed,
        "digit_coords": digit_coords[:4],
        "decor_coords": decor_coords
    }

def build_grid_from_design(rows_needed, digit_coords, decor_coords, placeholder="*"):
    """Crea un bloque nuevo siguiendo el diseño, usando placeholder en dígitos."""
    grid = [[""]*6 for _ in range(rows_needed)]
    for (ri, ci) in decor_coords:
        if 0 <= ri < rows_needed and 0 <= ci < 6:
            grid[ri][ci] = "."  # decoración minimal
    for (ri, ci) in digit_coords:
        if 0 <= ri < rows_needed and 0 <= ci < 6:
            grid[ri][ci] = placeholder
    return grid

def merge_existing(dest_rows):
    """Si ya existe todo_fig (xlsx o csv), lo cargamos para NO pisar figuras existentes."""
    rows = []
    if OUT_FIG_XLSX.exists() and pd is not None:
        try:
            df = pd.read_excel(OUT_FIG_XLSX, dtype=str).fillna("")
            cols = list(df.columns)
            if cols:
                cols[0] = "figura"; df.columns = cols
            for c in COLS:
                if c not in df.columns:
                    df[c] = ""
            df = df[COLS]
            rows = [[str(v) for v in r] for _, r in df.iterrows()]
        except Exception:
            rows = []
    if not rows and OUT_FIG_CSV.exists():
        rows = read_csv_rows(OUT_FIG_CSV)
        if rows and rows[0] and rows[0][0].lower() == "figura":
            rows = rows[1:]
    if not rows:
        return {}

    figs = group_figures(rows)
    return figs

def flatten_figs(figs_dict):
    """Convierte dict fig->grid a filas para escribir."""
    rows = []
    for fig in sorted(figs_dict):
        g = figs_dict[fig]
        g = [(row + [""]*6)[:6] for row in g]
        rows.append([fig] + g[0])
        for r in g[1:]:
            rows.append([""] + r)
    return rows

def main():
    ap = argparse.ArgumentParser(description="Completa figuras hasta 100 siguiendo el diseño de la plantilla (C4–F4 como guía).")
    ap.add_argument("--hasta", type=int, default=100, help="Número total de figuras deseadas (default 100)")
    ap.add_argument("--placeholder", default="*", help="Placeholder para posiciones de dígito (default '*')")
    args = ap.parse_args()

    # 1) Leer plantilla
    tpl_rows = read_table(IN_TPL_XLSX, IN_TPL_CSV)
    if not tpl_rows:
        print("❌ No se encontró 'plantilla_fig.xlsx' ni 'plantilla_fig.csv' con datos.")
        sys.exit(1)

    tpl_figs = group_figures(tpl_rows)
    if not tpl_figs:
        print("❌ La plantilla no contiene figuras válidas (columna 'figura').")
        sys.exit(1)

    # 2) Aprender diseño (usando el bloque más pequeño y, si existe, fila 4 como referencia C4–F4)
    design = learn_design_from_smallest(tpl_figs)
    rows_needed   = design["rows_needed"]
    digit_coords  = design["digit_coords"]
    decor_coords  = design["decor_coords"]

    # 3) Traer figuras ya existentes en salida (para no pisarlas)
    existing_out = merge_existing(OUT_FIG_XLSX)

    # 4) Partimos de las figuras de la plantilla como base
    result = {}
    for fig, g in tpl_figs.items():
        result[fig] = [(row + [""]*6)[:6] for row in g]

    # 5) Si hay figuras ya en salida, respetarlas (prioridad a lo existente en destino)
    for fig, g in existing_out.items():
        result[fig] = [(row + [""]*6)[:6] for row in g]

    # 6) Completar hasta N con diseño aprendido
    current_max = max(result.keys()) if result else 0
    target = max(args.hasta, current_max)
    for fig in range(1, target+1):
        if fig not in result:
            result[fig] = build_grid_from_design(rows_needed, digit_coords, decor_coords, placeholder=args.placeholder)

    # 7) Guardar
    out_rows = flatten_figs(result)
    write_csv_rows(OUT_FIG_CSV, COLS, out_rows)
    _ = write_xlsx_rows(OUT_FIG_XLSX, COLS, out_rows,
                        col_widths={"figura":6,"a":5,"b":5,"c":5,"d":5,"e":5,"f":5})

    # 8) Resumen
    print("\n✅ Figuras completadas.")
    print(f"   Diseño aprendido: alto={rows_needed} filas; dígitos en={sorted(digit_coords)}; decor={len(decor_coords)} celdas.")
    print(f"   Total figuras generadas: {target}")
    print("   Archivos:")
    print("   - todo_fig.csv")
    print("   - todo_fig.xlsx")
    print("\nSiguiente paso (render en consola, modo diseño de plantilla):")
    print("   python leer_figuras.py --input todo_fig.xlsx --render tiles --no-trim-h")

if __name__ == "__main__":
    main()
