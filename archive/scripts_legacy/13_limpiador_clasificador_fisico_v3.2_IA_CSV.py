import os
import shutil
import pandas as pd
import base64
import json
import time
import random 
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
CARPETA_ORIGEN = os.path.join(BASE_DIR, "FOTOS_COMPETENCIA")
CARPETA_DESTINO_RAIZ = os.path.join(BASE_DIR, "CLASIFICACION_FINAL_IA")
ARCHIVO_REPORTE = os.path.join(BASE_DIR, "Reporte_Clasificacion_Fisica_IA.csv") # NUEVO

# Cliente OpenAI
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except:
    print("❌ ERROR CRÍTICO: No hay API Key. Este script requiere IA.")
    exit()

# Cache
CACHE_FILE = os.path.join(BASE_DIR, "clasificacion_ia_cache.json")
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

# Categorías Maestras
CATEGORIAS = ["REPUESTOS", "HERRAMIENTAS", "LUJOS_ACCESORIOS", "EMBELLECIMIENTO", "BASURA"]

# ================= UTILIDADES CON REINTENTO =================
def analizar_imagen_con_retry(ruta_img):
    """Usa GPT-4o con reintentos automáticos si falla."""
    file_hash = f"{os.path.basename(ruta_img)}_{os.path.getsize(ruta_img)}"
    if file_hash in CACHE: return CACHE[file_hash]

    max_retries = 5
    base_wait = 2 # Segundos

    for intento in range(max_retries):
        try:
            with open(ruta_img, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')

            prompt = f"""
            Clasifica esta imagen en UNA de estas categorías exactas:
            {CATEGORIAS}
            
            - REPUESTOS: Piezas mecánicas/eléctricas de moto.
            - HERRAMIENTAS: Llaves, destornilladores, copas.
            - LUJOS_ACCESORIOS: Cascos, guantes, stickers.
            - EMBELLECIMIENTO: Shampoos, ceras.
            - BASURA: Logos, personas, texto solo, borrosas.
            
            Responde SOLO la categoría.
            """

            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}
                ],
                max_tokens=20
            )
            
            cat = resp.choices[0].message.content.strip().upper()
            for c in CATEGORIAS:
                if c in cat:
                    cat = c
                    break
            
            if cat not in CATEGORIAS: cat = "BASURA"
            
            CACHE[file_hash] = cat
            return cat

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                wait_time = base_wait * (2 ** intento) + random.uniform(0, 1) # Backoff exponencial
                print(f"   ⏳ Límite alcanzado en {os.path.basename(ruta_img)}. Reintentando en {round(wait_time, 1)}s...")
                time.sleep(wait_time)
            else:
                print(f"Error IA en {os.path.basename(ruta_img)}: {e}")
                return "ERROR_IA"
    
    return "ERROR_IA" # Si falla después de 5 intentos

# ================= MOTOR PRINCIPAL =================
def clasificar_con_ia():
    print("--- CLASIFICACIÓN VISUAL ROBUSTA (IA + RETRY + CSV) ---")
    
    if not os.path.exists(CARPETA_ORIGEN):
        print(f"❌ No existe {CARPETA_ORIGEN}")
        return

    # Crear estructura
    for c in CATEGORIAS + ["ERROR_IA", "CORRUPTAS"]:
        os.makedirs(os.path.join(CARPETA_DESTINO_RAIZ, c), exist_ok=True)

    imagenes = [f for f in os.listdir(CARPETA_ORIGEN) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    print(f"🔍 Imágenes a procesar: {len(imagenes)}")
    
    registros_csv = [] # Lista para guardar resultados
    
    # Función Worker
    def worker(img_file):
        ruta_origen = os.path.join(CARPETA_ORIGEN, img_file)
        
        # Clasificar
        categoria = analizar_imagen_con_retry(ruta_origen)
        
        # Mover
        ruta_destino = os.path.join(CARPETA_DESTINO_RAIZ, categoria, img_file)
        try:
            shutil.copy2(ruta_origen, ruta_destino)
            
            # Retornar datos para el CSV
            return {
                "Filename": img_file,
                "Categoria_IA": categoria,
                "Ruta_Final": ruta_destino
            }
        except: 
            return {
                "Filename": img_file,
                "Categoria_IA": "ERROR_MOVIMIENTO",
                "Ruta_Final": ""
            }

    # Ejecución Multihilo (Reducida a 3 hilos para estabilidad)
    with ThreadPoolExecutor(max_workers=3) as executor:
        resultados = list(executor.map(worker, imagenes))
        
        # Filtrar Nones si hubo errores graves
        registros_csv = [r for r in resultados if r is not None]

    # Guardar CSV
    if registros_csv:
        df = pd.DataFrame(registros_csv)
        df.to_csv(ARCHIVO_REPORTE, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n✅ REPORTE CSV GENERADO: {ARCHIVO_REPORTE}")

    guardar_cache()
    print(f"✅ CLASIFICACIÓN IA TERMINADA")
    print(f"   Revisa: {CARPETA_DESTINO_RAIZ}")

if __name__ == "__main__":
    clasificar_con_ia()