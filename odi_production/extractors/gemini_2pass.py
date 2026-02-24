
import os
import json
from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")

CLASSIFY_PROMPT = "Mira esta pagina de un catalogo PDF de repuestos de motos. Clasifica en: A) PAGINA CON FOTOS (fotografias reales de productos), B) PAGINA SOLO TABLA (solo tablas/precios/texto), C) PAGINA MIXTA (fotos Y tablas). Responde SOLO con: A, B, o C"

DETECT_PROMPT = "Esta pagina tiene fotografias de productos. Identifica SOLO las FOTOGRAFIAS reales (con textura, sombras). NO incluyas rectangulos de color, celdas de tabla, texto, logos. Para cada foto real: {photos: [{product_name: str, bbox_pct: {x1, y1, x2, y2}, nearby_sku: str, nearby_price: str}]}. Coordenadas en porcentaje 0-100. Si no hay fotos reales: {photos: []}"

class Gemini2PassDetector:
    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.0-flash")
    
    def classify_page(self, image_path):
        from PIL import Image
        try:
            img = Image.open(image_path)
            response = self.model.generate_content([CLASSIFY_PROMPT, img], generation_config={"temperature": 0.1, "max_output_tokens": 10})
            result = response.text.strip().upper()
            for letter in ["A", "B", "C"]:
                if letter in result:
                    return letter
            return "C"
        except:
            return "C"
    
    def detect_photos(self, image_path):
        from PIL import Image
        try:
            img = Image.open(image_path)
            response = self.model.generate_content([DETECT_PROMPT, img], generation_config={"temperature": 0.1, "max_output_tokens": 4096})
            return self._parse_response(response.text)
        except:
            return []
    
    def _parse_response(self, text):
        try:
            text = text.strip()
            if text.startswith("```"):
                parts = text.split("```")
                if len(parts) > 1:
                    text = parts[1]
                    if text.startswith("json"):
                        text = text[4:]
            text = text.strip()
            data = json.loads(text)
            photos = data.get("photos", [])
            valid = []
            for p in photos:
                bbox = p.get("bbox_pct", {})
                if not all(k in bbox for k in ["x1", "y1", "x2", "y2"]):
                    continue
                bbox_list = [bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]]
                if bbox_list[2] <= bbox_list[0] or bbox_list[3] <= bbox_list[1]:
                    continue
                valid.append({"name": p.get("product_name", "Producto"), "bbox": bbox_list, "sku": p.get("nearby_sku", ""), "price": p.get("nearby_price", "")})
            return valid
        except:
            return []
    
    def crop_and_save(self, image_path, photo, output_dir, prefix, page_num):
        from PIL import Image
        os.makedirs(output_dir, exist_ok=True)
        img = Image.open(image_path)
        w, h = img.size
        bbox = photo["bbox"]
        x1, y1 = int(bbox[0]/100*w), int(bbox[1]/100*h)
        x2, y2 = int(bbox[2]/100*w), int(bbox[3]/100*h)
        pad_x, pad_y = int((x2-x1)*0.05), int((y2-y1)*0.05)
        x1, y1 = max(0, x1-pad_x), max(0, y1-pad_y)
        x2, y2 = min(w, x2+pad_x), min(h, y2+pad_y)
        crop = img.crop((x1, y1, x2, y2))
        if crop.width < 100 or crop.height < 100:
            return None
        sku = photo.get("sku", "").replace("/", "_").replace(" ", "_")[:20] or f"p{page_num:03d}"
        filename = f"{prefix}_{sku}_{page_num:03d}.png"
        filepath = os.path.join(output_dir, filename)
        crop.save(filepath)
        return filepath

