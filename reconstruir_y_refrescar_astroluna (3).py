#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reconstruye 'matriz_astro_luna' con esquema COMPLETO (derivando u,d,c,um y banderas 0..9)
desde 'astroluna' (o 'astro_luna') y luego refresca automáticamente las tablas downstream.

Uso recomendado (Windows):
  python reconstruir_y_refrescar_astroluna.py --db "C:\\RadarPremios\\radar_premios.db" --reporte "C:\\RadarPremios\\reporte_full.csv" --vacuum

Puedes simular primero:
  python reconstruir_y_refrescar_astroluna.py --db "C:\\RadarPremios\\radar_premios.db" --dry-run
"""

import argparse
import os
import sqlite3
from contextlib import contextmanager
from typing import List, Optional, Sequence, Tuple

MATRIX_TABLE = "matriz_astro_luna"
SOURCE_CANDIDATES = ["astroluna", "astro_luna"]

# Tablas que NO se tocan (fuentes y otros sorteos)
DEFAULT_EXCLUDES = [
    "astroluna", "astro_luna",
    "tolima", "huila", "manizales", "quindio", "medellin", "boyaca",
    "baloto_premios", "baloto_resultados", "revancha_premios", "revancha_resultados",
]

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

def detect_source(conn: sqlite3.Connection) -> Optional[str]:
    for t in SOURCE_CANDIDATES:
        if table_exists(conn, t):
            return t
    return None

def required_cols(conn: sqlite3.Connection, name: str):
    cols = get_cols(conn, name)
    all_cols = [c[1] for c in cols]
    req = [c[1] for c in cols if c[3] == 1 and c[5] == 0 and c[4] is None]  # NOT NULL & not-PK & sin default
    return all_cols, req

def create_full_matrix_sql(source: str) -> str:
    """
    Crea el SQL que:
    - Genera tabla matriz_astro_luna_new con el esquema completo
    - Población derivando um,c,d,u desde numero (rellenando con printf('%04d', numero))
    - Crea banderas um_0..um_9, c_0..c_9, d_0..d_9, u_0..u_9
    - Completa columnas 'origen', 'origen_tabla', 'combinacion'
    - Reemplaza la tabla existente de manera atómica
    """
    # Columnas de banderas
    pos = ["um", "c", "d", "u"]
    digits = list(range(10))
    flag_cols = []
    for p in pos:
        for k in digits:
            flag_cols.append(f'{p}_{k} INTEGER NOT NULL')

    create_sql = f"""
DROP TABLE IF EXISTS matriz_astro_luna_new;

CREATE TABLE matriz_astro_luna_new (
  fecha TEXT NOT NULL,
  numero INTEGER NOT NULL,
  signo TEXT,
  um INTEGER NOT NULL,
  c  INTEGER NOT NULL,
  d  INTEGER NOT NULL,
  u  INTEGER NOT NULL,
  origen TEXT NOT NULL,
  origen_tabla TEXT NOT NULL,
  combinacion TEXT NOT NULL,
  {", ".join(flag_cols)}
);

-- Insertar calculando dígitos desde numero (4 cifras; se ajusta con printf para ceros a la izquierda)
INSERT INTO matriz_astro_luna_new (
  fecha, numero, signo, um, c, d, u, origen, origen_tabla, combinacion,
  {", ".join([f"{p}_{k}" for p in pos for k in digits])}
)
WITH base AS (
  SELECT
    fecha,
    numero,
    signo,
    -- representamos el número a 4 dígitos para asegurar um,c,d,u
    printf('%04d', CAST(numero AS INTEGER)) AS n4
  FROM "{source}"
),
dig AS (
  SELECT
    fecha,
    numero,
    signo,
    CAST(substr(n4, 1, 1) AS INTEGER) AS um,
    CAST(substr(n4, 2, 1) AS INTEGER) AS c,
    CAST(substr(n4, 3, 1) AS INTEGER) AS d,
    CAST(substr(n4, 4, 1) AS INTEGER) AS u
  FROM base
)
SELECT
  fecha,
  numero,
  signo,
  um, c, d, u,
  'matriz' AS origen,
  '{source}' AS origen_tabla,
  (CAST(um AS TEXT) || '-' || CAST(c AS TEXT) || '-' || CAST(d AS TEXT) || '-' || CAST(u AS TEXT)) AS combinacion,
  {", ".join([f"CASE WHEN um={k} THEN 1 ELSE 0 END AS um_{k}" for k in digits])},
  {", ".join([f"CASE WHEN c={k} THEN 1 ELSE 0 END AS c_{k}" for k in digits])},
  {", ".join([f"CASE WHEN d={k} THEN 1 ELSE 0 END AS d_{k}" for k in digits])},
  {", ".join([f"CASE WHEN u={k} THEN 1 ELSE 0 END AS u_{k}" for k in digits])}
FROM dig
;
    """.strip()

    swap_sql = f"""
