#!/usr/bin/env python3
import sys, os, json, time, requests, warnings, logging
from dotenv import load_dotenv
import pdfplumber
import openai
import chromadb

warnings.filterwarnings("ignore")
load_dotenv("/opt/odi/.env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("arm")

PDF = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Armotos/CATALOGO NOVIEMBRE V01-2025 NF.pdf"
OUT = "/opt/odi/data/ARMOTOS"
os.makedirs(OUT + "/json", exist_ok=True)

PROMPT = "Extrae productos de este catalogo de motos. JSON: {products:[{sku,title,price,category,compatibility:[motos]}]}. Solo JSON valido."

def main():
    log.info("=" * 40)
    log.info("ARMOTOS PIPELINE v2")
    
    log.info("[1/4] Extrayendo datos...")
    cli = openai.OpenAI()
    prods = []
    
    with pdfplumber.open(PDF) as pdf:
        log.info("  Paginas: %d", len(pdf.pages))
        for pn, pg in enumerate(pdf.pages, 1):
            if pn == 1: continue
            if pn % 10 == 0: log.info("  Pag %d/256", pn)
            txt = pg.extract_text() or ""
            if len(txt) < 30: continue
            try:
                msg = PROMPT + "\n\n" + txt[:4000]
                r = cli.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":msg}],
                    temperature=0.1, response_format={"type":"json_object"}
                )
                data = json.loads(r.choices[0].message.content)
                for p in data.get("products",[]):
                    p["page"] = pn
                    prods.append(p)
            except: pass
    
    log.info("  Productos: %d", len(prods))
    
    log.info("[2/4] Normalizando...")
    for p in prods:
        t = str(p.get("title","Producto")).replace("[","").replace("]","").strip().title()
        if "Armotos" not in t: t = t + " - Armotos"
        p["title"] = t
        p["vendor"] = "ARMOTOS"
        try:
            price = str(p.get("price","")).replace(",","").replace("$","").strip()
            p["price"] = float(price) if price and float(price) > 0 else 50000
        except: p["price"] = 50000
        cat = p.get("category","Repuesto")
        compat = p.get("compatibility",[])
        compat_html = "".join(["<li>" + m + "</li>" for m in compat[:5]]) if compat else "<li>Consultar</li>"
        p["body_html"] = "<div><h3>Descripcion</h3><p>" + t + " de alta calidad por ARMOTOS.</p><h3>Especificaciones</h3><ul><li>Categoria: " + cat + "</li><li>Marca: ARMOTOS</li><li>Garantia: 6 meses</li></ul><h3>Compatibilidad</h3><ul>" + compat_html + "</ul></div>"
    
    with open(OUT + "/json/products.json", "w") as f:
        json.dump(prods, f, indent=2, ensure_ascii=False)
    
    log.info("[3/4] Subiendo a Shopify...")
    shop, token = os.getenv("ARMOTOS_SHOP"), os.getenv("ARMOTOS_TOKEN")
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    created, errors = 0, 0
    
    for i, p in enumerate(prods):
        if i % 25 == 0: log.info("  %d/%d (ok:%d)", i, len(prods), created)
        sku = p.get("sku") or "ARM" + str(i+1).zfill(4)
        tags = [p.get("category","repuesto").lower(), "armotos"]
        payload = {"product": {"title": p["title"], "body_html": p["body_html"], "vendor": "ARMOTOS",
            "product_type": p.get("category","Repuesto").title(), "tags": ", ".join(tags), "status": "active",
            "variants": [{"price": str(p["price"]), "sku": sku, "inventory_management": "shopify", "inventory_quantity": 10}]}}
        try:
            r = requests.post("https://" + shop + "/admin/api/2024-10/products.json", headers=headers, json=payload, timeout=30)
            if r.status_code == 201: created += 1
            else: errors += 1
            time.sleep(0.25)
        except: errors += 1
    
    log.info("  Creados: %d, Errores: %d", created, errors)
    
    log.info("[4/4] ChromaDB...")
    try:
        col = chromadb.HttpClient(host="localhost", port=8000).get_collection("odi_ind_motos")
        docs, metas, ids = [], [], []
        for i, p in enumerate(prods):
            docs.append(p["title"] + " " + p.get("category","") + " ARMOTOS")
            metas.append({"title": p["title"], "price": p["price"], "vendor": "ARMOTOS", "category": p.get("category","repuesto")})
            ids.append("armotos_" + str(i+1).zfill(5))
        for i in range(0, len(docs), 500):
            col.add(documents=docs[i:i+500], metadatas=metas[i:i+500], ids=ids[i:i+500])
        log.info("  Indexados: %d", len(docs))
    except Exception as e:
        log.error("  Error: %s", e)
    
    log.info("=" * 40)
    log.info("COMPLETADO: %d productos, %d shopify", len(prods), created)

if __name__ == "__main__":
    main()
