#!/usr/bin/env python3
"""
ODI Image Resolver - Descarga imagenes de CUALQUIER fuente.

Fuentes soportadas:
  - Google Drive (sharing links)
  - Dropbox (sharing links)
  - URLs directas (jpg, png, webp)
  - Archivos locales (ruta en disco)
  - CDN de proveedor (URLs embebidas en CSV)

Uso dentro del pipeline:
  resolver = ImageResolver(cache_dir="/opt/odi/data/image_cache")
  image_bytes = resolver.resolve("https://drive.google.com/file/d/XXXX/view?usp=sharing")
  if image_bytes:
      shopify_uploader.upload_image(product_id, image_bytes)

Integracion en pipeline (paso de imagenes):
  El PipelineExecutor llama a resolver.resolve() para cada producto
  que tenga campo 'image_url' en los datos extraidos del CSV/Excel.
"""

import os
import re
import time
import hashlib
import logging
import requests
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger("odi.image_resolver")


class ImageResolver:
    """
    Resuelve URLs de imagenes de multiples fuentes a bytes descargables.

    Caracteristicas:
    - Deteccion automatica de fuente (Google Drive, Dropbox, directa, local)
    - Cache local para no re-descargar (idempotente)
    - Rate limiting configurable
    - Validacion de formato (solo jpg, png, webp, gif)
    - Retry con backoff exponencial
    - Logging de cada descarga para trazabilidad
    """

    # Tamano maximo de imagen aceptado (10 MB)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024

    # Formatos de imagen validos (magic bytes)
    MAGIC_BYTES = {
        b'\xff\xd8\xff': 'jpeg',
        b'\x89PNG': 'png',
        b'RIFF': 'webp',  # WebP starts with RIFF
        b'GIF8': 'gif',
    }

    # Rate limit: segundos entre descargas
    RATE_LIMIT = 0.3  # ~3 descargas por segundo

    def __init__(self, cache_dir: str = "/opt/odi/data/image_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ODI-ImageResolver/1.0"
        })
        self._last_request_time = 0
        self.stats = {"resolved": 0, "cached": 0, "failed": 0, "skipped": 0}

    # ─────────────────────────────────────────────────────────
    # METODO PRINCIPAL - Punto de entrada unico
    # ─────────────────────────────────────────────────────────

    def resolve(self, image_ref: str, product_sku: str = "") -> Optional[bytes]:
        """
        Resuelve cualquier referencia de imagen a bytes.

        Args:
            image_ref: URL, ruta local, o referencia de imagen
            product_sku: SKU del producto (para nombrar cache)

        Returns:
            bytes de la imagen, o None si falla
        """
        if not image_ref or not image_ref.strip():
            self.stats["skipped"] += 1
            return None

        image_ref = image_ref.strip()

        # 1. Verificar cache
        cache_key = self._cache_key(image_ref)
        cached = self._get_from_cache(cache_key)
        if cached:
            self.stats["cached"] += 1
            logger.debug(f"Cache hit: {product_sku or cache_key[:12]}")
            return cached

        # 2. Detectar fuente y resolver
        source_type, download_url = self._detect_and_convert(image_ref)

        if not download_url:
            logger.warning(f"No se pudo resolver: {image_ref[:80]}")
            self.stats["failed"] += 1
            return None

        # 3. Descargar
        image_bytes = self._download(download_url, source_type)

        if image_bytes:
            # 4. Validar que es imagen real
            if self._validate_image(image_bytes):
                self._save_to_cache(cache_key, image_bytes)
                self.stats["resolved"] += 1
                logger.info(
                    f"OK {source_type}: {product_sku or cache_key[:12]} "
                    f"({len(image_bytes)//1024}KB)"
                )
                return image_bytes
            else:
                logger.warning(
                    f"No es imagen valida: {product_sku} "
                    f"(fuente: {source_type})"
                )
                self.stats["failed"] += 1
                return None

        self.stats["failed"] += 1
        return None

    # ─────────────────────────────────────────────────────────
    # DETECCION DE FUENTE
    # ─────────────────────────────────────────────────────────

    def _detect_and_convert(self, ref: str) -> Tuple[str, Optional[str]]:
        """
        Detecta el tipo de fuente y convierte a URL descargable.

        Returns:
            (tipo_fuente, url_descargable) o (tipo, None) si no soportado
        """
        # Archivo local
        if os.path.isfile(ref):
            return ("local", ref)

        # Google Drive
        if "drive.google.com" in ref:
            url = self._convert_google_drive(ref)
            return ("google_drive", url)

        # Dropbox
        if "dropbox.com" in ref:
            url = self._convert_dropbox(ref)
            return ("dropbox", url)

        # OneDrive
        if "1drv.ms" in ref or "onedrive.live.com" in ref:
            url = self._convert_onedrive(ref)
            return ("onedrive", url)

        # URL directa (termina en extension de imagen o es URL http)
        if ref.startswith(("http://", "https://")):
            return ("direct_url", ref)

        # Ruta que parece archivo pero no existe
        if "/" in ref or "\\" in ref:
            logger.warning(f"Archivo local no encontrado: {ref}")
            return ("local_missing", None)

        return ("unknown", None)

    # ─────────────────────────────────────────────────────────
    # CONVERTIDORES POR FUENTE
    # ─────────────────────────────────────────────────────────

    def _convert_google_drive(self, url: str) -> Optional[str]:
        """
        Convierte URL de Google Drive a URL de descarga directa.

        Soporta:
        - https://drive.google.com/file/d/FILE_ID/view?usp=sharing
        - https://drive.google.com/open?id=FILE_ID
        - https://drive.google.com/uc?id=FILE_ID
        """
        file_id = None

        # Patron: /file/d/{FILE_ID}/
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)

        # Patron: ?id={FILE_ID}
        if not file_id:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            file_id = qs.get('id', [None])[0]

        if file_id:
            # URL de descarga directa de Google Drive
            return f"https://drive.google.com/uc?export=download&id={file_id}"

        logger.warning(f"No se pudo extraer file_id de Google Drive: {url[:80]}")
        return None

    def _convert_dropbox(self, url: str) -> Optional[str]:
        """
        Convierte URL de Dropbox a URL de descarga directa.
        Cambia ?dl=0 por ?dl=1 o agrega ?raw=1
        """
        if "?dl=0" in url:
            return url.replace("?dl=0", "?dl=1")
        elif "?" in url:
            return url + "&raw=1"
        else:
            return url + "?raw=1"

    def _convert_onedrive(self, url: str) -> Optional[str]:
        """
        Convierte URL de OneDrive a URL de descarga directa.
        Reemplaza 'redir' por 'download' en el path.
        """
        if "1drv.ms" in url:
            # Short link - seguir redirect
            return url  # Se resolvera en _download via redirects
        return url.replace("redir", "download")

    # ─────────────────────────────────────────────────────────
    # DESCARGA
    # ─────────────────────────────────────────────────────────

    def _download(self, url_or_path: str, source_type: str,
                  max_retries: int = 3) -> Optional[bytes]:
        """
        Descarga imagen con retry y rate limiting.
        Para archivos locales, lee directamente.
        """
        # Archivo local
        if source_type == "local":
            try:
                with open(url_or_path, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error leyendo archivo local: {e}")
                return None

        # Rate limiting
        self._rate_limit()

        # Descarga HTTP con retry
        for attempt in range(max_retries):
            try:
                resp = self.session.get(
                    url_or_path,
                    timeout=30,
                    allow_redirects=True,
                    stream=True
                )

                if resp.status_code == 200:
                    content = resp.content

                    # Verificar tamano
                    if len(content) > self.MAX_IMAGE_SIZE:
                        logger.warning(
                            f"Imagen muy grande: {len(content)//1024//1024}MB "
                            f"(max {self.MAX_IMAGE_SIZE//1024//1024}MB)"
                        )
                        return None

                    # Google Drive: detectar pagina de confirmacion
                    # (archivos grandes requieren confirmacion)
                    if source_type == "google_drive" and b"</html>" in content[:1000]:
                        confirm_url = self._handle_gdrive_confirmation(
                            content, url_or_path)
                        if confirm_url:
                            self._rate_limit()
                            resp2 = self.session.get(
                                confirm_url, timeout=30, allow_redirects=True)
                            if resp2.status_code == 200:
                                return resp2.content
                        return None

                    return content

                elif resp.status_code == 404:
                    logger.warning(f"404 Not Found: {url_or_path[:80]}")
                    return None

                elif resp.status_code == 429:
                    # Rate limited - esperar mas
                    wait = 2 ** (attempt + 2)
                    logger.info(f"Rate limited, esperando {wait}s...")
                    time.sleep(wait)
                    continue

                else:
                    logger.warning(
                        f"HTTP {resp.status_code} en intento {attempt+1}: "
                        f"{url_or_path[:80]}"
                    )

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout intento {attempt+1}: {url_or_path[:60]}")
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error intento {attempt+1}: {e}")
            except Exception as e:
                logger.error(f"Error inesperado: {e}")
                return None

            # Backoff exponencial
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

        return None

    def _handle_gdrive_confirmation(self, html_content: bytes,
                                     original_url: str) -> Optional[str]:
        """
        Google Drive muestra pagina de confirmacion para archivos grandes.
        Extrae el link de confirmacion.
        """
        try:
            html = html_content.decode('utf-8', errors='ignore')
            # Buscar el confirm token
            match = re.search(r'confirm=([a-zA-Z0-9_-]+)', html)
            if match:
                token = match.group(1)
                return f"{original_url}&confirm={token}"

            # Alternativa: buscar link directo en el HTML
            match = re.search(r'href="(/uc\?export=download[^"]+)"', html)
            if match:
                return f"https://drive.google.com{match.group(1)}"
        except Exception:
            pass
        return None

    # ─────────────────────────────────────────────────────────
    # VALIDACION
    # ─────────────────────────────────────────────────────────

    def _validate_image(self, data: bytes) -> bool:
        """Verifica que los bytes son una imagen real (magic bytes)."""
        if len(data) < 8:
            return False
        for magic, fmt in self.MAGIC_BYTES.items():
            if data[:len(magic)] == magic:
                return True
        return False

    # ─────────────────────────────────────────────────────────
    # CACHE
    # ─────────────────────────────────────────────────────────

    def _cache_key(self, ref: str) -> str:
        """Genera key de cache basado en hash de la referencia."""
        return hashlib.sha256(ref.encode()).hexdigest()[:16]

    def _get_from_cache(self, key: str) -> Optional[bytes]:
        """Lee imagen del cache local."""
        for ext in ["jpg", "png", "webp", "gif", "jpeg"]:
            path = self.cache_dir / f"{key}.{ext}"
            if path.exists():
                return path.read_bytes()
        return None

    def _save_to_cache(self, key: str, data: bytes):
        """Guarda imagen en cache local."""
        # Detectar formato por magic bytes
        ext = "jpg"  # default
        for magic, fmt in self.MAGIC_BYTES.items():
            if data[:len(magic)] == magic:
                ext = fmt
                break

        path = self.cache_dir / f"{key}.{ext}"
        path.write_bytes(data)

    # ─────────────────────────────────────────────────────────
    # UTILIDADES
    # ─────────────────────────────────────────────────────────

    def _rate_limit(self):
        """Aplica rate limiting entre requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT:
            time.sleep(self.RATE_LIMIT - elapsed)
        self._last_request_time = time.time()

    def get_stats(self) -> dict:
        """Retorna estadisticas de resolucion."""
        return {
            **self.stats,
            "total": sum(self.stats.values()),
            "cache_dir": str(self.cache_dir),
            "cache_files": len(list(self.cache_dir.glob("*")))
        }

    def clear_cache(self):
        """Limpia el cache de imagenes."""
        for f in self.cache_dir.glob("*"):
            f.unlink()
        logger.info("Cache de imagenes limpiado")


# ─────────────────────────────────────────────────────────
# TEST STANDALONE
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    resolver = ImageResolver()

    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"Testing URL: {url}")
        img = resolver.resolve(url, product_sku="test")
        if img:
            print(f"SUCCESS: {len(img)//1024}KB downloaded")
        else:
            print("FAILED")
    else:
        print("Usage: python odi_image_resolver.py <url>")
        print("Stats:", resolver.get_stats())
