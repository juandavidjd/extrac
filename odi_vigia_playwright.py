#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════════
                        ODI VIGIA PLAYWRIGHT v1.0
              Sistema de Monitoreo de Competencia y Mercado
══════════════════════════════════════════════════════════════════════════════════

PROPOSITO:
    Vigia es el "ojo de mercado" de ODI. Monitorea sitios de competencia y
    marketplaces para extraer:
    - Precios de competidores
    - Nuevos productos
    - Cambios de inventario
    - Tendencias de mercado

ARQUITECTURA:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         VIGIA PLAYWRIGHT                                │
    ├─────────────────────────────────────────────────────────────────────────┤
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌────────────┐  │
    │  │ Competitor  │   │ Marketplace │   │   Price     │   │  Alertas   │  │
    │  │ Scraper     │   │ Monitor     │   │ Comparator  │   │  Engine    │  │
    │  └─────────────┘   └─────────────┘   └─────────────┘   └────────────┘  │
    │         │                 │                 │                │          │
    │         └─────────────────┴─────────────────┴────────────────┘          │
    │                                   │                                     │
    │                          ┌────────┴────────┐                            │
    │                          │  Event Emitter  │                            │
    │                          │  (Tony narra)   │                            │
    │                          └─────────────────┘                            │
    └─────────────────────────────────────────────────────────────────────────┘

EVENTOS QUE EMITE:
    - VIGIA_SCAN_START      : Inicio de escaneo
    - VIGIA_COMPETITOR_FOUND: Competidor detectado
    - VIGIA_PRICE_CHANGE    : Cambio de precio detectado
    - VIGIA_NEW_PRODUCT     : Nuevo producto en mercado
    - VIGIA_STOCK_ALERT     : Alerta de inventario
    - VIGIA_SCAN_COMPLETE   : Escaneo completado

INSTALACION:
    pip install playwright pandas
    playwright install chromium

AUTOR: ODI Team
VERSION: 1.0 (Skeleton)
══════════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import re
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod

# Verificar Playwright
try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright no instalado: pip install playwright && playwright install chromium")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Event Emitter (importar si existe)
try:
    from odi_event_emitter import ODIEventEmitter, EventType
    EMITTER_AVAILABLE = True
except ImportError:
    EMITTER_AVAILABLE = False


# ============================================================================
# CONFIGURACION
# ============================================================================

VERSION = "1.0"
SCRIPT_NAME = "ODI Vigia Playwright"

# Configuracion de scraping
DEFAULT_TIMEOUT = 30000  # ms
DEFAULT_DELAY = 2000     # ms entre requests
MAX_RETRIES = 3

# Directorios
OUTPUT_DIR = os.getenv("VIGIA_OUTPUT_DIR", "/tmp/vigia_output")
SCREENSHOTS_DIR = os.path.join(OUTPUT_DIR, "screenshots")
CACHE_DIR = os.path.join(OUTPUT_DIR, "cache")


# ============================================================================
# MODELOS DE DATOS
# ============================================================================

@dataclass
class CompetitorProduct:
    """Producto detectado en competidor."""
    source: str = ""          # URL o nombre del competidor
    sku: str = ""
    name: str = ""
    price: float = 0.0
    original_price: float = 0.0  # Precio anterior (si hay descuento)
    currency: str = "COP"
    category: str = ""
    brand: str = ""
    availability: str = ""    # "in_stock", "out_of_stock", "limited"
    url: str = ""
    image_url: str = ""
    scraped_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PriceAlert:
    """Alerta de cambio de precio."""
    product_sku: str
    competitor: str
    old_price: float
    new_price: float
    change_percent: float
    alert_type: str  # "price_drop", "price_increase", "new_product"
    timestamp: str = ""


@dataclass
class ScanResult:
    """Resultado de un escaneo."""
    competitor: str
    products_found: int = 0
    new_products: int = 0
    price_changes: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    timestamp: str = ""


# ============================================================================
# COMPETIDORES CONFIGURADOS
# ============================================================================

