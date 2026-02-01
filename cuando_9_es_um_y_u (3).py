# python cuando_9_es_um_y_u.py

import sqlite3
import pandas as pd

# Rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_9_es_um_y_u.csv'

# Conexión a SQLite
conn = sqlite3.connect(DB_PATH)

try:
    # Consulta SQL con filtro
    query = """
    SELECT Fecha, numero, um_9, u_9
    FROM decimo_resumen_matriz_aslu
    WHERE um_9 = 1 AND u_9 = 1
    """

    # Ejecutar consulta y cargar en DataFrame
    df = pd.read_sql_query(query, conn)

    # Guardar resultado en CSV
    df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

    print(f'✅ Archivo creado: {OUTPUT_FILE}')

except Exception as e:
    print(f'❌ Error al generar el archivo: {e}')

finally:
    conn.close()
