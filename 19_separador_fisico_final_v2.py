import os
import pandas as pd
import shutil

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
CARPETA_ORIGEN = os.path.join(BASE_DIR, "FOTOS_COMPETENCIA")
CARPETA_DESTINO_RAIZ = os.path.join(BASE_DIR, "CLASIFICACION_FINAL")

# Archivos CSV que tienen la clasificación (Prioridad al último leído)
ARCHIVOS_CLASIFICACION = [
    "catalogo_kaiqi_imagenes_ARMOTOS.csv",
    "catalogo_kaiqi_imagenes.csv",
    "imagenes_descartadas_no_moto.csv"
]

# Mapeo de "Tipo_Contenido" -> Carpeta Destino
MAPA_CATEGORIAS = {
    # HERRAMIENTAS
    'herramienta': 'HERRAMIENTAS',
    'herramienta_taller': 'HERRAMIENTAS',
    'kit_herramientas': 'HERRAMIENTAS',
    'herramientas_mecanicas': 'HERRAMIENTAS',
    'herramienta_manual': 'HERRAMIENTAS',
    'equipo_taller': 'HERRAMIENTAS',
    'herramienta_no_repuesto': 'HERRAMIENTAS',
    'herramienta_garage': 'HERRAMIENTAS',
    'maquina_para_moto': 'HERRAMIENTAS',
    'herramientas_varias': 'HERRAMIENTAS',
    'herramienta_lubricacion': 'HERRAMIENTAS',
    'herramienta_mecanico': 'HERRAMIENTAS',
    'herramienta_mecánica': 'HERRAMIENTAS',
    'herramienta_mantenimiento': 'HERRAMIENTAS',
    'herramienta_mecanica': 'HERRAMIENTAS',
    'herramienta_moto': 'HERRAMIENTAS',
    'herramienta_neumática': 'HERRAMIENTAS',
    'herramienta_mano': 'HERRAMIENTAS',
    'herramientas': 'HERRAMIENTAS',
    'herramienta_automotriz': 'HERRAMIENTAS',

    # EMBELLECIMIENTO / LIMPIEZA
    'producto_limpieza': 'EMBELLECIMIENTO',
    'producto_de_limpieza': 'EMBELLECIMIENTO',
    'limpieza': 'EMBELLECIMIENTO',
    
    # LUJOS / ACCESORIOS / PROTECCION
    'equipo_proteccion': 'LUJOS_Y_ACCESORIOS',
    'protector_personal': 'LUJOS_Y_ACCESORIOS',
    'accesorio': 'LUJOS_Y_ACCESORIOS',
    'accesorio_no_moto': 'LUJOS_Y_ACCESORIOS',
    'accesorio_moto': 'LUJOS_Y_ACCESORIOS',
    
    # REPUESTOS (Lo principal)
    'repuesto_moto': 'REPUESTOS',
    'repuesto_motocarguero': 'REPUESTOS',
    
    # BASURA / OTROS
    'no_repuesto_moto': 'BASURA',
    'desconocido': 'BASURA',
    'otros': 'BASURA',
    'no_repuesto': 'BASURA',
    'otro': 'BASURA',
    'no identificado': 'BASURA',
    'repuesto_no_moto': 'BASURA',
    'logo_empresa': 'BASURA',
    'no_es_repuesto_moto': 'BASURA',
    'otro_vehiculo': 'BASURA'
}

def clasificar_fisicamente():
    print("--- INICIANDO CLASIFICACIÓN FÍSICA V2 (CORREGIDO) ---")
    
    # 1. Crear carpetas destino
    for carpeta in set(MAPA_CATEGORIAS.values()):
        path = os.path.join(CARPETA_DESTINO_RAIZ, carpeta)
        os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.join(CARPETA_DESTINO_RAIZ, "SIN_CLASIFICAR"), exist_ok=True)
        
    # 2. Cargar Diccionario de Clasificación en Memoria
    diccionario_archivos = {} # { "foto.jpg": "HERRAMIENTAS" }
    
    for nombre_csv in ARCHIVOS_CLASIFICACION:
        ruta_csv = os.path.join(BASE_DIR, nombre_csv)
        if os.path.exists(ruta_csv):
            print(f"📚 Leyendo: {nombre_csv}...")
            try:
                # Intentar leer con ; o ,
                try: df = pd.read_csv(ruta_csv, sep=';', on_bad_lines='skip')
                except: df = pd.read_csv(ruta_csv, sep=',', on_bad_lines='skip')
                
                # Normalizar columnas (quitar espacios)
                df.columns = [c.strip() for c in df.columns]
                
                # Buscar columnas clave (flexible)
                col_file = next((c for c in df.columns if 'Filename' in c or 'Imagen' in c), None)
                col_type = next((c for c in df.columns if 'Tipo' in c or 'Type' in c), None)
                
                if col_file and col_type:
                    for _, row in df.iterrows():
                        fname = str(row[col_file]).strip()
                        ftype = str(row[col_type]).strip()
                        
                        # Mapear
                        carpeta_destino = MAPA_CATEGORIAS.get(ftype, 'SIN_CLASIFICAR')
                        # Si ya existe y la nueva es BASURA, no sobrescribir si la anterior era buena
                        diccionario_archivos[fname] = carpeta_destino
                else:
                    print(f"   ⚠️ Columnas no encontradas en {nombre_csv}")
            except Exception as e:
                print(f"   ❌ Error crítico leyendo {nombre_csv}: {e}")

    print(f"📝 Total archivos clasificados en memoria: {len(diccionario_archivos)}")
    
    # 3. Mover Archivos Físicos
    count_movidos = 0
    
    if not os.path.exists(CARPETA_ORIGEN):
        print(f"❌ No encuentro la carpeta de fotos: {CARPETA_ORIGEN}")
        return

    archivos_fisicos = os.listdir(CARPETA_ORIGEN)
    print(f"📂 Archivos físicos a mover: {len(archivos_fisicos)}")
    
    for archivo in archivos_fisicos:
        # Determinar destino
        if archivo in diccionario_archivos:
            carpeta = diccionario_archivos[archivo]
        else:
            carpeta = "SIN_CLASIFICAR"
            
        origen = os.path.join(CARPETA_ORIGEN, archivo)
        destino = os.path.join(CARPETA_DESTINO_RAIZ, carpeta, archivo)
        
        try:
            # Usamos shutil.move para trasladar
            shutil.move(origen, destino)
            count_movidos += 1
            # Feedback visual cada 100 archivos
            if count_movidos % 100 == 0:
                print(f"   Movidos {count_movidos} archivos...", end="\r")
        except Exception as e:
            print(f"Error moviendo {archivo}: {e}")

    print("\n" + "="*50)
    print(f"✅ CLASIFICACIÓN FINALIZADA")
    print(f"   Archivos movidos: {count_movidos}")
    print(f"   Ubicación: {CARPETA_DESTINO_RAIZ}")
    print("="*50)

if __name__ == "__main__":
    clasificar_fisicamente()