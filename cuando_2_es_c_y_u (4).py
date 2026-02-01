import sqlite3
import pandas as pd

# Rutas de configuración
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_2_es_c_y_u.csv'
TABLE_NAME = 'tercer_resumen_matriz_aslu'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL para c_2 y u_2 igual a 1
query = f"""
    SELECT fecha, numero, c_2, u_2
    FROM {TABLE_NAME}
    WHERE c_2 = 1 AND u_2 = 1
"""

# Ejecutar consulta y exportar resultado
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
