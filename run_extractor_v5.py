import os
import glob
import traceback

from modules.table_detector_cv import OpenCVTableDetector
from modules.table_detector_lp import LayoutParserDetector
from modules.table_detector_hybrid import HybridDetector
from modules.page_segmenter import PageSegmenter
from modules.cell_extractor import CellExtractor
from modules.vision_extractor import VisionExtractor
from modules.product_builder import ProductBuilder
from modules.catalog_integrator import CatalogIntegrator
from modules.exporter import Exporter


# --------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PAGES_DIR = os.path.join(BASE_DIR, "pages")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SEGMENTS_DIR = os.path.join(OUTPUT_DIR, "segments")
CELLS_DIR = os.path.join(OUTPUT_DIR, "cells")
CATALOG_DIR = os.path.join(OUTPUT_DIR, "catalog")

os.makedirs(SEGMENTS_DIR, exist_ok=True)
os.makedirs(CELLS_DIR, exist_ok=True)
os.makedirs(CATALOG_DIR, exist_ok=True)


# --------------------------------------------------------------
# SELECCIONAR DETECTOR
# --------------------------------------------------------------
def select_detector():
    """
    Selección automática:
    - Si LP falla → usar OpenCV
    - Si imagen tiene tablas complejas → usar híbrido
    """

    # Por ahora usar híbrido en todos los casos
    return HybridDetector(
        cv_detector=OpenCVTableDetector(),
        lp_detector=LayoutParserDetector()
    )


# --------------------------------------------------------------
# PIPELINE PRINCIPAL
# --------------------------------------------------------------

def main():
    print("\n===================================================")
    print("            EXTRACTOR ADSI V5 – PIPELINE")
    print("===================================================")
    print("Carpeta de páginas:", PAGES_DIR)
    print("---------------------------------------------------\n")

    # 1) Instanciar módulos
    detector = select_detector()
    segmenter = PageSegmenter(detector)
    cell_extractor = CellExtractor(margin=4)
    vision = VisionExtractor(model="gpt-4o-mini")
    builder = ProductBuilder()
    integrator = CatalogIntegrator()
    exporter = Exporter(output_dir=CATALOG_DIR)

    # 2) Obtener todas las páginas
    pages = sorted(glob.glob(os.path.join(PAGES_DIR, "*.png")))
    print(f"Total páginas detectadas: {len(pages)}\n")

    # 3) Procesar páginas una por una
    for idx, page_path in enumerate(pages, 1):
        print(f"\n📝 [PÁGINA {idx}/{len(pages)}] {os.path.basename(page_path)}")
        print("---------------------------------------------------")

        try:
            # --- SEGMENTACIÓN DE LA PÁGINA ---
            result = segmenter.segment_page(page_path)

            json_data = result["json"]
            blocks = result["blocks"]
            processed_page_path = result["processed_path"]

            # Guardar JSON de la página
            json_filename = os.path.splitext(os.path.basename(page_path))[0] + ".json"
            json_output_path = os.path.join(SEGMENTS_DIR, json_filename)
            segmenter.save_json(json_data, json_output_path)

            print(f"✔ Segmentación completada: {json_output_path}")

            # --- RECORTE DE CELDAS ---
            print("Recortando celdas...")
            cell_files = cell_extractor.extract_cells(
                processed_page_path,
                blocks,
                output_dir=os.path.join(CELLS_DIR)
            )
            print(f"✔ {len(cell_files)} recortes generados")

            # --- PROCESAR CADA RECORTE CON LLM VISION ---
            for cell in blocks:
                img_file = cell.get("file")
                if not img_file:
                    continue

                print(f"[LLM] Analizando {os.path.basename(img_file)}...")

                parsed = vision.process_cell(img_file)
                if parsed:
                    builder.add_fragment(parsed)

        except Exception as e:
            print("❌ ERROR en esta página")
            traceback.print_exc()
            continue

    # ----------------------------------------------------------
    # 4) CONSTRUIR PRODUCTOS FINALES
    # ----------------------------------------------------------
    print("\n🔧 Construyendo productos unificados...")
    products = builder.build()
    print(f"✔ Total productos reconstruidos: {len(products)}")

    # ----------------------------------------------------------
    # 5) INTEGRAR EN CATÁLOGO
    # ----------------------------------------------------------
    print("\n📚 Integrando catálogo maestro...")
    df = integrator.integrate(products)
    print(f"✔ Catálogo listo: {len(df)} filas")

    # ----------------------------------------------------------
    # 6) EXPORTAR RESULTADOS
    # ----------------------------------------------------------
    print("\n📦 Exportando resultados...")
    exporter.export_all(df)

    print("\n🎉 EXTRACCIÓN COMPLETA — EXTRACTOR ADSI V5\n")


# --------------------------------------------------------------
# EJECUTAR PIPELINE
# --------------------------------------------------------------

if __name__ == "__main__":
    main()
