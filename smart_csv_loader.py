import os
import re
import pandas as pd

def smart_load_csv(path):
    """
    Lector inteligente para CSV dañados o irregularmente formateados.
    - Tolera comas sin comillas
    - Tolera columnas desalineadas
    - Tolera líneas corruptas
    - Reconstruye filas con número variable de columnas
    """
    print(f"[SMART] Leyendo CSV tolerante: {path}")

    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe el archivo: {path}")

    rows = []
    max_cols = 0

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # dividir la línea respetando comillas
            parts = re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)

            # limpiar comillas
            parts = [p.replace('"', '').strip() for p in parts]

            rows.append(parts)
            max_cols = max(max_cols, len(parts))

    # igualar longitud de filas
    normalized = []
    for r in rows:
        if len(r) < max_cols:
            r += [""] * (max_cols - len(r))
        elif len(r) > max_cols:
            r = r[:max_cols]
        normalized.append(r)

    df = pd.DataFrame(normalized)
    df.columns = [f"col_{i}" for i in range(max_cols)]

    print(f"[SMART] Columnas detectadas: {max_cols}")
    print(f"[SMART] Filas cargadas: {len(df)}")

    return df
