import sqlite3
import pandas as pd
import os

db_path = '../data/loterias.db'
crudos_path = '../data/crudos'

TABLAS_LOTERIAS = ["tolima", "huila", "manizales", "quindio", "medellin", "boyaca"]
TABLAS_SORTEOS = [
    "astroluna",
    "baloto_resultados",
    "baloto_premios",
    "revancha_resultados",
    "revancha_premios",
]

ESQUEMAS = {
    "astroluna": ["fecha", "numero", "signo"],
    "baloto_resultados": ["sorteo", "modo", "fecha", "n1", "n2", "n3", "n4", "n5", "sb"],
    "baloto_premios": ["sorteo", "modo", "fecha", "aciertos", "premio_total", "ganadores", "premio_por_ganador"],
    "revancha_resultados": ["sorteo", "modo", "fecha", "n1", "n2", "n3", "n4", "n5", "sb"],
    "revancha_premios": ["sorteo", "modo", "fecha", "aciertos", "premio_total", "ganadores", "premio_por_ganador"]
}

CREACION_TABLAS = {
    "astroluna": '''CREATE TABLE IF NOT EXISTS astroluna (
        fecha TEXT, numero TEXT, signo TEXT)''',

    "baloto_resultados": '''CREATE TABLE IF NOT EXISTS baloto_resultados (
        sorteo INTEGER, modo TEXT, fecha TEXT, n1 INTEGER, n2 INTEGER,
        n3 INTEGER, n4 INTEGER, n5 INTEGER, sb INTEGER)''',

    "baloto_premios": '''CREATE TABLE IF NOT EXISTS baloto_premios (
        sorteo INTEGER, modo TEXT, fecha TEXT, aciertos TEXT,
        premio_total TEXT, ganadores INTEGER, premio_por_ganador TEXT)''',

    "revancha_resultados": '''CREATE TABLE IF NOT EXISTS revancha_resultados (
        sorteo INTEGER, modo TEXT, fecha TEXT, n1 INTEGER, n2 INTEGER,
        n3 INTEGER, n4 INTEGER, n5 INTEGER, sb INTEGER)''',

    "revancha_premios": '''CREATE TABLE IF NOT EXISTS revancha_premios (
        sorteo INTEGER, modo TEXT, fecha TEXT, aciertos TEXT,
        premio_total TEXT, ganadores INTEGER, premio_por_ganador TEXT)''',
}

# Agregar creación para tablas de loterías
for nombre in TABLAS_LOTERIAS:
    CREACION_TABLAS[nombre] = f'''CREATE TABLE IF NOT EXISTS {nombre} (
        fecha TEXT, numero TEXT)'''

def cargar_tabla(nombre_tabla, df, conn):
    if nombre_tabla not in CREACION_TABLAS:
        print(f"❌ No hay esquema definido para {nombre_tabla}")
        return

    conn.execute(CREACION_TABLAS[nombre_tabla])

    # Reemplazar columnas si vienen con alias
    columnas_alias = {
        'superbalota': 'sb',
        'premio_unitario': 'premio_por_ganador'
    }
    df.rename(columns=columnas_alias, inplace=True)

    # Añadir columnas faltantes por lógica
    if 'modo' not in df.columns and 'baloto' in nombre_tabla:
        df['modo'] = 'baloto'
    if 'modo' not in df.columns and 'revancha' in nombre_tabla:
        df['modo'] = 'revancha'

    esperadas = ESQUEMAS.get(nombre_tabla, [])
    faltantes = [col for col in esperadas if col not in df.columns]

    if faltantes:
        print(f"[✗] Estructura inválida para {nombre_tabla}. Faltan columnas: {faltantes}")
        print(f"    → Columnas disponibles: {list(df.columns)}")
        return

    # Solo insertar el último sorteo o fila más reciente
    ultima = df.sort_values(by='fecha' if 'fecha' in df.columns else 'sorteo').tail(1)
    if ultima.isnull().all(axis=1).any():
        print(f"[✗] {nombre_tabla}: contiene valores nulos en última fila, se omite")
        return

    placeholders = ','.join(['?'] * len(esperadas))
    query = f"INSERT INTO {nombre_tabla} ({','.join(esperadas)}) VALUES ({placeholders})"
    conn.execute(query, tuple(ultima[esperadas].values[0]))
    print(f"[✓] Insertado en {nombre_tabla}: {ultima.iloc[0].to_dict()}")

def main():
    if not os.path.exists(db_path):
        print("❌ Base de datos no encontrada.")
        return

    conn = sqlite3.connect(db_path)

    archivos = os.listdir(crudos_path)

    for archivo in archivos:
        if not archivo.endswith('.csv'):
            continue

        nombre_tabla = archivo.replace('.csv', '').lower()
        archivo_path = os.path.join(crudos_path, archivo)

        try:
            df = pd.read_csv(archivo_path)
            cargar_tabla(nombre_tabla, df, conn)
        except Exception as e:
            print(f"❌ Error procesando {archivo}: {e}")

    conn.commit()
    conn.close()
    print("\n✅ Base de datos actualizada correctamente.")

if __name__ == "__main__":
    main()
