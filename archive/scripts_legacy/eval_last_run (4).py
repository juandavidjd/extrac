# -*- coding: utf-8 -*-
"""
eval_last_run.py — Evalúa el último run almacenado en DB contra el último sorteo real (MAX(fecha))
- Imprime bloque VEREDICTO (TOP-5 / TOP-100 / MISS) + folio básico
Uso:
  python eval_last_run.py --db "C:\RadarPremios\radar_premios.db"
"""
import argparse, sqlite3, datetime

def eval_run(conn):
    # Último run
    r = conn.execute("""
        SELECT run_id, created_at, seed, w_hotcold, w_cal, w_dp, w_exact
        FROM runs
        ORDER BY run_id DESC
        LIMIT 1
    """).fetchone()
    if not r:
        print("[INFO] No hay runs guardados aún.")
        return

    run_id, created_at, seed, w_hot, w_cal, w_dp, w_ex = r

    # Número ganador más reciente
    win = conn.execute("""
        SELECT fecha, numero
        FROM astro_luna
        WHERE fecha = (SELECT MAX(fecha) FROM astro_luna)
        LIMIT 1
    """).fetchone()
    if not win:
        print("[INFO] No hay registros en astro_luna.")
        return

    maxf, win_num = win

    # Rank del número en TOP y en ALL
    top_rank = conn.execute("""
        SELECT MIN(rank)
        FROM run_candidates
        WHERE run_id = ? AND numero = ?
    """, (run_id, win_num)).fetchone()[0]

    # Si no está en run_candidates, es MISS
    veredicto = "MISS ❌"
    if top_rank is not None:
        if top_rank <= 5:
            veredicto = "TOP-5 ✅"
        elif top_rank <= 100:
            veredicto = "TOP-100"

    # Impresión
    print("\n==================== VEREDICTO (post-run) ====================")
    print(f"Fecha real más reciente: {maxf}")
    print(f"Número ganador:         {win_num}")
    print(f"Run evaluado:           run_id={run_id}  created_at={created_at}  seed={seed}")
    print(f"Veredicto:              {veredicto}  (rank={top_rank if top_rank is not None else '—'})")
    print("==============================================================\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        eval_run(conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
