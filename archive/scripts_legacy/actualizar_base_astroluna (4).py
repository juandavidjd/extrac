#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import hashlib
import os
import sqlite3
from datetime import datetime

# ============== Utilidades de logging ==============

def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def write_log_line(fh, line):
    fh.write(line.rstrip() + "\n")
    fh.flush()

# ============== SQL Helpers ==============

def normalize_all_fecha_columns(conn, logfh):
    write_log_line(logfh, "[STEP] Normalizar columnas 'fecha' (DD/MM/YYYY -> YYYY-MM-DD) en todas las tablas.")
    cur = conn.cursor()
    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
    """)
    tables = [r[0] for r in cur.fetchall()]

    for t in tables:
        # saltar tablas sin columna 'fecha'
        cur.execute(f"PRAGMA table_info({t})")
        cols = [row[1] for row in cur.fetchall()]
        if "fecha" not in cols:
            continue
        # normaliza solo si hay barras
        cur.execute(f"SELECT COUNT(*) FROM {t} WHERE fecha LIKE '%/%'")
        with_slashes = cur.fetchone()[0]
        if with_slashes == 0:
            write_log_line(logfh, f"  - {t}: OK (sin barras)")
            continue

        write_log_line(logfh, f"  - {t}: normalizando {with_slashes} filas con barras...")
        conn.execute(f"""
            UPDATE {t}
               SET fecha = CASE
                 WHEN fecha GLOB '??/??/????'
                 THEN SUBSTR(fecha,7,4) || '-' || SUBSTR(fecha,4,2) || '-' || SUBSTR(fecha,1,2)
                 ELSE fecha
               END
             WHERE fecha LIKE '%/%'
        """)

def rebuild_matriz(conn, logfh):
    write_log_line(logfh, "[STEP] Reconstruir 'matriz_astro_luna' desde 'astro_luna'.")
    conn.execute("DROP TABLE IF EXISTS matriz_astro_luna")
    # numero a 4 dígitos y columnas um, c, d, u
    conn.execute("""
        CREATE TABLE matriz_astro_luna AS
        SELECT
            fecha,
            numero,
            SUBSTR('0000'||numero, -4) AS numero4,
            CAST(SUBSTR('0000'||numero, -4, 1) AS INT) AS um,
            CAST(SUBSTR('0000'||numero, -3, 1) AS INT) AS c,
            CAST(SUBSTR('0000'||numero, -2, 1) AS INT) AS d,
            CAST(SUBSTR('0000'||numero, -1, 1) AS INT) AS u
        FROM astro_luna
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matriz_fecha ON matriz_astro_luna(fecha)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matriz_numero ON matriz_astro_luna(numero)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_matriz_umcdu ON matriz_astro_luna(um,c,d,u)")

