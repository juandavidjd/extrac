#!/usr/bin/env python3
"""
ODI Hotspot Mapper v1.0
Extracts product bounding boxes from catalog PDF pages using Vision AI

Output: hotspot_map.json with structure:
{
  "page_2": {
    "image_path": "/path/to/page_2.png",
    "products": [
      {"codigo": "03860", "bbox": {"x": 10.5, "y": 15.2, "w": 25.0, "h": 30.0}, "confidence": 0.95}
    ]
  }
}
"""

import os
import sys
import json
import base64
import time
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Optional
import requests

sys.path.insert(0, "/opt/odi")
from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")

class HotspotMapper:
    def __init__(self, store: str = "ARMOTOS"):
        self.store = store
        self.data_dir = Path(f"/opt/odi/data/{store}")
        self.pdf_path = self.data_dir / "catalogo" / "CATALOGO NOVIEMBRE V01-2025 NF.pdf"
        self.output_dir = self.data_dir / "hotspot_pages"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load product-to-page mapping
        with open(self.data_dir / "json" / "all_products.json") as f:
            self.products = json.load(f)

        self.page_products = self._build_page_map()

        # Vision AI config
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.gemini_key = os.getenv("GOOGLE_API_KEY")

    def _build_page_map(self) -> Dict[int, List[Dict]]:
        """Build mapping of page -> products on that page"""
        page_map = {}
        for p in self.products:
            page = p.get("page", 0)
            if page not in page_map:
                page_map[page] = []
            page_map[page].append({
                "codigo": p.get("codigo", ""),
                "nombre": p.get("nombre", ""),
                "precio": p.get("precio", "")
            })
        return page_map

    def extract_page_image(self, page_num: int, dpi: int = 150) -> str:
        """Extract page as PNG image, returns path"""
        output_path = self.output_dir / f"page_{page_num}.png"

        if output_path.exists():
            return str(output_path)

        doc = fitz.open(self.pdf_path)
        page = doc[page_num - 1]  # 0-indexed

        # Render at specified DPI
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(output_path))
        doc.close()

        return str(output_path)

    def _image_to_base64(self, image_path: str) -> str:
        """Convert image to base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _call_vision_ai(self, image_path: str, products_on_page: List[Dict]) -> Optional[Dict]:
        """Call Vision AI to extract bounding boxes"""

        image_b64 = self._image_to_base64(image_path)

        # Build product list for prompt
        product_codes = [str(p["codigo"]) if not isinstance(p["codigo"], list) else ",".join(p["codigo"]) for p in products_on_page]
        product_list = ", ".join(product_codes)

        prompt = f"""Analyze this catalog page image. Find the exact location of each product.

Products to locate (by code): {product_list}

For EACH product code, provide its bounding box as percentage coordinates (0-100):
- x: left edge percentage from image left
- y: top edge percentage from image top
- w: width as percentage of image width
- h: height as percentage of image height

Return ONLY valid JSON in this exact format:
{{
  "products": [
    {{"codigo": "03860", "bbox": {{"x": 10.5, "y": 15.2, "w": 25.0, "h": 30.0}}, "confidence": 0.95}},
    {{"codigo": "03858", "bbox": {{"x": 45.0, "y": 15.2, "w": 25.0, "h": 30.0}}, "confidence": 0.90}}
  ]
}}

