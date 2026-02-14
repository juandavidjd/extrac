import sqlite3
import pandas as pd

# Ruta de base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_PATH = r'C:\RadarPremios\data\limpio\cuando_cero_es_c_y_d.csv'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta para filtrar donde c_0 == 1 y d_0 == 1
query = """
SELECT fecha, numero, c_0, d_0
FROM primer_resumen_matriz_aslu
WHERE c_0 = 1 AND d_0 = 1
"""

# Leer datos y exportar
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_PATH, sep='\t', index=False, encoding='utf-8')

conn.close()
print(f'✅ Archivo generado: {OUTPUT_PATH}')
