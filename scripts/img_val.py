#!/usr/bin/env python3
import os, json, sys
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT = "Es esta imagen una FOTO REAL de producto fisico? Responde JSON: {valid:true/false,reason:texto_corto}"

model = genai.GenerativeModel("gemini-2.0-flash")

def validate(path):
    with open(path, "rb") as f:
        data = f.read()
    mime = "image/png" if path.endswith(".png") else "image/jpeg"
    resp = model.generate_content([PROMPT, {"mime_type": mime, "data": data}])
    text = resp.text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return {"valid": False, "reason": "parse error"}

path = sys.argv[1] if len(sys.argv) > 1 else "."
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10

if os.path.isfile(path):
    r = validate(path)
    print("VALIDA" if r.get("valid") else "INVALIDA", r.get("reason", ""))
else:
    imgs = list(Path(path).glob("*.jpg")) + list(Path(path).glob("*.jpeg")) + list(Path(path).glob("*.png"))
    if limit:
        imgs = imgs[:limit]
    ok, fail = 0, 0
    for i, img in enumerate(imgs, 1):
        r = validate(str(img))
        status = "OK" if r.get("valid") else "FAIL"
        if r.get("valid"): ok += 1
        else: fail += 1
        reason = r.get("reason", "")[:30]
        print(f"[{i}] {img.name[:25]}: {status} - {reason}")
    print(f"\nTotal: {ok} OK, {fail} FAIL")
