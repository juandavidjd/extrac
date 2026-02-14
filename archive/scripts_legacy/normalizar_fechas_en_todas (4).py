# normalizar_fechas_en_todas.py
# Uso:
#   python normalizar_fechas_en_todas.py --db "C:\RadarPremios\radar_premios.db"
import argparse, sqlite3, sys, os

SQL_LIST_TABLES = """
SELECT name
FROM sqlite_master
WHERE type='table'
  AND name NOT LIKE 'sqlite_%';
"""

SQL_PRAGMA_TABLE_INFO = "PRAGMA table_info({});"

SQL_COUNT_BARRAS = "SELECT COUNT(*) FROM {} WHERE {} LIKE '%/%';"

SQL_UPDATE_NORMALIZA = """
UPDATE {tabla}
SET {col} = CASE
  WHEN {col} GLOB '??/??/????'
    THEN substr({col},7,4) || '-' || substr({col},4,2) || '-' || substr({col},1,2)
  ELSE {col}
END
WHERE {col} LIKE '%/%';
"""

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True, help="Ruta a la base SQLite")
    args = p.parse_args()

    db = args.db
    if not os.path.exists(db):
        print(f"[ERROR] No existe: {db}")
        sys.exit(1)

    con = sqlite3.connect(db)
    con.isolation_level = None  # usaremos BEGIN/COMMIT manual
    cur = con.cursor()

    # Recolectar tablas con columna 'fecha' (tipo TEXT o sin tipo)
    cur.execute(SQL_LIST_TABLES)
    tablas = [r[0] for r in cur.fetchall()]
    objetivos = []  # [(tabla, col_fecha)]
    for t in tablas:
        cur.execute(SQL_PRAGMA_TABLE_INFO.format(f'"{t}"'))
        cols = cur.fetchall()  # cid, name, type, notnull, dflt, pk
        for _, name, ctype, *_ in cols:
            if name.lower() == "fecha":
                objetivos.append((t, name))
                break

    print(f"[INFO] Tablas con columna 'fecha': {len(objetivos)}")
    for t, c in sorted(objetivos):
        # ¿Cuántas con barra?
        cur.execute(SQL_COUNT_BARRAS.format(f'"{t}"', f'"{c}"'))
        con_barra = cur.fetchone()[0]
        if con_barra == 0:
            print(f"  - {t}: OK (sin barras)")
            continue

        print(f"  - {t}: normalizando {con_barra} filas ...")
        try:
            cur.execute("BEGIN;")
            cur.execute(SQL_UPDATE_NORMALIZA.format(tabla=f'"{t}"', col=f'"{c}"'))
            cur.execute("COMMIT;")
        except Exception as e:
            cur.execute("ROLLBACK;")
            print(f"    [WARN] {t}: no se pudo normalizar -> {e}")

    # Índices por rendimiento (si existen las tablas)
    for idx_stmt in [
        'CREATE INDEX IF NOT EXISTS idx_astro_luna_fecha ON "astro_luna"(fecha);',
        'CREATE INDEX IF NOT EXISTS idx_matriz_aslu_fecha ON "matriz_astro_luna"(fecha);',
        'CREATE INDEX IF NOT EXISTS idx_todos_resumen_aslu_fecha ON "todos_resumen_matriz_aslu"(fecha);'
    ]:
        try:
            cur.execute(idx_stmt)
        except Exception:
            pass

    # Resumen rápido
    def max_fecha(tabla):
        try:
            cur.execute(f'SELECT COUNT(*), MAX(fecha) FROM "{tabla}";')
            n, mx = cur.fetchone()
            return n, mx
        except Exception:
            return None, None

    for t in ["astro_luna", "matriz_astro_luna", "todos_resumen_matriz_aslu"]:
        n, mx = max_fecha(t)
        if n is not None:
            print(f"[CHECK] {t}: COUNT={n} | MAX(fecha)={mx}")

    print("[OK] Listo.")

if __name__ == "__main__":
    main()