-- Reemplazo atómico
PRAGMA foreign_keys = OFF;
DROP TABLE IF EXISTS matriz_astro_luna_backup;
ALTER TABLE "{MATRIX_TABLE}" RENAME TO matriz_astro_luna_backup;
ALTER TABLE matriz_astro_luna_new RENAME TO "{MATRIX_TABLE}";
DROP TABLE IF EXISTS matriz_astro_luna_backup;
PRAGMA foreign_keys = ON;
    """.strip()

    return create_sql + "\n\n" + swap_sql

def refresh_downstream(conn: sqlite3.Connection, targets: Optional[Sequence[str]], exclude: Optional[Sequence[str]], dry_run: bool):
    if not table_exists(conn, MATRIX_TABLE):
        raise SystemExit("[ERROR] No existe la tabla '{}'.".format(MATRIX_TABLE))

    src_cols = [c[1] for c in get_cols(conn, MATRIX_TABLE)]
    objs = get_objects(conn)

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
            acciones.append((name, otype, "omitida (faltan requeridas: {})".format(faltan), None, None))
            continue

        antes = count_rows(conn, name)
        if not dry_run:
            with tx(conn):
                conn.execute(f'DELETE FROM "{name}"')
                cols_sql = ", ".join([f'"{c}"' for c in comunes])
                conn.execute(f'INSERT INTO "{name}" ({cols_sql}) SELECT {cols_sql} FROM "{MATRIX_TABLE}"')
        despues = count_rows(conn, name) if not dry_run else None
        acciones.append((name, otype, "refrescada desde {}".format(MATRIX_TABLE), antes, despues))

    return acciones

def main():
    ap = argparse.ArgumentParser(description="Reconstruir matriz_astro_luna (completa) y refrescar downstream")
    ap.add_argument("--db", required=True, help="Ruta a la BD SQLite. Ej: C:\\RadarPremios\\radar_premios.db")
    ap.add_argument("--dry-run", action="store_true", help="Solo mostrar lo que se haría, sin escribir")
    ap.add_argument("--targets", nargs="*", help="Refrescar solo estas tablas (opcional)")
    ap.add_argument("--exclude", nargs="*", help="Exclusiones adicionales (se suman a las por defecto)")
    ap.add_argument("--reporte", help="Guardar reporte CSV")
    ap.add_argument("--vacuum", action="store_true", help="VACUUM al final si no es dry-run")
    args = ap.parse_args()

    db_path = args.db
    if not os.path.isfile(db_path):
        ejemplo = r'C:\RadarPremios\radar_premios.db'
        raise SystemExit(
            "[ERROR] No se puede abrir la BD: {db}\nEjemplo (Windows):\n  python {script} --db \"{ejemplo}\"".format(
                db=db_path, script=os.path.basename(__file__), ejemplo=ejemplo
            )
        )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # 1) Reconstruir matriz con esquema completo (desde fuente)
        src = detect_source(conn)
        if not src:
            raise SystemExit("[ERROR] No se encontró tabla fuente 'astroluna' ni 'astro_luna'.")
        if not table_exists(conn, MATRIX_TABLE):
            # Si no existe, la creamos directo (sin backup)
            pass

        sql_script = create_full_matrix_sql(src)

        if args.dry_run:
            # Mostrar resumen de lo que haríamos
            try:
                max_src = conn.execute(f"SELECT MAX(fecha) FROM '{src}'").fetchone()[0]
            except Exception:
                max_src = None
            print("[INFO] DRY-RUN: Se reconstruiría '{}' desde '{}' con esquema extendido.".format(MATRIX_TABLE, src))
            print("[INFO] MAX(fecha) en fuente {} -> {}".format(src, max_src))
        else:
            print("[INFO] Reconstruyendo '{}' (esquema completo) desde '{}' ...".format(MATRIX_TABLE, src))
            with tx(conn):
                conn.executescript(sql_script)
            max_src = conn.execute(f"SELECT MAX(fecha) FROM '{src}'").fetchone()[0]
            max_mat = conn.execute(f"SELECT MAX(fecha) FROM '{MATRIX_TABLE}'").fetchone()[0]
            print("[OK] Matriz reconstruida. MAX(fecha) src={} | matriz={}".format(max_src, max_mat))

        # 2) Refrescar downstream (ahora la matriz SÍ tiene todas las columnas)
        print("[INFO] Refrescando downstream desde '{}' ... (dry_run={})".format(MATRIX_TABLE, args.dry_run))
        acciones = refresh_downstream(conn, targets=args.targets, exclude=args.exclude, dry_run=args.dry_run)

        # 3) Reporte
        hdr = ["tabla", "tipo", "accion", "filas_antes", "filas_despues"]
        print("\nREPORTE:")
        print("\t".join(hdr))
        for row in acciones:
            print("\t".join("" if v is None else str(v) for v in row))

        if args.reporte:
            try:
                import pandas as pd
                df = pd.DataFrame(acciones, columns=hdr)
                df.to_csv(args.reporte, index=False, encoding="utf-8")
                print("[OK] Reporte guardado en: {}".format(args.reporte))
            except Exception as e:
                print("[WARN] No se pudo guardar el reporte CSV: {}".format(e))

        # 4) VACUUM opcional
        if args.vacuum and not args.dry_run:
            try:
                print("[INFO] VACUUM ...")
                conn.execute("VACUUM")
                print("[OK] VACUUM listo.")
            except Exception as e:
                print("[WARN] VACUUM falló: {}".format(e))

        print("[OK] Proceso finalizado.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
