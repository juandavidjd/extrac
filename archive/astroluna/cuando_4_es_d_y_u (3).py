import sqlite3
import pandas as pd

# Rutas de configuración
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_4_es_d_y_u.csv'
TABLE_NAME = 'quinto_resumen_matriz_aslu'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL para filtrar d_4 y u_4 igual a 1
query = f"""
    SELECT fecha, numero, d_4, u_4
    FROM {TABLE_NAME}
    WHERE d_4 = 1 AND u_4 = 1
"""

# Ejecutar consulta y exportar resultados
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