COMPETITORS = {
    # Competidores directos SRM (motos)
    "mercadolibre_motos": {
        "name": "MercadoLibre Motos",
        "base_url": "https://listado.mercadolibre.com.co/repuestos-motos",
        "type": "marketplace",
        "selectors": {
            "product_card": ".ui-search-result",
            "title": ".ui-search-item__title",
            "price": ".price-tag-fraction",
            "link": ".ui-search-link",
            "image": ".ui-search-result-image__element"
        },
        "pagination": ".andes-pagination__link"
    },

    "linio_motos": {
        "name": "Linio Repuestos Motos",
        "base_url": "https://www.linio.com.co/c/repuestos-motos",
        "type": "marketplace",
        "selectors": {
            "product_card": ".catalogue-product",
            "title": ".product-name",
            "price": ".price-main-md",
            "link": "a.product-card",
            "image": ".product-image img"
        }
    },

    "exito_motos": {
        "name": "Exito Motos",
        "base_url": "https://www.exito.com/motos",
        "type": "retail",
        "selectors": {
            "product_card": ".product-card",
            "title": ".product-card__name",
            "price": ".product-card__price",
            "link": ".product-card__link",
            "image": ".product-card__image img"
        }
    },

    # Competidores especificos de autopartes
    "auteco": {
        "name": "Auteco Mobility",
        "base_url": "https://www.auteco.com.co/repuestos",
        "type": "oem",
        "selectors": {
            "product_card": ".product-item",
            "title": ".product-item-name",
            "price": ".price",
            "link": ".product-item-link"
        }
    },

    # Placeholder para competidores locales
    "competitor_local_1": {
        "name": "Competidor Local 1",
        "base_url": "",  # Configurar
        "type": "local",
        "selectors": {}
    }
}


# ============================================================================
# SCRAPER BASE
# ============================================================================

class BaseScraper(ABC):
    """Clase base para scrapers de competidores."""

    def __init__(self, competitor_id: str, config: dict):
        self.competitor_id = competitor_id
        self.config = config
        self.name = config.get("name", competitor_id)
        self.base_url = config.get("base_url", "")
        self.selectors = config.get("selectors", {})
        self.emitter = ODIEventEmitter(source="vigia") if EMITTER_AVAILABLE else None

    @abstractmethod
    async def scrape(self, page: Page, search_term: str = None) -> List[CompetitorProduct]:
        """Ejecuta el scraping. Implementar en subclases."""
        pass

    async def _safe_get_text(self, page: Page, selector: str) -> str:
        """Obtiene texto de forma segura."""
        try:
            element = await page.query_selector(selector)
            if element:
                return (await element.text_content() or "").strip()
        except:
            pass
        return ""

    async def _safe_get_attr(self, page: Page, selector: str, attr: str) -> str:
        """Obtiene atributo de forma segura."""
        try:
            element = await page.query_selector(selector)
            if element:
                return await element.get_attribute(attr) or ""
        except:
            pass
        return ""

    def _parse_price(self, price_text: str) -> float:
        """Parsea precio de texto a float."""
        if not price_text:
            return 0.0
        # Remover simbolos de moneda y separadores
        cleaned = re.sub(r'[^\d.,]', '', price_text)
        # Manejar formato colombiano (1.234.567 o 1,234,567)
        if '.' in cleaned and ',' in cleaned:
            # Determinar cual es separador de miles
            if cleaned.rindex('.') > cleaned.rindex(','):
                cleaned = cleaned.replace(',', '')
            else:
                cleaned = cleaned.replace('.', '').replace(',', '.')
        elif '.' in cleaned and cleaned.count('.') > 1:
            cleaned = cleaned.replace('.', '')
        elif ',' in cleaned:
            cleaned = cleaned.replace(',', '.')
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _emit(self, event_type: str, data: dict):
        """Emite evento si el emitter esta disponible."""
        if self.emitter:
            self.emitter.emit(event_type, data)


# ============================================================================
# SCRAPER MERCADOLIBRE
# ============================================================================

