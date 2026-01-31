import base64
import json
from modules.modelo_llm import LLMClient
from modules.normalizer import ADSINormalizer


class LLMParser:
    def __init__(self):
        self.llm = LLMClient()
        self.norm = ADSINormalizer()

    def _encode_image(self, img_path):
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def parse_row(self, img_path):
        """
        Envía una fila recortada a OpenAI Vision y obtiene JSON estructurado.
        """
        img_b64 = self._encode_image(img_path)

        prompt = """
Extrae de esta imagen un JSON limpio con la siguiente estructura:

{
  "codigo": "",
  "descripcion": "",
  "precio": "",
  "empaque": "",
  "fotos": [],
  "variantes": []
}

Reglas:
- No inventes nada. Solo extrae lo visible.
- Codigo debe ser exacto.
- Si hay más de un código asociado a colores o variantes, colócalos en "variantes".
- Limpia saltos de línea.
- Precio siempre solo números.
- Empaque debe ser exactamente el texto visible (X1, PAR, X10, etc.)
- "fotos": lista que incluya SOLO el nombre de la imagen recortada.
"""

        raw = self.llm.ask_vision(prompt, img_b64)

        # Validar JSON
        try:
            data = json.loads(raw)
        except:
            data = {"error": "JSON inválido", "raw": raw}

        return self.norm.normalize(data)
