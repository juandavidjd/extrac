#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestador Astroluna v5

Novedades v5:
- Se incluyen reglas para tablas *_resumen_matriz_aslu (primer_, segundo_, ... , decimo_).
  Estrategia: "copia segura" -> se detectan columnas comunes con matriz_astro_luna
  y se repuebla la tabla con SELECT de esas columnas. (Sin agregación hasta
  tener el esquema/definición exacta.)

Pipeline:
1) (Opcional) Reconstruye matriz_astro_luna extendida desde astro_luna/astroluna.
2) Reconstruye:
   - cuando_{digit|cero}_es_{patron}
   - todo_cuando_{digit|cero}_es
   - todos_cuando_son  (UNPIVOT um/c/d/u)
   - *_resumen_matriz_aslu (copia segura desde matriz)

Uso:
  python orquestador_astroluna_v5.py --db "C:\\RadarPremios\\radar_premios.db" --reconstruir-matriz --dry-run
  python orquestador_astroluna_v5.py --db "C:\\RadarPremios\\radar_premios.db" --reconstruir-matriz --reporte "C:\\RadarPremios\\reporte_v5.csv" --vacuum
"""

import argparse
import os
import re
import sqlite3
from contextlib import contextmanager
from typing import List, Optional, Sequence, Tuple

MATRIX_TABLE = "matriz_astro_luna"
SOURCE_CANDIDATES = ["astro_luna", "astroluna"]

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
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None

def get_objects(conn: sqlite3.Connection) -> List[Tuple[str, str]]:
    sql = (
        "SELECT name, type FROM sqlite_master "
        "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' "
        "ORDER BY type DESC, name"
    )
    return conn.execute(sql).fetchall()

def get_cols(conn: sqlite3.Connection, name: str):
    return conn.execute(f"PRAGMA table_info('{name}')").fetchall()

def count_rows(conn: sqlite3.Connection, name: str) -> int:
    return conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]

def detect_source(conn: sqlite3.Connection) -> Optional[str]:
    for t in SOURCE_CANDIDATES:
        if table_exists(conn, t):
            return t
    return None

# ---------------- Reconstrucción extendida de la matriz ----------------
def create_full_matrix_sql(source: str, matrix_exists: bool) -> str:
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

INSERT INTO matriz_astro_luna_new (
  fecha, numero, signo, um, c, d, u, origen, origen_tabla, combinacion,
  {", ".join([f"{p}_{k}" for p in pos for k in digits])}
)
WITH base AS (
  SELECT
    fecha,
    numero,
    signo,
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
FROM dig;
""".strip()

    if matrix_exists:
        swap_sql = f"""
PRAGMA foreign_keys = OFF;
DROP TABLE IF EXISTS matriz_astro_luna_backup;
ALTER TABLE "{MATRIX_TABLE}" RENAME TO matriz_astro_luna_backup;
ALTER TABLE matriz_astro_luna_new RENAME TO "{MATRIX_TABLE}";
DROP TABLE IF EXISTS matriz_astro_luna_backup;
PRAGMA foreign_keys = ON;
""".strip()
    else:
        swap_sql = f"""
PRAGMA foreign_keys = OFF;
ALTER TABLE matriz_astro_luna_new RENAME TO "{MATRIX_TABLE}";
PRAGMA foreign_keys = ON;
""".strip()

    return create_sql + "\n\n" + swap_sql

# ---------------- Reglas por NOMBRE: cuando_*, todo_cuando_*, todos_cuando_son, *_resumen_* ----------------
DIGIT_MAP = {
    "cero": 0, "0": 0, "1": 1, "2": 2, "3": 3, "4": 4,
    "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
}

TOKEN_TO_POS = {
    "um": "um",
    "umil": "um",
    "c": "c",
    "centena": "c",
    "d": "d",
    "decena": "d",
    "u": "u",
    "unidad": "u",
}

RE_CUANDO = re.compile(r"^cuando_(?P<d>[a-z0-9]+)_es_(?P<pat>.+)$")
RE_TODO_CUANDO = re.compile(r"^todo_cuando_(?P<d>[a-z0-9]+)_es$")
RE_RESUMEN = re.compile(r"^(primer|segundo|tercer|cuarto|quinto|sexto|septimo|octavo|noveno|decimo)_resumen_matriz_aslu$")

def parse_cuando(name: str):
    m = RE_CUANDO.match(name)
    if not m:
        return None
    d_raw = m.group("d").lower()
    pat_raw = m.group("pat")
    if d_raw not in DIGIT_MAP:
        return None
    digit = DIGIT_MAP[d_raw]
    parts_and = pat_raw.split("_y_")
    groups = []
    for part in parts_and:
        tokens = part.split("_")
        mapped = []
        for t in tokens:
            t = t.strip().lower()
            if t in TOKEN_TO_POS:
                mapped.append(TOKEN_TO_POS[t])
        if mapped:
            groups.append(mapped)
    return digit, groups

