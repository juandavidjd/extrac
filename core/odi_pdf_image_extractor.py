#!/usr/bin/env python3
"""
ODI PDF Image Extractor — Extraccion de imagenes de catalogos PDF
a resolucion profesional para Shopify.

Estandar ODI:
  - Minimo 300 DPI de extraccion
  - Canvas 2000x2000 para producto individual
  - PNG como master, JPG optimizado para upload
  - NUNCA subir imagen menor a 1600px de lado mayor

Uso:
  extractor = PdfImageExtractor()

  # Extraer todas las paginas de un PDF
  pages = extractor.extract_pages("/path/to/catalogo.pdf", dpi=300)

  # Crear canvas profesional para Shopify
  image_bytes = extractor.create_product_canvas(pages[0])

  # Validar antes de subir
  if extractor.validate_for_shopify(image_bytes):
      shopify_api.upload_image(product_id, image_bytes)

Dependencias:
  pip install pdf2image Pillow
  apt-get install -y poppler-utils
"""

import os
import io
import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger("odi.pdf_image")

# Estandar ODI de imagen
MIN_DPI = 300
CANVAS_SIZE = 2000       # px, cuadrado
MIN_UPLOAD_SIZE = 1600   # px, lado mayor
JPEG_QUALITY = 90        # calidad para Shopify
PADDING_RATIO = 0.85     # 85% del canvas = 15% padding


