# python todo_cuando_9_es.py

import sqlite3
import pandas as pd
import os

# Rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\todo_cuando_9_es.csv'

# Lista de tablas que se van a unir
tablas = [
    'cuando_9_es_unidad',
    'cuando_9_es_decena',
    'cuando_9_es_centena',
    'cuando_9_es_umil',
    'cuando_9_es_d_y_u',
    'cuando_9_es_c_y_u',
    'cuando_9_es_um_y_u',
    'cuando_9_es_c_y_d',
    'cuando_9_es_um_y_d',
    'cuando_9_es_um_y_c',
    'cuando_9_es_c_d_y_u',
    'cuando_9_es_um_c_d_y_u',
    'cuando_9_es_um_c_y_d',
    'cuando_9_es_um_c_y_u',
    'cuando_9_es_um_d_y_u'
]

# Conexión a SQLite
conn = sqlite3.connect(DB_PATH)

# Acumulador de DataFrames
df_combined = []

try:
    for tabla in tablas:
        query = f"SELECT * FROM {tabla}"
        df = pd.read_sql_query(query, conn)
        df['origen'] = tabla  # Añadir columna que indica la tabla de origen
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
