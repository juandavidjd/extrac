#!/usr/bin/env python3
import os, json, time, requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

API_VERSION = "2024-01"
JSON_PATH = "/opt/odi/data/orden_maestra_v6"

STORES = ["STORE", "VITTON", "LEO", "KAIQI", "CBI", "MCLMOTOS", "ARMOTOS", 
          "BARA", "JAPAN", "YOKOMAR", "IMBRA", "DUNA", "OH_IMPORTACIONES", "DFG"]

def get_creds(store):
    return os.getenv(store + "_SHOP"), os.getenv(store + "_TOKEN")

def api_call(shop, token, method, endpoint, data=None):
    url = "https://" + shop + "/admin/api/" + API_VERSION + "/" + endpoint
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    for attempt in range(3):
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                r = requests.post(url, headers=headers, json=data, timeout=60)
            elif method == "DELETE":
                r = requests.delete(url, headers=headers, timeout=30)
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 2)))
                continue
            return r
        except:
            if attempt < 2: time.sleep(2)
    return None

def wipe_store(shop, token):
    deleted = 0
    while True:
        r = api_call(shop, token, "GET", "products.json?limit=250&fields=id")
        if not r or r.status_code != 200: break
        products = r.json().get("products", [])
        if not products: break
        for p in products:
            dr = api_call(shop, token, "DELETE", "products/" + str(p["id"]) + ".json")
            if dr and dr.status_code in [200, 204]: deleted += 1
            time.sleep(0.2)
    return deleted

def upload_products(shop, token, products):
    uploaded, errors = 0, 0
    for i, p in enumerate(products):
        title = p.get("title", "Sin titulo")
        price = p.get("price", 0) or 0
        sku = p.get("sku", "")
        images = []
        for img in p.get("images", []):
            if isinstance(img, dict) and img.get("src"):
                images.append({"src": img["src"]})
            elif isinstance(img, str) and img.startswith("http"):
                images.append({"src": img})
        product_data = {
            "product": {
                "title": title,
                "status": "draft" if price == 0 else "active",
                "variants": [{"sku": sku, "price": str(price), "inventory_management": "shopify", "inventory_quantity": 10}]
            }
        }
        if images: product_data["product"]["images"] = images
        r = api_call(shop, token, "POST", "products.json", product_data)
        if r and r.status_code == 201: uploaded += 1
        else: errors += 1
        if (i + 1) % 100 == 0:
            print("    Progreso: " + str(i+1) + "/" + str(len(products)) + " (" + str(uploaded) + " ok, " + str(errors) + " err)")
        time.sleep(0.25)
    return uploaded, errors

def main():
    print("=" * 70)
    print("UPLOAD ORDEN MAESTRA v6 - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)
    results = []
    for store in STORES:
        print("\n[" + store + "]")
        print("-" * 50)
        shop, token = get_creds(store)
        if not shop or not token:
            print("  ERROR: Sin credenciales")
            results.append({"store": store, "status": "NO_CREDS"})
            continue
        json_file = JSON_PATH + "/" + store + "_products.json"
        if not os.path.exists(json_file):
            print("  ERROR: JSON no encontrado")
            results.append({"store": store, "status": "NO_JSON"})
            continue
        with open(json_file, "r") as f:
            products = json.load(f)
        print("  JSON: " + str(len(products)) + " productos")
        print("  Eliminando existentes...")
        deleted = wipe_store(shop, token)
        print("  Eliminados: " + str(deleted))
        print("  Subiendo...")
        uploaded, errors = upload_products(shop, token, products)
        print("  Resultado: " + str(uploaded) + " subidos, " + str(errors) + " errores")
        results.append({"store": store, "json": len(products), "deleted": deleted, "uploaded": uploaded, "errors": errors})
    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)
    total_json, total_uploaded, total_errors = 0, 0, 0
    for r in results:
        if "uploaded" in r:
            print(r["store"].ljust(20) + " | JSON: " + str(r["json"]).rjust(5) + " | Subidos: " + str(r["uploaded"]).rjust(5) + " | Err: " + str(r["errors"]).rjust(3))
            total_json += r["json"]
            total_uploaded += r["uploaded"]
            total_errors += r["errors"]
        else:
            print(r["store"].ljust(20) + " | " + r["status"])
    print("-" * 70)
    print("TOTAL".ljust(20) + " | JSON: " + str(total_json).rjust(5) + " | Subidos: " + str(total_uploaded).rjust(5) + " | Err: " + str(total_errors).rjust(3))
    print("\nCompletado: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()
