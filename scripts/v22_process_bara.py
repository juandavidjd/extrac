#!/usr/bin/env python3
"""V22 BARA Processor with rich taxonomy from catalogo_imagenes"""
import csv, json, sys, requests, time, re, os
from datetime import datetime
import psycopg2
sys.path.insert(0, "/opt/odi")
from core.ficha_360_template import build_ficha_360

DB = {"host": "172.18.0.8", "port": 5432, "database": "odi", "user": "odi_user", "password": "odi_secure_password"}

def load_image_taxonomy(path):
    """Load rich taxonomy from catalogo_imagenes"""
    taxonomy = {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                filename = row.get("Filename_Original", "")
                # Extract SKU from filename (e.g., "1-11-131-PASTILLAS...")
                sku_match = re.match(r"^([\d\-]+)", filename)
                if sku_match:
                    sku = sku_match.group(1).rstrip("-")
                    taxonomy[sku] = {
                        "sistema": row.get("Sistema", ""),
                        "subsistema": row.get("SubSistema", ""),
                        "componente": row.get("Componente_Taxonomia", ""),
                        "funcion": row.get("Funcion", ""),
                        "compatibilidad": row.get("Compatibilidad_Probable_Texto", ""),
                        "tags": row.get("Tags_Sugeridos", ""),
                        "nombre_comercial": row.get("Nombre_Comercial_Catalogo", "")
                    }
    except Exception as e:
        print(f"Warning: Could not load taxonomy: {e}")
    return taxonomy

def main():
    empresa = "BARA"
    print(f"=== V22 BARA PROCESSOR ===")
    print(f"Start: {datetime.now().strftime('%H:%M:%S')}")
    
    # Load taxonomy from catalogo_imagenes
    taxonomy_path = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Bara/catalogo_imagenes_Bara.csv"
    taxonomy = load_image_taxonomy(taxonomy_path)
    print(f"Loaded taxonomy for {len(taxonomy)} items")
    
    # Read price list
    csv_path = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Bara/Lista_Precios_Bara.csv"
    products = []
    
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            sku = row.get("CODIGO", "").strip()
            titulo = row.get("DESCRIPCION", "").strip()
            precio = row.get("PRECIO", "").strip()
            
            if not sku:
                continue
            
            # Normalize title
            if titulo.isupper():
                titulo = titulo.title()
            
            # Parse price
            try:
                precio_f = float(re.sub(r"[^\d.]", "", str(precio))) if precio else 0
            except:
                precio_f = 0
            
            status = "active" if precio_f > 0 else "draft"
            
            # Get taxonomy enrichment if available
            tax = taxonomy.get(sku, {})
            compatibilidad = tax.get("compatibilidad", "")
            
            # Build extra_info from taxonomy
            extra_info = {}
            if tax.get("sistema"):
                extra_info["sistema"] = tax["sistema"]
            if tax.get("subsistema"):
                extra_info["subsistema"] = tax["subsistema"]
            if tax.get("funcion"):
                extra_info["info_tecnica"] = tax["funcion"]
            
            # Generate ficha 360
            body = build_ficha_360(titulo, sku, compatibilidad, empresa, extra_info)
            
            handle = re.sub(r"[^a-z0-9]+", "-", titulo.lower())[:80] + "-bara"
            
            products.append({
                "sku": sku,
                "title": titulo,
                "handle": handle,
                "body_html": body,
                "vendor": empresa,
                "product_type": tax.get("sistema", "Repuestos"),
                "status": status,
                "price": precio_f,
                "inventory": 10,
                "tags": tax.get("tags", "")
            })
    
    con_precio = sum(1 for p in products if p["price"] > 0)
    con_tax = sum(1 for p in products if p["product_type"] != "Repuestos")
    print(f"Products: {len(products)} | With price: {con_precio} | With taxonomy: {con_tax}")
    
    # Get Shopify config
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT shopify_shop_url, shopify_api_password FROM empresas WHERE codigo = %s", (empresa,))
    shop, token = cur.fetchone()
    cur.close()
    conn.close()
    print(f"Shopify: {shop}")
    
    # Upload to Shopify
    url = f"https://{shop}/admin/api/2024-01/products.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    ok = err = 0
    
    for i, p in enumerate(products):
        data = {"product": {
            "title": p["title"],
            "handle": p["handle"],
            "body_html": p["body_html"],
            "vendor": p["vendor"],
            "product_type": p["product_type"],
            "status": p["status"],
            "tags": p["tags"],
            "variants": [{
                "sku": p["sku"],
                "price": str(p["price"]) if p["price"] > 0 else "0",
                "inventory_management": "shopify",
                "inventory_quantity": p["inventory"]
            }]
        }}
        
        try:
            r = requests.post(url, headers=headers, json=data, timeout=30)
            if r.status_code == 201:
                ok += 1
            else:
                err += 1
                if err <= 3:
                    print(f"  Error {p[sku]}: {r.status_code}")
        except Exception as e:
            err += 1
        
        time.sleep(0.25)
        if (i+1) % 100 == 0:
            print(f"  {i+1}/{len(products)} ok={ok} err={err}")
    
    print(f"\n=== RESULT ===")
    print(f"Uploaded: {ok} | Errors: {err}")
    print(f"End: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
