import sqlite3
import pandas as pd

# Ruta de la base y salida del archivo
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_PATH = r'C:\RadarPremios\data\limpio\segundo_resumen_matriz_aslu.csv'

# Conexión a SQLite
conn = sqlite3.connect(DB_PATH)

# Consulta desde la tabla matriz
query = "SELECT fecha, numero, signo, um, c, d, u FROM matriz_astro_luna"
df = pd.read_sql_query(query, conn)

# Asegurar que columnas clave sean texto
for col in ['numero', 'um', 'c', 'd', 'u']:
    df[col] = df[col].astype(str)

# Número objetivo a analizar
digito = '1'

# Crear columnas binarizadas para presencia del número 1
df[f'um_{digito}'] = df['um'].apply(lambda x: 1 if x == digito else 0)
df[f'c_{digito}']  = df['c'].apply(lambda x: 1 if x == digito else 0)
df[f'd_{digito}']  = df['d'].apply(lambda x: 1 if x == digito else 0)
df[f'u_{digito}']  = df['u'].apply(lambda x: 1 if x == digito else 0)

# Guardar resultado
df.to_csv(OUTPUT_PATH, sep='\t', index=False, encoding='utf-8')

conn.close()
print(f'✅ Resumen del dígito 1 exportado en: {OUTPUT_PATH}')