def rebuild_resumenes(conn, logfh):
    write_log_line(logfh, "[STEP] Reconstruir tablas resumen*.")
    # todos_resumen_matriz_aslu: copia segura de la matriz (para la vista 'todo')
    conn.execute("DROP TABLE IF EXISTS todos_resumen_matriz_aslu")
    conn.execute("""
        CREATE TABLE todos_resumen_matriz_aslu AS
        SELECT fecha, numero, um, c, d, u
        FROM matriz_astro_luna
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trma_fecha_numero ON todos_resumen_matriz_aslu(fecha, numero)")

def rebuild_todos_cuando_son(conn, logfh):
    write_log_line(logfh, "[STEP] Reconstruir 'todos_cuando_son'.")
    conn.execute("DROP TABLE IF EXISTS todos_cuando_son")
    # Unpivote de um/c/d/u
    conn.execute("""
        CREATE TABLE todos_cuando_son AS
        SELECT fecha, numero, 'um' AS posicion, um AS digito FROM matriz_astro_luna
        UNION ALL
        SELECT fecha, numero, 'c'  AS posicion, c  AS digito FROM matriz_astro_luna
        UNION ALL
        SELECT fecha, numero, 'd'  AS posicion, d  AS digito FROM matriz_astro_luna
        UNION ALL
        SELECT fecha, numero, 'u'  AS posicion, u  AS digito FROM matriz_astro_luna
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tcs_fecha_num ON todos_cuando_son(fecha, numero)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tcs_digito_pos ON todos_cuando_son(digito, posicion)")

def rebuild_todo_cuando_es(conn, logfh):
    write_log_line(logfh, "[STEP] Reconstruir 'todo_cuando_*_es' (0..9).")
    for dig in range(10):
        conn.execute(f"DROP TABLE IF EXISTS todo_cuando_{dig}_es")
        conn.execute(f"""
            CREATE TABLE todo_cuando_{dig}_es AS
            SELECT fecha, numero
            FROM matriz_astro_luna
            WHERE um={dig} OR c={dig} OR d={dig} OR u={dig}
        """)
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_tc{dig}_fecha_num ON todo_cuando_{dig}_es(fecha, numero)")

def rebuild_cuando_detalladas(conn, logfh):
    write_log_line(logfh, "[STEP] Reconstruir tablas 'cuando_*' detalladas.")
    # Reglas (sufijo -> condición SQL con placeholder {dig})
    reglas = {
        "umil": "um={dig}",
        "centena": "c={dig}",
        "decena": "d={dig}",
        "unidad": "u={dig}",
        "um_y_c": "um={dig} AND c={dig}",
        "um_y_d": "um={dig} AND d={dig}",
        "um_y_u": "um={dig} AND u={dig}",
        "c_y_d": "c={dig} AND d={dig}",
        "c_y_u": "c={dig} AND u={dig}",
        "d_y_u": "d={dig} AND u={dig}",
        "c_d_y_u": "(c={dig} AND d={dig}) AND u={dig}",
        "um_c_y_d": "(um={dig} AND c={dig}) AND d={dig}",
        "um_c_y_u": "(um={dig} AND c={dig}) AND u={dig}",
        "um_d_y_u": "(um={dig} AND d={dig}) AND u={dig}",
        "um_c_d_y_u": "(um={dig} AND c={dig} AND d={dig}) AND u={dig}",
    }

    for dig in range(10):
        for sufijo, cond in reglas.items():
            tabla = f"cuando_{dig}_es_{sufijo}"
            conn.execute(f"DROP TABLE IF EXISTS {tabla}")
            conn.execute(f"""
                CREATE TABLE {tabla} AS
                SELECT fecha, numero
                FROM matriz_astro_luna
                WHERE {cond.format(dig=dig)}
            """)
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{tabla}_fecha_num ON {tabla}(fecha, numero)")

def ensure_view_todo(conn, join_kind: str, logfh):
    # join_kind: 'inner' o 'left'
    join_kw = "JOIN" if join_kind == "inner" else "LEFT JOIN"
    write_log_line(logfh, f"[STEP] Asegurar vista 'todo' ({join_kind.upper()} JOIN).")
    conn.execute("DROP VIEW IF EXISTS todo")
    conn.execute(f"""
        CREATE VIEW todo AS
        SELECT *
        FROM todos_resumen_matriz_aslu AS a
        {join_kw} todos_cuando_son AS b
          ON a.fecha = b.fecha
         AND a.numero = b.numero
    """)
    # Log del SQL exacto de la vista
    cur = conn.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='todo'")
    sql_view = cur.fetchone()[0]
    write_log_line(logfh, "[VIEW todo SQL]")
    write_log_line(logfh, sql_view)

def checks(conn, logfh):
    write_log_line(logfh, "[CHECK] Conteos y máximas fechas clave:")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MAX(fecha) FROM astro_luna")
    n_a, max_a = cur.fetchone()
    write_log_line(logfh, f"  - astro_luna: COUNT={n_a} | MAX(fecha)={max_a}")

    cur.execute("SELECT COUNT(*), MAX(fecha) FROM matriz_astro_luna")
    n_m, max_m = cur.fetchone()
    write_log_line(logfh, f"  - matriz_astro_luna: COUNT={n_m} | MAX(fecha)={max_m}")

    cur.execute("SELECT COUNT(*), MAX(fecha) FROM todos_resumen_matriz_aslu")
    n_r, max_r = cur.fetchone()
    write_log_line(logfh, f"  - todos_resumen_matriz_aslu: COUNT={n_r} | MAX(fecha)={max_r}")

    cur.execute("SELECT COUNT(*), MAX(fecha) FROM todo")
    n_t, max_t = cur.fetchone()
    write_log_line(logfh, f"  - todo(view): COUNT={n_t} | MAX(fecha)={max_t}")

def write_report(conn, report_path, logfh):
    # Reporte simple de verificación
    rows = []
    cur = conn.cursor()
    items = [
        ("astro_luna", "table"),
        ("matriz_astro_luna", "table"),
        ("todos_resumen_matriz_aslu", "table"),
        ("todo", "view"),
    ]
    for name, typ in items:
        cur.execute(f"SELECT COUNT(*), MAX(fecha) FROM {name}")
        count, maxf = cur.fetchone()
        rows.append((name, typ, "ok", count, maxf))

    import csv
    with open(report_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["objeto","tipo","estado","count","max_fecha"])
        writer.writerows(rows)
    write_log_line(logfh, f"[OK] Reporte guardado en: {report_path}")

# ============== MAIN ==============

def main():
    ap = argparse.ArgumentParser(description="Actualización integral de base AstroLuna")
    ap.add_argument("--db", required=True, help="Ruta al archivo .db de SQLite")
    ap.add_argument("--reporte", help="Ruta para CSV de reporte")
    ap.add_argument("--vacuum", action="store_true", help="Ejecutar VACUUM al final")
    ap.add_argument("--dry-run", action="store_true", help="Simular (no escribe)")
    ap.add_argument("--todo-join", choices=["left","inner"], default="inner",
                    help="Tipo de JOIN para vista 'todo' (default: inner)")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        raise SystemExit(f"[ERROR] No existe el archivo de base: {db_path}")

    # Log file (en la carpeta del .db)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(os.path.dirname(db_path), f"actualizar_base_astroluna_{stamp}.log.txt")

    # Abrir log
    with open(log_path, "w", encoding="utf-8") as logfh:
        write_log_line(logfh, "="*78)
        write_log_line(logfh, f"[INFO] Inicio: {now_str()}")
        write_log_line(logfh, f"[INFO] DB: {db_path}")
        md5_before = md5_file(db_path)
        write_log_line(logfh, f"[INFO] MD5 (antes): {md5_before}")
        write_log_line(logfh, f"[INFO] Opciones: dry_run={args.dry_run} | vacuum={args.vacuum} | todo_join={args.todo-join if False else args.todo_join}")

        # Conexión con control manual de transacción
        conn = sqlite3.connect(db_path, isolation_level=None)  # autocommit OFF; usaremos BEGIN/COMMIT manual
        conn.execute("PRAGMA foreign_keys=OFF;")
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        # user_version (auditoría)
        cur = conn.execute("PRAGMA user_version;")
        user_version = cur.fetchone()[0]
        write_log_line(logfh, f"[INFO] PRAGMA user_version={user_version}")

        try:
            if args.dry_run:
                write_log_line(logfh, "[INFO] DRY-RUN activo: no se escribirán cambios. Solo diagnósticos.")
                # Diagnósticos ligeros
                normalize_all_fecha_columns(conn, logfh)  # no cambia nada si no hay barras
                # Vista actual
                c = conn.execute("SELECT sql FROM sqlite_master WHERE type='view' AND name='todo'")
                row = c.fetchone()
                if row:
                    write_log_line(logfh, "[VIEW todo SQL (actual)]")
                    write_log_line(logfh, row[0])
                else:
                    write_log_line(logfh, "[WARN] La vista 'todo' no existe actualmente.")
                checks(conn, logfh)
                write_log_line(logfh, "[OK] DRY-RUN finalizado.")
                return

            # Transacción
            started_tx = False
            try:
                conn.execute("BEGIN IMMEDIATE;")
                started_tx = True
            except sqlite3.OperationalError as e:
                # Si ya hay transacción activa, seguimos sin marcar started_tx (evita commit/rollback dobles)
                write_log_line(logfh, f"[WARN] BEGIN IMMEDIATE falló ({e}); se continuará sin bandera de transacción.")

            # Pasos
            write_log_line(logfh, "[INFO] Normalizando fechas...")
            normalize_all_fecha_columns(conn, logfh)

            write_log_line(logfh, "[INFO] Reconstruyendo 'matriz_astro_luna'...")
            rebuild_matriz(conn, logfh)

            write_log_line(logfh, "[INFO] Reconstruyendo tablas resumen*...")
            rebuild_resumenes(conn, logfh)

            write_log_line(logfh, "[INFO] Reconstruyendo 'todos_cuando_son'...")
            rebuild_todos_cuando_son(conn, logfh)

            write_log_line(logfh, "[INFO] Reconstruyendo 'todo_cuando_*_es'...")
            rebuild_todo_cuando_es(conn, logfh)

            write_log_line(logfh, "[INFO] Reconstruyendo tablas 'cuando_*' detalladas...")
            rebuild_cuando_detalladas(conn, logfh)

            write_log_line(logfh, f"[INFO] Asegurando vista 'todo' ({args.todo_join.upper()} JOIN) ...")
            ensure_view_todo(conn, args.todo_join, logfh)

            # Commit
            if started_tx:
                conn.execute("COMMIT;")

        except Exception as e:
            if 'started_tx' in locals() and started_tx:
                try:
                    conn.execute("ROLLBACK;")
                except sqlite3.OperationalError:
                    pass
            write_log_line(logfh, f"[ERROR] {e!r}")
            raise
        finally:
            # Reporte opcional
            if args.reporte and not args.dry_run:
                write_report(conn, args.reporte, logfh)

            # VACUUM opcional
            if args.vacuum and not args.dry_run:
                write_log_line(logfh, "[INFO] VACUUM ...")
                try:
                    conn.execute("VACUUM;")
                    write_log_line(logfh, "[OK] VACUUM listo.")
                except sqlite3.OperationalError as e:
                    write_log_line(logfh, f"[WARN] VACUUM omitido: {e}")

            # Chequeos finales
            checks(conn, logfh)

            # MD5 después
            md5_after = md5_file(db_path)
            write_log_line(logfh, f"[INFO] MD5 (después): {md5_after}")

            # Cierre
            conn.close()
            write_log_line(logfh, f"[INFO] Fin: {now_str()}")
            write_log_line(logfh, "="*78)

    print("[OK] Proceso finalizado.")
    print(f"[OK] Log escrito en: {log_path}")

if __name__ == "__main__":
    main()
