import sqlite3
import pandas as pd

# Configuración
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\todo_cuando_1_es.csv'

# Lista de tablas que contienen combinaciones del número 1
tablas = [
    'cuando_1_es_unidad',
    'cuando_1_es_decena',
    'cuando_1_es_centena',
    'cuando_1_es_umil',
    'cuando_1_es_d_y_u',
    'cuando_1_es_c_y_u',
    'cuando_1_es_um_y_u',
    'cuando_1_es_c_y_d',
    'cuando_1_es_um_y_d',
    'cuando_1_es_um_y_c',
    'cuando_1_es_c_d_y_u',
    'cuando_1_es_um_c_d_y_u',
    'cuando_1_es_um_c_y_d',
    'cuando_1_es_um_c_y_u',
    'cuando_1_es_um_d_y_u',
]

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Leer y unificar todas las tablas
dfs = []
for tabla in tablas:
    try:
        df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
        df['origen'] = tabla  # Añadir columna para rastrear el origen
        dfs.append(df)
    except Exception as e:
        print(f"⚠️ No se pudo leer la tabla {tabla}: {e}")

# Concatenar y guardar
if dfs:
    df_final = pd.concat(dfs, ignore_index=True)
    df_final.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')
    print(f"✅ Archivo generado: {OUTPUT_FILE}")
else:
    print("❌ No se encontraron datos para combinar.")

# Cierre
conn.close()
