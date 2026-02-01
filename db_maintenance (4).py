#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_maintenance.py — Puesta a punto para RadarPremios (SQLite)

Acciones:
  1) Crear/asegurar índices recomendados
  2) Asegurar vista `todo` con INNER JOIN (opcional: --todo-join left|inner)
  3) ANALYZE y VACUUM (conmutables)

Uso:
  python db_maintenance.py --db "C:\\RadarPremios\\radar_premios.db" --todo-join inner --no-vacuum
  python db_maintenance.py --db "C:\\RadarPremios\\radar_premios.db" --dry-run

Notas:
- Idempotente: usa IF NOT EXISTS y comprueba antes de recrear la vista.
- Seguro: transacciones por bloque; rollback ante error.
"""

import argparse
import datetime
import sqlite3
import sys
from typing import List, Tuple

RECOMMENDED_INDEXES = [
    # Núcleo
    ("astro_luna",                "idx_astro_luna_fecha",               "CREATE INDEX IF NOT EXISTS idx_astro_luna_fecha ON astro_luna(fecha)"),
    ("matriz_astro_luna",         "idx_matriz_aslu_fecha",              "CREATE INDEX IF NOT EXISTS idx_matriz_aslu_fecha ON matriz_astro_luna(fecha)"),
    ("matriz_astro_luna",         "idx_matriz_aslu_numero",             "CREATE INDEX IF NOT EXISTS idx_matriz_aslu_numero ON matriz_astro_luna(numero)"),
    ("matriz_astro_luna",         "idx_matriz_aslu_fecha_numero",       "CREATE INDEX IF NOT EXISTS idx_matriz_aslu_fecha_numero ON matriz_astro_luna(fecha, numero)"),

    # Resumen principal
    ("todos_resumen_matriz_aslu", "idx_trma_fecha",                     "CREATE INDEX IF NOT EXISTS idx_trma_fecha ON todos_resumen_matriz_aslu(fecha)"),
    ("todos_resumen_matriz_aslu", "idx_trma_numero",                    "CREATE INDEX IF NOT EXISTS idx_trma_numero ON todos_resumen_matriz_aslu(numero)"),
    ("todos_resumen_matriz_aslu", "idx_trma_fecha_numero",              "CREATE INDEX IF NOT EXISTS idx_trma_fecha_numero ON todos_resumen_matriz_aslu(fecha, numero)"),

    # UNPIVOT de posiciones
    ("todos_cuando_son",          "idx_tcs_fecha",                      "CREATE INDEX IF NOT EXISTS idx_tcs_fecha ON todos_cuando_son(fecha)"),
    ("todos_cuando_son",          "idx_tcs_numero",                     "CREATE INDEX IF NOT EXISTS idx_tcs_numero ON todos_cuando_son(numero)"),
    ("todos_cuando_son",          "idx_tcs_digito",                     "CREATE INDEX IF NOT EXISTS idx_tcs_digito ON todos_cuando_son(digito)"),
    ("todos_cuando_son",          "idx_tcs_pos_digito",                 "CREATE INDEX IF NOT EXISTS idx_tcs_pos_digito ON todos_cuando_son(posicion, digito)"),
    ("todos_cuando_son",          "idx_tcs_fecha_numero",               "CREATE INDEX IF NOT EXISTS idx_tcs_fecha_numero ON todos_cuando_son(fecha, numero)"),

    # Tablas todo_cuando_X_es (0..9) — se crearán dinámicamente (fecha, numero)
    # Tablas cuando_* — índice básico por (fecha) y (numero) se crearán dinámicamente
]

VIEW_TODO_SQL_TEMPLATE = """CREATE VIEW "todo" AS
SELECT *
FROM todos_resumen_matriz_aslu AS a
{join_type} JOIN todos_cuando_son AS b
  ON a.fecha = b.fecha
 AND a.numero = b.numero
