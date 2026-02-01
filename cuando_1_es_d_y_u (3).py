import sqlite3
import pandas as pd

# Ruta a la base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_1_es_d_y_u.csv'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL: filtrar donde d_1 = 1 y u_1 = 1
query = """
    SELECT fecha, numero, d_1, u_1
    FROM segundo_resumen_matriz_aslu
    WHERE d_1 = 1 AND u_1 = 1
"""

# Ejecutar consulta y guardar resultado en DataFrame
df = pd.read_sql_query(query, conn)

# Exportar a CSV con separador de tabulación
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
