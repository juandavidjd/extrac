#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestador Astroluna v6

Cambios clave v6:
- Habilitado rebuild para 'todos_resumen_matriz_aslu' (copia segura desde matriz).
- Verificación explícita (COUNT y MAX(fecha)) de 'astro_luna', 'matriz_astro_luna' y de la vista 'todo'.
- Opción --recrear-vista-todo para (re)crear: CREATE VIEW todo AS SELECT * FROM matriz_astro_luna.

Uso:
  DRY-RUN:
    python orquestador_astroluna_v6.py --db "C:\\RadarPremios\\radar_premios.db" --reconstruir-matriz --dry-run

  Real + reporte + VACUUM:
    python orquestador_astroluna_v6.py --db "C:\\RadarPremios\\radar_premios.db" --reconstruir-matriz --reporte "C:\\RadarPremios\\reporte_v6.csv" --vacuum

  Recrear la vista 'todo':
    python orquestador_astroluna_v6.py --db "C:\\RadarPremios\\radar_premios.db" --recrear-vista-todo
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
    "astroluna", "astro_luna",  # Fuente (se verifica, no se escribe)
    "tolima", "huila", "manizales", "quindio", "medellin", "boyaca",
    "baloto_premios", "baloto_resultados", "revancha_premios", "revancha_resultados",
]

# Objetos que siempre verificamos (aunque estén excluidos para escritura)
ALWAYS_VERIFY = ["astro_luna", MATRIX_TABLE, "todos_resumen_matriz_aslu", "todo"]

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
        "SELECT 1 FROM sqlite_master WHERE name=?",
        (name,)
    ).fetchone() is not None

def object_type(conn: sqlite3.Connection, name: str) -> Optional[str]:
    row = conn.execute(
        "SELECT type FROM sqlite_master WHERE name=?", (name,)
    ).fetchone()
    return row[0] if row else None

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

def max_fecha(conn: sqlite3.Connection, name: str) -> Optional[str]:
    try:
        return conn.execute(f'SELECT MAX(fecha) FROM "{name}"').fetchone()[0]
    except Exception:
        return None

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

# ---------------- Reglas por nombre ----------------
DIGIT_MAP = {
    "cero": 0, "0": 0, "1": 1, "2": 2, "3": 3, "4": 4,
    "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
}

TOKEN_TO_POS = {
    "um": "um", "umil": "um",
    "c": "c", "centena": "c",
    "d": "d", "decena": "d",
    "u": "u", "unidad": "u",
}

RE_CUANDO = re.compile(r"^cuando_(?P<d>[a-z0-9]+)_es_(?P<pat>.+)$")
RE_TODO_CUANDO = re.compile(r"^todo_cuando_(?P<d>[a-z0-9]+)_es$")
RE_RESUMEN = re.compile(r"^(primer|segundo|tercer|cuarto|quinto|sexto|septimo|octavo|noveno|decimo)_resumen_matriz_aslu$")
RE_TODOS_RESUMEN = re.compile(r"^todos_resumen_matriz_aslu$")

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
    # Para {primer..decimo}_resumen_matriz_aslu
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

def rebuild_todos_resumen_table(conn: sqlite3.Connection, table: str, dry: bool) -> str:
    # Para 'todos_resumen_matriz_aslu'
    return rebuild_resumen_table(conn, table, dry)

# ---------------- Verificaciones y vista 'todo' ----------------
def verify_object(conn: sqlite3.Connection, name: str) -> Tuple[str, str]:
    typ = object_type(conn, name)
    if not typ:
        return ("no existe", "")
    if typ == "table":
        try:
            n = count_rows(conn, name)
            mf = max_fecha(conn, name)
            return ("verificada", f"COUNT={n} | MAX(fecha)={mf}")
        except Exception as e:
            return ("error verificación", str(e))
    if typ == "view":
        try:
            n = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            mf = None
            # Intentamos MAX(fecha) si existe
            try:
                mf = conn.execute(f'SELECT MAX(fecha) FROM "{name}"').fetchone()[0]
            except Exception:
                pass
            det = f"COUNT={n}"
            if mf is not None:
                det += f" | MAX(fecha)={mf}"
            return ("verificada", det)
        except Exception as e:
            return ("error verificación", str(e))
    return ("omitida", "tipo no manejado")

