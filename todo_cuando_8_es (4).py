import sqlite3
import pandas as pd
import os

# Configuración
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\todo_cuando_8_es.csv'

# Lista de tablas a procesar con sus columnas
tablas_columnas = {
    'cuando_8_es_unidad': ['fecha', 'numero', 'u_8'],
    'cuando_8_es_decena': ['fecha', 'numero', 'd_8'],
    'cuando_8_es_centena': ['fecha', 'numero', 'c_8'],
    'cuando_8_es_umil': ['fecha', 'numero', 'um_8'],
    'cuando_8_es_d_y_u': ['fecha', 'numero', 'd_8', 'u_8'],
    'cuando_8_es_c_y_u': ['fecha', 'numero', 'c_8', 'u_8'],
    'cuando_8_es_um_y_u': ['fecha', 'numero', 'um_8', 'u_8'],
    'cuando_8_es_c_y_d': ['fecha', 'numero', 'c_8', 'd_8'],
    'cuando_8_es_um_y_d': ['fecha', 'numero', 'um_8', 'd_8'],
    'cuando_8_es_um_y_c': ['fecha', 'numero', 'um_8', 'c_8'],
    'cuando_8_es_c_d_y_u': ['fecha', 'numero', 'c_8', 'd_8', 'u_8'],
    'cuando_8_es_um_c_d_y_u': ['fecha', 'numero', 'um_8', 'c_8', 'd_8', 'u_8'],
    'cuando_8_es_um_c_y_d': ['fecha', 'numero', 'um_8', 'c_8', 'd_8'],
    'cuando_8_es_um_c_y_u': ['fecha', 'numero', 'um_8', 'c_8', 'u_8'],
    'cuando_8_es_um_d_y_u': ['fecha', 'numero', 'um_8', 'd_8', 'u_8']
}

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# DataFrames acumulados
dataframes = []

# Leer y acumular datos de todas las tablas
for tabla, columnas in tablas_columnas.items():
    try:
        query = f"SELECT {', '.join(columnas)} FROM {tabla}"
        df = pd.read_sql_query(query, conn)
        df['origen'] = tabla
        dataframes.append(df)
        print(f"✅ Procesado: {tabla}")
    except Exception as e:
        print(f"⚠️ Error al procesar {tabla}: {e}")

# Concatenar y guardar
if dataframes:
    df_total = pd.concat(dataframes, ignore_index=True)
    df_total.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')
    print(f"\n✅ Archivo generado con todas las combinaciones: {OUTPUT_FILE}")
else:
    print("❌ No se generó ningún archivo. No se pudieron leer tablas.")

# Cerrar conexión
conn.close()
