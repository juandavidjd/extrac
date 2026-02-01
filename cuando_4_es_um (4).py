import sqlite3
import pandas as pd

# Rutas de configuración
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_4_es_umil.csv'
TABLE_NAME = 'quinto_resumen_matriz_aslu'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL para filtrar um_4 = 1
query = f"""
    SELECT fecha, numero, um_4
    FROM {TABLE_NAME}
    WHERE um_4 = 1
"""

# Ejecutar la consulta y exportar los resultados
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar la conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
