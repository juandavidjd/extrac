#\!/usr/bin/env python3
"""Sync Shopify products to PostgreSQL for cross-audit"""
import sys, requests, psycopg2
from datetime import datetime

DB = {"host": "172.18.0.8", "port": 5432, "database": "odi", "user": "odi_user", "password": "odi_secure_password"}

def main():
    empresa = sys.argv[1].upper() if len(sys.argv) > 1 else "IMBRA"
    print(f"=== V22 SYNC: {empresa} Shopify -> PostgreSQL ===")
    
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    
    # Get Shopify config and empresa_id
    cur.execute("SELECT id, shopify_shop_url, shopify_api_password FROM empresas WHERE codigo = %s", (empresa,))
    row = cur.fetchone()
    if not row:
        print(f"ERROR: {empresa} not found")
        return
    
    empresa_id, shop, token = row
    print(f"Empresa ID: {empresa_id}, Shop: {shop}")
    
    # Fetch products from Shopify
    products = []
    url = f"https://{shop}/admin/api/2024-01/products.json?limit=250"
    headers = {"X-Shopify-Access-Token": token}
    
    while url:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        products.extend(data.get("products", []))
        
        link = r.headers.get("Link", "")
        url = None
        if "rel=\"next\"" in link:
            for part in link.split(","):
                if "rel=\"next\"" in part:
                    url = part.split("<")[1].split(">")[0]
                    break
    
    print(f"Fetched {len(products)} products from Shopify")
    
    # Insert all products (UPSERT)
    inserted = updated = 0
    for p in products:
        shopify_id = p["id"]
        codigo = p["variants"][0].get("sku", "") if p.get("variants") else ""
        if not codigo:
            codigo = f"SHOP-{shopify_id}"  # Generate codigo if missing
        title = p.get("title", "")
        price = float(p["variants"][0].get("price", 0)) if p.get("variants") else 0
        vendor = p.get("vendor", empresa)
        product_type = p.get("product_type", "")
        status = p.get("status", "active")
        
        try:
            cur.execute("""
                INSERT INTO productos (empresa_id, codigo_proveedor, titulo_raw, titulo_normalizado, precio_sin_iva, shopify_product_id, status, stock)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 10)
                ON CONFLICT (empresa_id, codigo_proveedor) 
                DO UPDATE SET 
                    titulo_normalizado = EXCLUDED.titulo_normalizado,
                    precio_sin_iva = EXCLUDED.precio_sin_iva,
                    shopify_product_id = EXCLUDED.shopify_product_id,
                    status = EXCLUDED.status,
                    updated_at = NOW()
            """, (empresa_id, codigo, title, title, price, shopify_id, status))
            
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"Error {codigo}: {e}")
    
    conn.commit()
    
    # Verify count
    cur.execute("SELECT COUNT(*), COUNT(shopify_product_id) FROM productos WHERE empresa_id = %s", (empresa_id,))
    total, with_id = cur.fetchone()
    
    cur.close()
    conn.close()
    
    print(f"Inserted/Updated: {inserted}")
    print(f"Total in PostgreSQL: {total} | With Shopify ID: {with_id}")
    print("SYNC COMPLETE")

if __name__ == "__main__":
    main()
