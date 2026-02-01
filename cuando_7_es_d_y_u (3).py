import sqlite3
import pandas as pd

# Configuración de rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_7_es_d_y_u.csv'
TABLE_NAME = 'octavo_resumen_matriz_aslu'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL
query = f"""
    SELECT fecha, numero, d_7, u_7
    FROM {TABLE_NAME}
    WHERE d_7 = 1 AND u_7 = 1
"""

# Ejecutar consulta y guardar en CSV
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cierre de conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
