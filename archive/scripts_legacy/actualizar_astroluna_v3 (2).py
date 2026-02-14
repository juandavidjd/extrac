#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v3 – Orquestador Astroluna

Flujo:
1) (Opcional) Reconstruye `matriz_astro_luna` desde `astroluna` (o `astro_luna`) proyectando columnas comunes,
   con validaciones para no romper NOT NULL; permite defaults si lo pides.
2) Actualiza automáticamente tablas downstream que dependen de `matriz_astro_luna`.

Características clave
- Exclusiones por defecto (otros sorteos y fuentes) + vistas omitidas.
- Por defecto aplica **full coverage**: refresca SOLO tablas cuyo 100% de columnas existe en la matriz.
- Puedes permitir refresco parcial con --allow-partial; si lo usas, puedes rellenar columnas faltantes con --fill-defaults col=VAL.
- --reconstruir-matriz: borra y llena `matriz_astro_luna` desde la fuente.
- Reporte CSV, dry-run y VACUUM.

Ejemplos (Windows):
  python actualizar_astroluna_v3.py --db "C:\\RadarPremios\\radar_premios.db" --reconstruir-matriz --dry-run
  python actualizar_astroluna_v3.py --db "C:\\RadarPremios\\radar_premios.db" --reconstruir-matriz --reporte "C:\\RadarPremios\\reporte_v3.csv" --vacuum
  python actualizar_astroluna_v3.py --db "C:\\RadarPremios\\radar_premios.db" --allow-partial --fill-defaults posicion='' signo=''
