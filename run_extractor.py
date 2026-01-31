import os
from modules.pipeline import ExtractionPipeline


def main():
    BASE = os.path.dirname(os.path.abspath(__file__))
    CROP_DIR = os.path.join(BASE, "output", "images", "crops")
    OUT_JSON = os.path.join(BASE, "output", "productos_llm.json")

    print("=== EXTRACTOR ADSI V5 – FASE 8 ===")
    print(f"Usando carpeta: {CROP_DIR}")

    if not os.path.exists(CROP_DIR):
        print("[ERROR] No existe la carpeta de recortes.")
        return

    pipeline = ExtractionPipeline()

    print("[1] Procesando imágenes...")
    productos = pipeline.process_folder(CROP_DIR)

    print(f"[2] Total procesados: {len(productos)}")

    print(f"[3] Guardando JSON en: {OUT_JSON}")
    pipeline.save_as_json(productos, OUT_JSON)

    print("=== FASE 8 COMPLETADA ===")


if __name__ == "__main__":
    main()