class MercadoLibreScraper(BaseScraper):
    """Scraper especializado para MercadoLibre."""

    async def scrape(self, page: Page, search_term: str = None) -> List[CompetitorProduct]:
        products = []

        url = self.base_url
        if search_term:
            url = f"https://listado.mercadolibre.com.co/{search_term.replace(' ', '-')}"

        self._emit("VIGIA_SCAN_START", {
            "competitor": self.name,
            "url": url
        })

        try:
            await page.goto(url, timeout=DEFAULT_TIMEOUT)
            await page.wait_for_selector(self.selectors["product_card"], timeout=10000)

            # Obtener todos los productos
            cards = await page.query_selector_all(self.selectors["product_card"])

            for card in cards[:50]:  # Limitar a 50 productos
                try:
                    title_el = await card.query_selector(self.selectors["title"])
                    price_el = await card.query_selector(self.selectors["price"])
                    link_el = await card.query_selector(self.selectors["link"])
                    img_el = await card.query_selector(self.selectors["image"])

                    title = await title_el.text_content() if title_el else ""
                    price_text = await price_el.text_content() if price_el else "0"
                    link = await link_el.get_attribute("href") if link_el else ""
                    img = await img_el.get_attribute("src") if img_el else ""

                    product = CompetitorProduct(
                        source=self.name,
                        name=title.strip(),
                        price=self._parse_price(price_text),
                        url=link,
                        image_url=img,
                        scraped_at=datetime.now().isoformat()
                    )

                    if product.name and product.price > 0:
                        products.append(product)

                except Exception as e:
                    continue

        except Exception as e:
            self._emit("VIGIA_ERROR", {
                "competitor": self.name,
                "error": str(e)
            })

        self._emit("VIGIA_SCAN_COMPLETE", {
            "competitor": self.name,
            "products_found": len(products)
        })

        return products


# ============================================================================
# SCRAPER GENERICO
# ============================================================================

class GenericScraper(BaseScraper):
    """Scraper generico configurable por selectores."""

    async def scrape(self, page: Page, search_term: str = None) -> List[CompetitorProduct]:
        products = []

        if not self.base_url:
            return products

        self._emit("VIGIA_SCAN_START", {
            "competitor": self.name,
            "url": self.base_url
        })

        try:
            await page.goto(self.base_url, timeout=DEFAULT_TIMEOUT)

            card_selector = self.selectors.get("product_card")
            if not card_selector:
                return products

            await page.wait_for_selector(card_selector, timeout=10000)
            cards = await page.query_selector_all(card_selector)

            for card in cards[:50]:
                try:
                    title = ""
                    price = 0.0
                    link = ""
                    img = ""

                    if self.selectors.get("title"):
                        title_el = await card.query_selector(self.selectors["title"])
                        if title_el:
                            title = (await title_el.text_content() or "").strip()

                    if self.selectors.get("price"):
                        price_el = await card.query_selector(self.selectors["price"])
                        if price_el:
                            price = self._parse_price(await price_el.text_content() or "0")

                    if self.selectors.get("link"):
                        link_el = await card.query_selector(self.selectors["link"])
                        if link_el:
                            link = await link_el.get_attribute("href") or ""

                    if self.selectors.get("image"):
                        img_el = await card.query_selector(self.selectors["image"])
                        if img_el:
                            img = await img_el.get_attribute("src") or ""

                    if title and price > 0:
                        products.append(CompetitorProduct(
                            source=self.name,
                            name=title,
                            price=price,
                            url=link,
                            image_url=img,
                            scraped_at=datetime.now().isoformat()
                        ))

                except:
                    continue

        except Exception as e:
            self._emit("VIGIA_ERROR", {
                "competitor": self.name,
                "error": str(e)
            })

        self._emit("VIGIA_SCAN_COMPLETE", {
            "competitor": self.name,
            "products_found": len(products)
        })

        return products


# ============================================================================
# COMPARADOR DE PRECIOS
# ============================================================================

