# -*- coding: utf-8 -*-
"""
score_candidates.py — Genera/lee 100 candidatos, los puntúa, guarda el run y (opcional) imprime VEREDICTO inmediato.
Ejemplo:
  python score_candidates.py --db "C:\RadarPremios\radar_premios.db" --gen 100 --seed 12345 --top 15 --shortlist 5 ^
         --export "C:\RadarPremios\candidatos_scored.csv" --export-all "C:\RadarPremios\candidatos_all.csv" ^
         --report "C:\RadarPremios\candidatos_scored.html" --auto-eval
"""
import argparse, csv, html, random, sqlite3, datetime, os, math
from pathlib import Path

# -------------- util db --------------
def get_max_fecha(conn):
    return conn.execute("SELECT MAX(fecha) FROM astro_luna").fetchone()[0]

def ensure_views(conn):
    # v_digit_hotcold
    conn.executescript("""
    CREATE VIEW IF NOT EXISTS v_digit_hotcold AS
    WITH last_date AS (
      SELECT MAX(date(fecha)) AS max_f FROM todos_cuando_son
    ),
    win AS (
      SELECT * FROM todos_cuando_son
      WHERE date(fecha) >= date((SELECT max_f FROM last_date), '-30 day')
    ),
    agg AS (
      SELECT digito, COUNT(*) AS cnt
      FROM win
      GROUP BY digito
    ),
    stats AS (
      SELECT COALESCE(MIN(cnt),0) AS mn,
             COALESCE(MAX(cnt),0) AS mx
      FROM agg
    )
    SELECT a.digito,
           COALESCE(a.cnt,0) AS cnt,
           CASE WHEN s.mx = s.mn THEN 0.5
                ELSE (a.cnt - s.mn) * 1.0 / (s.mx - s.mn)
           END AS hotcold_norm
    FROM agg a CROSS JOIN stats s;
    """)
    # v_last_seen_exact
    conn.executescript("""
    CREATE VIEW IF NOT EXISTS v_last_seen_exact AS
    SELECT
        numero,
        CAST(julianday((SELECT MAX(fecha) FROM astro_luna)) - julianday(MAX(fecha)) AS INTEGER) AS dias_desde
    FROM astro_luna
    GROUP BY numero;
    """)

def pattern_bonus(numstr: str) -> float:
    # Bonos/penalizaciones por patrón
    s = numstr
    uniq = len(set(s))
    if uniq == 4:   # todos distintos
        return +0.10
    if uniq == 3:   # un par
        return +0.05
    if uniq == 2:   # doble-doble o triple
        # triple o 2 pares se tratan neutro/leves
        if any(s.count(d)>=3 for d in set(s)):
            return 0.00
        return +0.05
    if uniq == 1:   # cuádruple
        return -0.05
    return 0.0

def last_seen_digitpos_norm(conn, cap_days=60):
    # mapa por posición -> {digito: score 0..1}
    maxf = get_max_fecha(conn)
    out = {}
    for p in ("um","c","d","u"):
        q = f"""
        WITH last AS (
          SELECT {p} AS digito, MAX(fecha) AS last_f
          FROM matriz_astro_luna
          GROUP BY {p}
        )
        SELECT l.digito,
               MIN(1.0, (julianday(?) - julianday(l.last_f)) / ? ) AS norm
        FROM last l
        """
        m = {}
        for dig, norm in conn.execute(q, (maxf, cap_days)):
            m[int(dig)] = float(norm) if norm is not None else 0.0
        # fill vacíos
        for d in range(10):
            m.setdefault(d, 1.0)  # si nunca visto, máxima recencia
        out[p] = m
    return out

