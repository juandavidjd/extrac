import sqlite3
import pandas as pd

# Ruta a la base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_1_es_c_d_y_u.csv'

# Conectar a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL: filtrar los registros donde c_1, d_1 y u_1 son iguales a 1
query = """
    SELECT fecha, numero, c_1, d_1, u_1
    FROM segundo_resumen_matriz_aslu
    WHERE c_1 = 1 AND d_1 = 1 AND u_1 = 1
"""

# Ejecutar y cargar los datos
df = pd.read_sql_query(query, conn)

# Guardar resultado como CSV
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
