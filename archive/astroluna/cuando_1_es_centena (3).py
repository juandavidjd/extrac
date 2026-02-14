import sqlite3
import pandas as pd

# Ruta de la base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_1_es_centena.csv'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta: registros donde c_1 == 1
query = """
    SELECT fecha, numero, c_1
    FROM segundo_resumen_matriz_aslu
    WHERE c_1 = 1
"""

# Leer resultados en DataFrame
df = pd.read_sql_query(query, conn)

# Guardar CSV con separador tabulador
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
