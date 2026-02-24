#\!/usr/bin/env python3
import csv, json, sys, requests, time, re, os
from datetime import datetime
import psycopg2
sys.path.insert(0, "/opt/odi")
from core.ficha_360_template import build_ficha_360

DB = {"host": "172.18.0.8", "port": 5432, "database": "odi", "user": "odi_user", "password": "odi_secure_password"}

def main():
    empresa = "IMBRA"
    print(f"=== V22 IMBRA PROCESSOR ===")
    
    # Read CSV
    csv_path = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Imbra/Base_Datos_Imbra.csv"
    products = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            sku = row.get("sku", "").strip()
            titulo = row.get("titulo", "").strip()
            precio = row.get("precio", "").strip()
            categoria = row.get("categoria", "").strip()
            imagen = row.get("imagenes", "").strip()
            
            if not sku: continue
            
            # Normalize title
            if titulo.isupper():
                titulo = titulo.title()
            
            # Parse price
            try:
                precio_f = float(re.sub(r"[^\d.]", "", precio)) if precio else 0
            except: precio_f = 0
            
            status = "active" if precio_f > 0 else "draft"
            
            # Build ficha
            body = build_ficha_360(titulo, sku, "", empresa)
            handle = re.sub(r"[^a-z0-9]+", "-", titulo.lower())[:80] + "-imbra"
            
            products.append({
                "sku": sku, "title": titulo, "handle": handle,
                "body_html": body, "vendor": empresa,
                "product_type": categoria or "Repuestos",
                "status": status, "price": precio_f,
                "inventory": 10, "image": imagen if imagen.startswith("http") else None
            })
    
    con_precio = sum(1 for p in products if p["price"] > 0)
    sin_precio = sum(1 for p in products if p["price"] == 0)
    print(f"Productos: {len(products)} | Con precio: {con_precio} | Draft: {sin_precio}")
    
    # Get Shopify config
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT shopify_shop_url, shopify_api_password FROM empresas WHERE codigo = %s", (empresa,))
    shop, token = cur.fetchone()
    cur.close()
    conn.close()
    print(f"Shopify: {shop}")
    
    # Upload
    url = f"https://{shop}/admin/api/2024-01/products.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    ok = err = 0
    
    for i, p in enumerate(products):
        data = {"product": {
            "title": p["title"], "handle": p["handle"], "body_html": p["body_html"],
            "vendor": p["vendor"], "product_type": p["product_type"], "status": p["status"],
            "variants": [{"sku": p["sku"], "price": str(p["price"]), "inventory_management": "shopify", "inventory_quantity": p["inventory"]}]
        }}
        if p["image"]: data["product"]["images"] = [{"src": p["image"]}]
        
        try:
            r = requests.post(url, headers=headers, json=data, timeout=30)
            if r.status_code == 201: ok += 1
            else: err += 1
        except: err += 1
        
        time.sleep(0.25)
        if (i+1) % 100 == 0: print(f"  {i+1}/{len(products)} ok={ok} err={err}")
    
    print(f"\n=== RESULTADO ===")
    print(f"Subidos: {ok} | Errores: {err}")

if __name__ == "__main__": main()
