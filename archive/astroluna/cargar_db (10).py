import os
import sqlite3
import pandas as pd

# Ruta base de archivos ya limpios
DATA_DIR = r'C:\RadarPremios\data\limpio'
DB_PATH = r'C:\RadarPremios\radar_premios.db'

# Archivos a cargar
archivos = [
    'boyaca.csv', 'huila.csv', 'manizales.csv', 'medellin.csv', 'quindio.csv', 'tolima.csv',
    'astro_luna.csv',
    'baloto_resultados.csv', 'baloto_premios.csv',
    'revancha_resultados.csv', 'revancha_premios.csv'
]

# Limpieza de nombres de columnas
def limpiar_columnas(cols):
    return [col.strip().lower().replace(" ", "_") for col in cols]

def cargar_datos():
    conn = sqlite3.connect(DB_PATH)

    for archivo in archivos:
        nombre_tabla = archivo.replace('.csv', '').lower()
        ruta_archivo = os.path.join(DATA_DIR, archivo)

        print(f'📥 Cargando {archivo} → tabla {nombre_tabla}')

        try:
            df = pd.read_csv(ruta_archivo, sep='\t', dtype=str, encoding='utf-8')
            df.columns = limpiar_columnas(df.columns)

            # Cargar en base de datos
            df.to_sql(nombre_tabla, conn, if_exists='replace', index=False)
            print(f'✅ Tabla {nombre_tabla} cargada con {len(df)} registros.')

        except Exception as e:
            print(f"❌ Error cargando {archivo}: {e}")

    conn.close()
    print(f'\n🟢 Base de datos lista en: {DB_PATH}')

if __name__ == '__main__':
    cargar_datos()