def build_where_for_cuando(digit: int, groups: List[List[str]]) -> str:
    clauses = []
    for g in groups:
        if len(g) == 1:
            clauses.append(f"{g[0]} = {digit}")
        else:
            clauses.append(" AND ".join(f"{p} = {digit}" for p in g))
    if not clauses:
        return "1=0"
    return " AND ".join(f"({c})" for c in clauses)

def is_todo_cuando(name: str):
    return RE_TODO_CUANDO.match(name)

def build_where_for_todo_cuando(digit: int) -> str:
    return f"(um = {digit} OR c = {digit} OR d = {digit} OR u = {digit})"

def rebuild_cuando_table(conn: sqlite3.Connection, table: str, dry: bool) -> Tuple[str, str]:
    parsed = parse_cuando(table)
    if not parsed:
        return ("omitida (nombre no reconocido)", None)
    digit, groups = parsed
    where = build_where_for_cuando(digit, groups)
    cols = [c[1] for c in get_cols(conn, MATRIX_TABLE)]
    dst_cols = [c[1] for c in get_cols(conn, table)]
    comunes = [c for c in dst_cols if c in cols]
    if not comunes:
        return ("omitida (sin columnas comunes con matriz)", None)
    colsql = ", ".join(f'"{c}"' for c in comunes)
    if dry:
        return (f"simulada (cuándo: {where})", where)
    with tx(conn):
        conn.execute(f'DELETE FROM "{table}"')
        conn.execute(f'INSERT INTO "{table}" ({colsql}) SELECT {colsql} FROM "{MATRIX_TABLE}" WHERE {where}')
    return (f"reconstruida (cuándo: {where})", where)

def rebuild_todo_cuando_table(conn: sqlite3.Connection, table: str, dry: bool) -> Tuple[str, str]:
    m = RE_TODO_CUANDO.match(table)
    if not m:
        return ("omitida (nombre no reconocido)", None)
    d_raw = m.group("d").lower()
    if d_raw not in DIGIT_MAP:
        return ("omitida (dígito no reconocido)", None)
    digit = DIGIT_MAP[d_raw]
    where = build_where_for_todo_cuando(digit)
    cols = [c[1] for c in get_cols(conn, MATRIX_TABLE)]
    dst_cols = [c[1] for c in get_cols(conn, table)]
    comunes = [c for c in dst_cols if c in cols]
    if not comunes:
        return ("omitida (sin columnas comunes con matriz)", None)
    colsql = ", ".join(f'"{c}"' for c in comunes)
    if dry:
        return (f"simulada (todo_cuando: {where})", where)
    with tx(conn):
        conn.execute(f'DELETE FROM "{table}"')
        conn.execute(f'INSERT INTO "{table}" ({colsql}) SELECT {colsql} FROM "{MATRIX_TABLE}" WHERE {where}')
    return (f"reconstruida (todo_cuando: {where})", where)

def rebuild_todos_cuando_son(conn: sqlite3.Connection, table: str, dry: bool) -> str:
    dst_cols = [c[1] for c in get_cols(conn, table)]
    src_cols = [c[1] for c in get_cols(conn, MATRIX_TABLE)]
    posibles = set(src_cols + ["posicion", "valor_pos"])
    comunes = [c for c in dst_cols if c in posibles]
    if not comunes:
        return "omitida (sin columnas compatibles)"
    def select_for(pos_col: str, label: str) -> str:
        current = []
        for c in comunes:
            if c == "posicion":
                current.append(f"'{label}' AS posicion")
            elif c == "valor_pos":
                current.append(f"{pos_col} AS valor_pos")
            else:
                current.append(f'"{c}"')
        return "SELECT " + ", ".join(current) + f' FROM "{MATRIX_TABLE}"'
    union_sql = "\nUNION ALL\n".join([
        select_for("um", "um"),
        select_for("c",  "c"),
        select_for("d",  "d"),
        select_for("u",  "u"),
    ])
    insert_cols = ", ".join(f'"{c}"' for c in comunes)
    if dry:
        return "simulada (UNPIVOT um/c/d/u)"
    with tx(conn):
        conn.execute(f'DELETE FROM "{table}"')
        conn.execute(f'INSERT INTO "{table}" ({insert_cols}) {union_sql}')
    return "reconstruida (UNPIVOT um/c/d/u)"

def rebuild_resumen_table(conn: sqlite3.Connection, table: str, dry: bool) -> str:
    """
    Regla genérica para *_resumen_matriz_aslu:
    - Detecta columnas comunes con matriz_astro_luna y repuebla con SELECT directo.
    - No asume agregaciones. Si luego quieres agregados, me pasas el esquema/definición y lo adapto.
    """
    if not RE_RESUMEN.match(table):
        return "omitida (nombre no coincide con *_resumen_matriz_aslu)"
    dst_cols = [c[1] for c in get_cols(conn, table)]
    src_cols = [c[1] for c in get_cols(conn, MATRIX_TABLE)]
    comunes = [c for c in dst_cols if c in src_cols]
    if not comunes:
        return "omitida (sin columnas comunes con matriz)"
    colsql = ", ".join(f'"{c}"' for c in comunes)
    if dry:
        return "simulada (copia segura desde matriz)"
    with tx(conn):
        conn.execute(f'DELETE FROM "{table}"')
        conn.execute(f'INSERT INTO "{table}" ({colsql}) SELECT {colsql} FROM "{MATRIX_TABLE}"')
    return "reconstruida (copia segura desde matriz)"

