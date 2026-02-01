import sqlite3
import pandas as pd

# Ruta de base de datos y archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_PATH = r'C:\RadarPremios\data\limpio\tercer_resumen_matriz_aslu.csv'

# Conectar a SQLite
conn = sqlite3.connect(DB_PATH)

# Leer la tabla matriz_astro_luna
query = "SELECT fecha, numero, signo, um, c, d, u FROM matriz_astro_luna"
df = pd.read_sql_query(query, conn)

# Asegurar que las columnas estén como texto
for col in ['numero', 'um', 'c', 'd', 'u']:
    df[col] = df[col].astype(str)

# Dígito a analizar
digito = '2'

# Agregar columnas binarizadas para presencia de '2'
df[f'um_{digito}'] = df['um'].apply(lambda x: 1 if x == digito else 0)
df[f'c_{digito}']  = df['c'].apply(lambda x: 1 if x == digito else 0)
df[f'd_{digito}']  = df['d'].apply(lambda x: 1 if x == digito else 0)
df[f'u_{digito}']  = df['u'].apply(lambda x: 1 if x == digito else 0)

# Guardar CSV
df.to_csv(OUTPUT_PATH, sep='\t', index=False, encoding='utf-8')

conn.close()
print(f'✅ Resumen del dígito 2 exportado en: {OUTPUT_PATH}')
