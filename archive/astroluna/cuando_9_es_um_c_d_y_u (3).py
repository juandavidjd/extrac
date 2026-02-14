import sqlite3
import pandas as pd

# Ruta de la base de datos
DB_PATH = r'C:\RadarPremios\radar_premios.db'

# Ruta del archivo de salida
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_9_es_um_c_d_y_u.csv'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

try:
    # Consulta SQL
    query = """
    SELECT Fecha, numero, um_9, c_9, d_9, u_9
    FROM decimo_resumen_matriz_aslu
    WHERE um_9 = 1 AND c_9 = 1 AND d_9 = 1 AND u_9 = 1
    """
    
    # Ejecutar y guardar
    df = pd.read_sql_query(query, conn)
    df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')
    
    print(f'✅ Archivo creado: {OUTPUT_FILE}')

except Exception as e:
    print(f'❌ Error al generar el archivo: {e}')

finally:
    conn.close()
