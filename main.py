import os

# Módulos internos del extractor
from modules.preprocessing import Preprocessor
from modules.layout_detector import LayoutDetector
from modules.table_detector import TableDetector
from modules.image_detector import ImageDetector
from modules.image_cropper import ImageCropper
from modules.ocr_reader import OCRReader
from modules.product_segmenter import ProductSegmenter
from modules.postprocessor import PostProcessor
from modules.image_assigner import ImageAssigner

# Normalización ADSI
from modules.normalizer import Normalizer
from modules.variant_builder import VariantBuilder
from modules.product_model import Product

# Validación + Corrección (Fase 6)
from modules.validator import Validator
from modules.cleaner import Cleaner

# Exportación (Fase 5)
from modules.export_manager import ExportManager

# Logging
from utils.logger import get_logger
logger = get_logger()


def run_extractor():
    logger.info("=== EXTRACTOR_V4 — Pipeline Completo Fase 1–6 ===")

    # ------------------------------------------------------------
    # Inicialización de módulos
    # ------------------------------------------------------------
    pre = Preprocessor()
    layout = LayoutDetector()
    table_det = TableDetector()
    imgdet = ImageDetector()
    cropper = ImageCropper()
    ocr = OCRReader()
    segmenter = ProductSegmenter()
    post = PostProcessor()
    assigner = ImageAssigner()

    normalizer = Normalizer()
    variant_builder = VariantBuilder()

    validator = Validator()
    cleaner = Cleaner()

    pages_dir = "input/pages/"
    pages = [p for p in os.listdir(pages_dir) if p.lower().endswith(".png")]

    all_products = []  # 🔥 Donde acumulamos todos los productos del catálogo

    # ============================================================
    # PROCESAMIENTO POR PÁGINA
    # ============================================================
    for page in pages:
        logger.info(f"Procesando página: {page}")

        img_path = os.path.join(pages_dir, page)

        # --------------------------------------------------------
        # 1 — PREPROCESAMIENTO
        # --------------------------------------------------------
        img, gray, norm = pre.process(img_path)

        # --------------------------------------------------------
        # 2 — DETECCIÓN DE LAYOUT
        # --------------------------------------------------------
        blocks = layout.detect(norm)

        # --------------------------------------------------------
        # 3 — DETECCIÓN DE IMÁGENES + CROP
        # --------------------------------------------------------
        image_blocks = imgdet.detect_images(norm)
        images = cropper.crop_blocks(img, image_blocks, page)

        # --------------------------------------------------------
        # 4 — SEGMENTACIÓN DE PRODUCTOS
        # --------------------------------------------------------
        rows = segmenter.segment_products(blocks)
        productos_detectados = []

        for fila in rows:

            y_pos = sum([b[1] for b in fila]) // len(fila)
            texto_fila = ""

            # OCR por cada bloque
            for b in fila:
                texto_fila += " " + ocr.clean_text(ocr.read_region(norm, b))

            cods = post.extract_codigos(texto_fila)
            precio = post.extract_precio(texto_fila)
            emp = post.extract_empaque(texto_fila)

            productos_detectados.append({
                "y": y_pos,
                "codigos": cods,
                "descripcion": texto_fila.strip(),
                "precio": precio,
                "empaque": emp
            })

        # --------------------------------------------------------
        # 5 — ASIGNAR IMÁGENES POR CERCANÍA
        # --------------------------------------------------------
        productos_detectados = assigner.assign(productos_detectados, images)

        # --------------------------------------------------------
        # 6 — NORMALIZACIÓN ADSI COMPLETA
        # --------------------------------------------------------
        productos_finales = []

        for prod in productos_detectados:
            for code in prod["codigos"]:

                p = Product(
                    codigo=code,
                    descripcion=prod["descripcion"],
                    precio=prod["precio"],
                    empaque=prod["empaque"],
                    imagen=prod["imagen"]
                )

                # 🔵 Normalización ADSI
                p.color = normalizer.detect_color(p.descripcion)
                p.modelo_moto = normalizer.detect_moto(p.descripcion)
                p.familia = normalizer.detect_familia(p.descripcion)
                p.subfamilia = normalizer.detect_subfamilia(p.descripcion)
                p.descripcion_tecnica, p.descripcion_marketing = \
                    normalizer.split_description(p.descripcion)

                productos_finales.append(p)

        # --------------------------------------------------------
        # 7 — VARIANTES PADRE-HIJO
        # --------------------------------------------------------
        productos_finales = variant_builder.assign_variants(productos_finales)

        logger.info(f"Productos procesados en {page}: {len(productos_finales)}")

        all_products.extend(productos_finales)

    # ============================================================
    # 8 — VALIDACIÓN + LIMPIEZA (FASE 6)
    # ============================================================
    logger.info("Ejecutando validación y limpieza…")

    report = validator.validate(all_products)
    productos_limpios = cleaner.fix(report)

    logger.info(f"Productos válidos después de limpieza: {len(productos_limpios)}")

    # ============================================================
    # 9 — EXPORTACIÓN PROFESIONAL (FASE 5)
    # ============================================================
    logger.info("Exportando archivos finales…")

    exporter = ExportManager()
    exporter.export_all(productos_limpios)

    logger.info("=== EXTRACTOR_V4 COMPLETADO ===")
    logger.info(f"Total productos exportados: {len(productos_limpios)}")


if __name__ == "__main__":
    run_extractor()
