import sqlite3
import pandas as pd
import os

# Ruta de entrada y salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_PATH = r'C:\RadarPremios\data\limpio\matriz_astro_luna.csv'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Leer tabla astro_luna
df = pd.read_sql_query("SELECT fecha, numero, signo FROM astro_luna", conn)

# Asegurar que 'numero' tenga siempre 4 dígitos como string
df['numero'] = df['numero'].astype(str).str.zfill(4)

# Descomponer número en columnas um, c, d, u
df['um'] = df['numero'].str[0]
df['c']  = df['numero'].str[1]
df['d']  = df['numero'].str[2]
df['u']  = df['numero'].str[3]

# Reordenar columnas
df = df[['fecha', 'numero', 'signo', 'um', 'c', 'd', 'u']]

# Guardar CSV
df.to_csv(OUTPUT_PATH, sep='\t', index=False, encoding='utf-8')

conn.close()
print(f'✅ Matriz generada: {OUTPUT_PATH}')
