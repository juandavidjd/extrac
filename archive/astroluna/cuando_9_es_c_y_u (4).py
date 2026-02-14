import sqlite3
import pandas as pd

# Ruta a la base de datos
DB_PATH = r'C:\RadarPremios\radar_premios.db'

# Ruta del archivo de salida
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_9_es_c_y_u.csv'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

try:
    # Consulta SQL
    query = """
    SELECT Fecha, numero, c_9, u_9
    FROM decimo_resumen_matriz_aslu
    WHERE c_9 = 1 AND u_9 = 1
    """
    
    # Ejecutar la consulta y guardar en DataFrame
    df = pd.read_sql_query(query, conn)
    
    # Guardar como CSV separado por tabulaciones
    df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')
    
    print(f'✅ Archivo creado: {OUTPUT_FILE}')

except Exception as e:
    print(f'❌ Error al generar el archivo: {e}')

finally:
    conn.close()
