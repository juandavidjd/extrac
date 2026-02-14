import sqlite3
import pandas as pd

# Rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_PATH = r'C:\RadarPremios\data\limpio\cuando_1_es_unidad.csv'

# Conectar a la base de datos
conn = sqlite3.connect(DB_PATH)

# Leer y filtrar datos
query = """
SELECT fecha, numero, u_1 
FROM segundo_resumen_matriz_aslu 
WHERE u_1 = 1
"""
df = pd.read_sql_query(query, conn)

# Guardar archivo CSV
df.to_csv(OUTPUT_PATH, sep='\t', index=False, encoding='utf-8')

conn.close()
print(f'✅ Archivo generado: {OUTPUT_PATH}')
