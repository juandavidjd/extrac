# -*- coding: utf-8 -*-
"""
generar_todo_sum.py
Genera 'todo_sum.csv' a partir de 'todo_pos.csv' con combinaciones aleatorias de 4 cifras.

- Lee 'todo_pos.csv' (UTF-8 con BOM recomendado).
- Detecta columnas flexibles: 'posicion'/'posición' y 'suma' o 'suma_cruda'.
- Ordena por posiciones 1º..8º (toma la primera ocurrencia de cada índice).
- Modos de combinación (sobre índices 0..7):
    * any4      : cualquier 4 índices (C(8,4)=70)
    * bloques   : ventanas contiguas de 4 (5 combos)
    * 2y2       : 2 de [0..3] y 2 de [4..7] preservando orden (36 combos)
- Filtros:
    * --require-zero  : exigir al menos un 0 en la combinación
    * --exclude-zero  : excluir combinaciones que contengan 0
- Salida:
    * 'todo_sum.csv' con una columna 'combinacion' (UTF-8 con BOM)

Uso:
  python generar_todo_sum.py
  python generar_todo_sum.py --n 50 --mode any4 --require-zero --seed 42
  python generar_todo_sum.py --mode bloques
  python generar_todo_sum.py --mode 2y2 --output otras_sum.csv
"""

import argparse
import re
import sys
import random
from itertools import combinations
from typing import List, Tuple

import pandas as pd

POS_PAT = re.compile(r"^\s*(\d+)")
POS_COL_CANDIDATES = ["posicion", "posición", "posiciÃ³n", "posici�n"]
SUM_COL_CANDIDATES = ["suma", "suma_cruda"]

def simplificar(num: int) -> int:
    """Reduce un entero sumando dígitos hasta un solo dígito (0..9)."""
    while num >= 10:
        num = sum(int(d) for d in str(num))
    return num

def _find_col(df: pd.DataFrame, candidates: List[str]) -> str | None:
    """Encuentra columna por nombre (tolerante a tildes/encoding)."""
    # matching directo (lowercase)
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    # matching normalizado (sin no-alfas)
    def norm(s: str) -> str:
        return re.sub(r"[^a-záéíóúñ]", "", s.lower())
    norm_map = {norm(c): c for c in df.columns}
    for cand in candidates:
        n = norm(cand)
        if n in norm_map:
            return norm_map[n]
    return None

def _extract_pos_index(value) -> int | None:
    if pd.isna(value):
        return None
    m = POS_PAT.match(str(value))
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None

def cargar_sumas(path: str) -> List[int]:
    """Carga las 8 cifras (1..8) desde todo_pos.csv. Usa 'suma' o simplifica 'suma_cruda'."""
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="utf-8")

    if df.empty:
        raise ValueError("todo_pos.csv está vacío.")

    col_pos = _find_col(df, POS_COL_CANDIDATES)
    if not col_pos:
        # heurística: toma una columna con valores tipo "1º" o números
        for c in df.columns:
            if df[c].astype(str).str.match(r"^\s*\d+").any():
                col_pos = c
                break
    if not col_pos:
        raise ValueError("No se encontró columna de posiciones (ej. 'posicion').")

    col_sum = _find_col(df, ["suma"])
    use_cruda = False
    if not col_sum:
        col_sum = _find_col(df, ["suma_cruda"])
        if not col_sum:
            raise ValueError("No se encontró columna 'suma' ni 'suma_cruda'.")
        use_cruda = True

    rows: List[Tuple[int,int]] = []
    for _, r in df.iterrows():
        idx = _extract_pos_index(r.get(col_pos, ""))
        if idx is None:
            continue
        val = r.get(col_sum, "")
        try:
            v = int(val)
        except Exception:
            continue
        if use_cruda:
            v = simplificar(v)
        rows.append((idx, v))

    if not rows:
        raise ValueError("No se pudieron extraer posiciones/sumas válidas.")

    # Ordena por posición y toma la primera aparición de cada índice 1..8
    rows.sort(key=lambda x: x[0])
    by_idx = {}
    for idx, v in rows:
        if 1 <= idx <= 8 and idx not in by_idx:
            by_idx[idx] = v

    sums = [by_idx[i] for i in range(1, 9) if i in by_idx]
    if len(sums) != 8:
        raise ValueError(f"Se esperaban 8 posiciones, se obtuvieron {len(sums)}. Revisa '{path}'.")
    return sums  # p.ej. [0,8,2,5,8,7,1,4]

