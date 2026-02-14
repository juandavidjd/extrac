import sqlite3
import pandas as pd

# Rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_PATH = r'C:\RadarPremios\data\limpio\cuando_cero_es_um_c_y_u.csv'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL
query = """
SELECT fecha, numero, um_0, c_0, u_0
FROM primer_resumen_matriz_aslu
WHERE um_0 = 1 AND c_0 = 1 AND u_0 = 1
"""

# Leer y exportar
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_PATH, sep='\t', index=False, encoding='utf-8')

# Cierre de conexión
conn.close()

print(f'✅ Archivo generado: {OUTPUT_PATH}')