"""

def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute("SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=? COLLATE NOCASE", (name,))
    return cur.fetchone() is not None

def list_tables_like(conn: sqlite3.Connection, pattern_sql_like: str) -> List[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ? ORDER BY name", (pattern_sql_like,))
    return [r[0] for r in cur.fetchall()]

def list_cuando_tables(conn: sqlite3.Connection) -> List[str]:
    return list_tables_like(conn, "cuando_%")

def list_todo_cuando_tables(conn: sqlite3.Connection) -> List[str]:
    return list_tables_like(conn, "todo_cuando_%_es")

def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return column in cols

def ensure_indexes(conn: sqlite3.Connection, dry_run: bool=False) -> List[Tuple[str,str]]:
    applied = []

    # 1) Índices fijos
    for tbl, idx, sql in RECOMMENDED_INDEXES:
        if not table_exists(conn, tbl):
            continue
        if dry_run:
            print(f"[DRY] {idx} -> {tbl}")
        else:
            conn.execute(sql)
        applied.append((tbl, idx))

    # 2) Índices para todo_cuando_%_es: (fecha, numero)
    for tbl in list_todo_cuando_tables(conn):
        if not (column_exists(conn, tbl, "fecha") and column_exists(conn, tbl, "numero")):
            continue
        idx = f"idx_{tbl}_fecha_numero"
        sql = f"CREATE INDEX IF NOT EXISTS {idx} ON {tbl}(fecha, numero)"
        if dry_run:
            print(f"[DRY] {idx} -> {tbl}")
        else:
            conn.execute(sql)
        applied.append((tbl, idx))

    # 3) Índices para cuando_%: (fecha) y (numero) si existen
    for tbl in list_cuando_tables(conn):
        if column_exists(conn, tbl, "fecha"):
            idx = f"idx_{tbl}_fecha"
            sql = f"CREATE INDEX IF NOT EXISTS {idx} ON {tbl}(fecha)"
            if dry_run:
                print(f"[DRY] {idx} -> {tbl}")
            else:
                conn.execute(sql)
            applied.append((tbl, idx))
        if column_exists(conn, tbl, "numero"):
            idx = f"idx_{tbl}_numero"
            sql = f"CREATE INDEX IF NOT EXISTS {idx} ON {tbl}(numero)"
            if dry_run:
                print(f"[DRY] {idx} -> {tbl}")
            else:
                conn.execute(sql)
            applied.append((tbl, idx))

    return applied

def ensure_view_todo(conn: sqlite3.Connection, join_type: str, dry_run: bool=False) -> None:
    join_kw = "INNER" if join_type.lower() == "inner" else "LEFT"
    sql = VIEW_TODO_SQL_TEMPLATE.format(join_type=join_kw)
    # Solo recrear si no existe o si el SQL es distinto
    cur = conn.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='todo'")
    row = cur.fetchone()
    needs_recreate = True
    if row and row[0]:
        existing = " ".join(row[0].split())
        target   = " ".join(sql.split())
        needs_recreate = (existing.lower() != target.lower())
    if not needs_recreate:
        print(f"[INFO] Vista 'todo' ya coincide ({join_kw} JOIN).")
        return

    if dry_run:
        print(f"[DRY] Re-crear vista 'todo' con {join_kw} JOIN")
        return

    conn.execute("DROP VIEW IF EXISTS todo;")
    conn.execute(sql)
    print(f"[OK] Vista 'todo' creada con {join_kw} JOIN.")

def run_analyze(conn: sqlite3.Connection, dry_run: bool=False):
    if dry_run:
        print("[DRY] ANALYZE")
        return
    conn.execute("ANALYZE;")
    print("[OK] ANALYZE ejecutado.")

def run_vacuum(conn: sqlite3.Connection, dry_run: bool=False):
    if dry_run:
        print("[DRY] VACUUM")
        return
    conn.execute("VACUUM;")
    print("[OK] VACUUM ejecutado.")

def main():
    parser = argparse.ArgumentParser(description="Puesta a punto de la base SQLite (RadarPremios).")
    parser.add_argument("--db", required=True, help="Ruta a la base de datos SQLite (*.db)")
    parser.add_argument("--todo-join", choices=["left","inner"], default="inner",
                        help="Tipo de JOIN en vista 'todo' (default=inner)")
    parser.add_argument("--no-analyze", action="store_true", help="No ejecutar ANALYZE")
    parser.add_argument("--no-vacuum", action="store_true", help="No ejecutar VACUUM")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar cambios sin aplicarlos")
    args = parser.parse_args()

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[INFO] db_maintenance.py — {ts}")
    print(f"[INFO] Base: {args.db}")
    if args.dry_run:
        print("[INFO] Modo: DRY-RUN (no se aplicarán cambios)")

    try:
        conn = sqlite3.connect(args.db)
        conn.execute("PRAGMA foreign_keys=OFF;")   # no FK en este esquema, evita bloqueos raros
        conn.execute("PRAGMA journal_mode=WAL;")   # mejor concurrencia
        conn.execute("PRAGMA synchronous=NORMAL;")

        # ---- Bloque 1: índices + vista
        conn.execute("BEGIN;")
        try:
            applied = ensure_indexes(conn, dry_run=args.dry_run)
            print(f"[INFO] Índices asegurados/planificados: {len(applied)}")
            ensure_view_todo(conn, join_type=args.todo_join, dry_run=args.dry_run)
            if not args.dry_run:
                conn.execute("COMMIT;")
            else:
                conn.execute("ROLLBACK;")
        except Exception as e:
            conn.execute("ROLLBACK;")
            raise

        # ---- Bloque 2: ANALYZE
        if not args.no_analyze:
            run_analyze(conn, dry_run=args.dry_run)

        # ---- Bloque 3: VACUUM
        if not args.no_vacuum:
            run_vacuum(conn, dry_run=args.dry_run)

        print("[OK] Puesta a punto finalizada.")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
