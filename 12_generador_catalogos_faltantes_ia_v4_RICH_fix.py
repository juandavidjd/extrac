import os
import pandas as pd
import base64
import json
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
SCRAP_DIR = r"C:\scrap"

# Cliente OpenAI
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except:
    client = None
    print("⚠️ ADVERTENCIA: No se detectó API Key.")

# Cache Avanzado
CACHE_FILE = os.path.join(BASE_DIR, "vision_rich_analysis_cache.json")
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f: CACHE = json.load(f)
    except: CACHE = {}
else:
    CACHE = {}

def guardar_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f: json.dump(CACHE, f, indent=2)
    except: pass

# ================= UTILIDADES =================

def encontrar_archivo(nombre_archivo):
    rutas = [os.path.join(BASE_DIR, nombre_archivo), os.path.join(SCRAP_DIR, nombre_archivo)]
    for r in rutas:
        if os.path.exists(r): return r
    return None

def cargar_referencias(nombre_archivo_csv, col_archivo, col_desc):
    refs = {}
    ruta_real = encontrar_archivo(nombre_archivo_csv)
    
    if ruta_real:
        try:
            # CORRECCIÓN: Lógica de lectura simplificada y robusta
            try: 
                df = pd.read_csv(ruta_real, encoding='utf-8-sig', on_bad_lines='skip', sep=None, engine='python')
            except: 
                try:
                    df = pd.read_csv(ruta_real, encoding='latin-1', sep=None, engine='python', on_bad_lines='skip')
                except Exception as e:
                    print(f"   ❌ Error fatal leyendo {nombre_archivo_csv}: {e}")
                    return {}

            # Normalizar columnas
            df.columns = [c.strip() for c in df.columns]
            
            if col_archivo in df.columns and col_desc in df.columns:
                for _, row in df.iterrows():
                    f = str(row[col_archivo]).strip().lower()
                    d = str(row[col_desc]).strip()
                    if len(d) > 2: refs[f] = d
            else:
                print(f"   ⚠️ Columnas no encontradas en {nombre_archivo_csv}. Buscaba: {col_archivo}, {col_desc}")

        except Exception as e:
            print(f"   ⚠️ Error procesando CSV: {e}")
            
    return refs

def analizar_imagen_profundo(ruta_img, nombre_ref=""):
    """Análisis 360 tipo Bara/Yokomar."""
    if not client: return {}
    
    file_hash = f"{os.path.basename(ruta_img)}_{os.path.getsize(ruta_img)}_RICH"
    if file_hash in CACHE: return CACHE[file_hash]

    try:
        with open(ruta_img, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')

        prompt = f"""
        Eres un experto en repuestos de moto (Mecánico Senior).
        Analiza esta imagen. Nombre sugerido: "{nombre_ref}".
        
        Responde un JSON ESTRICTO con esta estructura exacta:
        {{
            "Es_Moto_o_Motocarguero": true,
            "Tipo_Contenido": "repuesto_moto", 
            "Confianza_Global": 0.95,
            "Identificacion_Repuesto": "Nombre técnico preciso",
            "Componente_Taxonomia": "Ej: Carburador",
            "Sistema": "Ej: Motor",
            "SubSistema": "Ej: Admisión",
            "Caracteristicas_Observadas": "Descripción visual breve",
            "Compatibilidad_Probable_Texto": "Motos compatibles sugeridas",
            "Funcion": "Para qué sirve",
            "Tags_Sugeridos": "tag1, tag2",
            "Notas_Sobre_Textos_Grabados": "Codigos visibles"
        }}
        """

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un experto en catálogos de motos. Responde solo JSON."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}
            ],
            max_tokens=400,
            response_format={"type": "json_object"}
        )
        
        contenido = resp.choices[0].message.content
        if not contenido: return {}
            
        data = json.loads(contenido)
        CACHE[file_hash] = data
        return data

    except Exception as e:
        # print(f"[IA Error]: {e}")
        return {}

# ================= LOTES =================

