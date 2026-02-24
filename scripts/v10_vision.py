#!/usr/bin/env python3
import os, json, base64, time
from pathlib import Path
from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gem = genai.GenerativeModel("gemini-2.0-flash")

PAGES = Path("/opt/odi/data/ARMOTOS/pages")
OUT = Path("/opt/odi/data/ARMOTOS/json")
OUT.mkdir(exist_ok=True)

PROMPT = "Analiza pagina catalogo ARMOTOS. Extrae productos como JSON: [{codigo,nombre,precio,compatibilidad,colores,posicion}]. Solo JSON array."

def gpt4o(path):
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    r = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"user","content":[
            {"type":"text","text":PROMPT},
            {"type":"image_url","image_url":{"url":"data:image/png;base64,"+b64}}
        ]}],
        max_tokens=4096
    )
    return r.choices[0].message.content

def gemini(path):
    with open(path, "rb") as f:
        data = f.read()
    r = gem.generate_content([PROMPT, {"mime_type":"image/png","data":data}])
    return r.text

def parse(text):
    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        text = text.replace("json", "").strip()
    s, e = text.find("["), text.rfind("]")+1
    if s >= 0 and e > s:
        return json.loads(text[s:e])
    return []

def process(num):
    pf = PAGES / f"page_{num:03d}.png"
    of = OUT / f"page_{num:03d}.json"
    if of.exists():
        return json.load(open(of))
    if not pf.exists():
        return []
    try:
        resp = gpt4o(pf)
        prov = "gpt4o"
    except Exception as e:
        print(f"  GPT4o err: {e}", flush=True)
        try:
            resp = gemini(pf)
            prov = "gemini"
        except:
            return []
    prods = parse(resp)
    for p in prods:
        p["page"] = num
        p["provider"] = prov
    json.dump(prods, open(of, "w"), ensure_ascii=False)
    return prods

pages = sorted([int(f.stem.split("_")[1]) for f in PAGES.glob("page_*.png")])
done = set(int(f.stem.split("_")[1]) for f in OUT.glob("page_*.json"))
print(f"Paginas: {len(pages)}, Ya: {len(done)}", flush=True)

all_p = []
for i, n in enumerate(pages, 1):
    if n in done:
        all_p.extend(json.load(open(OUT / f"page_{n:03d}.json")))
    else:
        all_p.extend(process(n))
        time.sleep(1.2)
    if i % 10 == 0:
        print(f"[{i}/{len(pages)}] {len(all_p)} prods", flush=True)

json.dump(all_p, open(OUT / "all_products.json", "w"), indent=2, ensure_ascii=False)
print(f"DONE: {len(all_p)} productos", flush=True)