class PdfImageExtractor:
    """Extrae imagenes de PDF industrial a resolucion profesional."""

    def __init__(self, output_dir: str = "/opt/odi/data/image_cache"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.stats = {"pages_extracted": 0, "canvases_created": 0, "failed": 0}

    def extract_pages(self, pdf_path: str, dpi: int = MIN_DPI,
                      pages: List[int] = None,
                      output_format: str = "png") -> List[str]:
        """
        Extrae paginas de PDF como imagenes PNG a alta resolucion.

        Args:
            pdf_path: Ruta al PDF
            dpi: DPI de extraccion (minimo 300)
            pages: Lista de paginas especificas (None = todas)
            output_format: 'png' o 'jpeg'

        Returns:
            Lista de rutas a los archivos de imagen extraidos
        """
        if dpi < MIN_DPI:
            logger.warning(f"DPI {dpi} < minimo {MIN_DPI}. Usando {MIN_DPI}.")
            dpi = MIN_DPI

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            logger.error(f"PDF no encontrado: {pdf_path}")
            return []

        pdf_name = pdf_path.stem
        page_dir = self.output_dir / f"{pdf_name}_pages"
        page_dir.mkdir(exist_ok=True)

        # Intentar con pdf2image (poppler)
        try:
            from pdf2image import convert_from_path

            kwargs = {
                "dpi": dpi,
                "fmt": output_format,
                "output_folder": str(page_dir),
                "paths_only": True,
                "thread_count": 4,
                "output_file": f"{pdf_name}_page",
            }

            if pages:
                kwargs["first_page"] = min(pages)
                kwargs["last_page"] = max(pages)

            logger.info(f"Extrayendo {pdf_path.name} a {dpi} DPI...")
            result_paths = convert_from_path(str(pdf_path), **kwargs)

            self.stats["pages_extracted"] += len(result_paths)
            logger.info(
                f"✅ Extraidas {len(result_paths)} paginas de {pdf_name} "
                f"a {dpi} DPI"
            )
            return [str(p) for p in result_paths]

        except ImportError:
            logger.warning("pdf2image no disponible, usando pdftoppm")
            return self._extract_with_pdftoppm(
                str(pdf_path), page_dir, dpi, pages, output_format)
        except Exception as e:
            logger.error(f"Error extrayendo PDF: {e}")
            self.stats["failed"] += 1
            return []

    def _extract_with_pdftoppm(self, pdf_path: str, output_dir: Path,
                                dpi: int, pages: List[int],
                                output_format: str) -> List[str]:
        """Fallback: usar pdftoppm de poppler-utils."""
        fmt_flag = "-png" if output_format == "png" else "-jpeg"
        cmd = [
            "pdftoppm",
            fmt_flag,
            "-r", str(dpi),
        ]

        if pages:
            cmd.extend(["-f", str(min(pages)), "-l", str(max(pages))])

        prefix = str(output_dir / "page")
        cmd.extend([pdf_path, prefix])

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"pdftoppm fallo: {e.stderr.decode()}")
            self.stats["failed"] += 1
            return []
        except FileNotFoundError:
            logger.error("pdftoppm no instalado. Ejecutar: apt-get install poppler-utils")
            return []

        ext = "png" if output_format == "png" else "jpg"
        results = sorted(output_dir.glob(f"page-*.{ext}"))
        self.stats["pages_extracted"] += len(results)
        return [str(p) for p in results]

    def extract_embedded_images(self, pdf_path: str) -> List[Tuple[str, bytes]]:
        """
        Extrae imagenes embebidas directamente del PDF.
        Util cuando el PDF tiene fotos de productos, no diagramas.

        Returns:
            Lista de tuplas (nombre, bytes)
        """
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            images = []

            for page_num, page in enumerate(doc):
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    name = f"page{page_num+1}_img{img_index+1}.{image_ext}"

                    # Verificar tamano minimo
                    if len(image_bytes) > 10000:  # >10KB
                        images.append((name, image_bytes))

            logger.info(f"Extraidas {len(images)} imagenes embebidas de {pdf_path}")
            return images

        except ImportError:
            logger.warning("PyMuPDF no disponible para extraccion de imagenes embebidas")
            return []
        except Exception as e:
            logger.error(f"Error extrayendo imagenes embebidas: {e}")
            return []

    def create_product_canvas(self, image_path: str,
                               canvas_size: int = CANVAS_SIZE,
                               padding_ratio: float = PADDING_RATIO) -> bytes:
        """
        Crea canvas cuadrado con imagen centrada y padding blanco.

        NO recorta. Centra proporcionalmente.
        Esto evita que Shopify haga crop agresivo.

        Args:
            image_path: Ruta a la imagen fuente
            canvas_size: Tamano del canvas cuadrado (default 2000)
            padding_ratio: Ratio de imagen vs padding (0.85 = 15% padding)

        Returns:
            bytes de la imagen JPEG optimizada
        """
        from PIL import Image

        img = Image.open(image_path)

        # Convertir a RGB si es necesario (para JPEG)
        if img.mode in ('RGBA', 'P', 'LA'):
            # Crear fondo blanco para transparencia
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Crear canvas blanco
        canvas = Image.new("RGB", (canvas_size, canvas_size), (255, 255, 255))

        # Escalar imagen para que quepa con padding
        target_size = int(canvas_size * padding_ratio)
        ratio = min(target_size / img.width, target_size / img.height)
        new_width = int(img.width * ratio)
        new_height = int(img.height * ratio)

        # Usar LANCZOS para mejor calidad de reescalado
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)

        # Centrar en canvas
        x = (canvas_size - new_width) // 2
        y = (canvas_size - new_height) // 2

        canvas.paste(img_resized, (x, y))

        # Exportar como bytes JPEG
        buf = io.BytesIO()
        canvas.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)

        self.stats["canvases_created"] += 1
        return buf.getvalue()

    def crop_product_from_page(self, page_path: str,
                                crop_box: Tuple[int, int, int, int]) -> bytes:
        """
        Recorta una region especifica de una pagina y crea canvas.

        Args:
            page_path: Ruta a la imagen de pagina
            crop_box: (left, top, right, bottom) en pixeles

        Returns:
            bytes de la imagen JPEG con canvas
        """
        from PIL import Image

        img = Image.open(page_path)
        cropped = img.crop(crop_box)

        # Guardar temporalmente y crear canvas
        temp_path = self.output_dir / "temp_crop.png"
        cropped.save(temp_path)

        result = self.create_product_canvas(str(temp_path))

        # Limpiar temp
        temp_path.unlink()

        return result

    def auto_crop_products(self, page_path: str,
                            grid: Tuple[int, int] = (2, 3)) -> List[bytes]:
        """
        Divide una pagina en grid y extrae cada celda como producto.
        Util para catalogos con productos en grid regular.

        Args:
            page_path: Ruta a la imagen de pagina
            grid: (columnas, filas)

        Returns:
            Lista de bytes, una por cada celda del grid
        """
        from PIL import Image

        img = Image.open(page_path)
        cols, rows = grid

        cell_width = img.width // cols
        cell_height = img.height // rows

        products = []

        for row in range(rows):
            for col in range(cols):
                left = col * cell_width
                top = row * cell_height
                right = left + cell_width
                bottom = top + cell_height

                # Agregar margen interior
                margin = 20
                crop_box = (
                    left + margin,
                    top + margin,
                    right - margin,
                    bottom - margin
                )

                product_bytes = self.crop_product_from_page(page_path, crop_box)
                products.append(product_bytes)

        return products

    def validate_for_shopify(self, image_bytes: bytes) -> bool:
        """Verifica que la imagen cumple estandar ODI para Shopify."""
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))

        width, height = img.size
        max_side = max(width, height)

        if max_side < MIN_UPLOAD_SIZE:
            logger.warning(
                f"Imagen {width}x{height} < minimo {MIN_UPLOAD_SIZE}px"
            )
            return False

        # Verificar tamano en bytes (Shopify max 20MB)
        if len(image_bytes) > 20 * 1024 * 1024:
            logger.warning(f"Imagen {len(image_bytes)//1024//1024}MB > 20MB max")
            return False

        return True

    def get_page_info(self, pdf_path: str) -> dict:
        """Obtiene informacion del PDF sin extraer."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)
            info = {
                "pages": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "page_size": None,
            }

            if len(doc) > 0:
                page = doc[0]
                rect = page.rect
                info["page_size"] = f"{int(rect.width)}x{int(rect.height)}"

            return info

        except ImportError:
            # Fallback con pdfinfo
            try:
                result = subprocess.run(
                    ["pdfinfo", pdf_path],
                    capture_output=True, text=True
                )
                lines = result.stdout.split("\n")
                info = {"pages": 0}
                for line in lines:
                    if line.startswith("Pages:"):
                        info["pages"] = int(line.split(":")[1].strip())
                return info
            except:
                return {"pages": 0, "error": "No se pudo leer info del PDF"}

    def get_stats(self) -> dict:
        """Retorna estadisticas de extraccion."""
        return {
            **self.stats,
            "output_dir": str(self.output_dir),
            "cache_size_mb": sum(
                f.stat().st_size for f in self.output_dir.rglob("*") if f.is_file()
            ) // (1024 * 1024)
        }


# ─────────────────────────────────────────────────────────
# TEST STANDALONE
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    extractor = PdfImageExtractor()

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]

        print(f"=== PDF Info ===")
        info = extractor.get_page_info(pdf_path)
        print(f"Paginas: {info.get('pages', '?')}")
        print(f"Tamano: {info.get('page_size', '?')}")

        print(f"\n=== Extrayendo a {MIN_DPI} DPI ===")
        pages = extractor.extract_pages(pdf_path, dpi=MIN_DPI)

        if pages:
            print(f"Extraidas {len(pages)} paginas")

            # Test canvas con primera pagina
            print(f"\n=== Creando canvas {CANVAS_SIZE}x{CANVAS_SIZE} ===")
            canvas_bytes = extractor.create_product_canvas(pages[0])
            print(f"Canvas: {len(canvas_bytes)//1024}KB")

            # Validar
            if extractor.validate_for_shopify(canvas_bytes):
                print("✅ Imagen valida para Shopify")
            else:
                print("❌ Imagen NO valida para Shopify")

            # Guardar test
            test_path = extractor.output_dir / "test_canvas.jpg"
            test_path.write_bytes(canvas_bytes)
            print(f"Guardado en: {test_path}")

        print(f"\n=== Stats ===")
        print(extractor.get_stats())

    else:
        print("Usage: python odi_pdf_image_extractor.py <pdf_path>")
        print(f"\nEstandar ODI:")
        print(f"  - DPI minimo: {MIN_DPI}")
        print(f"  - Canvas: {CANVAS_SIZE}x{CANVAS_SIZE}")
        print(f"  - Upload minimo: {MIN_UPLOAD_SIZE}px")
        print(f"  - JPEG quality: {JPEG_QUALITY}")
