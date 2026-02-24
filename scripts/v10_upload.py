#!/usr/bin/env python3
import os, json, base64, time, re
from pathlib import Path
from collections import defaultdict
import requests
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

SHOP = os.getenv("ARMOTOS_SHOP") or os.getenv("SHOPIFY_ARMOTOS_SHOP")
TOKEN = os.getenv("ARMOTOS_TOKEN") or os.getenv("SHOPIFY_ARMOTOS_TOKEN")
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
BASE_URL = "https://" + SHOP + "/admin/api/2025-01"

PRODUCTS_FILE = "/opt/odi/data/ARMOTOS/json/all_products.json"
IMAGES_DIR = Path("/opt/odi/data/ARMOTOS/images")

def normalize_title(title):
    if not title:
        return "Producto ARMOTOS"
    return " ".join(str(title).strip().title().split())[:255]

def generate_ficha(p):
    nombre = p.get("nombre", "Producto")
    codigo = p.get("codigo", "N/A")
    compat = p.get("compatibilidad", "")
    colores = p.get("colores", [])
    if isinstance(colores, list):
        colores = ", ".join(colores)
    html = "<div class=ficha-360>"
    html += "<h3>" + str(nombre) + "</h3>"
    if compat:
        html += "<p><b>Compatible:</b> " + str(compat) + "</p>"
    if colores:
        html += "<p><b>Colores:</b> " + str(colores) + "</p>"
    html += "<p><b>Codigo:</b> " + str(codigo) + "</p></div>"
    return html

def find_image(page_num):
    for ext in ["png", "jpeg", "jpg"]:
        pattern = "page_" + str(page_num).zfill(3) + "_img_*." + ext
        matches = list(IMAGES_DIR.glob(pattern))
        if matches:
            return matches[0]
    return None

def deduplicate(products):
    by_code = defaultdict(list)
    for p in products:
        code = str(p.get("codigo", "")).strip()
        if code:
            by_code[code].append(p)
    result = []
    for code, variants in by_code.items():
        base = variants[0].copy()
        all_colors = set()
        for v in variants:
            c = v.get("colores", [])
            if isinstance(c, list):
                all_colors.update(c)
            elif c:
                all_colors.add(c)
        if all_colors:
            base["colores"] = list(all_colors)
        prices = [v.get("precio", 0) for v in variants if v.get("precio")]
        if prices:
            base["precio"] = max(prices)
        result.append(base)
    return result

def upload(p):
    page = p.get("page", 0)
    img_path = find_image(page)
    title = normalize_title(p.get("nombre", "Producto"))
    body = generate_ficha(p)
    price = p.get("precio", 0)
    if isinstance(price, str):
        price = int(re.sub(r"[^\d]", "", price) or 0)
    
    data = {"product": {
        "title": title,
        "body_html": body,
        "vendor": "ARMOTOS",
        "product_type": "Repuesto Moto",
        "status": "active",
        "tags": str(p.get("compatibilidad", "")),
        "variants": [{"sku": str(p.get("codigo", "")), "price": str(price)}]
    }}
    
    has_img = False
    if img_path and img_path.exists():
        try:
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            data["product"]["images"] = [{"attachment": b64}]
            has_img = True
        except:
            pass
    
    for _ in range(3):
        try:
            r = requests.post(BASE_URL + "/products.json", json=data, headers=HEADERS, timeout=60)
            if r.status_code == 201:
                return True, has_img
            elif r.status_code == 429:
                time.sleep(3)
            else:
                return False, False
        except:
            time.sleep(2)
    return False, False

with open(PRODUCTS_FILE) as f:
    products = json.load(f)
print("Raw:", len(products), flush=True)

products = deduplicate(products)
print("Dedup:", len(products), flush=True)

ok, with_img, err = 0, 0, 0
for i, p in enumerate(products, 1):
    success, has_img = upload(p)
    if success:
        ok += 1
        if has_img:
            with_img += 1
    else:
        err += 1
    if i % 50 == 0:
        print("["+str(i)+"/"+str(len(products))+"] OK:"+str(ok)+" IMG:"+str(with_img), flush=True)
    time.sleep(0.6)

print("\nRESULT: OK="+str(ok)+" IMG="+str(with_img)+" ERR="+str(err), flush=True)
