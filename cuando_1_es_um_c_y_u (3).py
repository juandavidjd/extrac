import sqlite3
import pandas as pd

# Ruta a la base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_1_es_um_c_y_u.csv'

# Conectar a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL filtrando por um_1, c_1 y u_1
query = """
    SELECT fecha, numero, um_1, c_1, u_1
    FROM segundo_resumen_matriz_aslu
    WHERE um_1 = 1 AND c_1 = 1 AND u_1 = 1
"""

# Ejecutar la consulta y cargar en DataFrame
df = pd.read_sql_query(query, conn)

# Exportar el resultado a CSV
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
