import sqlite3
import pandas as pd

# Ruta de entrada y salida
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_PATH = r'C:\RadarPremios\data\limpio\sexto_resumen_matriz_aslu.csv'

# Conexión a base de datos
conn = sqlite3.connect(DB_PATH)

# Leer datos desde tabla
query = "SELECT fecha, numero, signo, um, c, d, u FROM matriz_astro_luna"
df = pd.read_sql_query(query, conn)

# Asegurar tipos string
for col in ['numero', 'um', 'c', 'd', 'u']:
    df[col] = df[col].astype(str)

# Dígito a analizar
digito = '5'

# Crear columnas de presencia del 5 por posición
df[f'um_{digito}'] = df['um'].apply(lambda x: 1 if x == digito else 0)
df[f'c_{digito}']  = df['c'].apply(lambda x: 1 if x == digito else 0)
df[f'd_{digito}']  = df['d'].apply(lambda x: 1 if x == digito else 0)
df[f'u_{digito}']  = df['u'].apply(lambda x: 1 if x == digito else 0)

# Guardar archivo CSV
df.to_csv(OUTPUT_PATH, sep='\t', index=False, encoding='utf-8')

conn.close()
print(f'✅ Resumen del dígito 5 exportado en: {OUTPUT_PATH}')
