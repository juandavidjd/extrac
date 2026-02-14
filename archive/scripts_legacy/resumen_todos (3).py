import sqlite3
import pandas as pd

# Rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_PATH = r'C:\RadarPremios\data\limpio\todos_resumen_matriz_aslu.csv'

# Conexión a base de datos
conn = sqlite3.connect(DB_PATH)

# Cargar datos base
query = "SELECT fecha, numero, signo, um, c, d, u FROM matriz_astro_luna"
df = pd.read_sql_query(query, conn)

# Cerrar conexión
conn.close()

# Asegurar que columnas estén como texto
for col in ['numero', 'um', 'c', 'd', 'u']:
    df[col] = df[col].astype(str)

# Agregar columnas binarias por cada dígito (0-9) en cada posición
for digito in range(10):
    d = str(digito)
    df[f'um_{d}'] = df['um'].apply(lambda x: 1 if x == d else 0)
    df[f'c_{d}']  = df['c'].apply(lambda x: 1 if x == d else 0)
    df[f'd_{d}']  = df['d'].apply(lambda x: 1 if x == d else 0)
    df[f'u_{d}']  = df['u'].apply(lambda x: 1 if x == d else 0)

# Guardar CSV con separador tabulado
df.to_csv(OUTPUT_PATH, sep='\t', index=False, encoding='utf-8')

print(f'✅ Archivo guardado en: {OUTPUT_PATH}')
