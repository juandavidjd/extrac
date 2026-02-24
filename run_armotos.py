#!/usr/bin/env python3
import sys
sys.path.insert(0, "/opt/odi/odi_production/extractors")
sys.path.insert(0, "/opt/odi/core")

import os, json, asyncio, logging, time, requests, warnings
from dotenv import load_dotenv
import pdfplumber
import openai
import chromadb

warnings.filterwarnings("ignore")
load_dotenv("/opt/odi/.env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("armotos")

PDF = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Armotos/CATALOGO NOVIEMBRE V01-2025 NF.pdf"
OUT = "/opt/odi/data/ARMOTOS"

PROMPT = "Extrae productos del catalogo en JSON: {products:[{sku,title,price,category,compatibility}]}. Solo JSON."

async def main():
    os.makedirs(f"{OUT}/images", exist_ok=True)
    os.makedirs(f"{OUT}/json", exist_ok=True)
    log.info("ARMOTOS PIPELINE INICIO")
    
    # F1: Imagenes
    log.info("[F1] Extrayendo imagenes")
    from odi_vision_extractor_v3 import VisionProductDetector
    from pdf2image import convert_from_path
    det = VisionProductDetector(use_gemini=True)
    imgs = []
    for b in range(2, 257, 10):
        log.info(f"  Pag {b}-{min(b+9,256)}")
        try:
            pgs = convert_from_path(PDF, dpi=200, first_page=b, last_page=min(b+9,256))
            for i, pg in enumerate(pgs):
                pn = b + i
                pp = f"{OUT}/images/pg{pn:03d}.png"
                pg.save(pp)
                prods = det.detect(pp)
                if prods:
                    crops = det.crop_products(pp, prods, f"{OUT}/images", "ARM", pn)
                    imgs.extend(crops)
                os.remove(pp)
        except Exception as e:
            log.error(f"  Err: {e}")
    log.info(f"  Total imagenes: {len(imgs)}")
    
    # F2: Datos
    log.info("[F2] Extrayendo datos")
    cli = openai.OpenAI()
    prods = []
    with pdfplumber.open(PDF) as pdf:
        for pn, pg in enumerate(pdf.pages, 1):
            if pn == 1: continue
            if pn % 30 == 0: log.info(f"  Pag {pn}/256")
            txt = pg.extract_text() or ""
            if len(txt) > 50:
                try:
                    msg = PROMPT + chr(10) + txt[:5000]
                    r = cli.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role":"user","content":msg}],
                        temperature=0.1, response_format={"type":"json_object"}
                    )
                    for p in json.loads(r.choices[0].message.content).get("products",[]):
                        p["page"] = pn
                        prods.append(p)
                except: pass
    log.info(f"  Total productos: {len(prods)}")
    
    # F3: Normalizar
    log.info("[F3] Normalizando")
    for p in prods:
        t = p.get("title","Producto").replace("[","").replace("]","").strip().title()
        if "Armotos" not in t: t = f"{t} - Armotos"
        p["title"] = t
        p["vendor"] = "ARMOTOS"
        try: p["price"] = float(str(p.get("price",0)).replace(",","").replace("$","")) or 50000
        except: p["price"] = 50000
        cat = p.get("category","Repuesto")
        p["body_html"] = f"<div><h3>Descripcion</h3><p>{t} de alta calidad.</p><h3>Categoria</h3><p>{cat}</p><h3>Garantia</h3><p>6 meses</p></div>"
    
    with open(f"{OUT}/json/products.json","w") as f: json.dump(prods,f,indent=2,ensure_ascii=False)
    
    # F4: Shopify
    log.info("[F4] Subiendo a Shopify")
    shop, token = os.getenv("ARMOTOS_SHOP"), os.getenv("ARMOTOS_TOKEN")
    h = {"X-Shopify-Access-Token":token,"Content-Type":"application/json"}
    ok = 0
    for i, p in enumerate(prods):
        if i % 50 == 0: log.info(f"  {i}/{len(prods)}")
        try:
            sku = p.get("sku") or f"ARM{i+1:04d}"
            r = requests.post(f"https://{shop}/admin/api/2025-07/products.json", headers=h, timeout=30,
                json={"product":{"title":p["title"],"body_html":p["body_html"],"vendor":"ARMOTOS",
                    "product_type":p.get("category","Repuesto"),"status":"active",
                    "variants":[{"price":str(p["price"]),"sku":sku}]}})
            if r.status_code == 201: ok += 1
            time.sleep(0.3)
        except: pass
    log.info(f"  Creados: {ok}")
    
    # F5: ChromaDB
    log.info("[F5] Indexando en ChromaDB")
    col = chromadb.HttpClient(host="localhost",port=8000).get_collection("odi_ind_motos")
    docs, metas, ids = [], [], []
    for i, p in enumerate(prods):
        docs.append(f"{p['title']} ARMOTOS")
        metas.append({"title":p["title"],"price":p["price"],"vendor":"ARMOTOS"})
        ids.append(f"arm{i+1:04d}")
    for i in range(0, len(docs), 500):
        col.add(documents=docs[i:i+500], metadatas=metas[i:i+500], ids=ids[i:i+500])
    log.info(f"  Indexados: {len(docs)}")
    
    log.info(f"COMPLETADO: {len(imgs)} imgs, {len(prods)} prods, {ok} shopify")

if __name__ == "__main__":
    asyncio.run(main())
