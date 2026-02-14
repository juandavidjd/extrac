# python todos_cuando_son.py

import sqlite3
import pandas as pd
import os

# Rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\todos_cuando_son.csv'

# Lista de tablas de todo_cuando_X_es
tablas = [
    'todo_cuando_0_es',
    'todo_cuando_1_es',
    'todo_cuando_2_es',
    'todo_cuando_3_es',
    'todo_cuando_4_es',
    'todo_cuando_5_es',
    'todo_cuando_6_es',
    'todo_cuando_7_es',
    'todo_cuando_8_es',
    'todo_cuando_9_es'
]

# Conexión a SQLite
conn = sqlite3.connect(DB_PATH)

# Acumulador de DataFrames
df_combined = []

try:
    for tabla in tablas:
        query = f"SELECT * FROM {tabla}"
        df = pd.read_sql_query(query, conn)
        df['origen_tabla'] = tabla  # Para rastrear el origen
        df_combined.append(df)

    # Concatenar todos los DataFrames
    resultado = pd.concat(df_combined, ignore_index=True)

    # Guardar como CSV
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    resultado.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

    print(f'✅ Archivo creado: {OUTPUT_FILE}')

except Exception as e:
    print(f'❌ Error durante la ejecución: {e}')

finally:
    conn.close()
