import sqlite3
import pandas as pd

# Configuración de rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_8_es_unidad.csv'
TABLE_NAME = 'noveno_resumen_matriz_aslu'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL
query = f"""
    SELECT fecha, numero, u_8
    FROM {TABLE_NAME}
    WHERE u_8 = 1
"""

# Ejecutar consulta y exportar a CSV
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cierre de conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
