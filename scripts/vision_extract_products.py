#!/usr/bin/env python3
import os, json, base64, time
from pathlib import Path
from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

PAGES_DIR = Path("/opt/odi/data/ARMOTOS/pages")
OUTPUT_DIR = Path("/opt/odi/data/ARMOTOS/json")
OUTPUT_DIR.mkdir(exist_ok=True)

PROMPT = """Analiza esta pagina de catalogo ARMOTOS. Extrae TODOS los productos.
Para cada producto: codigo, nombre, precio (numero COP), compatibilidad, colores, posicion.
Responde SOLO JSON array: [{"codigo":"X","nombre":"Y","precio":12345,"compatibilidad":"MOTOS","colores":[],"posicion":"centro"}]
Si no hay productos: []"""

def extract_gpt4o(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    r = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"user","content":[
            {"type":"text","text":PROMPT},
            {"type":"image_url","image_url":{"url":f"data:image/png;base64,{b64}"}}
        ]}],
        max_tokens=4096
    )
    return r.choices[0].message.content

def extract_gemini(path):
    with open(path, "rb") as f:
        data = f.read()
    r = gemini_model.generate_content([PROMPT, {"mime_type":"image/png","data":data}])
    return r.text

def parse_json(text):
    text = text.strip()
    if "")[1].replace("json","").strip()
    start, end = text.find("["), text.rfind("]")+1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return []

def process_page(num):
    page_file = PAGES_DIR / f"page_{num:03d}.png"
    out_file = OUTPUT_DIR / f"page_{num:03d}.json"
    if out_file.exists():
        with open(out_file) as f:
            return json.load(f)
    if not page_file.exists():
        return []
    try:
        resp = extract_gpt4o(page_file)
        prov = "gpt4o"
    except Exception as e:
        print(f"    GPT-4o error: {e}", flush=True)
        try:
            resp = extract_gemini(page_file)
            prov = "gemini"
        except:
            return []
    products = parse_json(resp)
    for p in products:
        p["page"] = num
        p["provider"] = prov
    with open(out_file, "w") as f:
        json.dump(products, f, ensure_ascii=False)
    return products

if __name__ == "__main__":
    print("=== VISION AI EXTRACTION ===", flush=True)
    pages = sorted([int(f.stem.split("_")[1]) for f in PAGES_DIR.glob("page_*.png")])
    print(f"Total: {len(pages)} paginas", flush=True)
    processed = set(int(f.stem.split("_")[1]) for f in OUTPUT_DIR.glob("page_*.json"))
    print(f"Ya procesadas: {len(processed)}", flush=True)
    
    all_products = []
    for i, num in enumerate(pages, 1):
        if num in processed:
            with open(OUTPUT_DIR / f"page_{num:03d}.json") as f:
                prods = json.load(f)
        else:
            prods = process_page(num)
            time.sleep(1.2)
        all_products.extend(prods)
        if i % 10 == 0:
            print(f"[{i}/{len(pages)}] {len(all_products)} productos", flush=True)
    
    with open(OUTPUT_DIR / "all_products.json", "w") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    print(f"COMPLETADO: {len(all_products)} productos", flush=True)
