import sqlite3
import pandas as pd

# Rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_1_es_c_y_u.csv'

# Conectar a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta: filtrar registros donde c_1 == 1 y u_1 == 1
query = """
    SELECT fecha, numero, c_1, u_1
    FROM segundo_resumen_matriz_aslu
    WHERE c_1 = 1 AND u_1 = 1
"""

# Ejecutar consulta
df = pd.read_sql_query(query, conn)

# Guardar CSV separado por tabulaciones
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cerrar conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
