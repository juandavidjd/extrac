import sqlite3
import pandas as pd

# Rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_cero_es_centena.csv'

# Conexión a SQLite
conn = sqlite3.connect(DB_PATH)

# Consulta SQL filtrando centena igual a 0
query = """
SELECT fecha, numero, c_0
FROM primer_resumen_matriz_aslu
WHERE c_0 = 1
"""
df = pd.read_sql_query(query, conn)
conn.close()

# Guardar archivo
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

print(f'✅ Archivo creado: {OUTPUT_FILE}')
