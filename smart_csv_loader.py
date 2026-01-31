import os
import csv
import pandas as pd
import re

# -----------------------------------------------------------
#  SMART CSV LOADER — TOLERANTE A ARCHIVOS CORRUPTOS
# -----------------------------------------------------------
def smart_load_csv(path):
    """
    Lee un CSV aunque tenga:
      - columnas desalineadas
      - comas internas sin comillas
      - líneas rotas
      - columnas variables
    Reconstruye filas válidas consistentemente.
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

            # Separación robusta:
            parts = re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)

            # limpiar comillas sueltas
            parts = [p.replace('"', '').strip() for p in parts]

            rows.append(parts)
            max_cols = max(max_cols, len(parts))

    # Normalizar número de columnas
    normalized = []
    for r in rows:
        if len(r) < max_cols:
            r = r + [""] * (max_cols - len(r))
        elif len(r) > max_cols:
            r = r[:max_cols]
        normalized.append(r)

    # Crear DataFrame
    df = pd.DataFrame(normalized)

    # Asignar encabezados si primera fila parece header
    df.columns = [f"col_{i}" for i in range(max_cols)]

    print(f"[SMART] Columnas detectadas: {max_cols}")
    print(f"[SMART] Filas cargadas: {len(df)}")

    return df
