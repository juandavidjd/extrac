import sqlite3
import pandas as pd

# Ruta a la base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_1_es_umil.csv'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL: filtrar donde um_1 == 1
query = """
    SELECT fecha, numero, um_1
    FROM segundo_resumen_matriz_aslu
    WHERE um_1 = 1
"""

# Ejecutar y cargar en DataFrame
df = pd.read_sql_query(query, conn)

# Guardar archivo CSV con separador tabulador
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