"""

import argparse
import os
import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Optional, Sequence, Tuple

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
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)
    ).fetchone() is not None

def get_objects(conn: sqlite3.Connection) -> List[Tuple[str, str]]:
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
    req = [c[1] for c in cols if c[3] == 1 and c[5] == 0 and c[4] is None]  # NOT NULL & not-PK & no default
    return all_cols, req

def parse_fill_defaults(items: Optional[Sequence[str]]) -> Dict[str, str]:
    defaults: Dict[str, str] = {}
    if items:
        for itm in items:
            if "=" in itm:
                k, v = itm.split("=", 1)
                defaults[k.strip()] = v.strip()
    return defaults

# ------------------ Reconstrucción de la matriz ------------------
def reconstruir_matriz(conn: sqlite3.Connection, src: str, matriz: str, allow_nulls: bool, dry_run: bool):
    dst_all, dst_req = required_cols(conn, matriz)
    src_cols = [c[1] for c in get_cols(conn, src)]
    comunes = [c for c in dst_all if c in src_cols]
    faltan_req = [c for c in dst_req if c not in src_cols]

    if faltan_req and not allow_nulls:
        raise SystemExit(
            "[ERROR] No se puede reconstruir '{matriz}': faltan columnas requeridas en '{src}': {faltan}".format(
                matriz=matriz, src=src, faltan=faltan_req
            )
        )

    before = count_rows(conn, matriz)
    if dry_run:
        # Solo mostramos qué pasaría
        return before, before, comunes, faltan_req

    with tx(conn):
        conn.execute(f'DELETE FROM "{matriz}"')
        if comunes:
            cols_sql = ", ".join(f'"{c}"' for c in comunes)
            conn.execute(
                f'INSERT INTO "{matriz}" ({cols_sql}) SELECT {cols_sql} FROM "{src}"'
            )

    after = count_rows(conn, matriz)
    return before, after, comunes, faltan_req

# ------------------ Refresh downstream desde matriz ---------------
def refresh_from_matrix(
    conn: sqlite3.Connection,
    full_coverage_only: bool,      # True = 100% columnas deben existir en la matriz
    allow_partial: bool,           # Si False y falta alguna requerida -> omitir
    targets: Optional[Sequence[str]],
    exclude: Optional[Sequence[str]],
    dry_run: bool,
    fill_defaults: Dict[str, str],
):
    if not table_exists(conn, MATRIX_TABLE):
        raise SystemExit("[ERROR] No existe la tabla '{0}'.".format(MATRIX_TABLE))

    src_cols = [c[1] for c in get_cols(conn, MATRIX_TABLE)]
    objs = get_objects(conn)

    exclude_set = set(DEFAULT_EXCLUDES)
    if exclude:
        exclude_set.update(exclude)

    acciones: List[Tuple[str, str, str, Optional[int], Optional[int]]] = []

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
        faltan_en_matriz = [c for c in dst_all if c not in src_cols]

        if full_coverage_only and faltan_en_matriz:
            acciones.append((name, otype, "omitida (full-coverage-only; faltan: {0})".format(faltan_en_matriz), None, None))
            continue

        if not full_coverage_only:
            if not allow_partial and any(c not in src_cols for c in dst_req):
                faltan_req = [c for c in dst_req if c not in src_cols]
                acciones.append((name, otype, "omitida (faltan requeridas: {0})".format(faltan_req), None, None))
                continue
            if len(comunes) == 0:
                acciones.append((name, otype, "omitida (sin columnas comunes)", None, None))
                continue

        antes = count_rows(conn, name)
        if not dry_run:
            with tx(conn):
                conn.execute(f'DELETE FROM "{name}"')
                if comunes:
                    cols_sql = ", ".join(f'"{c}"' for c in comunes)
                    conn.execute(
                        f'INSERT INTO "{name}" ({cols_sql}) SELECT {cols_sql} FROM "{MATRIX_TABLE}"'
                    )
                # Rellenar defaults en columnas que NO existen en la matriz
                for col, val in fill_defaults.items():
                    if col in dst_all and col not in src_cols:
                        conn.execute(f'UPDATE "{name}" SET "{col}" = ?', (val,))
        despues = count_rows(conn, name) if not dry_run else None
        acciones.append((name, otype, "refrescada desde {0}".format(MATRIX_TABLE), antes, despues))

    return acciones

# ------------------------------- CLI ------------------------------
def main():
    ap = argparse.ArgumentParser(description="v3 Orquestador Astroluna: reconstruye matriz y refresca downstream")
    ap.add_argument("--db", required=True, help="Ruta a la BD SQLite. Ej: C:\\RadarPremios\\radar_premios.db")
    ap.add_argument("--reconstruir-matriz", action="store_true", help="Reconstruir matriz_astro_luna desde astroluna/astro_luna")
    ap.add_argument("--permitir-nulos-matriz", action="store_true", help="Permitir NULLs en requeridas al reconstruir matriz (no recomendado)")
    ap.add_argument("--allow-partial", action="store_true", help="Permitir refresh parcial (intersección de columnas)")
    ap.add_argument("--fill-defaults", nargs="*", help="Pares col=VAL para rellenar columnas destino que NO están en la matriz")
    ap.add_argument("--targets", nargs="*", help="Tablas específicas a refrescar")
    ap.add_argument("--exclude", nargs="*", help="Exclusiones adicionales")
    ap.add_argument("--dry-run", action="store_true", help="Simular sin escribir cambios")
    ap.add_argument("--reporte", help="Guardar reporte CSV")
    ap.add_argument("--vacuum", action="store_true", help="VACUUM al final si no es dry-run")
    args = ap.parse_args()

    db_path = args.db
    if not os.path.isfile(db_path):
        ejemplo = r'C:\RadarPremios\radar_premios.db'
        msg = (
            "[ERROR] No se puede abrir la BD: {db}\n"
            "Ejemplo (Windows):\n"
            "  python {script} --db \"{ejemplo}\"\n"
        ).format(db=db_path, script=os.path.basename(__file__), ejemplo=ejemplo)
        raise SystemExit(msg)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        # 1) Reconstrucción de matriz (si se pide)
        if args.reconstruir_matriz:
            src = detect_source(conn)
            if not src:
                raise SystemExit("[ERROR] No se encontró tabla fuente 'astroluna' ni 'astro_luna'.")
            if not table_exists(conn, MATRIX_TABLE):
                raise SystemExit("[ERROR] No existe la tabla '{0}'.".format(MATRIX_TABLE))
            print("[INFO] Reconstruyendo '{matriz}' desde '{src}' ... (dry_run={dry})".format(
                matriz=MATRIX_TABLE, src=src, dry=args.dry_run
            ))
            before, after, comunes, faltan_req = reconstruir_matriz(
                conn, src, MATRIX_TABLE, allow_nulls=args.permitir_nulos_matriz, dry_run=args.dry_run
            )
            print("[MATRIZ] columnas comunes: {n} -> {ejemplo}{suf}".format(
                n=len(comunes),
                ejemplo=comunes[:10],
                suf=" ..." if len(comunes) > 10 else ""
            ))
            if faltan_req:
                print("[WARN] Requeridas faltantes en fuente: {0}".format(faltan_req))
            # Mostrar últimas fechas (si existe 'fecha')
            try:
                max_src = conn.execute(f"SELECT MAX(fecha) FROM '{src}'").fetchone()[0]
                max_mat = conn.execute(f"SELECT MAX(fecha) FROM '{MATRIX_TABLE}'").fetchone()[0]
                print("[FECHAS] MAX(fecha) {src} = {fs} | {mat} = {fm}".format(
                    src=src, fs=max_src, mat=MATRIX_TABLE, fm=max_mat
                ))
            except Exception:
                pass
        else:
            print("[INFO] Reconstrucción de matriz omitida.")

        # 2) Refresh downstream (full coverage por defecto; si pasas --allow-partial lo relajamos)
        print("[INFO] Refrescando downstream desde '{mat}' ... (dry_run={dry})".format(
            mat=MATRIX_TABLE, dry=args.dry_run
        ))
        fill_defaults = parse_fill_defaults(args.fill_defaults)
        full_coverage_only = not args.allow_partial
        acciones = refresh_from_matrix(
            conn,
            full_coverage_only=full_coverage_only,
            allow_partial=args.allow_partial,
            targets=args.targets,
            exclude=args.exclude,
            dry_run=args.dry_run,
            fill_defaults=fill_defaults
        )

        # Salida
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
                print("[OK] Reporte guardado en: {0}".format(args.reporte))
            except Exception as e:
                print("[WARN] No se pudo guardar el reporte: {0}".format(e))

        if args.vacuum and not args.dry_run:
            try:
                print("[INFO] VACUUM ...")
                conn.execute("VACUUM")
                print("[OK] VACUUM listo.")
            except Exception as e:
                print("[WARN] VACUUM falló: {0}".format(e))
        print("[OK] Finalizado.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
