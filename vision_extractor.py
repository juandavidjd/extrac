import os
import base64
import json
import time

from openai import OpenAI


class VisionExtractor:
    """
    Analiza cada recorte usando GPT-4o-mini Vision.
    Devuelve un diccionario estructurado con campos estandarizados.
    """

    def __init__(self, model="gpt-4o-mini", retries=2):
        self.model = model
        self.retries = retries

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Falta variable de entorno OPENAI_API_KEY")

        self.client = OpenAI(api_key=api_key)


    # ---------------------------------------------------------
    # Convertir imagen a base64
    # ---------------------------------------------------------
    def load_image_b64(self, path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


    # ---------------------------------------------------------
    # Prompt ADSI V5
    # ---------------------------------------------------------
    def build_prompt(self):
        return """
Eres un extractor profesional de catálogos técnicos y comerciales.
Analiza la imagen y devuelve SOLO un JSON válido con:

- codigo: (string, si no existe "SIN_CODIGO")
- descripcion: nombre del producto
- precio: si aparece, numérico sin símbolos
- empaque: texto si aparece
- marketing: texto atractivo si aplica
- tecnico: especificaciones técnicas si aplica
- familia: categoría general (ej: Cauchos, Herramientas, Kits)
- subfamilia: categoría más específica
- observaciones: cualquier dato útil adicional

Reglas:
- NO inventes información.
- Si hay varias referencias en la misma imagen, describe solo la más clara.
- Si hay color, inclúyelo.
- Si ves tabla dentro del recorte, interpreta las columnas principales.
- No coloques comentarios fuera del JSON.
- Si la imagen contiene sólo texto, igualmente estructura los campos.
"""


    # ---------------------------------------------------------
    # Llamada al modelo Vision
    # ---------------------------------------------------------
    def query_model(self, prompt, img_b64):
        payload = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_b64}"
            }
        }

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Extractor ADSI Vision V5"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        payload
                    ]
                }
            ],
            temperature=0
        )

        return response.choices[0].message.content


    # ---------------------------------------------------------
    # Limpiar/eliminar texto fuera del JSON
    # ---------------------------------------------------------
    def clean_json(self, raw):
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            raw = raw[start:end]
            return json.loads(raw)
        except:
            return {}


    # ---------------------------------------------------------
    # Normalizar precio
    # ---------------------------------------------------------
    def normalize_price(self, p):
        if not p:
            return ""
        p = str(p).replace("$", "").replace(",", "").strip()
        try:
            return str(float(p))
        except:
            return ""


    # ---------------------------------------------------------
    # Método principal: analiza una celda (un recorte)
    # ---------------------------------------------------------
    def analyze(self, image_path):
        img_b64 = self.load_image_b64(image_path)
        prompt = self.build_prompt()

        for attempt in range(self.retries + 1):
            try:
                raw = self.query_model(prompt, img_b64)
                data = self.clean_json(raw)

                # Normalizar precio
                if "precio" in data:
                    data["precio"] = self.normalize_price(data.get("precio"))

                data["file"] = os.path.basename(image_path)
                return data

            except Exception as e:
                print(f"[VISION ERROR] intento {attempt} → {e}")
                time.sleep(0.5)

        return {
            "codigo": "SIN_CODIGO",
            "descripcion": "",
            "precio": "",
            "empaque": "",
            "marketing": "",
            "tecnico": "",
            "familia": "",
            "subfamilia": "",
            "observaciones": "",
            "file": os.path.basename(image_path)
        }