def last_seen_exact_norm(conn, candidates, cap_days=180):
    # devuelve mapa numero->norm (0..1)
    maxf = get_max_fecha(conn)
    # tabla temporal con candidatos
    conn.execute("DROP TABLE IF EXISTS sel")
    conn.execute("CREATE TEMP TABLE sel(numero TEXT PRIMARY KEY)")
    conn.executemany("INSERT INTO sel(numero) VALUES (?)", [(c,) for c in candidates])

    q = """
    WITH last AS (
      SELECT a.numero, MAX(a.fecha) AS last_f
      FROM astro_luna a
      JOIN sel s ON s.numero = a.numero
      GROUP BY a.numero
    )
    SELECT s.numero,
           CASE
             WHEN l.last_f IS NULL THEN 1.0
             ELSE MIN(1.0, (julianday(?) - julianday(l.last_f)) / ? )
           END AS norm
    FROM sel s
    LEFT JOIN last l ON l.numero = s.numero
    """
    m = {}
    for num, norm in conn.execute(q, (maxf, cap_days)):
        m[num] = float(norm)
    # candidatos que nunca salieron (no aparecieron en last)
    for c in candidates:
        m.setdefault(c, 1.0)
    return m

def load_hotcold(conn):
    return {int(r["digito"]): float(r["hotcold_norm"])
            for r in conn.execute("SELECT digito, hotcold_norm FROM v_digit_hotcold")}

def cal_effect(conn, numstr: str, horizon=30):
    # efecto calendario básico: compara el dígito líder con el día de la semana del próximo sorteo
    # Heurística placeholder: usa hotcold de cada dígito y promedia con ligero sesgo si el dígito coincide con día%10
    # Si quieres algo más profundo, aquí se engancha.
    today = conn.execute("SELECT MAX(fecha) FROM astro_luna").fetchone()[0]
    dow = datetime.datetime.strptime(today, "%Y-%m-%d").weekday()  # 0..6
    digits = list(map(int, numstr))
    base = 0.0
    for d in digits:
        base += (1.0 if d == (dow % 10) else 0.6)
    return base / 4.0  # 0.6..1.0 aprox

def score_one(conn, numstr: str, w_hot=0.25, w_cal=0.2, w_dp=0.2, w_exact=0.35,
              dp_map=None, hc_map=None, exact_map=None):
    um, c, d, u = map(int, numstr)
    # hot/cold por dígito (promedio)
    hot = sum(hc_map.get(x, 0.5) for x in (um,c,d,u)) / 4.0
    # calendario
    cal = cal_effect(conn, numstr)
    # recencia por dígito/posición
    dp = (dp_map["um"][um] + dp_map["c"][c] + dp_map["d"][d] + dp_map["u"][u]) / 4.0
    # recencia exacta del número
    exact = exact_map.get(numstr, 1.0)
    # patrón
    patt = pattern_bonus(numstr)

    score = (w_hot*hot + w_cal*cal + w_dp*dp + w_exact*exact) + patt
    return {
        "numero": numstr,
        "score": score,
        "hotcold": hot,
        "cal": cal,
        "dp": dp,
        "exact": exact,
        "patt": patt
    }

def gen_candidates(n=100, allow_repeat=False, seed=None, allow_patterns=None, deny_patterns=None):
    rnd = random.Random(seed)
    out = set()
    while len(out) < n:
        num = f"{rnd.randint(0,9999):04d}"
        if not allow_repeat and num in out:
            continue
        ok = True
        if allow_patterns:
            ok = any(p(num) for p in allow_patterns)
        if ok and deny_patterns:
            if any(p(num) for p in deny_patterns):
                ok = False
        if ok:
            out.add(num)
    return list(out)

def export_csv(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["rank","numero","score","hotcold","cal","dp","exact","patt"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])

def export_html(rows, path: Path, title="Candidatos puntuados"):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    html_rows = []
    for r in rows:
        html_rows.append(
            f"<tr><td>{r['rank']}</td><td>{r['numero']}</td>"
            f"<td>{r['score']:.6f}</td><td>{r['hotcold']:.3f}</td>"
            f"<td>{r['cal']:.3f}</td><td>{r['dp']:.3f}</td>"
            f"<td>{r['exact']:.3f}</td><td>{r['patt']:+.3f}</td></tr>"
        )
    doc = f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 16px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align:right; }}
