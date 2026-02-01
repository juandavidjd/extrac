# -*- coding: utf-8 -*-
"""
generar_plantilla.py
Crea 'plantilla_fig.csv' con 36 figuras en formato de BLOQUES para leer_figuras.py.
Cada figura tiene exactamente 4 huecos (marcados con '*').

Lógica por defecto: ficha 2x2 centrada (dos filas, columnas c y d).
Incluye patrones alternativos y rotación opcional.

Uso:
  python generar_plantilla.py
  python generar_plantilla.py --patron center2x2
  python generar_plantilla.py --patron fila4
  python generar_plantilla.py --patron col2col2
  python generar_plantilla.py --patron cruz
  python generar_plantilla.py --patron L
  python generar_plantilla.py --patron diag
  python generar_plantilla.py --rotate   # rota patrones en las 36 figuras
  python generar_plantilla.py --output plantilla_fig.csv
"""

import csv
import argparse
from typing import List, Tuple

# Grid base: 6 columnas a..f
COLS = 6

def blank_row() -> List[str]:
    return [""] * COLS

def apply_holes(rows: List[List[str]], holes: List[Tuple[int,int]]) -> List[List[str]]:
    """
    rows: lista de filas (cada fila len=6)
    holes: lista de (r,c) 0-indexed donde colocar '*'
    """
    out = [r[:] for r in rows]
    for r, c in holes:
        if 0 <= r < len(out) and 0 <= c < COLS:
            out[r][c] = "*"
    return out

# ---------- Patrones (4 huecos cada uno) ----------
def pattern_center2x2() -> List[List[str]]:
    """
    2 filas x 6 columnas, huecos en columnas c,d para filas 0 y 1
    (c=2, d=3 en índice 0)
    """
    rows = [blank_row(), blank_row()]
    holes = [(0,2),(0,3),(1,2),(1,3)]
    return apply_holes(rows, holes)

def pattern_fila4() -> List[List[str]]:
    """Una sola fila con 4 huecos contiguos centrados (b..e)."""
    rows = [blank_row()]
    holes = [(0,1),(0,2),(0,3),(0,4)]
    return apply_holes(rows, holes)

def pattern_col2col2() -> List[List[str]]:
    """Dos columnas centrales con dos huecos cada una (4 en total)."""
    rows = [blank_row(), blank_row(), blank_row()]
    holes = [(0,2),(1,2),(1,3),(2,3)]
    return apply_holes(rows, holes)

def pattern_cruz() -> List[List[str]]:
    """Cruz pequeña centrada (3 filas), usando 4 puntos de la cruz."""
    rows = [blank_row(), blank_row(), blank_row()]
    holes = [(0,2),(1,2),(1,3),(2,3)]
    return apply_holes(rows, holes)

def pattern_L() -> List[List[str]]:
    """Forma L (3 filas), 3 vertical + 1 horizontal."""
    rows = [blank_row(), blank_row(), blank_row()]
    holes = [(0,2),(1,2),(2,2),(2,3)]
    return apply_holes(rows, holes)

def pattern_diag() -> List[List[str]]:
    """Diagonal 2x2 inclinada (arriba izq -> abajo der)."""
    rows = [blank_row(), blank_row(), blank_row()]
    holes = [(0,2),(1,3),(1,2),(2,3)]
    return apply_holes(rows, holes)

PATTERNS = {
    "center2x2": pattern_center2x2,
    "fila4":     pattern_fila4,
    "col2col2":  pattern_col2col2,
    "cruz":      pattern_cruz,
    "L":         pattern_L,
    "diag":      pattern_diag,
}

ROTATION_ORDER = ["center2x2", "fila4", "col2col2", "cruz", "L", "diag"]

def make_figure_block(pattern_name: str) -> List[List[str]]:
    if pattern_name not in PATTERNS:
        raise ValueError(f"Patrón desconocido: {pattern_name}")
    return PATTERNS[pattern_name]()

def validate_block(block: List[List[str]]) -> None:
    # Debe haber exactamente 4 '*' en el bloque
    count = sum(1 for row in block for v in row if v != "")
    if count != 4:
        raise ValueError(f"El patrón produce {count} huecos; deben ser 4.")

def write_template(output: str, pattern: str, rotate: bool) -> None:
    with open(output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["figura","a","b","c","d","e","f"])
        for fig in range(1, 37):
            patt = (ROTATION_ORDER[(fig-1) % len(ROTATION_ORDER)]) if rotate else pattern
            block = make_figure_block(patt)
            validate_block(block)
            # primera fila del bloque con id de figura
            w.writerow([fig] + block[0])
            # filas siguientes con primera celda vacía
            for row in block[1:]:
                w.writerow([""] + row)

def main():
    ap = argparse.ArgumentParser(description="Genera plantilla_fig.csv con 36 figuras (4 huecos por figura).")
    ap.add_argument("--output", default="plantilla_fig.csv", help="Ruta de salida (default: plantilla_fig.csv)")
    ap.add_argument("--patron", choices=list(PATTERNS.keys()), default="center2x2",
                    help="Patrón por figura (default: center2x2)")
    ap.add_argument("--rotate", action="store_true",
                    help="Rota patrones (center2x2,fila4,col2col2,cruz,L,diag) a lo largo de las 36 figuras")
    args = ap.parse_args()

    write_template(args.output, pattern=args.patron, rotate=args.rotate)
    print(f"✅ Plantilla generada en '{args.output}'.")
    if args.rotate:
        print(f"   Patrones rotados en orden: {', '.join(ROTATION_ORDER)}")
    else:
        print(f"   Patrón usado: {args.patron}")

if __name__ == "__main__":
    main()
