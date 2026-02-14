import sqlite3
import pandas as pd

# Rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\todo_cuando_3_es.csv'

# Diccionario de tablas y columnas a extraer
TABLAS = {
    'cuando_3_es_unidad': ['fecha', 'numero', 'u_3'],
    'cuando_3_es_decena': ['fecha', 'numero', 'd_3'],
    'cuando_3_es_centena': ['fecha', 'numero', 'c_3'],
    'cuando_3_es_umil': ['fecha', 'numero', 'um_3'],
    'cuando_3_es_d_y_u': ['fecha', 'numero', 'd_3', 'u_3'],
    'cuando_3_es_c_y_u': ['fecha', 'numero', 'c_3', 'u_3'],
    'cuando_3_es_um_y_u': ['fecha', 'numero', 'um_3', 'u_3'],
    'cuando_3_es_c_y_d': ['fecha', 'numero', 'c_3', 'd_3'],
    'cuando_3_es_um_y_d': ['fecha', 'numero', 'um_3', 'd_3'],
    'cuando_3_es_um_y_c': ['fecha', 'numero', 'um_3', 'c_3'],
    'cuando_3_es_c_d_y_u': ['fecha', 'numero', 'c_3', 'd_3', 'u_3'],
    'cuando_3_es_um_c_d_y_u': ['fecha', 'numero', 'um_3', 'c_3', 'd_3', 'u_3'],
    'cuando_3_es_um_c_y_d': ['fecha', 'numero', 'um_3', 'c_3', 'd_3'],
    'cuando_3_es_um_c_y_u': ['fecha', 'numero', 'um_3', 'c_3', 'u_3'],
    'cuando_3_es_um_d_y_u': ['fecha', 'numero', 'um_3', 'd_3', 'u_3']
}

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Lista para acumular resultados
todos_los_datos = []

# Recorrer tablas y agregar columna 'combinacion'
for tabla, columnas in TABLAS.items():
    try:
        query = f"SELECT {', '.join(columnas)} FROM {tabla}"
        df = pd.read_sql_query(query, conn)
        df["combinacion"] = tabla
        todos_los_datos.append(df)
    except Exception as e:
        print(f"⚠️ Error al procesar {tabla}: {e}")

# Unir todos los DataFrames en uno solo
df_final = pd.concat(todos_los_datos, ignore_index=True)

# Exportar a CSV
df_final.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cierre de conexión
conn.close()

print(f"✅ Archivo consolidado generado: {OUTPUT_FILE}")
