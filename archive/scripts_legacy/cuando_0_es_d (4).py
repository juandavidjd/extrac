import sqlite3
import pandas as pd

# Rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_cero_es_decena.csv'

# Conexión a SQLite
conn = sqlite3.connect(DB_PATH)

# Consulta filtrada
query = """
SELECT fecha, numero, d_0 
FROM primer_resumen_matriz_aslu
WHERE d_0 = 1
"""
df = pd.read_sql_query(query, conn)

conn.close()

# Guardar como CSV
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

print(f'✅ Archivo creado: {OUTPUT_FILE}')
