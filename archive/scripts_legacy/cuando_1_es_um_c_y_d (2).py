import sqlite3
import pandas as pd

# Ruta de base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_1_es_um_c_y_d.csv'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL con filtro para um_1, c_1, d_1
query = """
    SELECT fecha, numero, um_1, c_1, d_1
    FROM segundo_resumen_matriz_aslu
    WHERE um_1 = 1 AND c_1 = 1 AND d_1 = 1
"""

# Leer resultados a un DataFrame
df = pd.read_sql_query(query, conn)

# Guardar como CSV separado por tabulaciones
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cierre de conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