def recreate_view_todo(conn: sqlite3.Connection) -> Tuple[str, str]:
    sql = f'CREATE VIEW IF NOT EXISTS todo AS SELECT * FROM "{MATRIX_TABLE}";'
    with tx(conn):
        # Si existe, la reemplazamos
        conn.execute('DROP VIEW IF EXISTS todo;')
        conn.execute(sql)
    return ("vista recreada", "todo = SELECT * FROM matriz_astro_luna")

# ---------------- Pipeline principal ----------------
def main():
    import pandas as pd

    ap = argparse.ArgumentParser(description="Orquestador Astroluna v6")
    ap.add_argument("--db", required=True, help="Ruta a la BD SQLite. Ej: C:\\RadarPremios\\radar_premios.db")
    ap.add_argument("--reconstruir-matriz", action="store_true", help="Reconstruir matriz extendida desde astro_luna/astroluna")
    ap.add_argument("--recrear-vista-todo", action="store_true", help="(Re)crear vista 'todo' como SELECT * FROM matriz_astro_luna")
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

    acciones: List[Tuple[str, str, str, str]] = []  # (tabla, tipo, accion, detalle)

    try:
        # 0) (Opcional) Recrear la vista 'todo'
        if args.recrear_vista_todo and not args.dry_run:
            estado, det = recreate_view_todo(conn)
            acciones.append(("todo", "view", estado, det))

        # 1) Reconstruir matriz extendida (opcional)
        if args.reconstruir_matriz:
            src = detect_source(conn)
            if not src:
                raise SystemExit("[ERROR] No se encontró tabla fuente 'astro_luna' ni 'astroluna'.")
            matrix_exists = table_exists(conn, MATRIX_TABLE)
            sql_script = create_full_matrix_sql(src, matrix_exists)
            if args.dry_run:
                max_src = max_fecha(conn, src)
                print("[INFO] DRY-RUN: reconstruir matriz extendida desde '{}' (MAX(fecha)={})".format(src, max_src))
            else:
                print("[INFO] Reconstruyendo matriz extendida desde '{}' ...".format(src))
                with tx(conn):
                    conn.executescript(sql_script)
                max_src = max_fecha(conn, src)
                max_mat = max_fecha(conn, MATRIX_TABLE)
                print("[OK] Matriz lista. MAX(fecha) src={} | matriz={}".format(max_src, max_mat))
        else:
            print("[INFO] Reconstrucción de matriz omitida.")

        # 2) Recorrer objetos y aplicar reglas
        objs = get_objects(conn)
        exclude_set = set(DEFAULT_EXCLUDES)
        if args.exclude:
            exclude_set.update(args.exclude)

        for name, otype in objs:
            # Verificación prioritaria para ALWAYS_VERIFY
            if name in ALWAYS_VERIFY:
                est, det = verify_object(conn, name)
                acciones.append((name, otype, est, det))
                # En el caso de 'todo', además permitir recreación si pidió y estaba en dry-run
                if name == "todo" and args.recrear_vista_todo and args.dry_run:
                    acciones.append(("todo", "view", "simulada (recrear vista)", "todo = SELECT * FROM matriz_astro_luna"))
                # No interrumpir; si además hay regla específica (todos_resumen) se aplicará abajo
                # excepto si es view (no se escribe).
                # Continuamos al siguiente para no duplicar acciones innecesarias.
                # (Seguimos porque 'todos_resumen_matriz_aslu' requiere rebuild además de verificación)
            
            # Vistas (salvo 'todo' que ya se manejó) no se tocan
            if otype == "view" and name != "todo":
                acciones.append((name, otype, "omitida (vista)", ""))
                continue

            # No tocar fuentes ni la propia matriz en escritura
            if name in exclude_set or name == MATRIX_TABLE:
                # Ya se verificó si aplica; de lo contrario solo se omite
                if name not in ALWAYS_VERIFY:
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

            # Regla: todos_resumen_matriz_aslu
            if RE_TODOS_RESUMEN.match(name):
                estado = rebuild_todos_resumen_table(conn, name, args.dry_run)
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