IMPORTANT:
- Coordinates are PERCENTAGES (0-100), not pixels
- Each product typically has a photo, code number, and price visible
- Look for the 5-digit code numbers to identify each product
- If you cannot find a product, set confidence to 0
- Be precise - a 5% error makes hotspots miss their target"""

        # Try OpenAI GPT-4o first
        if self.openai_key:
            try:
                response = self._call_openai(image_b64, prompt)
                if response:
                    return response
            except Exception as e:
                print(f"    OpenAI error: {e}")

        # Fallback to Gemini
        if self.gemini_key:
            try:
                response = self._call_gemini(image_b64, prompt)
                if response:
                    return response
            except Exception as e:
                print(f"    Gemini error: {e}")

        return None

    def _call_openai(self, image_b64: str, prompt: str) -> Optional[Dict]:
        """Call OpenAI GPT-4o Vision"""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.1
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            # Extract JSON from response
            return self._parse_json_response(content)

        return None

    def _call_gemini(self, image_b64: str, prompt: str) -> Optional[Dict]:
        """Call Google Gemini Vision"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}"

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_b64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2000
            }
        }

        resp = requests.post(url, json=payload, timeout=120)
        if resp.status_code == 200:
            content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_json_response(content)

        return None

    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """Parse JSON from AI response"""
        import re

        # Try to find JSON block
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Try direct parse
        try:
            return json.loads(content)
        except:
            pass

        return None

    def process_page(self, page_num: int) -> Dict:
        """Process a single page and extract hotspots"""
        products_on_page = self.page_products.get(page_num, [])

        if not products_on_page:
            return {"page": page_num, "status": "no_products", "products": []}

        print(f"  Página {page_num}: {len(products_on_page)} productos")

        # Extract page image
        image_path = self.extract_page_image(page_num)
        print(f"    Imagen: {image_path}")

        # Call Vision AI
        result = self._call_vision_ai(image_path, products_on_page)

        if result and "products" in result:
            found = len([p for p in result["products"] if p.get("confidence", 0) > 0.5])
            print(f"    Vision AI: {found}/{len(products_on_page)} productos localizados")

            return {
                "page": page_num,
                "image_path": image_path,
                "status": "success",
                "expected": len(products_on_page),
                "found": found,
                "products": result["products"]
            }
        else:
            print(f"    Vision AI: FAILED")
            return {
                "page": page_num,
                "image_path": image_path,
                "status": "vision_failed",
                "expected": len(products_on_page),
                "found": 0,
                "products": []
            }

    def run_sample(self, pages: List[int] = None, n_pages: int = 10) -> Dict:
        """Run on sample pages"""
        if pages is None:
            # Get first n pages with products
            pages = sorted(self.page_products.keys())[:n_pages]

        print("=" * 70)
        print(f"HOTSPOT MAPPER - {self.store} - {len(pages)} PÁGINAS DE MUESTRA")
        print("=" * 70)

        results = {
            "store": self.store,
            "sample_mode": True,
            "pages_processed": len(pages),
            "hotspots": {}
        }

        total_expected = 0
        total_found = 0

        for page_num in pages:
            page_result = self.process_page(page_num)
            results["hotspots"][f"page_{page_num}"] = page_result
            total_expected += page_result.get("expected", 0)
            total_found += page_result.get("found", 0)
            time.sleep(1)  # Rate limiting

        results["summary"] = {
            "total_expected": total_expected,
            "total_found": total_found,
            "accuracy": round(total_found / total_expected * 100, 1) if total_expected > 0 else 0
        }

        # Save results
        output_path = self.data_dir / "hotspot_map_sample.json"
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print()
        print("=" * 70)
        print(f"RESUMEN: {total_found}/{total_expected} productos localizados ({results['summary']['accuracy']}%)")
        print(f"Guardado: {output_path}")
        print("=" * 70)

        return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Hotspot Mapper")
    parser.add_argument("--store", default="ARMOTOS", help="Store name")
    parser.add_argument("--pages", type=int, nargs="+", help="Specific pages to process")
    parser.add_argument("--sample", type=int, default=10, help="Number of sample pages")

    args = parser.parse_args()

    mapper = HotspotMapper(args.store)
    results = mapper.run_sample(pages=args.pages, n_pages=args.sample)

    # Print detailed results
    print("\nDETALLE POR PÁGINA:")
    print("-" * 70)
    for page_key, page_data in results["hotspots"].items():
        page_num = page_data["page"]
        status = page_data["status"]
        if status == "success":
            for prod in page_data["products"]:
                codigo = prod.get("codigo", "???")
                bbox = prod.get("bbox", {})
                conf = prod.get("confidence", 0)
                x, y, w, h = bbox.get("x", 0), bbox.get("y", 0), bbox.get("w", 0), bbox.get("h", 0)
                print(f"  Pág {page_num:3} | {codigo} | bbox: x={x:5.1f}% y={y:5.1f}% w={w:5.1f}% h={h:5.1f}% | conf: {conf:.0%}")
