import os
import pandas as pd
import shutil

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
CARPETA_ORIGEN = os.path.join(BASE_DIR, "FOTOS_COMPETENCIA")
CARPETA_DESTINO_RAIZ = os.path.join(BASE_DIR, "CLASIFICACION_FINAL")

# Archivos CSV
ARCHIVOS_CLASIFICACION = [
    "catalogo_kaiqi_imagenes_ARMOTOS.csv",
    "catalogo_kaiqi_imagenes.csv",
    "imagenes_descartadas_no_moto.csv"
]

# MAPA MAESTRO DE CATEGORÍAS (Actualizado con tu diagnóstico)
MAPA_CATEGORIAS = {
    # --- HERRAMIENTAS ---
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

    # --- EMBELLECIMIENTO / LIMPIEZA ---
    'producto_limpieza': 'EMBELLECIMIENTO',
    'producto_de_limpieza': 'EMBELLECIMIENTO',
    'limpieza': 'EMBELLECIMIENTO',
    
    # --- LUJOS / ACCESORIOS / PROTECCION ---
    'equipo_proteccion': 'LUJOS_Y_ACCESORIOS',
    'protector_personal': 'LUJOS_Y_ACCESORIOS',
    'accesorio': 'LUJOS_Y_ACCESORIOS',
    'accesorio_no_moto': 'LUJOS_Y_ACCESORIOS',
    'accesorio_moto': 'LUJOS_Y_ACCESORIOS',
    
    # --- REPUESTOS (Lo principal) ---
    'repuesto_moto': 'REPUESTOS',
    'repuesto_motocarguero': 'REPUESTOS',
    
    # --- BASURA / OTROS ---
    'no_repuesto_moto': 'BASURA',
    'desconocido': 'BASURA',
    'otros': 'BASURA',
    'no_repuesto': 'BASURA',
    'otro': 'BASURA',
    'no identificado': 'BASURA',
    'repuesto_no_moto': 'BASURA',
    'logo_empresa': 'BASURA',
    'no_es_repuesto_moto': 'BASURA',
    'otro_vehiculo': 'BASURA',
    'nan': 'BASURA'
}

def clasificar_fisicamente_v3():
    print("--- INICIANDO CLASIFICACIÓN FÍSICA V3 (MAPA COMPLETO) ---")
    
    # 1. Crear estructura de carpetas
    if os.path.exists(CARPETA_DESTINO_RAIZ):
        shutil.rmtree(CARPETA_DESTINO_RAIZ) # Limpiar intento anterior
    os.makedirs(CARPETA_DESTINO_RAIZ, exist_ok=True)
    
    targets = set(MAPA_CATEGORIAS.values())
    for t in targets:
        os.makedirs(os.path.join(CARPETA_DESTINO_RAIZ, t), exist_ok=True)
    os.makedirs(os.path.join(CARPETA_DESTINO_RAIZ, "SIN_CLASIFICAR"), exist_ok=True)

    # 2. Cargar Diccionario
    diccionario = {}
    
    for nombre_csv in ARCHIVOS_CLASIFICACION:
        ruta = os.path.join(BASE_DIR, nombre_csv)
        if os.path.exists(ruta):
            print(f"📚 Leyendo: {nombre_csv}")
            try:
                try: df = pd.read_csv(ruta, sep=';', on_bad_lines='skip')
                except: df = pd.read_csv(ruta, sep=',', on_bad_lines='skip')
                
                df.columns = [c.strip() for c in df.columns]
                
                # Detectar columnas
                col_f = next((c for c in df.columns if 'Filename' in c or 'Imagen' in c), None)
                col_t = next((c for c in df.columns if 'Tipo' in c), None)
                
                if col_f and col_t:
                    for _, row in df.iterrows():
                        fname = str(row[col_f]).strip()
                        ftype = str(row[col_t]).strip()
                        # Guardar mapeo
                        diccionario[fname] = MAPA_CATEGORIAS.get(ftype, 'SIN_CLASIFICAR')
            except: pass

    print(f"📝 {len(diccionario)} archivos mapeados.")

    # 3. Mover Archivos
    if not os.path.exists(CARPETA_ORIGEN):
        print("❌ No existe carpeta origen.")
        return

    archivos = os.listdir(CARPETA_ORIGEN)
    movidos = 0
    
    for archivo in archivos:
        destino_folder = diccionario.get(archivo, "SIN_CLASIFICAR")
        
        origen = os.path.join(CARPETA_ORIGEN, archivo)
        destino = os.path.join(CARPETA_DESTINO_RAIZ, destino_folder, archivo)
        
        try:
            shutil.move(origen, destino)
            movidos += 1
            if movidos % 200 == 0: print(f"   Movidos {movidos}...", end="\r")
        except Exception as e:
            print(f"Error: {e}")

    print("\n" + "="*50)
    print(f"✅ FINALIZADO")
    print(f"   Total movidos: {movidos}")
    print(f"   Revisa: {CARPETA_DESTINO_RAIZ}")
    print("="*50)

if __name__ == "__main__":
    clasificar_fisicamente_v3()