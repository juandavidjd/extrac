
import os
import json
from PIL import Image
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

# FIX 2 y 4: Prompt mejorado con asociacion foto-producto y SKU correcto
UNIFIED_PROMPT = """Analiza esta pagina de catalogo de repuestos de motos marca {STORE}.

Para CADA PRODUCTO visible en esta pagina, extrae:

{{
  "products": [
    {{
      "name": "nombre del producto como aparece",
      "normalized_title": "Nombre Limpio - Marca Modelo CC",
      "sku": "codigo/referencia del producto",
      "price": precio como numero (0 si no visible),
      "description": "descripcion breve del producto",
      "category": "categoria (frenos, suspension, transmision, etc.)",
      "compatible_models": ["modelo1", "modelo2"],
      "has_photo": true o false,
      "photo_bbox_pct": {{"x1": 10, "y1": 20, "x2": 45, "y2": 80}}
    }}
  ],
  "page_type": "A, B, o C"
}}

REGLAS IMPORTANTES:

1. ASOCIACION FOTO-PRODUCTO: Vincula cada foto SOLO con el producto que esta INMEDIATAMENTE adyacente. La foto esta ENCIMA o AL LADO del nombre/SKU. Si una foto esta entre dos productos y no es claro cual es, marca has_photo: false para ambos.

2. SKU/REFERENCIA: Es un codigo alfanumerico unico, formato tipico: letras+numeros (ARM-001, FRC-125, KEC624Z). NO es: precio (,054), numero de pagina (pag 56), codigo de color (ROJO), cantidad (x10). Si no puedes identificar SKU con certeza, pon: "SIN-SKU"

3. COORDENADAS: bbox_pct en porcentaje (0-100) de la pagina. x1,y1 = esquina superior izquierda, x2,y2 = esquina inferior derecha.

4. FOTOS REALES: Solo incluir fotos reales de productos (con textura, sombras). Ignorar rectangulos de color, iconos, logos.

Solo productos REALES. Ignorar headers, logos, decoraciones."""


# FIX 3: Ficha 360 sin "La Roca Motorepuestos"
def generate_ficha_360(product, store_name):
    sku = product.get("sku", "N/A")
    category = product.get("category", "Repuesto")
    models = ", ".join(product.get("compatible_models", [])) or "Consultar"
    desc = product.get("description", "Repuesto de alta calidad")
    
    html = f"""<div class="ficha-360">
<h2>Descripcion</h2>
<p>{desc}. Repuesto de alta calidad marca {store_name}. Categoria: {category}.</p>
<h2>Informacion Tecnica</h2>
<table><tr><td>Referencia</td><td>{sku}</td></tr><tr><td>Marca</td><td>{store_name}</td></tr><tr><td>Categoria</td><td>{category}</td></tr><tr><td>Condicion</td><td>Nuevo</td></tr><tr><td>Garantia</td><td>6 meses</td></tr></table>
<h2>Compatibilidad</h2>
<p>Modelos: {models}</p>
<h2>Beneficios</h2>
<ul><li>Materiales de primera calidad</li><li>Ajuste exacto</li><li>Especificaciones OEM</li><li>Mejora rendimiento y seguridad</li></ul>
<h2>Recomendaciones</h2>
<p>Instalacion por tecnico especializado.</p>
<h2>Proveedor</h2>
<p>{store_name}</p>
</div>"""
    return html


class UnifiedExtractor:
    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        # FIX 1: Global SKU tracking for deduplication across pages
        self.global_skus = {}
        self.page_stats = {"A": 0, "B": 0, "C": 0}
    
    def extract_page_unified(self, image_path, store_name, page_num, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(f"{output_dir}/images", exist_ok=True)
        
        img = Image.open(image_path)
        w, h = img.size
        
        prompt = UNIFIED_PROMPT.replace("{STORE}", store_name)
        
        try:
            response = self.model.generate_content([prompt, img], generation_config={"temperature": 0.1, "max_output_tokens": 8192})
            data = self._parse_response(response.text)
        except Exception as e:
            print(f"  Error Gemini: {e}")
            return []
        
        # FIX 5: Track page type
        page_type = data.get("page_type", "C")
        if page_type in self.page_stats:
            self.page_stats[page_type] += 1
        
        products = data.get("products", [])
        
        # FIX 1: Deduplicate within page by SKU
        seen_skus = {}
        for prod in products:
            sku = prod.get("sku", "SIN-SKU")
            if sku in seen_skus:
                # Prefer the one with photo
                if prod.get("has_photo") and not seen_skus[sku].get("has_photo"):
                    seen_skus[sku] = prod
            else:
                seen_skus[sku] = prod
        products = list(seen_skus.values())
        
        results = []
        
        for i, prod in enumerate(products):
            sku = prod.get("sku", f"SIN-SKU-P{page_num:03d}-{i}")
            
            # FIX 1: Global deduplication - skip if already processed
            if sku in self.global_skus and sku != "SIN-SKU":
                continue
            
            self.global_skus[sku] = True
            prod["body_html"] = generate_ficha_360(prod, store_name)
            
            if prod.get("has_photo") and prod.get("photo_bbox_pct"):
                img_path = self._crop_and_save(img, prod["photo_bbox_pct"], output_dir, store_name, page_num, sku)
                prod["image_path"] = img_path
            else:
                prod["image_path"] = None
            
            prod["page_num"] = page_num
            prod["store"] = store_name
            results.append(prod)
        
        return results
    
    def _parse_response(self, text):
        try:
            text = text.strip()
            if "```" in text:
                parts = text.split("```")
                if len(parts) > 1:
                    text = parts[1]
                    if text.startswith("json"):
                        text = text[4:]
            return json.loads(text.strip())
        except:
            return {"products": []}
    
    def _crop_and_save(self, img, bbox, output_dir, prefix, page_num, sku):
        w, h = img.size
        x1 = int(bbox.get("x1", 0) / 100 * w)
        y1 = int(bbox.get("y1", 0) / 100 * h)
        x2 = int(bbox.get("x2", 100) / 100 * w)
        y2 = int(bbox.get("y2", 100) / 100 * h)
        
        pad_x, pad_y = int((x2-x1)*0.05), int((y2-y1)*0.05)
        x1, y1 = max(0, x1-pad_x), max(0, y1-pad_y)
        x2, y2 = min(w, x2+pad_x), min(h, y2+pad_y)
        
        if x2 <= x1 or y2 <= y1:
            return None
        
        crop = img.crop((x1, y1, x2, y2))
        if crop.width < 100 or crop.height < 100:
            return None
        
        pixels = list(crop.convert("RGB").getdata())[:500]
        if len(set(pixels)) < 15:
            return None
        
        safe_sku = str(sku).replace("/", "_").replace(" ", "_").replace(":", "-")[:30]
        filename = f"{prefix}_p{page_num:03d}_{safe_sku}.png"
        filepath = f"{output_dir}/images/{filename}"
        crop.save(filepath)
        return filepath
    
    def get_stats(self):
        return {
            "unique_skus": len(self.global_skus),
            "page_types": self.page_stats
        }
