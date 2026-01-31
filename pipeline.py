import os
import json
import time
from modules.parser_llm import LLMParser
from openai import RateLimitError


class ExtractionPipeline:
    def __init__(self):
        self.parser = LLMParser()

    def process_folder(self, folder_path):
        productos = []
        files = sorted(os.listdir(folder_path))

        for fname in files:
            if not fname.lower().endswith((".png", ".jpg", ".jpeg")):
                continue

            img_path = os.path.join(folder_path, fname)
            print(f"[LLM] Procesando {fname}...")

            intentos = 0

            while intentos < 4:
                try:
                    result = self.parser.parse_row(img_path)
                    productos.append(result)
                    time.sleep(0.35)  # throttle preventivo
                    break

                except RateLimitError:
                    intentos += 1
                    wait = 0.7 * intentos
                    print(f"[WAIT] Rate limit alcanzado. Reintentando en {wait} segundos...")
                    time.sleep(wait)

                except Exception as e:
                    print(f"[ERROR] Falló {fname}: {e}")
                    break

        return productos

    def save_as_json(self, productos, outfile):
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(productos, f, indent=4, ensure_ascii=False)
