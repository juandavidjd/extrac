import sqlite3
import pandas as pd
import os

# Configuración
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\todo_cuando_7_es.csv'

# Lista de tablas de combinaciones
tablas = [
    'cuando_7_es_unidad',
    'cuando_7_es_decena',
    'cuando_7_es_centena',
    'cuando_7_es_umil',
    'cuando_7_es_d_y_u',
    'cuando_7_es_c_y_u',
    'cuando_7_es_um_y_u',
    'cuando_7_es_c_y_d',
    'cuando_7_es_um_y_d',
    'cuando_7_es_um_y_c',
    'cuando_7_es_c_d_y_u',
    'cuando_7_es_um_c_d_y_u',
    'cuando_7_es_um_c_y_d',
    'cuando_7_es_um_c_y_u',
    'cuando_7_es_um_d_y_u'
]

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

dataframes = []

# Procesar cada tabla
for tabla in tablas:
    try:
        df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
        df['origen'] = tabla  # Para identificar la fuente de cada fila
        dataframes.append(df)
        print(f"✅ Tabla procesada: {tabla}")
    except Exception as e:
        print(f"⚠️ Error al procesar {tabla}: {e}")

# Combinar todas las tablas
if dataframes:
    df_total = pd.concat(dataframes, ignore_index=True).drop_duplicates()
    df_total.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')
    print(f"\n✅ Archivo final generado: {OUTPUT_FILE}")
else:
    print("❌ No se encontró ninguna tabla válida para combinar.")

# Cerrar conexión
conn.close()
