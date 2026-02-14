#!/usr/bin/env python3
import os, sys, json
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import requests, time

load_dotenv("/opt/odi/.env")

BASE_DATA = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data"
IDENTITY = "/opt/odi/data/identidad"
OUTPUT = "/opt/odi/data/processed"

sys.path.insert(0, "/opt/odi/core")
from title_normalizer import normalize_title, detect_sistema
from html_template import generate_body_html, load_brand

def load_csv_safe(path):
    for sep in [",", ";", "	"]:
        for enc in ["utf-8", "latin-1"]:
            try:
                df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str, on_bad_lines="skip")
                if len(df.columns) > 1:
                    return df
            except:
                pass
    return None

def process_store(empresa, empresa_key):
    data_path = Path(BASE_DATA) / empresa
    out_dir = Path(OUTPUT) / empresa_key
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Procesando {empresa}...")
    
    # Find CSVs
    base_csv = list(data_path.glob("*[Bb]ase*[Dd]atos*.csv"))
    if not base_csv:
        base_csv = list(data_path.glob("*.csv"))
    
    if not base_csv:
        print("No CSV found")
        return None
    
    df = load_csv_safe(base_csv[0])
    if df is None:
        return None
    
    print(f"Loaded {len(df)} rows from {base_csv[0].name}")
    
    # Find columns
    col_desc = col_sku = col_price = col_qty = None
    for col in df.columns:
        cl = col.lower()
        if "desc" in cl or "titulo" in cl or "nombre" in cl:
            col_desc = col
        if "codigo" in cl or "sku" in cl or "ref" in cl:
            col_sku = col
        if "precio" in cl or "price" in cl:
            col_price = col
        if "cant" in cl or "qty" in cl or "stock" in cl:
            col_qty = col
    
    products = []
    seen = set()
    
    for idx, row in df.iterrows():
        desc = str(row.get(col_desc, "")).strip() if col_desc else ""
        if not desc or desc == "nan":
            continue
        
        sku_orig = str(row.get(col_sku, "")).strip() if col_sku else ""
        sku = f"{empresa_key[:3]}-{sku_orig or idx}"
        
        if sku in seen:
            continue
        seen.add(sku)
        
        price = 0.0
        if col_price:
            try:
                price = float(str(row.get(col_price, "0")).replace(",", "").replace("$", ""))
            except:
                pass
        
        qty = 0
        if col_qty:
            try:
                qty = int(float(str(row.get(col_qty, "0")).replace(",", "")))
            except:
                pass
        
        title = normalize_title(desc)
        sistema = detect_sistema(desc)
        
        p = {
            "sku": sku,
            "title": title,
            "price": price,
            "quantity": qty,
            "category": sistema.capitalize() if sistema != "general" else "Repuesto",
            "sistema": sistema,
            "vendor": empresa
        }
        p["body_html"] = generate_body_html(p, empresa_key)
        p["tags"] = f"{sistema}, Moto, Repuesto"
        products.append(p)
    
    output_file = out_dir / "products_ready.json"
    with open(output_file, "w") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(products)} products to {output_file}")
    return products

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 process_store_1a.py EMPRESA [EMPRESA_KEY]")
        sys.exit(1)
    empresa = sys.argv[1]
    key = sys.argv[2] if len(sys.argv) > 2 else empresa.upper().replace(" ", "_")
    process_store(empresa, key)
