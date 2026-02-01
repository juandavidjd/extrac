import sqlite3
import pandas as pd
import os

# Rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\todo_cuando_2_es.csv'

# Lista de tablas a combinar
tablas = [
    'cuando_2_es_unidad',
    'cuando_2_es_decena',
    'cuando_2_es_centena',
    'cuando_2_es_umil',
    'cuando_2_es_d_y_u',
    'cuando_2_es_c_y_u',
    'cuando_2_es_um_y_u',
    'cuando_2_es_c_y_d',
    'cuando_2_es_um_y_d',
    'cuando_2_es_um_y_c',
    'cuando_2_es_c_d_y_u',
    'cuando_2_es_um_c_d_y_u',
    'cuando_2_es_um_c_y_d',
    'cuando_2_es_um_c_y_u',
    'cuando_2_es_um_d_y_u'
]

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Lista para almacenar los DataFrames
dfs = []

# Cargar cada tabla desde la base de datos
for tabla in tablas:
    try:
        df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
        df['origen_tabla'] = tabla
        dfs.append(df)
        print(f"✅ Cargado desde base de datos: {tabla}")
    except Exception as e:
        print(f"❌ Error al cargar {tabla} desde la base de datos: {e}")

# Cerrar conexión
conn.close()

# Concatenar todos los DataFrames si hay alguno cargado
if dfs:
    df_final = pd.concat(dfs, ignore_index=True)
    df_final.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')
    print(f"\n✅ Archivo generado con todas las combinaciones: {OUTPUT_FILE}")
else:
    print("❌ No se pudo generar el archivo. No se cargaron datos.")
