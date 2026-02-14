import sqlite3
import pandas as pd

# Ruta a la base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_cero_es_um_d_y_u.csv'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL con filtros para um_0, d_0 y u_0 igual a 1
query = """
SELECT fecha, numero, um_0, d_0, u_0
FROM primer_resumen_matriz_aslu
WHERE um_0 = 1 AND d_0 = 1 AND u_0 = 1
"""

# Ejecutar consulta y guardar resultados
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cierre de conexión
conn.close()
print(f'✅ Archivo generado: {OUTPUT_FILE}')
