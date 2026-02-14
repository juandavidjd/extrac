import os
import pandas as pd

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"

# Archivos a procesar
ARCHIVOS = {
    "ARMOTOS": "catalogo_kaiqi_imagenes_ARMOTOS.csv",
    "ARMOTOSS": "catalogo_kaiqi_imagenes_Armotoss.csv",  # Ojo con la mayúscula final si aplica
    # Puedes añadir más si quieres reclasificar otros
}

# Mapeo de "Tipo_Contenido" (Sucio) -> "Sistema / Tipo" (Limpio)
# Tu regla de negocio: "REPUESTOS", "HERRAMIENTAS", "LUJOS_ACCESORIOS", "EMBELLECIMIENTO"
MAPA_LOGICO = {
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
    
    # LUJOS / ACCESORIOS
    'equipo_proteccion': 'LUJOS_Y_ACCESORIOS',
    'protector_personal': 'LUJOS_Y_ACCESORIOS',
    'accesorio': 'LUJOS_Y_ACCESORIOS',
    'accesorio_no_moto': 'LUJOS_Y_ACCESORIOS',
    'accesorio_moto': 'LUJOS_Y_ACCESORIOS',
    
    # REPUESTOS
    'repuesto_moto': 'REPUESTOS',
    'repuesto_motocarguero': 'REPUESTOS',
    
    # BASURA / DESCARTAR (Esto lo marcaremos para filtrar después)
    'no_repuesto_moto': 'DESCARTE',
    'desconocido': 'DESCARTE',
    'otros': 'DESCARTE',
    'no_repuesto': 'DESCARTE',
    'otro': 'DESCARTE',
    'no identificado': 'DESCARTE',
    'repuesto_no_moto': 'DESCARTE',
    'logo_empresa': 'DESCARTE',
    'no_es_repuesto_moto': 'DESCARTE',
    'otro_vehiculo': 'DESCARTE',
    'nan': 'DESCARTE'
}

def reclasificar_csvs():
    print("--- RECLASIFICACIÓN LÓGICA DE CSVS (ARMOTOS) ---")
    
    for nombre_clave, archivo in ARCHIVOS.items():
        ruta_csv = os.path.join(BASE_DIR, archivo)
        
        if not os.path.exists(ruta_csv):
            print(f"⚠️ No encuentro {archivo}")
            continue
            
        print(f"\n📄 Procesando: {archivo}")
        try:
            # Cargar
            try: df = pd.read_csv(ruta_csv, sep=';', encoding='utf-8-sig')
            except: df = pd.read_csv(ruta_csv, sep=',', encoding='latin-1')
            
            # Crear columnas nuevas limpias
            df['Categoria_SRM'] = df['Tipo_Contenido'].map(MAPA_CATEGORIAS).fillna('DESCARTE')
            
            # Estadísticas
            conteo = df['Categoria_SRM'].value_counts()
            print("   📊 Distribución:")
            print(conteo.to_string())
            
            # Guardar CORREGIDO
            nombre_salida = archivo.replace(".csv", "_CORREGIDO.csv")
            ruta_salida = os.path.join(BASE_DIR, nombre_salida)
            
            # Opcional: Si quieres sobreescribir el original, usa ruta_csv en lugar de ruta_salida
            # df.to_csv(ruta_csv, index=False, sep=';', encoding='utf-8-sig') 
            
            df.to_csv(ruta_salida, index=False, sep=';', encoding='utf-8-sig')
            print(f"   ✅ Guardado: {nombre_salida}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n===============================")
    print(" PROCESO TERMINADO")
    print("===============================")

if __name__ == "__main__":
    reclasificar_csvs()