#!/usr/bin/env python3
"""Update body_html with V22 templates"""
import sys, requests, re, psycopg2
sys.path.insert(0, "/opt/odi")
from core.ficha_360_template import build_ficha_360

DB = {"host": "172.18.0.8", "port": 5432, "database": "odi", "user": "odi_user", "password": "odi_secure_password"}

def main():
    empresa = sys.argv[1].upper() if len(sys.argv) > 1 else "IMBRA"
    print(f"=== V22 UPDATE BODY: {empresa} ===")
    
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT id, shopify_shop_url, shopify_api_password FROM empresas WHERE codigo = %s", (empresa,))
    empresa_id, shop, token = cur.fetchone()
    
    # Get all products from Shopify
    products = []
    url = f"https://{shop}/admin/api/2024-01/products.json?limit=250&fields=id,title,variants"
    headers = {"X-Shopify-Access-Token": token}
    
    while url:
        r = requests.get(url, headers=headers, timeout=30)
        data = r.json()
        products.extend(data.get("products", []))
        link = r.headers.get("Link", "")
        url = None
        if "rel=\"next\"" in link:
            for part in link.split(","):
                if "rel=\"next\"" in part:
                    url = part.split("<")[1].split(">")[0]
    
    print(f"Found {len(products)} products")
    
    updated = 0
    for i, p in enumerate(products):
        pid = p["id"]
        title = p.get("title", "")
        sku = p["variants"][0].get("sku", "") if p.get("variants") else ""
        
        # Generate new body with V22 templates
        body = build_ficha_360(title, sku, "", empresa)
        
        # Update via API
        update_url = f"https://{shop}/admin/api/2024-01/products/{pid}.json"
        data = {"product": {"id": pid, "body_html": body}}
        
        try:
            r = requests.put(update_url, headers=headers, json=data, timeout=30)
            if r.status_code == 200:
                updated += 1
        except Exception as e:
            pass
        
        if (i+1) % 100 == 0:
            print(f"  {i+1}/{len(products)} updated={updated}")
    
    print(f"\nUpdated: {updated}/{len(products)}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