LOTES = [
    {
        "nombre": "DFG",
        "carpeta": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_DFG"),
        "referencia": "Base_Datos_DFG.csv",
        "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_DFG.csv"),
        "col_a": "Imagen_Final", "col_d": "Nombre_Producto"
    },
    {
        "nombre": "ARMOTOS",
        "carpeta": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_ARMOTOS"),
        "referencia": "Base_Datos_Armotos.csv",
        "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_ARMOTOS.csv"),
        "col_a": "Imagen_SEO", "col_d": "Nombre_Producto"
    },
    {
        "nombre": "ARMOTOSS",
        "carpeta": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_ARMOTOSS"),
        "referencia": "Base_Datos_Armotoss.csv",
        "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_ARMOTOSS.csv"),
        "col_a": "Imagen_Final", "col_d": "Descripcion"
    }
]

# ================= MOTOR =================

def procesar_lote(lote):
    print(f"\n🚀 Enriqueciendo Lote: {lote['nombre']}...")
    
    carpeta = lote['carpeta']
    if not os.path.exists(carpeta):
        # Fallback scrap
        c_alt = os.path.join(SCRAP_DIR, os.path.basename(carpeta))
        if os.path.exists(c_alt): carpeta = c_alt
        else: 
            print(f"   ❌ Carpeta no encontrada: {lote['carpeta']}")
            return

    refs = cargar_referencias(lote['referencia'], lote['col_a'], lote['col_d'])
    imagenes = [f for f in os.listdir(carpeta) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    print(f"   🔍 {len(imagenes)} imágenes a procesar.")

    resultados = []
    
    def worker(img_file):
        ruta = os.path.join(carpeta, img_file)
        nombre_ref = refs.get(img_file.lower(), "")
        
        # Análisis IA Profundo
        ia = analizar_imagen_profundo(ruta, nombre_ref)
        
        # Nombre final
        nombre_final = ia.get("Identificacion_Repuesto", nombre_ref)
        if not nombre_final: nombre_final = os.path.splitext(img_file)[0]
        
        # Estructura IDENTICA a Bara.csv
        return {
            "Filename_Original": img_file,
            "Es_Moto_o_Motocarguero": ia.get("Es_Moto_o_Motocarguero", True),
            "Tipo_Contenido": ia.get("Tipo_Contenido", "repuesto_moto"),
            "Confianza_Global": ia.get("Confianza_Global", 0.90),
            "Identificacion_Repuesto": nombre_final,
            "Componente_Taxonomia": ia.get("Componente_Taxonomia", nombre_final.split()[0]),
            "Sistema": ia.get("Sistema", "General"),
            "SubSistema": ia.get("SubSistema", ""),
            "Caracteristicas_Observadas": ia.get("Caracteristicas_Observadas", ""),
            "Compatibilidad_Probable_Texto": ia.get("Compatibilidad_Probable_Texto", ""),
            "Compatibilidad_Probable_JSON": "[]",
            "Funcion": ia.get("Funcion", ""),
            "Nombre_Comercial_Catalogo": nombre_final,
            "Tags_Sugeridos": ia.get("Tags_Sugeridos", ""),
            "Notas_Sobre_Textos_Grabados": ia.get("Notas_Sobre_Textos_Grabados", ""),
            "Necesita_Modelo_Grande": False
        }

    # Reducimos hilos para evitar saturar API
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i, res in enumerate(executor.map(worker, imagenes)):
            resultados.append(res)
            if i % 10 == 0: print(f"   ... {i}/{len(imagenes)} procesados", end="\r")

    if resultados:
        df = pd.DataFrame(resultados)
        # Columnas ordenadas
        cols_bara = [
            "Filename_Original", "Es_Moto_o_Motocarguero", "Tipo_Contenido", "Confianza_Global",
            "Identificacion_Repuesto", "Componente_Taxonomia", "Sistema", "SubSistema",
            "Caracteristicas_Observadas", "Compatibilidad_Probable_Texto", "Compatibilidad_Probable_JSON",
            "Funcion", "Nombre_Comercial_Catalogo", "Tags_Sugeridos", "Notas_Sobre_Textos_Grabados",
            "Necesita_Modelo_Grande"
        ]
        # Rellenar faltantes
        for c in cols_bara:
            if c not in df.columns: df[c] = ""
            
        df = df[cols_bara]
        df.to_csv(lote['salida'], index=False, sep=';', encoding='utf-8-sig')
        print(f"   ✅ Generado Rico: {os.path.basename(lote['salida'])}")
    
    guardar_cache()

if __name__ == "__main__":
    print("--- GENERADOR V12.4: CATÁLOGOS RICOS (FIXED) ---")
    for lote in LOTES:
        procesar_lote(lote)
    print("\n✨ PROCESO COMPLETADO.")