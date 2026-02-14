import sqlite3
import pandas as pd

# Ruta de la base de datos y salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\todo_cuando_0_es.csv'

# Listado de tablas que representan combinaciones del "cero"
tablas = [
    'cuando_cero_es_unidad',
    'cuando_cero_es_decena',
    'cuando_cero_es_centena',
    'cuando_cero_es_umil',
    'cuando_cero_es_d_y_u',
    'cuando_cero_es_c_y_u',
    'cuando_cero_es_um_y_u',
    'cuando_cero_es_c_y_d',
    'cuando_cero_es_um_y_d',
    'cuando_cero_es_um_y_c',
    'cuando_cero_es_c_d_y_u',
    'cuando_cero_es_um_c_d_y_u',
    'cuando_cero_es_um_c_y_d',
    'cuando_cero_es_um_c_y_u',
    'cuando_cero_es_um_d_y_u'
]

# Conectar a la base de datos
conn = sqlite3.connect(DB_PATH)

# Cargar y concatenar todos los datos
dataframes = []
for tabla in tablas:
    try:
        df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
        df['origen'] = tabla  # Agrega columna para identificar fuente
        dataframes.append(df)
    except Exception as e:
        print(f"⚠️ Error cargando {tabla}: {e}")

# Concatenar todos los dataframes
if dataframes:
    df_todo = pd.concat(dataframes, ignore_index=True)
    df_todo.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')
    print(f"✅ Archivo generado: {OUTPUT_FILE}")
else:
    print("❌ No se encontraron datos válidos para unir.")

# Cerrar conexión
conn.close()
