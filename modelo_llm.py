import os
import base64
from openai import OpenAI


class LLMClient:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("ERROR: Falta la variable de entorno OPENAI_API_KEY")

        self.client = OpenAI(api_key=api_key)

    def ask_vision(self, prompt, image_b64):

        # Formato correcto para OpenAI Vision (enero 2025)
        image_payload = {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{image_b64}"
            }
        }

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto en extracción estructurada de catálogos comerciales y técnicos."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        image_payload
                    ]
                }
            ],
            temperature=0
        )

        # ESTA ES LA FORMA CORRECTA (2025):
        return response.choices[0].message.content
