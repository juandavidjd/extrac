import sqlite3
import pandas as pd

# Ruta de la base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_1_es_c_y_d.csv'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta para seleccionar solo registros con c_1 == 1 y d_1 == 1
query = """
    SELECT fecha, numero, c_1, d_1
    FROM segundo_resumen_matriz_aslu
    WHERE c_1 = 1 AND d_1 = 1
"""

# Leer los datos en un DataFrame
df = pd.read_sql_query(query, conn)

# Exportar a CSV
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cierre de conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