def generar_pool_indices(mode: str) -> List[Tuple[int,int,int,int]]:
    """Genera el pool de combinaciones de índices según el modo."""
    idxs = list(range(8))
    if mode == "any4":
        return list(combinations(idxs, 4))  # 70
    if mode == "bloques":
        return [(0,1,2,3), (1,2,3,4), (2,3,4,5), (3,4,5,6), (4,5,6,7)]  # 5
    if mode == "2y2":
        left = list(combinations(range(0,4), 2))
        right = list(combinations(range(4,8), 2))
        return [a + b for a in left for b in right]  # 36
    raise ValueError("Modo inválido. Usa: any4 | bloques | 2y2")

def filtrar_por_cero(indices_pool: List[Tuple[int,int,int,int]], sums: List[int],
                     require_zero: bool, exclude_zero: bool) -> List[Tuple[int,int,int,int]]:
    if require_zero and exclude_zero:
        raise ValueError("No puede exigir y excluir cero a la vez.")
    out = []
    for idxs in indices_pool:
        vals = [sums[i] for i in idxs]
        if require_zero and 0 not in vals:
            continue
        if exclude_zero and 0 in vals:
            continue
        out.append(idxs)  # devolvemos ÍNDICES
    return out

def elegir_combos(indices_validos: List[Tuple[int,int,int,int]], n: int, seed: int | None,
                  allow_repeats: bool) -> List[Tuple[int,int,int,int]]:
    if seed is not None:
        random.seed(seed)
    if not indices_validos:
        return []
    if allow_repeats and n > 0:
        return [random.choice(indices_validos) for _ in range(n)]
    # sin repetición
    k = min(n, len(indices_validos))
    return random.sample(indices_validos, k)

def main():
    ap = argparse.ArgumentParser(description="Genera 'todo_sum.csv' con combinaciones de 4 cifras desde 'todo_pos.csv'.")
    ap.add_argument("--input", default="todo_pos.csv", help="Ruta del CSV de posiciones (default: todo_pos.csv)")
    ap.add_argument("--output", default="todo_sum.csv", help="Ruta de salida (default: todo_sum.csv)")
    ap.add_argument("--n", type=int, default=50, help="Cantidad de combinaciones (default: 50)")
    ap.add_argument("--mode", choices=["any4","bloques","2y2"], default="any4", help="Modo de combinaciones (default: any4)")
    ap.add_argument("--require-zero", action="store_true", help="Exigir al menos un 0 en cada combinación")
    ap.add_argument("--exclude-zero", action="store_true", help="Excluir combinaciones que contengan 0")
    ap.add_argument("--seed", type=int, default=None, help="Semilla aleatoria (opcional)")
    ap.add_argument("--allow-repeats", action="store_true", help="Permite repetir combinaciones si pides más que el pool")
    ap.add_argument("--debug", action="store_true", help="Imprime detalles del proceso")
    args = ap.parse_args()

    try:
        sums = cargar_sumas(args.input)
    except Exception as e:
        print(f"❌ Error cargando '{args.input}': {e}", file=sys.stderr)
        sys.exit(1)

    pool = generar_pool_indices(args.mode)
    pool_valid = filtrar_por_cero(pool, sums, args.require_zero, args.exclude_zero)

    if not pool_valid:
        print("❌ No hay combinaciones válidas con los filtros y modo elegidos.", file=sys.stderr)
        sys.exit(1)

    chosen_indices = elegir_combos(pool_valid, args.n, args.seed, args.allow_repeats)

    # Convertir a strings de 4 cifras
    combos_str = ["".join(str(sums[i]) for i in idxs) for idxs in chosen_indices]

    # Guardar CSV en UTF-8 BOM (excel-friendly)
    pd.DataFrame({"combinacion": combos_str}).to_csv(args.output, index=False, encoding="utf-8-sig")

    if args.debug:
        print(f"Base (8 cifras): {sums}")
        print(f"Modo: {args.mode} | Pool total: {len(pool)} | Válidos con filtros: {len(pool_valid)}")
        print(f"Solicitadas: {args.n} | Generadas: {len(combos_str)} | allow_repeats={args.allow_repeats}")
        if not args.allow_repeats and args.n > len(pool_valid):
            print("⚠️  Se solicitó más de lo disponible sin repetición; se devolvió el máximo posible.")

    print(f"✅ Generado '{args.output}' con {len(combos_str)} combinaciones.")

if __name__ == "__main__":
    main()
