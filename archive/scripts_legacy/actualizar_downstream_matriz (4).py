
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Actualiza automáticamente las tablas que dependen de `matriz_astro_luna`.
- Omite VISTAS y tablas excluidas por defecto (otros sorteos y fuentes).
- Solo refresca tablas cuya totalidad de columnas NOT NULL (sin default y no-PK)
  existen en `matriz_astro_luna`. El resto se omiten y se reportan.
- Inserta las columnas COMUNES (intersección) en el mismo orden.
- Soporta --targets para limitar, --exclude para añadir exclusiones, --dry-run y --reporte CSV.

Uso básico:
  python actualizar_downstream_matriz.py --db radar_premios.db
Con dry-run (simulación):
  python actualizar_downstream_matriz.py --db radar_premios.db --dry-run
Solo algunas tablas:
  python actualizar_downstream_matriz.py --db radar_premios.db --targets cuando_1_es_unidad resumen_matriz_aslu
Añadir exclusiones:
  python actualizar_downstream_matriz.py --db radar_premios.db --exclude tabla_x tabla_y
Exportar reporte:
  python actualizar_downstream_matriz.py --db radar_premios.db --reporte reporte.csv
"""

import argparse
import sqlite3
from contextlib import contextmanager
from typing import List, Optional, Sequence, Tuple

# --------- Exclusiones por defecto (NO se tocan) ---------
DEFAULT_EXCLUDES = [
    # Fuentes / base
    "astroluna", "astro_luna",
    # Otros sorteos (no-Astroluna)
    "tolima", "huila", "manizales", "quindio", "medellin", "boyaca",
    "baloto_premios", "baloto_resultados", "revancha_premios", "revancha_resultados",
]

MATRIX_TABLE = "matriz_astro_luna"

@contextmanager
def tx(conn: sqlite3.Connection):
    try:
        conn.execute("BEGIN IMMEDIATE;")
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise

def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None

def get_objects(conn: sqlite3.Connection) -> List[Tuple[str,str]]:
    sql = (
        "SELECT name, type FROM sqlite_master "
        "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' "
        "ORDER BY type DESC, name"
    )
    return conn.execute(sql).fetchall()

def get_cols(conn: sqlite3.Connection, name: str):
    # cid, name, type, notnull, dflt_value, pk
    return conn.execute(f"PRAGMA table_info('{name}')").fetchall()

def count_rows(conn: sqlite3.Connection, name: str) -> int:
    return conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]

def required_cols(conn: sqlite3.Connection, name: str):
    cols = get_cols(conn, name)
    all_cols = [c[1] for c in cols]
    req = [c[1] for c in cols if c[3] == 1 and c[5] == 0 and c[4] is None]  # NOT NULL & no-PK & sin default
    return all_cols, req

def refresh_from_matrix(conn: sqlite3.Connection, targets: Optional[Sequence[str]], exclude: Optional[Sequence[str]], dry_run: bool):
    if not table_exists(conn, MATRIX_TABLE):
        raise SystemExit(f"No existe la tabla '{MATRIX_TABLE}'.")
    src_cols = [c[1] for c in get_cols(conn, MATRIX_TABLE)]
    objs = get_objects(conn)

    # Merge de exclusiones: por defecto + explícitas
    exclude_set = set(DEFAULT_EXCLUDES)
    if exclude:
        exclude_set.update(exclude)

    acciones = []  # (tabla, tipo, accion, filas_antes, filas_despues)

    for name, otype in objs:
        if otype == "view":
            acciones.append((name, otype, "omitida (vista)", None, None))
            continue
        if name == MATRIX_TABLE or name in exclude_set:
            acciones.append((name, otype, "omitida (fuente/excluida)", None, None))
            continue
        if targets and name not in targets:
            continue

        dst_all, dst_req = required_cols(conn, name)
        comunes = [c for c in dst_all if c in src_cols]
        puede = set(dst_req).issubset(set(src_cols)) and len(comunes) > 0

        if not puede:
            faltan = [c for c in dst_req if c not in src_cols]
            acciones.append((name, otype, f"omitida (faltan requeridas: {faltan})", None, None))
            continue

        antes = count_rows(conn, name)
        if not dry_run:
            with tx(conn):
                conn.execute(f'DELETE FROM "{name}"')
                cols_sql = ", ".join([f'"{c}"' for c in comunes])
                conn.execute(f'INSERT INTO "{name}" ({cols_sql}) SELECT {cols_sql} FROM "{MATRIX_TABLE}"')
        despues = count_rows(conn, name) if not dry_run else None
        acciones.append((name, otype, f"refrescada desde {MATRIX_TABLE}", antes, despues))

    return acciones

def main():
    ap = argparse.ArgumentParser(description="Actualizar downstream desde matriz_astro_luna (Astroluna)")
    ap.add_argument("--db", required=True, help="Ruta a la base de datos SQLite")
    ap.add_argument("--targets", nargs="*", help="Tablas específicas a refrescar (opcional)")
    ap.add_argument("--exclude", nargs="*", help="Exclusiones adicionales (se suman a las predeterminadas)")
    ap.add_argument("--dry-run", action="store_true", help="Simular sin escribir cambios")
    ap.add_argument("--reporte", help="Ruta CSV para exportar el reporte (opcional)")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    try:
        acciones = refresh_from_matrix(conn, targets=args.targets, exclude=args.exclude, dry_run=args.dry_run)

        # stdout
        hdr = ["tabla", "tipo", "accion", "filas_antes", "filas_despues"]
        print("\nREPORTE:")
        print("\t".join(hdr))
        for row in acciones:
            print("\t".join("" if v is None else str(v) for v in row))

        # CSV opcional
        if args.reporte:
            import pandas as pd
            df = pd.DataFrame(acciones, columns=hdr)
            df.to_csv(args.reporte, index=False, encoding="utf-8")
            print(f"[OK] Reporte guardado en: {args.reporte}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