# ---------------- Pipeline principal ----------------
def main():
    ap = argparse.ArgumentParser(description="Orquestador Astroluna v5: matriz extendida + reglas por tabla (incluye *_resumen_matriz_aslu)")
    ap.add_argument("--db", required=True, help="Ruta a la BD SQLite. Ej: C:\\RadarPremios\\radar_premios.db")
    ap.add_argument("--reconstruir-matriz", action="store_true", help="Reconstruir matriz extendida desde astro_luna/astroluna")
    ap.add_argument("--dry-run", action="store_true", help="Simular sin escribir cambios")
    ap.add_argument("--targets", nargs="*", help="Limitar a ciertas tablas")
    ap.add_argument("--exclude", nargs="*", help="Exclusiones adicionales")
    ap.add_argument("--reporte", help="Guardar reporte CSV")
    ap.add_argument("--vacuum", action="store_true", help="VACUUM al final (si no es dry-run)")
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
        # 1) Reconstruir matriz extendida (opcional)
        if args.reconstruir_matriz:
            src = detect_source(conn)
            if not src:
                raise SystemExit("[ERROR] No se encontró tabla fuente 'astro_luna' ni 'astroluna'.")
            matrix_exists = table_exists(conn, MATRIX_TABLE)
            sql_script = create_full_matrix_sql(src, matrix_exists)
            if args.dry_run:
                try:
                    max_src = conn.execute(f"SELECT MAX(fecha) FROM '{src}'").fetchone()[0]
                except Exception:
                    max_src = None
                print("[INFO] DRY-RUN: reconstruir matriz extendida desde '{}' (MAX(fecha)={})".format(src, max_src))
            else:
                print("[INFO] Reconstruyendo matriz extendida desde '{}' ...".format(src))
                with tx(conn):
                    conn.executescript(sql_script)
                max_src = conn.execute(f"SELECT MAX(fecha) FROM '{src}'").fetchone()[0]
                max_mat = conn.execute(f"SELECT MAX(fecha) FROM '{MATRIX_TABLE}'").fetchone()[0]
                print("[OK] Matriz lista. MAX(fecha) src={} | matriz={}".format(max_src, max_mat))
        else:
            print("[INFO] Reconstrucción de matriz omitida.")

        # 2) Recorrer objetos y aplicar reglas
        objs = get_objects(conn)
        exclude_set = set(DEFAULT_EXCLUDES)
        if args.exclude:
            exclude_set.update(args.exclude)

        acciones: List[Tuple[str, str, str, str]] = []  # (tabla, tipo, accion, detalle)
        for name, otype in objs:
            if otype == "view":
                acciones.append((name, otype, "omitida (vista)", ""))
                continue
            if name in exclude_set or name == MATRIX_TABLE:
                acciones.append((name, otype, "omitida (fuente/excluida)", ""))
                continue
            if args.targets and name not in args.targets:
                continue

            # Regla: todos_cuando_son
            if name == "todos_cuando_son":
                estado = rebuild_todos_cuando_son(conn, name, args.dry_run)
                acciones.append((name, otype, estado, ""))
                continue

            # Regla: todo_cuando_{d}_es
            if is_todo_cuando(name):
                estado, where = rebuild_todo_cuando_table(conn, name, args.dry_run)
                acciones.append((name, otype, estado, where or ""))
                continue

            # Regla: cuando_{d}_es_{patron}
            if RE_CUANDO.match(name):
                estado, where = rebuild_cuando_table(conn, name, args.dry_run)
                acciones.append((name, otype, estado, where or ""))
                continue

            # Regla: *_resumen_matriz_aslu
            if RE_RESUMEN.match(name):
                estado = rebuild_resumen_table(conn, name, args.dry_run)
                acciones.append((name, otype, estado, ""))
                continue

            # Por defecto: no tocar
            acciones.append((name, otype, "omitida (sin regla específica)", ""))

        # 3) Reporte
        hdr = ["tabla", "tipo", "accion", "detalle"]
        print("\nREPORTE:")
        print("\t".join(hdr))
        for r in acciones:
            print("\t".join("" if v is None else str(v) for v in r))

        if args.reporte:
            try:
                import pandas as pd
                df = pd.DataFrame(acciones, columns=hdr)
                df.to_csv(args.reporte, index=False, encoding="utf-8")
                print("[OK] Reporte guardado en: {}".format(args.reporte))
            except Exception as e:
                print("[WARN] No se pudo guardar el reporte CSV: {}".format(e))

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
