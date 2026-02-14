import os
import pandas as pd

# Directorios de entrada y salida
CRUDO_DIR = r'C:\RadarPremios\data\crudo'
LIMPIO_DIR = r'C:\RadarPremios\data\limpio'

# Crear carpeta de salida si no existe
os.makedirs(LIMPIO_DIR, exist_ok=True)

# Archivos a limpiar
archivos = [
    'boyaca.csv', 'huila.csv', 'manizales.csv', 'medellin.csv', 'quindio.csv', 'tolima.csv',
    'astro_luna.csv',
    'baloto_resultados.csv', 'baloto_premios.csv',
    'revancha_resultados.csv', 'revancha_premios.csv'
]

# Columnas que deben mantenerse como texto con ceros a la izquierda
mantener_texto = {'numero', 'sorteo'}

# Función para limpiar nombres de columnas
def limpiar_columna(col):
    return col.strip().lower().replace(" ", "_")

# Limpieza y guardado
for archivo in archivos:
    ruta_crudo = os.path.join(CRUDO_DIR, archivo)
    ruta_limpio = os.path.join(LIMPIO_DIR, archivo)

    print(f'🧽 Procesando {archivo}')

    try:
        # Intento 1: autodetección de delimitador
        df = pd.read_csv(ruta_crudo, sep=None, engine='python', dtype=str, encoding='utf-8', skipinitialspace=True)

        # Si solo detectó una columna, puede que el delimitador esté mal
        if len(df.columns) == 1:
            print(f"⚠️ Delimitador autodetectado falló para {archivo}, reintentando con TAB...")
            df = pd.read_csv(ruta_crudo, sep='\t', dtype=str, encoding='utf-8', skipinitialspace=True)

    except Exception as e:
        print(f"❌ Error leyendo {archivo}: {e}")
        continue

    # Limpiar nombres de columnas
    df.columns = [limpiar_columna(col) for col in df.columns]

    # Reemplazos estándar en todos los datos
    df.replace(to_replace=[r'^\s*$', r'^–$', r'^N/?A$', 'nan'], value='', regex=True, inplace=True)

    # Procesamiento por columna
    for col in df.columns:
        try:
            if col == 'sb':
                df[col] = df[col].astype(str).str.strip()  # sin zfill
            elif col in mantener_texto:
                df[col] = df[col].astype(str).str.zfill(4)
            elif df[col].str.contains(r'\$').any():
                df[col] = df[col].str.replace(r'[\$,]', '', regex=True).str.strip()
                df[col] = df[col].replace('', '0')
                df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                df[col] = df[col].astype(str).str.strip()
        except Exception as e:
            print(f"⚠️ Error procesando columna '{col}' en archivo '{archivo}': {e}")

    # Guardar limpio
    try:
        df.to_csv(ruta_limpio, sep='\t', index=False, encoding='utf-8')
        print(f"✅ Guardado limpio: {ruta_limpio}")
    except Exception as e:
        print(f"❌ Error guardando {archivo}: {e}")

print(f'\n🟢 Limpieza finalizada. Archivos disponibles en: {LIMPIO_DIR}')
