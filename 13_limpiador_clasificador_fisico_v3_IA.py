import os
import shutil
import pandas as pd
import base64
import json
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
CARPETA_ORIGEN = os.path.join(BASE_DIR, "FOTOS_COMPETENCIA")
CARPETA_DESTINO_RAIZ = os.path.join(BASE_DIR, "CLASIFICACION_FINAL_IA")

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

# ================= UTILIDADES =================
def analizar_imagen(ruta_img):
    """Usa GPT-4o para clasificar visualmente."""
    file_hash = f"{os.path.basename(ruta_img)}_{os.path.getsize(ruta_img)}"
    if file_hash in CACHE: return CACHE[file_hash]

    try:
        with open(ruta_img, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')

        prompt = f"""
        Clasifica esta imagen en UNA de estas categorías exactas:
        {CATEGORIAS}
        
        - REPUESTOS: Piezas mecánicas/eléctricas de moto (bujías, cilindros, frenos).
        - HERRAMIENTAS: Llaves, destornilladores, copas, máquinas.
        - LUJOS_ACCESORIOS: Cascos, guantes, stickers decorativos, luces LED tuning.
        - EMBELLECIMIENTO: Shampoos, ceras, sprays.
        - BASURA: Logos, personas, texto solo, fotos borrosas o irrelevantes.
        
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
        # Limpieza básica por si la IA responde con texto extra
        for c in CATEGORIAS:
            if c in cat:
                cat = c
                break
        
        if cat not in CATEGORIAS: cat = "BASURA" # Fallback seguro
        
        CACHE[file_hash] = cat
        return cat

    except Exception as e:
        print(f"Error IA en {os.path.basename(ruta_img)}: {e}")
        return "ERROR_IA"

# ================= MOTOR PRINCIPAL =================
def clasificar_con_ia():
    print("--- CLASIFICACIÓN VISUAL PROFUNDA (IA) ---")
    
    if not os.path.exists(CARPETA_ORIGEN):
        print(f"❌ No existe {CARPETA_ORIGEN}")
        return

    # Crear estructura
    for c in CATEGORIAS + ["ERROR_IA", "CORRUPTAS"]:
        os.makedirs(os.path.join(CARPETA_DESTINO_RAIZ, c), exist_ok=True)

    imagenes = [f for f in os.listdir(CARPETA_ORIGEN) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    print(f"🔍 Imágenes a procesar: {len(imagenes)}")
    
    # Función Worker
    def worker(img_file):
        ruta_origen = os.path.join(CARPETA_ORIGEN, img_file)
        
        # Clasificar
        categoria = analizar_imagen(ruta_origen)
        
        # Mover
        ruta_destino = os.path.join(CARPETA_DESTINO_RAIZ, categoria, img_file)
        try:
            shutil.copy2(ruta_origen, ruta_destino)
            return 1
        except: return 0

    # Ejecución Multihilo (Cuidado con el saldo, 5 hilos es prudente)
    with ThreadPoolExecutor(max_workers=5) as executor:
        list(executor.map(worker, imagenes))
        
    guardar_cache()
    print(f"\n✅ CLASIFICACIÓN IA TERMINADA")
    print(f"   Revisa: {CARPETA_DESTINO_RAIZ}")

if __name__ == "__main__":
    clasificar_con_ia()