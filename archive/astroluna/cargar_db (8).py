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
    'revancha_resultados.csv', 'revancha_premios.csv', 'matriz_astro_luna.csv'] #, 'primer_resumen_matriz_aslu.csv', 
    #'segundo_resumen_matriz_aslu.csv', 'tercer_resumen_matriz_aslu.csv', 'cuarto_resumen_matriz_aslu.csv',
  #  'quinto_resumen_matriz_aslu.csv', 'sexto_resumen_matriz_aslu.csv', 'septimo_resumen_matriz_aslu.csv',
    #'octavo_resumen_matriz_aslu.csv', 'noveno_resumen_matriz_aslu.csv', 'decimo_resumen_matriz_aslu.csv',
   # 'todos_resumen_matriz_aslu.csv', 'cuando_cero_es_unidad.csv', 'cuando_cero_es_decena.csv', 'cuando_cero_es_centena.csv',
  #  'cuando_cero_es_umil.csv', 'cuando_cero_es_d_y_u.csv', 'cuando_cero_es_c_y_u.csv', 'cuando_cero_es_um_y_u.csv',
   # 'cuando_cero_es_c_y_d.csv', 'cuando_cero_es_um_y_d.csv', 'cuando_cero_es_um_y_c.csv', 'cuando_cero_es_c_d_y_u.csv',
   # 'cuando_cero_es_um_c_d_y_u.csv', 'cuando_cero_es_um_c_y_d.csv', 'cuando_cero_es_um_c_y_u.csv', 'cuando_cero_es_um_d_y_u.csv',
   # 'todo_cuando_0_es.csv', 'cuando_1_es_unidad.csv', 'cuando_1_es_decena.csv', 'cuando_1_es_centena.csv', 'cuando_1_es_umil.csv',
  #  'cuando_1_es_d_y_u.csv', 'cuando_1_es_c_y_u.csv', 'cuando_1_es_um_y_u.csv', 'cuando_1_es_c_y_d.csv', 'cuando_1_es_um_y_d.csv',
  #  'cuando_1_es_um_y_c.csv', 'cuando_1_es_c_d_y_u.csv', 'cuando_1_es_um_c_d_y_u.csv', 'cuando_1_es_um_c_y_d.csv', 'cuando_1_es_um_c_y_u.csv',
  #  'cuando_1_es_um_d_y_u.csv', 'todo_cuando_1_es.csv', 'cuando_2_es_unidad.csv', 'cuando_2_es_decena.csv', 'cuando_2_es_centena.csv', 'cuando_2_es_umil.csv', 'cuando_2_es_c_d_y_u.csv',
  #  'cuando_2_es_c_y_d.csv', 'cuando_2_es_c_y_u.csv', 'cuando_2_es_d_y_u.csv', 'cuando_2_es_um_c_d_y_u.csv', 'cuando_2_es_um_c_y_d.csv', 
  #  'cuando_2_es_um_c_y_u.csv', 'cuando_2_es_um_d_y_u.csv', 'cuando_2_es_um_y_c.csv', 'cuando_2_es_um_y_d.csv' , 'cuando_2_es_um_y_u.csv', 
  #  'todo_cuando_2_es.csv', 'cuando_3_es_unidad.csv', 'cuando_3_es_decena.csv', 'cuando_3_es_centena.csv', 'cuando_3_es_umil.csv', 'cuando_3_es_um_c_y_d.csv','cuando_3_es_c_y_u.csv',
  #  'cuando_3_es_d_y_u.csv', 'cuando_3_es_c_d_y_u.csv', 'cuando_3_es_um_c_d_y_u.csv', 'cuando_3_es_c_y_d.csv', 'cuando_3_es_um_c_y_u.csv', 'cuando_3_es_um_d_y_u.csv',
  #  'cuando_3_es_um_y_c.csv', 'cuando_3_es_um_y_d.csv', 'cuando_3_es_um_y_u.csv', 'todo_cuando_3_es.csv', 'cuando_4_es_unidad.csv', 'cuando_4_es_decena.csv', 'cuando_4_es_centena.csv',
   # 'cuando_4_es_umil.csv', 'cuando_4_es_c_d_y_u.csv', 'cuando_4_es_c_y_d.csv','cuando_4_es_c_y_u.csv', 'cuando_4_es_d_y_u.csv', 'cuando_4_es_um_c_d_y_u.csv', 'cuando_4_es_um_c_y_d.csv',
  #  'cuando_4_es_um_c_y_u.csv', 'cuando_4_es_um_d_y_u.csv', 'cuando_4_es_um_y_c.csv', 'cuando_4_es_um_y_d.csv', 'cuando_4_es_um_y_u.csv', 'todo_cuando_4_es.csv', 'cuando_5_es_unidad.csv', 'cuando_5_es_decena.csv',
  #  'cuando_5_es_centena.csv', 'cuando_5_es_umil.csv', 'cuando_5_es_c_d_y_u.csv', 'cuando_5_es_c_y_d.csv', 'cuando_5_es_c_y_u.csv', 'cuando_5_es_d_y_u.csv', 'cuando_5_es_um_c_d_y_u.csv', 'cuando_5_es_um_c_y_d.csv',
  #  'cuando_5_es_um_c_y_u.csv', 'cuando_5_es_um_d_y_u.csv', 'cuando_5_es_um_y_c.csv', 'cuando_5_es_um_y_d.csv', 'cuando_5_es_um_y_u.csv', 'todo_cuando_5_es.csv', 'cuando_6_es_unidad.csv', 'cuando_6_es_decena.csv',
   # 'cuando_6_es_centena.csv', 'cuando_6_es_umil.csv', 'cuando_6_es_c_d_y_u.csv', 'cuando_6_es_c_y_d.csv', 'cuando_6_es_d_y_u.csv', 'cuando_6_es_um_c_d_y_u.csv', 'cuando_6_es_c_y_u.csv', 'cuando_6_es_um_c_y_d.csv',
   # 'cuando_6_es_um_c_y_u.csv', 'cuando_6_es_um_d_y_u.csv', 'cuando_6_es_um_y_c.csv', 'cuando_6_es_um_y_d.csv', 'cuando_6_es_um_y_u.csv', 'todo_cuando_6_es.csv', 'cuando_7_es_unidad.csv', 'cuando_7_es_decena.csv',
   # 'cuando_7_es_centena.csv', 'cuando_7_es_umil.csv', 'cuando_7_es_c_d_y_u.csv', 'cuando_7_es_c_y_d.csv', 'cuando_7_es_c_y_u.csv', 'cuando_7_es_d_y_u.csv', 'cuando_7_es_um_c_d_y_u.csv', 'cuando_7_es_um_c_y_d.csv',
   # 'cuando_7_es_um_c_y_u.csv', 'cuando_7_es_um_d_y_u.csv', 'cuando_7_es_um_y_c.csv', 'cuando_7_es_um_y_d.csv', 'cuando_7_es_um_y_u.csv', 'todo_cuando_7_es.csv', 'cuando_8_es_unidad.csv', 'cuando_8_es_decena.csv',
   # 'cuando_8_es_centena.csv', 'cuando_8_es_umil.csv', 'cuando_8_es_c_d_y_u.csv', 'cuando_8_es_c_y_d.csv', 'cuando_8_es_c_y_u.csv', 'cuando_8_es_d_y_u.csv', 'cuando_8_es_um_c_d_y_u.csv',
   # 'cuando_8_es_um_c_y_d.csv', 'cuando_8_es_um_c_y_u.csv', 'cuando_8_es_um_d_y_u.csv', 'cuando_8_es_um_y_c.csv', 'cuando_8_es_um_y_d.csv', 'cuando_8_es_um_y_u.csv', 'todo_cuando_8_es.csv', 'cuando_9_es_unidad.csv',
    #'cuando_9_es_decena.csv', 'cuando_9_es_centena.csv', 'cuando_9_es_umil.csv', 'cuando_9_es_c_d_y_u.csv', 'cuando_9_es_c_y_d.csv', 'cuando_9_es_c_y_u.csv', 'cuando_9_es_d_y_u.csv', 'cuando_9_es_um_c_d_y_u.csv',
    #'cuando_9_es_um_c_y_d.csv', 'cuando_9_es_um_c_y_u.csv', 'cuando_9_es_um_d_y_u.csv', 'cuando_9_es_um_y_d.csv', 'cuando_9_es_um_y_c.csv', 'cuando_9_es_um_y_u.csv', 'todo_cuando_9_es.csv', 'todos_cuando_son.csv',
    


     


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
