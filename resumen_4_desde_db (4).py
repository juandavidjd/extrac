import sqlite3
import pandas as pd

# Ruta a la base y al archivo de salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_PATH = r'C:\RadarPremios\data\limpio\quinto_resumen_matriz_aslu.csv'

# Conectar a la base de datos
conn = sqlite3.connect(DB_PATH)

# Leer la tabla matriz_astro_luna
query = "SELECT fecha, numero, signo, um, c, d, u FROM matriz_astro_luna"
df = pd.read_sql_query(query, conn)

# Asegurar que los valores sean texto
for col in ['numero', 'um', 'c', 'd', 'u']:
    df[col] = df[col].astype(str)

# Dígito objetivo
digito = '4'

# Crear columnas de detección
df[f'um_{digito}'] = df['um'].apply(lambda x: 1 if x == digito else 0)
df[f'c_{digito}']  = df['c'].apply(lambda x: 1 if x == digito else 0)
df[f'd_{digito}']  = df['d'].apply(lambda x: 1 if x == digito else 0)
df[f'u_{digito}']  = df['u'].apply(lambda x: 1 if x == digito else 0)

# Guardar CSV
df.to_csv(OUTPUT_PATH, sep='\t', index=False, encoding='utf-8')

conn.close()
print(f'✅ Resumen del dígito 4 exportado en: {OUTPUT_PATH}')