class PriceComparator:
    """Compara precios entre escaneos y genera alertas."""

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_file = os.path.join(cache_dir, "price_history.json")
        self.history = self._load_history()

    def _load_history(self) -> dict:
        """Carga historial de precios."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_history(self):
        """Guarda historial de precios."""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def compare(self, products: List[CompetitorProduct]) -> List[PriceAlert]:
        """Compara productos con historial y genera alertas."""
        alerts = []

        for product in products:
            key = f"{product.source}:{product.name}"

            if key in self.history:
                old_price = self.history[key]["price"]
                if old_price != product.price and old_price > 0:
                    change_percent = ((product.price - old_price) / old_price) * 100

                    alert_type = "price_drop" if change_percent < 0 else "price_increase"

                    # Solo alertar si cambio es significativo (>5%)
                    if abs(change_percent) > 5:
                        alerts.append(PriceAlert(
                            product_sku=product.sku or product.name[:20],
                            competitor=product.source,
                            old_price=old_price,
                            new_price=product.price,
                            change_percent=round(change_percent, 2),
                            alert_type=alert_type,
                            timestamp=datetime.now().isoformat()
                        ))
            else:
                # Producto nuevo
                alerts.append(PriceAlert(
                    product_sku=product.sku or product.name[:20],
                    competitor=product.source,
                    old_price=0,
                    new_price=product.price,
                    change_percent=0,
                    alert_type="new_product",
                    timestamp=datetime.now().isoformat()
                ))

            # Actualizar historial
            self.history[key] = {
                "price": product.price,
                "name": product.name,
                "last_seen": product.scraped_at
            }

        self._save_history()
        return alerts


# ============================================================================
# VIGIA PRINCIPAL
# ============================================================================

class ODIVigia:
    """Motor principal de monitoreo de mercado."""

    def __init__(self):
        self.scrapers: Dict[str, BaseScraper] = {}
        self.comparator = PriceComparator()
        self.emitter = ODIEventEmitter(source="vigia") if EMITTER_AVAILABLE else None
        self._init_scrapers()

    def _init_scrapers(self):
        """Inicializa scrapers configurados."""
        for comp_id, config in COMPETITORS.items():
            if comp_id == "mercadolibre_motos":
                self.scrapers[comp_id] = MercadoLibreScraper(comp_id, config)
            else:
                self.scrapers[comp_id] = GenericScraper(comp_id, config)

    async def scan_competitor(
        self,
        browser: Browser,
        competitor_id: str,
        search_term: str = None
    ) -> ScanResult:
        """Escanea un competidor especifico."""
        start_time = datetime.now()
        result = ScanResult(
            competitor=competitor_id,
            timestamp=start_time.isoformat()
        )

        scraper = self.scrapers.get(competitor_id)
        if not scraper:
            result.errors.append(f"Scraper no encontrado: {competitor_id}")
            return result

        page = await browser.new_page()

        try:
            # Configurar user agent realista
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

            # Ejecutar scraping
            products = await scraper.scrape(page, search_term)
            result.products_found = len(products)

            # Comparar precios
            alerts = self.comparator.compare(products)
            result.new_products = sum(1 for a in alerts if a.alert_type == "new_product")
            result.price_changes = sum(1 for a in alerts if a.alert_type in ["price_drop", "price_increase"])

            # Emitir alertas
            for alert in alerts:
                if self.emitter:
                    if alert.alert_type == "price_drop":
                        self.emitter.emit("VIGIA_PRICE_CHANGE", {
                            "competitor": alert.competitor,
                            "product": alert.product_sku,
                            "old_price": alert.old_price,
                            "new_price": alert.new_price,
                            "change": f"{alert.change_percent}%"
                        })
                    elif alert.alert_type == "new_product":
                        self.emitter.emit("VIGIA_NEW_PRODUCT", {
                            "competitor": alert.competitor,
                            "product": alert.product_sku,
                            "price": alert.new_price
                        })

        except Exception as e:
            result.errors.append(str(e))

        finally:
            await page.close()

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result

    async def scan_all(self, search_term: str = None) -> List[ScanResult]:
        """Escanea todos los competidores configurados."""
        if not PLAYWRIGHT_AVAILABLE:
            print("❌ Playwright no disponible")
            return []

        results = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            for comp_id in self.scrapers.keys():
                print(f"🔍 Escaneando: {COMPETITORS[comp_id]['name']}...")
                result = await self.scan_competitor(browser, comp_id, search_term)
                results.append(result)

                # Delay entre competidores
                await asyncio.sleep(DEFAULT_DELAY / 1000)

            await browser.close()

        return results

    async def scan_category(self, category: str) -> List[ScanResult]:
        """Escanea competidores por categoria de producto."""
        # Mapeo de categorias a terminos de busqueda
        category_terms = {
            "frenos": "pastillas freno moto",
            "motor": "kit piston moto",
            "transmision": "cadena moto",
            "electrico": "bateria moto",
            "suspension": "amortiguador moto"
        }

        term = category_terms.get(category.lower(), category)
        return await self.scan_all(search_term=term)


# ============================================================================
# CLI
# ============================================================================

def print_banner():
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      🕷️  ODI VIGIA PLAYWRIGHT v{VERSION}                        ║
║                 Sistema de Monitoreo de Competencia y Mercado                ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")


def print_help():
    print("""
