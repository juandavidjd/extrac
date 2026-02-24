#!/usr/bin/env python3
"""
V22 BARA Consolidated Processor
Principio: Revisar TODA la carpeta, cruzar TODO por código
"""
import csv, json, sys, requests, time, re, os
from datetime import datetime
import psycopg2

sys.path.insert(0, "/opt/odi")
from core.ficha_360_template import build_ficha_360

DB = {"host": "172.18.0.8", "port": 5432, "database": "odi", "user": "odi_user", "password": "odi_secure_password"}
DATA_DIR = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI"

def load_taxonomia():
    """Load rich taxonomy from catalogo_imagenes"""
    taxonomia = {}
    path = f"{DATA_DIR}/Data/Bara/catalogo_imagenes_Bara.csv"
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            filename = row.get("Filename_Original", "")
            match = re.match(r"^([\d]+-[\d]+-[\d]+)", filename)
            if match:
                sku = match.group(1)
                taxonomia[sku] = {
                    "sistema": row.get("Sistema", ""),
                    "subsistema": row.get("SubSistema", ""),
                    "componente": row.get("Componente_Taxonomia", ""),
                    "funcion": row.get("Funcion", ""),
                    "caracteristicas": row.get("Caracteristicas_Observadas", ""),
                    "compatibilidad_texto": row.get("Compatibilidad_Probable_Texto", ""),
                    "compatibilidad_json": row.get("Compatibilidad_Probable_JSON", ""),
                    "tags": row.get("Tags_Sugeridos", ""),
                    "nombre_comercial": row.get("Nombre_Comercial_Catalogo", "")
                }
    return taxonomia

def load_imagenes():
    """Map SKUs to real image files"""
    imagenes = {}
    img_dir = f"{DATA_DIR}/Imagenes/Bara/"
    for f in os.listdir(img_dir):
        if f.endswith((".jpg", ".png", ".jpeg")):
            match = re.match(r"^([\d]+-[\d]+-[\d]+)", f)
            if match:
                sku = match.group(1)
                imagenes[sku] = os.path.join(img_dir, f)
    return imagenes

def normalize_title(title):
    if not title:
        return title
    if title.isupper():
        lowercase_words = {"de", "del", "la", "el", "los", "las", "para", "con", "sin", "en", "y", "o", "a", "al", "por"}
        words = title.lower().split()
        result = []
        for i, word in enumerate(words):
            if i == 0:
                result.append(word.capitalize())
            elif word in lowercase_words:
                result.append(word.lower())
            else:
                result.append(word.capitalize())
        return " ".join(result)
    return title

def build_info_tecnica(tax):
    """Build info técnica from taxonomy data"""
    parts = []
    if tax.get("funcion"):
        parts.append(tax["funcion"])
    if tax.get("caracteristicas"):
        # Truncate if too long
        carac = tax["caracteristicas"][:200]
        if len(tax["caracteristicas"]) > 200:
            carac += "..."
        parts.append(carac)
    return " ".join(parts) if parts else None

def main():
    empresa = "BARA"
    print(f"=== V22 BARA CONSOLIDATED PROCESSOR ===")
    print(f"Start: {datetime.now().strftime('%H:%M:%S')}")
    
    # 1. Load all data sources
    print("\n[1/4] Loading data sources...")
    taxonomia = load_taxonomia()
    print(f"  Taxonomia: {len(taxonomia)} items")
    imagenes = load_imagenes()
    print(f"  Imagenes: {len(imagenes)} items")
    
    # 2. Read price list (source of truth)
    print("\n[2/4] Processing Lista_Precios...")
    csv_path = f"{DATA_DIR}/Data/Bara/Lista_Precios_Bara.csv"
    products = []
    
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            sku = row.get("CODIGO", "").strip()
            titulo = row.get("DESCRIPCION", "").strip()
            precio = row.get("PRECIO", "").strip()
            
            if not sku:
                continue
            
            # Normalize
            titulo_norm = normalize_title(titulo)
            try:
                precio_f = float(re.sub(r"[^\d.]", "", str(precio))) if precio else 0
            except:
                precio_f = 0
            
            status = "active" if precio_f > 0 else "draft"
            
            # Enrich with taxonomy
            tax = taxonomia.get(sku, {})
            compatibilidad = tax.get("compatibilidad_texto", "")
            
            # Build extra_info from taxonomy
            extra_info = {}
            info_tec = build_info_tecnica(tax)
            if info_tec:
                extra_info["info_tecnica"] = info_tec
            if tax.get("sistema"):
                extra_info["sistema"] = tax["sistema"]
            
            # Get image path
            imagen_path = imagenes.get(sku)
            
            # Generate ficha 360
            body = build_ficha_360(titulo_norm, sku, compatibilidad, empresa, extra_info)
            handle = re.sub(r"[^a-z0-9]+", "-", titulo_norm.lower())[:80] + "-bara"
            
            products.append({
                "sku": sku,
                "title": titulo_norm,
                "handle": handle,
                "body_html": body,
                "vendor": empresa,
                "product_type": tax.get("sistema", "Repuestos"),
                "status": status,
                "price": precio_f,
                "inventory": 10,
                "tags": tax.get("tags", ""),
                "image_path": imagen_path,
                "has_taxonomy": bool(tax),
                "has_image": bool(imagen_path)
            })
    
    # Stats
    con_precio = sum(1 for p in products if p["price"] > 0)
    con_tax = sum(1 for p in products if p["has_taxonomy"])
    con_img = sum(1 for p in products if p["has_image"])
    print(f"  Total: {len(products)}")
    print(f"  Con precio: {con_precio}")
    print(f"  Con taxonomia: {con_tax}")
    print(f"  Con imagen: {con_img}")
    
    # 3. Get Shopify config and upload
    print("\n[3/4] Uploading to Shopify...")
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT shopify_shop_url, shopify_api_password FROM empresas WHERE codigo = %s", (empresa,))
    shop, token = cur.fetchone()
    cur.close()
    conn.close()
    print(f"  Shop: {shop}")
    
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
        
        # TODO: Upload image if available (Phase 2)
        
        try:
            r = requests.post(url, headers=headers, json=data, timeout=30)
            if r.status_code == 201:
                ok += 1
            else:
                err += 1
                if err <= 3:
                    print(f"    Error {p[sku]}: {r.status_code}")
        except Exception as e:
            err += 1
        
        time.sleep(0.25)
        if (i+1) % 100 == 0:
            print(f"    {i+1}/{len(products)} ok={ok} err={err}")
    
    print(f"\n[4/4] Result")
    print(f"  Uploaded: {ok}")
    print(f"  Errors: {err}")
    print(f"  End: {datetime.now().strftime('%H:%M:%S')}")
    return ok

if __name__ == "__main__":
    main()
