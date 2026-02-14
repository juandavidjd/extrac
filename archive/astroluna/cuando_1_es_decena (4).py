import sqlite3
import pandas as pd

# Ruta de la base de datos y de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_1_es_decena.csv'

# Conectar a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL: extrae los registros donde d_1 == 1
query = """
    SELECT fecha, numero, d_1
    FROM segundo_resumen_matriz_aslu
    WHERE d_1 = 1
"""

# Ejecutar la consulta y guardar en DataFrame
df = pd.read_sql_query(query, conn)

# Guardar como CSV
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
