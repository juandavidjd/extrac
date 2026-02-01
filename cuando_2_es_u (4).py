import sqlite3
import pandas as pd

# Configuración de rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_2_es_unidad.csv'
TABLE_NAME = 'tercer_resumen_matriz_aslu'

# Conectar a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL
query = f"""
    SELECT fecha, numero, u_2
    FROM {TABLE_NAME}
    WHERE u_2 = 1
"""

# Ejecutar consulta y guardar resultado
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