th {{ background:#f2f2f2; text-align:center; }}
td:nth-child(2), th:nth-child(2) {{ text-align:center; }}
</style>
</head><body>
<h2>{html.escape(title)}</h2>
<table>
<thead><tr><th>Rank</th><th>Número</th><th>Score</th><th>Hot/Cold</th><th>Cal</th><th>DP</th><th>Exact</th><th>Patrón</th></tr></thead>
<tbody>
{''.join(html_rows)}
</tbody></table>
</body></html>"""
    with path.open("w", encoding="utf-8") as f:
        f.write(doc)

def save_run(conn, rows, weights, meta):
    # tablas
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS runs(
      run_id     INTEGER PRIMARY KEY AUTOINCREMENT,
      created_at TEXT DEFAULT (datetime('now')),
      seed       INTEGER,
      w_hotcold  REAL,
      w_cal      REAL,
      w_dp       REAL,
      w_exact    REAL
    );
    CREATE TABLE IF NOT EXISTS run_candidates(
      run_id   INTEGER,
      rank     INTEGER,
      numero   TEXT,
      score    REAL,
      hotcold  REAL,
      cal      REAL,
      dp       REAL,
      exact    REAL,
      patt     REAL
    );
    """)
    cur = conn.execute(
        "INSERT INTO runs(seed,w_hotcold,w_cal,w_dp,w_exact) VALUES(?,?,?,?,?)",
        (meta["seed"], weights["w_hot"], weights["w_cal"], weights["w_dp"], weights["w_exact"])
    )
    run_id = cur.lastrowid
    conn.executemany("""
      INSERT INTO run_candidates(run_id,rank,numero,score,hotcold,cal,dp,exact,patt)
      VALUES(?,?,?,?,?,?,?,?,?)
    """, [
        (run_id, r["rank"], r["numero"], r["score"], r["hotcold"], r["cal"], r["dp"], r["exact"], r["patt"])
        for r in rows
    ])
    conn.commit()
    return run_id

def evaluate_now(conn, run_id):
    # compara con MAX(fecha)
    win = conn.execute("""
        SELECT fecha, numero
        FROM astro_luna
        WHERE fecha=(SELECT MAX(fecha) FROM astro_luna)
        LIMIT 1
    """).fetchone()
    if not win:
        return None
    maxf, win_num = win
    rank = conn.execute("""
        SELECT MIN(rank) FROM run_candidates
        WHERE run_id=? AND numero=?
    """, (run_id, win_num)).fetchone()[0]
    if rank is None:
        verdict = "MISS ❌"
    elif rank <= 5:
        verdict = "TOP-5 ✅"
    elif rank <= 100:
        verdict = "TOP-100"
    else:
        verdict = "MISS ❌"
    return {"fecha": maxf, "win_num": win_num, "rank": rank, "veredicto": verdict}

def score_all(conn, candidates, w_hot=0.25, w_cal=0.2, w_dp=0.2, w_exact=0.35,
              cap_digitpos=60, cap_exact=180, cal_horizon=30):
    ensure_views(conn)
    hc_map = load_hotcold(conn)
    dp_map = last_seen_digitpos_norm(conn, cap_days=cap_digitpos)
    exact_map = last_seen_exact_norm(conn, candidates, cap_days=cap_exact)

    rows = []
    for num in candidates:
        rows.append(score_one(conn, num, w_hot, w_cal, w_dp, w_exact, dp_map, hc_map, exact_map))
    rows.sort(key=lambda r: (-r["score"], r["numero"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--gen", type=int, default=100)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--candidatos", type=str, default=None, help="ruta CSV con columna 'numero' (opcional)")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--shortlist", type=int, default=5)
    ap.add_argument("--export", type=str, default=None)
    ap.add_argument("--export-all", type=str, default=None)
    ap.add_argument("--report", type=str, default=None)
    ap.add_argument("--w-hotcold", type=float, default=0.25)
    ap.add_argument("--w-cal", type=float, default=0.20)
    ap.add_argument("--w-dp", type=float, default=0.20)
    ap.add_argument("--w-exact", type=float, default=0.35)
    ap.add_argument("--cap-digitpos", type=int, default=60)
    ap.add_argument("--cap-exact", type=int, default=180)
    ap.add_argument("--cal-horizon", type=int, default=30)
    ap.add_argument("--auto-eval", action="store_true", help="Imprime VEREDICTO contra MAX(fecha) tras guardar el run")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        # candidatos
        if args.candidatos:
            nums = []
            with open(args.candidatos, "r", encoding="utf-8") as f:
                rdr = csv.DictReader(f)
                for row in rdr:
                    nums.append(str(row["numero"]).zfill(4))
        else:
            nums = gen_candidates(args.gen, seed=args.seed)

        rows = score_all(
            conn, nums,
            w_hot=args.w_hotcold, w_cal=args.w_cal, w_dp=args.w_dp, w_exact=args.w_exact,
            cap_digitpos=args.cap_digitpos, cap_exact=args.cap_exact, cal_horizon=args.cal_horizon
        )

        # TOP N
        top_rows = rows[:args.top]
        print(f"TOP {args.top}")
        for r in top_rows:
            print(f"{r['numero']}  score={r['score']:.6f}  hotcold={r['hotcold']:.3f}  cal={r['cal']:.3f}  dp={r['dp']:.3f}  exact={r['exact']:.3f}  patt={r['patt']:+.3f}")

        # exports
        if args.export:
            export_csv(top_rows, Path(args.export))
            print(f"[OK] CSV → {args.export}")
        if args.export_all:
            export_csv(rows, Path(args.export_all))
            print(f"[OK] CSV (todos) → {args.export_all}")
        if args.report:
            export_html(top_rows, Path(args.report))
            print(f"[OK] HTML → {args.report}")

        # Shortlist + Folio
        shortlist_n = max(1, min(args.shortlist, args.top))
        sl = rows[:shortlist_n]

        print("\n================================================================")
        print(f"SHORTLIST FINAL ({shortlist_n} propuestas)")
        print("----------------------------------------------------------------")
        for r in sl:
            print(f" {r['rank']:>2}. {r['numero']}  score={r['score']:.6f}  hotcold={r['hotcold']:.3f}  cal={r['cal']:.3f}  dp={r['dp']:.3f}  exact={r['exact']:.3f}  patt={r['patt']:+.3f}")
        print("----------------------------------------------------------------")
        print("FOLIO DEL RUN")
        print("----------------------------------------------------------------")
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"timestamp: {ts}")
        print(f"db: {args.db}")
        print(f"gen: {args.gen}")
        print(f"seed: {args.seed}")
        print(f"top: {args.top}")
        print(f"shortlist: {shortlist_n}")
        print(f"w_hotcold: {args.w_hotcold}")
        print(f"w_cal: {args.w_cal}")
        print(f"w_dp: {args.w_dp}")
        print(f"w_exact: {args.w_exact}")
        print(f"cap_digitpos: {args.cap_digitpos}")
        print(f"cap_exact: {args.cap_exact}")
        print(f"export_top: {args.export or ''}")
        print(f"export_all: {args.export_all or ''}")
        print(f"report_html: {args.report or ''}")
        print("================================================================")

        # Guardar en DB
        run_id = save_run(conn, rows, {
            "w_hot": args.w_hotcold, "w_cal": args.w_cal, "w_dp": args.w_dp, "w_exact": args.w_exact
        }, meta={"seed": args.seed})
        print(f"\n[OK] Run guardado en DB con run_id={run_id}")

        # VEREDICTO inmediato si se pide
        if args.auto-eval if False else args.auto_eval:  # protección por nombres con guion
            pass
        if getattr(args, "auto_eval", False):
            res = evaluate_now(conn, run_id)
            if res:
                print("\n==================== VEREDICTO (post-run) ====================")
                print(f"Fecha real más reciente: {res['fecha']}")
                print(f"Número ganador:         {res['win_num']}")
                print(f"Run evaluado:           run_id={run_id}  seed={args.seed}")
                print(f"Veredicto:              {res['veredicto']}  (rank={res['rank'] if res['rank'] is not None else '—'})")
                print("==============================================================\n")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
