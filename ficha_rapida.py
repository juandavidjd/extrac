#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ficha_rapida.py
Crea una figura/ficha a partir de 4 cifras (p.ej. 2582) con un diseño compacto:
- 3 filas x 6 columnas (a..f)
- Decoración mínima con puntitos en marco
- Los 4 dígitos van al centro (C–D en dos filas)

Uso:
  python ficha_rapida.py 2582
  python ficha_rapida.py 2582 --boxes
  python ficha_rapida.py 2582 --save ficha.csv
"""

import sys, csv, argparse

# Posiciones (fila, col) 0-index
DIGIT_POS = [(1,2),(1,3),(2,2),(2,3)]                  # C–D dos filas
DECOR_POS = [(0,1),(0,4),(2,1),(2,4),(1,0),(1,5)]      # puntitos marco

def build_grid(combo: str):
    """Devuelve grid 3x6 (lista de filas con 6 strings) para la ficha."""
    if len(combo) != 4 or not combo.isdigit():
        raise ValueError("La combinación debe tener exactamente 4 dígitos, ej. 2582.")
    g = [[""]*6 for _ in range(3)]
    for (r,c) in DECOR_POS:
        g[r][c] = "·"
    digs = list(combo)
    for k,(r,c) in enumerate(DIGIT_POS):
        g[r][c] = digs[k]
    return g

# -------- Render en consola --------
def render_tiles(grid, gap=1):
    sep = " "*gap
    lines=[]
    for row in grid:
        # imprime caracteres tal cual; vacío => espacio
        cells = [x if x!="" else " " for x in row]
        lines.append(sep.join(cells))
    return lines

def render_boxes(grid, gap=1):
    sep = " "*gap
    def box(v):
        s = v if v!="" else " "
        return ["┌─┐", f"│{s}│", "└─┘"]
    l1=l2=l3=""
    for i,v in enumerate(row := grid[0]):
        b=box(v); l1+= ("" if i==0 else sep)+b[0]; l2+= ("" if i==0 else sep)+b[1]; l3+= ("" if i==0 else sep)+b[2]
    out=[l1,l2,l3]
    for rr in grid[1:]:
        l1=l2=l3=""
        for i,v in enumerate(rr):
            b=box(v); l1+= ("" if i==0 else sep)+b[0]; l2+= ("" if i==0 else sep)+b[1]; l3+= ("" if i==0 else sep)+b[2]
        out += [l1,l2,l3]
    return out

def save_csv(path, grid):
    """Guarda una sola figura tipo todo_fig.csv (con encabezados)."""
    header = ["figura","a","b","c","d","e","f"]
    rows = [[1]+grid[0], [""]+grid[1], [""]+grid[2]]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def main():
    ap = argparse.ArgumentParser(description="Crea una ficha pulida (3x6) para 4 dígitos.")
    ap.add_argument("combo", help="Combinación de 4 dígitos, ej. 2582")
    ap.add_argument("--boxes", action="store_true", help="Render en modo cajitas (3x3 por celda)")
    ap.add_argument("--gap", type=int, default=1, help="Espacio entre columnas (default 1)")
    ap.add_argument("--save", metavar="FICHERO", help="Guardar CSV compatible (ej. ficha.csv)")
    args = ap.parse_args()

    grid = build_grid(args.combo)

    print("\nFigura (tiles):" if not args.boxes else "\nFigura (boxes):")
    lines = render_boxes(grid, gap=args.gap) if args.boxes else render_tiles(grid, gap=args.gap)
    for ln in lines: print(ln)
    print()

    if args.save:
        save_csv(args.save, grid)
        print(f"💾 Guardado: {args.save} (formato todo_fig.csv con 1 figura)")

if __name__ == "__main__":
    main()
