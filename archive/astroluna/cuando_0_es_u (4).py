import sqlite3
import pandas as pd

# Rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_cero_es_unidad.csv'

# Conexión a SQLite
conn = sqlite3.connect(DB_PATH)

# Consulta filtrada: solo cuando u_0 es 1
query = """
SELECT fecha, numero, u_0 
FROM primer_resumen_matriz_aslu
WHERE u_0 = 1
"""
df = pd.read_sql_query(query, conn)

conn.close()

# Guardar archivo CSV
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

print(f'✅ Archivo creado con casos donde el 0 está en unidad: {OUTPUT_FILE}')