USO:
    python odi_vigia_playwright.py [comando] [opciones]

COMANDOS:
    scan                Escanea todos los competidores
    scan <competitor>   Escanea un competidor especifico
    search <term>       Busca termino en todos los competidores
    category <cat>      Escanea por categoria (frenos, motor, etc.)
    list                Lista competidores configurados

OPCIONES:
    --output, -o DIR    Directorio de salida
    --headless          Modo sin interfaz (default)
    --visible           Mostrar navegador

EJEMPLOS:
    python odi_vigia_playwright.py scan
    python odi_vigia_playwright.py scan mercadolibre_motos
    python odi_vigia_playwright.py search "pastillas freno fz"
    python odi_vigia_playwright.py category frenos

COMPETIDORES CONFIGURADOS:
""")
    for comp_id, config in COMPETITORS.items():
        print(f"    {comp_id:<25} {config['name']}")


async def main():
    print_banner()

    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright no instalado.")
        print("   pip install playwright")
        print("   playwright install chromium")
        sys.exit(1)

    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h']:
        print_help()
        sys.exit(0)

    command = sys.argv[1]
    vigia = ODIVigia()

    if command == 'list':
        print("\nCompetidores configurados:\n")
        for comp_id, config in COMPETITORS.items():
            status = "✓" if config.get("base_url") else "⚠ (sin URL)"
            print(f"  {status} {comp_id:<25} {config['name']}")
        return

    if command == 'scan':
        target = sys.argv[2] if len(sys.argv) > 2 else None

        if target:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                result = await vigia.scan_competitor(browser, target)
                await browser.close()

            print(f"\n📊 Resultado: {result.competitor}")
            print(f"   Productos: {result.products_found}")
            print(f"   Nuevos: {result.new_products}")
            print(f"   Cambios precio: {result.price_changes}")
            print(f"   Duracion: {result.duration_seconds:.1f}s")
            if result.errors:
                print(f"   Errores: {result.errors}")
        else:
            results = await vigia.scan_all()
            print("\n📊 Resumen de escaneo:\n")
            for r in results:
                status = "✓" if not r.errors else "⚠"
                print(f"  {status} {r.competitor:<25} {r.products_found} productos, {r.price_changes} cambios")

    elif command == 'search':
        if len(sys.argv) < 3:
            print("❌ Especifica termino de busqueda")
            sys.exit(1)
        term = ' '.join(sys.argv[2:])
        print(f"\n🔍 Buscando: {term}\n")
        results = await vigia.scan_all(search_term=term)

        total_products = sum(r.products_found for r in results)
        print(f"\n📊 Total encontrado: {total_products} productos")

    elif command == 'category':
        if len(sys.argv) < 3:
            print("❌ Especifica categoria (frenos, motor, transmision, electrico, suspension)")
            sys.exit(1)
        category = sys.argv[2]
        print(f"\n🏷️ Categoria: {category}\n")
        results = await vigia.scan_category(category)

        total_products = sum(r.products_found for r in results)
        print(f"\n📊 Total encontrado: {total_products} productos en categoria {category}")

    else:
        print(f"❌ Comando desconocido: {command}")
        print_help()


if __name__ == "__main__":
    asyncio.run(main())
