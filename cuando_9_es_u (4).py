import sqlite3
import pandas as pd

# Ruta a la base de datos
DB_PATH = r'C:\RadarPremios\radar_premios.db'
# Ruta al archivo de salida
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_9_es_unidad.csv'

# Establecer conexión con la base de datos
conn = sqlite3.connect(DB_PATH)

try:
    # Consulta SQL para filtrar por u_9 = 1
    query = """
    SELECT Fecha, numero, u_9
    FROM decimo_resumen_matriz_aslu
    WHERE u_9 = 1
    """

    # Ejecutar consulta y cargar en DataFrame
    df = pd.read_sql_query(query, conn)

    # Guardar resultados en CSV
    df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')
    print(f'✅ Archivo creado: {OUTPUT_FILE}')

except Exception as e:
    print(f'❌ Error al generar el archivo: {e}')

finally:
    # Cerrar conexión
    conn.close()
