import sqlite3
import pandas as pd

# Ruta a la base de datos y salida del archivo
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_PATH = r'C:\RadarPremios\data\limpio\primer_resumen_matriz_aslu.csv'

# Conectar a SQLite
conn = sqlite3.connect(DB_PATH)

# Leer desde la tabla matriz_astro_luna
query = "SELECT fecha, numero, signo, um, c, d, u FROM matriz_astro_luna"
df = pd.read_sql_query(query, conn)

# Asegurar que todas las columnas relevantes son string
for col in ['numero', 'um', 'c', 'd', 'u']:
    df[col] = df[col].astype(str)

# Agregar columnas de presencia del dígito '0' en cada posición
df['um_0'] = df['um'].apply(lambda x: 1 if x == '0' else 0)
df['c_0']  = df['c'].apply(lambda x: 1 if x == '0' else 0)
df['d_0']  = df['d'].apply(lambda x: 1 if x == '0' else 0)
df['u_0']  = df['u'].apply(lambda x: 1 if x == '0' else 0)

# Guardar como CSV
df.to_csv(OUTPUT_PATH, sep='\t', index=False, encoding='utf-8')

conn.close()
print(f'✅ Resumen del dígito 0 exportado en: {OUTPUT_PATH}')
