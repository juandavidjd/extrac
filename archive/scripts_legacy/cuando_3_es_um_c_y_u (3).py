import sqlite3
import pandas as pd

# Rutas de configuración
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_3_es_um_c_y_u.csv'
TABLE_NAME = 'cuarto_resumen_matriz_aslu'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL con filtros um_3, c_3 y u_3
query = f"""
    SELECT fecha, numero, um_3, c_3, u_3
    FROM {TABLE_NAME}
    WHERE um_3 = 1 AND c_3 = 1 AND u_3 = 1
"""

# Ejecutar y exportar
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
