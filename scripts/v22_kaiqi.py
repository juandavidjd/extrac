#!/usr/bin/env python3
import csv, json, sys, requests, time, re, os
from datetime import datetime
import psycopg2
sys.path.insert(0, "/opt/odi")
from core.ficha_360_template import build_ficha_360

DB = {"host": "172.18.0.8", "port": 5432, "database": "odi", "user": "odi_user", "password": "odi_secure_password"}
DATA_DIR = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI"

def load_taxonomia():
    taxonomia = {}
    path = f"{DATA_DIR}/Data/Kaiqi/catalogo_imagenes_Kaiqi.csv"
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            filename = row.get("Filename_Original", "")
            sku_match = re.search(r"-([A-Z0-9]+)\.jpg", filename, re.I)
            if sku_match:
                sku = sku_match.group(1).upper()
                taxonomia[sku] = {
                    "sistema": row.get("Sistema", ""),
                    "funcion": row.get("Funcion", ""),
                    "caracteristicas": row.get("Caracteristicas_Observadas", ""),
                    "compatibilidad": row.get("Compatibilidad_Probable_Texto", ""),
                    "tags": row.get("Tags_Sugeridos", "")
                }
    return taxonomia

def load_base_datos():
    data = {}
    path = f"{DATA_DIR}/Data/Kaiqi/Base_Datos_Kaiqi.csv"
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            sku = row.get("CODIGO", "").strip().upper()
            if sku:
                data[sku] = row.get("Imagen_URL_Origen", "")
    return data

def main():
    empresa = "KAIQI"
    print(f"=== V22 KAIQI PROCESSOR ===")
    
    taxonomia = load_taxonomia()
    print(f"Taxonomia: {len(taxonomia)}")
    base_datos = load_base_datos()
    print(f"Base_Datos: {len(base_datos)}")
    
    csv_path = f"{DATA_DIR}/Data/Kaiqi/Lista_Precios_Kaiqi.csv"
    products = []
    
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            sku = row.get("CODIGO", "").strip()
            titulo = row.get("DESCRIPCION", "").strip()
            precio = row.get("PRECIO", "").strip()
            if not sku: continue
            
            sku_up = sku.upper()
            if titulo.isupper():
                titulo = titulo.title()
            
            try:
                precio_f = float(re.sub(r"[^\d.]", "", precio)) if precio else 0
            except: precio_f = 0
            
            status = "active" if precio_f > 0 else "draft"
            tax = taxonomia.get(sku_up, {})
            compat = tax.get("compatibilidad", "")
            
            extra = {}
            if tax.get("funcion"):
                extra["info_tecnica"] = tax["funcion"][:150]
            
            body = build_ficha_360(titulo, sku, compat, empresa, extra)
            handle = re.sub(r"[^a-z0-9]+", "-", titulo.lower())[:80] + "-kaiqi"
            
            img_url = base_datos.get(sku_up, "")
            
            products.append({
                "sku": sku, "title": titulo, "handle": handle,
                "body_html": body, "vendor": empresa,
                "product_type": tax.get("sistema", "Repuestos"),
                "status": status, "price": precio_f, "inventory": 10,
                "tags": tax.get("tags", ""),
                "image_url": img_url if img_url.startswith("http") else None
            })
    
    print(f"Products: {len(products)}")
    print(f"Con taxonomy: {sum(1 for p in products if p['product_type'] != 'Repuestos')}")
    
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT shopify_shop_url, shopify_api_password FROM empresas WHERE codigo = %s", (empresa,))
    shop, token = cur.fetchone()
    cur.close()
    conn.close()
    print(f"Shop: {shop}")
    
    url = f"https://{shop}/admin/api/2024-01/products.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    ok = err = 0
    
    for i, p in enumerate(products):
        data = {"product": {
            "title": p["title"], "handle": p["handle"], "body_html": p["body_html"],
            "vendor": p["vendor"], "product_type": p["product_type"], "status": p["status"],
            "tags": p["tags"],
            "variants": [{"sku": p["sku"], "price": str(p["price"]), "inventory_management": "shopify", "inventory_quantity": p["inventory"]}]
        }}
        if p.get("image_url"):
            data["product"]["images"] = [{"src": p["image_url"]}]
        
        try:
            r = requests.post(url, headers=headers, json=data, timeout=30)
            if r.status_code == 201: ok += 1
            else: err += 1
        except: err += 1
        
        time.sleep(0.25)
        if (i+1) % 100 == 0: print(f"  {i+1}/{len(products)} ok={ok} err={err}")
    
    print(f"Uploaded: {ok} | Errors: {err}")

if __name__ == "__main__": main()
