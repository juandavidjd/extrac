import sqlite3
import pandas as pd

# Ruta de base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_PATH = r'C:\RadarPremios\data\limpio\cuando_cero_es_um_y_d.csv'

# Conectar a la base de datos
conn = sqlite3.connect(DB_PATH)

# Ejecutar la consulta SQL
query = """
SELECT fecha, numero, um_0, d_0
FROM primer_resumen_matriz_aslu
WHERE um_0 = 1 AND d_0 = 1
"""

# Leer el resultado en DataFrame y exportar a CSV
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_PATH, sep='\t', index=False, encoding='utf-8')

conn.close()
print(f'✅ Archivo generado: {OUTPUT_PATH}')
