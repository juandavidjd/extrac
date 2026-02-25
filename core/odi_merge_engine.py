#!/usr/bin/env python3
"""
ODI V24.1 - Merge Engine Generico
Multi-Source Merge: Shopify + Excel + Images + GDrive.
"""
import json
import requests
import time
from datetime import datetime
from typing import Dict
from pathlib import Path

BRANDS_DIR = Path("/opt/odi/data/brands")
PROFILES_DIR = Path("/opt/odi/data/profiles")
REPORTS_DIR = Path("/opt/odi/data/reports")


class MergeEngine:
    def __init__(self, empresa: str):
        self.empresa = empresa.upper()
        self.brand_config = self._load_brand()
        self.profile = self._load_profile()

    def _load_brand(self) -> Dict:
        path = BRANDS_DIR / f"{self.empresa.lower()}.json"
        return json.load(open(path)) if path.exists() else {}

    def _load_profile(self) -> Dict:
        path = PROFILES_DIR / f"{self.empresa}.json"
        if not path.exists():
            path = PROFILES_DIR / "_default.json"
        return json.load(open(path)) if path.exists() else {"sources": {}}

    def collect_shopify(self) -> Dict:
        cfg = self.brand_config.get("shopify", {})
        shop, token = cfg.get("shop"), cfg.get("token")
        if not shop or not token:
            return {}
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"
        headers = {"X-Shopify-Access-Token": token}
        products = {}
        url = f"https://{shop}/admin/api/2024-10/products.json"
        params = {"fields": "id,title,variants,images,status", "limit": 250}
        while url:
            resp = requests.get(url, headers=headers, params=params, timeout=60)
            if resp.status_code != 200:
                break
            for p in resp.json().get("products", []):
                v = p.get("variants", [{}])[0]
                sku = v.get("sku", "")
                if sku:
                    products[sku] = {"product_id": p["id"], "title": p.get("title", ""),
                                    "price": float(v.get("price", 0) or 0), "status": p.get("status"),
                                    "has_image": len(p.get("images", [])) > 0}
            link = resp.headers.get("Link", "")
            url = None
            params = {}
            if "rel=\"next\"" in link:
                for part in link.split(","):
                    if "rel=\"next\"" in part:
                        url = part.split(";")[0].strip().strip("<>")
            time.sleep(0.3)
        print(f"[COLLECT] Shopify: {len(products)}")
        return products

    def collect_excel_prices(self) -> Dict:
        src = self.profile.get("sources", {}).get("excel_prices", {})
        if not src.get("enabled"):
            return {}
        path = Path(src.get("path", ""))
        if not path.exists():
            return {}
        prices = {}
        data = json.load(open(path))
        for item in data:
            sku = item.get("sku") or item.get("codigo", "")
            price = item.get("price") or item.get("precio")
            if sku and price:
                prices[str(sku)] = float(price)
        print(f"[COLLECT] Excel: {len(prices)}")
        return prices

    def collect_image_bank(self) -> Dict:
        src = self.profile.get("sources", {}).get("image_bank", {})
        if not src.get("enabled"):
            return {}
        images = {}
        for p in src.get("paths", []):
            path = Path(p)
            if path.exists():
                for img in list(path.glob("*.png")) + list(path.glob("*.jpg")):
                    images[img.stem] = str(img)
        print(f"[COLLECT] Images: {len(images)}")
        return images

    def collect_gdrive(self) -> Dict:
        src = self.profile.get("sources", {}).get("gdrive_links", {})
        if not src.get("enabled"):
            return {}
        path = Path(src.get("path", ""))
        if not path.exists():
            return {}
        links = {}
        for item in json.load(open(path)):
            sku = item.get("sku", "")
            url = item.get("gdrive_url") or item.get("image_url", "")
            if sku and url:
                links[str(sku)] = url
        print(f"[COLLECT] GDrive: {len(links)}")
        return links

    def merge(self, shopify, prices, images, gdrive) -> Dict:
        all_skus = set(shopify.keys()) | set(prices.keys())
        master = {}
        for sku in all_skus:
            s = shopify.get(sku, {})
            master[sku] = {"sku": sku, "product_id": s.get("product_id"),
                          "shopify_price": s.get("price", 0), "excel_price": prices.get(sku),
                          "status": s.get("status"), "has_image": s.get("has_image", False),
                          "local_image": images.get(sku), "gdrive": gdrive.get(sku),
                          "in_shopify": sku in shopify,
                          "has_price": prices.get(sku) is not None or s.get("price", 0) > 1}
        print(f"[MERGE] Master: {len(master)}")
        return master

    def decide(self, master) -> Dict:
        d = {"activate": [], "draft": [], "needs_image": [], "gaps": []}
        for sku, m in master.items():
            if not m["in_shopify"]:
                d["gaps"].append(sku)
            elif m["has_price"] and m["status"] == "draft":
                d["activate"].append(sku)
            elif not m["has_price"] and m["status"] == "active":
                d["draft"].append(sku)
            if not m["has_image"] and (m["local_image"] or m["gdrive"]):
                d["needs_image"].append(sku)
        print(f"[DECIDE] Activate:{len(d[activate])} Draft:{len(d[draft])} Gaps:{len(d[gaps])}")
        return d

    def execute(self, master, decisions, dry_run=True) -> Dict:
        cfg = self.brand_config.get("shopify", {})
        shop, token = cfg.get("shop"), cfg.get("token")
        if not shop or not token:
            return {"error": "no_creds"}
        if not shop.endswith(".myshopify.com"):
            shop = f"{shop}.myshopify.com"
        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        results = {"activated": 0, "dry_run": dry_run}
        if dry_run:
            results["would_activate"] = len(decisions["activate"])
            return results
        for sku in decisions["activate"][:100]:
            pid = master.get(sku, {}).get("product_id")
            if not pid:
                continue
            url = f"https://{shop}/admin/api/2024-10/products/{pid}.json"
            resp = requests.put(url, headers=headers, json={"product": {"id": pid, "status": "active"}}, timeout=30)
            if resp.status_code == 200:
                results["activated"] += 1
            time.sleep(0.5)
        return results

    def run_merge(self, dry_run=True) -> Dict:
        print(f"[MERGE] {self.empresa}")
        shopify = self.collect_shopify()
        prices = self.collect_excel_prices()
        images = self.collect_image_bank()
        gdrive = self.collect_gdrive()
        master = self.merge(shopify, prices, images, gdrive)
        decisions = self.decide(master)
        results = self.execute(master, decisions, dry_run)
        report = {"empresa": self.empresa, "ts": datetime.now().isoformat(),
                  "master": len(master), "decisions": {k: len(v) for k, v in decisions.items()}, "results": results}
        with open(REPORTS_DIR / f"{self.empresa.lower()}_merge_report.json", "w") as f:
            json.dump(report, f, indent=2)
        return report


def run_merge(empresa, dry_run=True):
    return MergeEngine(empresa).run_merge(dry_run)


def main():
    import sys
    if len(sys.argv) < 2:
        print("Uso: python odi_merge_engine.py <EMPRESA> [--dry-run|--execute]")
        return
    empresa, mode = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "--dry-run"
    print(json.dumps(run_merge(empresa, mode != "--execute"), indent=2))


if __name__ == "__main__":
    main()
