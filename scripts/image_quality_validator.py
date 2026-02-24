#!/usr/bin/env python3
"""Image Quality Validator v1.0 - Gemini Vision"""
import os, json
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT = """Analiza esta imagen. Es una FOTO REAL de un producto fisico?

VALIDA: fotografia real, producto tangible, textura/sombras reales
INVALIDA: texto/numeros, logos, color solido, dibujos, tablas, placeholder

Responde JSON: {"valid": true/false, "reason": "corto", "confidence": 0.0-1.0}"""

class ImageQualityValidator:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        self.stats = {"validated": 0, "valid": 0, "invalid": 0}
    
    def validate_image(self, path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            ext = Path(path).suffix.lower()
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(ext.strip("."), "image/jpeg")
            
            resp = self.model.generate_content([PROMPT, {"mime_type": mime, "data": data}])
            text = resp.text.strip()
            # Clean JSON from markdown
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            result = json.loads(text)
            
            self.stats["validated"] += 1
            self.stats["valid" if result.get("valid") else "invalid"] += 1
            return {"path": path, **result}
        except Exception as e:
            return {"path": path, "valid": False, "reason": str(e)[:50], "confidence": 0}
    
    def validate_dir(self, directory, limit=None):
        imgs = list(Path(directory).glob("*.jpg")) + list(Path(directory).glob("*.png"))
        if limit: imgs = imgs[:limit]
        for i, img in enumerate(imgs, 1):
            r = self.validate_image(str(img))
            s = "OK" if r.get("valid") else "FAIL"
            print(f"[{i}/{len(imgs)}] {img.name}: {s} - {r.get(\"reason\", \"\")}")
        print(f"\nResumen: {self.stats}")

if __name__ == "__main__":
    import sys
    v = ImageQualityValidator()
    if len(sys.argv) > 1:
        p = sys.argv[1]
        lim = int(sys.argv[2]) if len(sys.argv) > 2 else None
        if os.path.isfile(p):
            r = v.validate_image(p)
            print(f"{VALIDA if r.get(valid) else INVALIDA}: {r.get(reason)}")
        elif os.path.isdir(p):
            v.validate_dir(p, lim)
