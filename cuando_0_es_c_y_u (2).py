import sqlite3
import pandas as pd

# Ruta a la base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_cero_es_c_y_u.csv'

# Conectar a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL para filtrar casos donde c_0 == 1 y u_0 == 1
query = """
SELECT fecha, numero, c_0, u_0
FROM primer_resumen_matriz_aslu
WHERE c_0 = 1 AND u_0 = 1
"""

# Ejecutar la consulta y cargar resultado en DataFrame
df = pd.read_sql_query(query, conn)

# Guardar resultado a archivo CSV
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
