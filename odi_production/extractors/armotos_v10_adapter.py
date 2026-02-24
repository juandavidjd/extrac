#!/usr/bin/env python3
"""ARMOTOS V10 Adapter - Integrates V10 data into ODI Pipeline"""

import os, sys, json, re, time, base64, logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

sys.path.insert(0, "/opt/odi")
sys.path.insert(0, "/opt/odi/core")

from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")

import requests
import chromadb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stdout)
logger = logging.getLogger("v10_adapter")
for h in logging.root.handlers:
    h.flush = lambda: sys.stdout.flush()

@dataclass
class NormalizedProduct:
    sku: str
    title: str
    description: str = ""
    price: float = 0.0
    vendor: str = "ARMOTOS"
    product_type: str = "Repuesto Moto"
    tags: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    status: str = "active"
    ficha_360: str = ""
    raw_data: Dict = field(default_factory=dict)

class V10Adapter:
    def __init__(self, store: str = "ARMOTOS"):
        self.store = store
        self.data_dir = Path(f"/opt/odi/data/{store}")
        self.json_path = self.data_dir / "json" / "all_products.json"
        self.images_dir = self.data_dir / "images"
        self.products = []
        self.shop = os.getenv(f"{store}_SHOP")
        self.token = os.getenv(f"{store}_TOKEN")
        self.api_version = "2025-07"
        self.chroma_client = chromadb.HttpClient(host="localhost", port=8000)
        self.collection_name = "odi_ind_motos"

        self.piezas = {
            "cadena": "Cadena", "corona": "Corona", "pinon": "Pinon",
            "llanta": "Llanta", "amortiguador": "Amortiguador", "freno": "Freno",
            "pastilla": "Pastilla Freno", "disco": "Disco Freno", "filtro": "Filtro",
            "aceite": "Aceite", "bujia": "Bujia", "bobina": "Bobina",
            "bateria": "Bateria", "faro": "Faro", "manubrio": "Manubrio",
            "manilar": "Manubrio", "espejo": "Espejo", "escape": "Escape",
            "clutch": "Clutch", "palanca": "Palanca", "pedal": "Pedal",
            "tornillo": "Tornilleria", "rodamiento": "Rodamiento", "guante": "Guantes",
            "casco": "Casco", "banco": "Banco Trabajo", "silla": "Silla Mecanico",
            "protector": "Protector", "kit": "Kit"
        }

    def load_v10_data(self):
        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def clean_price(self, price_str):
        if not price_str or price_str == "N/A": return 0.0
        price_str = str(price_str)
        price_str = re.sub(r"[^\d.,]", "", price_str)
        if "." in price_str and "," not in price_str:
            parts = price_str.split(".")
            if len(parts) == 2 and len(parts[1]) == 3:
                price_str = price_str.replace(".", "")
        price_str = price_str.replace(",", ".")
        try:
            price = float(price_str)
            if 0 < price < 100: price = price * 1000
            return price
        except: return 0.0

    def find_image(self, codigo):
        for ext in [".png", ".jpg"]:
            for c in [codigo.zfill(5), codigo]:
                img = self.images_dir / f"{c}{ext}"
                if img.exists(): return str(img)
        return None

    def normalize_title(self, raw_title, raw_data):
        title_lower = raw_title.lower()
        pieza = None
        for k, v in self.piezas.items():
            if k in title_lower:
                pieza = v
                break
        parts = [pieza or raw_title.title()]
        colores = raw_data.get("colores")
        if colores and colores != "N/A":
            if isinstance(colores, list): parts.extend(colores)
            else: parts.append(str(colores))
        codigo = raw_data.get("codigo", "")
        if codigo: parts.append(f"[{codigo}]")
        return " ".join(parts)

    def generate_ficha_360(self, product):
        raw = product.raw_data
        compat = raw.get("compatibilidad", "Universal")
        if isinstance(compat, list): compat = ", ".join(compat)
        return f"<div class='ficha-360'><h2>{product.title}</h2><p>Codigo: {product.sku}</p><p>Precio: ${product.price:,.0f} COP</p><p>Compatibilidad: {compat}</p><p>ARMOTOS - Repuestos de calidad</p></div>"

    def transform_products(self, raw_products):
        normalized = []
        for raw in raw_products:
            codigo = str(raw.get("codigo", "")).strip()
            if not codigo: continue
            nombre = raw.get("nombre", "Producto")
            precio = self.clean_price(raw.get("precio"))
            image_path = self.find_image(codigo)
            product = NormalizedProduct(
                sku=codigo,
                title=self.normalize_title(nombre, raw),
                price=precio,
                images=[image_path] if image_path else [],
                raw_data=raw
            )
            product.tags = ["ARMOTOS", "Repuesto Moto"]
            compat = raw.get("compatibilidad")
            if compat and compat != "N/A":
                if isinstance(compat, list): product.tags.extend(compat)
                else: product.tags.append(str(compat))
            product.ficha_360 = self.generate_ficha_360(product)
            product.description = f"{nombre}. Codigo: {codigo}. {product.ficha_360}"
            normalized.append(product)
        logger.info(f"Transformed {len(normalized)} products, {sum(1 for p in normalized if p.images)} with images")
        return normalized

    def upload_image(self, product_id, image_path):
        try:
            with open(image_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            url = f"https://{self.shop}/admin/api/{self.api_version}/products/{product_id}/images.json"
            resp = requests.post(url, json={"image": {"attachment": data}},
                headers={"X-Shopify-Access-Token": self.token}, timeout=30)
            return resp.status_code == 200
        except: return False

    def upload_to_shopify(self, products):
        results = {"uploaded": 0, "failed": 0, "with_images": 0}
        url = f"https://{self.shop}/admin/api/{self.api_version}/products.json"
        headers = {"X-Shopify-Access-Token": self.token, "Content-Type": "application/json"}

        for i, product in enumerate(products):
            try:
                payload = {"product": {
                    "title": product.title,
                    "body_html": product.description,
                    "vendor": product.vendor,
                    "product_type": product.product_type,
                    "tags": ", ".join(product.tags),
                    "status": "active",
                    "variants": [{"sku": product.sku, "price": str(product.price), "inventory_management": "shopify", "inventory_quantity": 10}]
                }}
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                if resp.status_code == 201:
                    results["uploaded"] += 1
                    pid = resp.json().get("product", {}).get("id")
                    if product.images and pid:
                        if self.upload_image(pid, product.images[0]):
                            results["with_images"] += 1
                    if (i+1) % 50 == 0:
                        print(f"[PROGRESS] {i+1}/{len(products)} uploaded, {results['with_images']} with images", flush=True)
                elif resp.status_code == 429:
                    logger.warning("Rate limited, waiting...")
                    time.sleep(2)
                else:
                    results["failed"] += 1
                time.sleep(0.6)
            except Exception as e:
                results["failed"] += 1
                logger.error(f"Error [{product.sku}]: {e}")
        return results

    def index_chromadb(self, products):
        try:
            collection = self.chroma_client.get_or_create_collection(self.collection_name)
            ids, docs, metas = [], [], []
            for p in products:
                ids.append(f"ARMOTOS_{p.sku}")
                docs.append(f"{p.title} {p.description} Precio: ${p.price:,.0f} COP")
                metas.append({"type": "product", "store": "ARMOTOS", "sku": p.sku, "title": p.title, "price": p.price})
            for i in range(0, len(ids), 500):
                collection.upsert(ids=ids[i:i+500], documents=docs[i:i+500], metadatas=metas[i:i+500])
            logger.info(f"Indexed {len(ids)} to ChromaDB")
            return len(ids)
        except Exception as e:
            logger.error(f"ChromaDB error: {e}")
            return 0

    def audit(self, products, n=10):
        import random
        sample = random.sample(products, min(n, len(products)))
        checks = {"sku": 0, "title": 0, "price": 0, "desc": 0, "tags": 0, "ficha": 0, "active": 0, "vendor": 0}
        for p in sample:
            if p.sku: checks["sku"] += 1
            if p.title and len(p.title) > 5: checks["title"] += 1
            if p.price > 0: checks["price"] += 1
            if p.description: checks["desc"] += 1
            if p.tags: checks["tags"] += 1
            if p.ficha_360: checks["ficha"] += 1
            if p.status == "active": checks["active"] += 1
            if p.vendor: checks["vendor"] += 1
        score = sum(checks.values()) / (len(checks) * n) * 10
        grade = "A" if score >= 9 else "B" if score >= 7 else "C"
        return {"score": round(score, 1), "grade": grade, "checks": checks}

    def execute(self):
        logger.info("=== ARMOTOS V10 Pipeline Start ===")
        start = time.time()
        raw = self.load_v10_data()
        logger.info(f"Loaded {len(raw)} raw products")
        self.products = self.transform_products(raw)
        audit = self.audit(self.products)
        logger.info(f"Pre-audit: GRADO {audit['grade']} ({audit['score']}/10)")
        if audit["grade"] != "A":
            logger.warning(f"Audit not GRADO A, continuing anyway...")
        upload = self.upload_to_shopify(self.products)
        indexed = self.index_chromadb(self.products)
        elapsed = time.time() - start
        results = {
            "success": True, "store": self.store,
            "total": len(self.products), "uploaded": upload["uploaded"],
            "with_images": upload["with_images"], "failed": upload["failed"],
            "chromadb": indexed, "audit": audit, "seconds": round(elapsed, 1)
        }
        logger.info(f"=== Complete in {elapsed:.1f}s ===")
        return results

if __name__ == "__main__":
    adapter = V10Adapter("ARMOTOS")
    r = adapter.execute()
    print(json.dumps(r, indent=2))
