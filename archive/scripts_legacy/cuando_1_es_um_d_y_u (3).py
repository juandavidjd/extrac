import sqlite3
import pandas as pd

# Ruta a la base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_1_es_um_d_y_u.csv'

# Conectar a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL
query = """
    SELECT fecha, numero, um_1, d_1, u_1
    FROM segundo_resumen_matriz_aslu
    WHERE um_1 = 1 AND d_1 = 1 AND u_1 = 1
"""

# Ejecutar consulta y guardar resultados
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar la conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
