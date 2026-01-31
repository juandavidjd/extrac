import os
import pandas as pd

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
CARPETA_ORIGEN = os.path.join(BASE_DIR, "FOTOS_COMPETENCIA")
ARCHIVOS_CSV = [
    "catalogo_kaiqi_imagenes_ARMOTOS.csv",
    "catalogo_kaiqi_imagenes.csv",
    "imagenes_descartadas_no_moto.csv"
]

# Mapeo de Categorías (El mismo de antes)
MAPA_CATEGORIAS = {
    'herramienta': 'HERRAMIENTAS',
    'herramienta_taller': 'HERRAMIENTAS',
    'kit_herramientas': 'HERRAMIENTAS',
    'producto_limpieza': 'EMBELLECIMIENTO',
    'equipo_proteccion': 'LUJOS_Y_ACCESORIOS',
    'repuesto_moto': 'REPUESTOS',
    'no_repuesto': 'BASURA',
    # ... (simplificado para diagnóstico)
}

def diagnosticar():
    print("--- DIAGNÓSTICO DE CLASIFICACIÓN ---")
    
    # 1. Verificar Archivos Físicos
    if not os.path.exists(CARPETA_ORIGEN):
        print(f"❌ La carpeta {CARPETA_ORIGEN} no existe.")
        return
    
    archivos_fisicos = set(os.listdir(CARPETA_ORIGEN))
    print(f"📂 Archivos en carpeta: {len(archivos_fisicos)}")
    if len(archivos_fisicos) > 0:
        print(f"   Ejemplo: {list(archivos_fisicos)[0]}")

    # 2. Analizar CSVs
    total_registros = 0
    coincidencias = 0
    categorias_encontradas = {}

    for nombre_csv in ARCHIVOS_CSV:
        ruta_csv = os.path.join(BASE_DIR, nombre_csv)
        if not os.path.exists(ruta_csv):
            print(f"⚠️ No encontrado: {nombre_csv}")
            continue
            
        print(f"\n📄 Analizando {nombre_csv}...")
        try:
            # Detectar separador
            df = pd.read_csv(ruta_csv, sep=None, engine='python')
            print(f"   Columnas detectadas: {list(df.columns)}")
            
            col_file = next((c for c in df.columns if 'Filename' in c or 'Imagen' in c), None)
            col_type = next((c for c in df.columns if 'Tipo' in c), None)
            
            if col_file and col_type:
                for _, row in df.iterrows():
                    fname = str(row[col_file]).strip()
                    ftype = str(row[col_type]).strip()
                    
                    total_registros += 1
                    
                    # Contar categorías crudas
                    categorias_encontradas[ftype] = categorias_encontradas.get(ftype, 0) + 1
                    
                    # Verificar si el archivo existe físicamente
                    if fname in archivos_fisicos:
                        coincidencias += 1
            else:
                print("   ❌ No se encontraron las columnas clave (Filename/Tipo).")
                
        except Exception as e:
            print(f"   ❌ Error leyendo CSV: {e}")

    print("\n" + "="*40)
    print("📊 RESULTADOS DEL DIAGNÓSTICO")
    print(f"   Total Registros en CSVs: {total_registros}")
    print(f"   Archivos Físicos que coinciden: {coincidencias}")
    
    print("\n🏷️  Categorías encontradas en los CSVs:")
    for cat, count in categorias_encontradas.items():
        destino = MAPA_CATEGORIAS.get(cat, "SIN_CLASIFICAR (Revisar Mapa)")
        print(f"   - '{cat}': {count} -> {destino}")

    if coincidencias == 0:
        print("\n❌ ALERTA CRÍTICA: Ningún archivo del CSV coincide con los de la carpeta.")
        print("   Posible causa: Los nombres en el CSV tienen rutas o extensiones diferentes.")
    elif coincidencias < total_registros:
        print(f"\n⚠️ ALERTA: Solo el {round(coincidencias/total_registros*100)}% de los registros tienen archivo físico.")

if __name__ == "__main__":
    diagnosticar()