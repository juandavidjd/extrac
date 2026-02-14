import sqlite3
import pandas as pd

# Ruta a la base de datos y al archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_cero_es_um_c_y_d.csv'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL para filtrar los registros
query = """
SELECT fecha, numero, um_0, c_0, d_0
FROM primer_resumen_matriz_aslu
WHERE um_0 = 1 AND c_0 = 1 AND d_0 = 1
"""

# Ejecutar y cargar resultado en DataFrame
df = pd.read_sql_query(query, conn)

# Exportar a CSV
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
