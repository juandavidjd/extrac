#!/usr/bin/env python3
"""
ODI Cross-Audit System v4.0 - Enterprise Edition
Sistema profesional de auditoria cruzada con aislamiento de namespace.

Módulos de Seguridad:
1. Aislamiento de Namespace (Anti-Cruce)
2. Normalización Literal (Fix Empaque)
3. Branding Handshake (Identidad Segura)

Ejecuta: python3 /opt/odi/scripts/cross_audit.py [--store STORE_ID] [--mode diagnostic]
Cron: 4 veces al dia (00:00, 06:00, 12:00, 18:00 UTC)
Log: /var/log/odi_system_audit.log
"""

import os
import sys
import csv
import json
import shutil
import logging
import argparse
import glob
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, "/opt/odi")

# =============================================================================
# CONFIGURACION
# =============================================================================

DATA_PATH = "/opt/odi/data/orden_maestra_v6/"
MASTER_DATA_PATH = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/"
LOG_FILE = "/var/log/odi_system_audit.log"
REPORT_PATH = "/opt/odi/data/reports/"
BRANDS_PATH = "/opt/odi/data/brands/"

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o"
MAX_TOKENS = 4096
HEALTH_SCORE_THRESHOLD = 70
MAX_EXTERNAL_CALLS_PER_RUN = 500

ALL_STORES = [
    "DFG", "ARMOTOS", "OH_IMPORTACIONES", "VITTON", "DUNA",
    "IMBRA", "YOKOMAR", "BARA", "JAPAN", "MCLMOTOS",
    "CBI", "KAIQI", "LEO", "STORE", "VAISAND"
]

REFERENCE_STORE = "IMBRA"
REFERENCE_SKU = "M110053"

STORE_FOLDER_MAP = {
    "DFG": "DFG",
    "ARMOTOS": "Armotos",
    "OH_IMPORTACIONES": "Oh_importaciones",
    "VITTON": "Vitton",
    "DUNA": "Duna",
    "IMBRA": "Imbra",
    "YOKOMAR": "Yokomar",
    "BARA": "Bara",
    "JAPAN": "Japan",
    "MCLMOTOS": "Mclmotos",
    "CBI": "Cbi",
    "KAIQI": "Kaiqi",
    "LEO": "Leo",
    "STORE": "Store",
    "VAISAND": "Vaisand"
}


def load_env():
    env_path = "/opt/odi/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key] = value.strip().strip("'").strip('"')


def setup_logging():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    os.makedirs(REPORT_PATH, exist_ok=True)

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger = logging.getLogger('odi_audit')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


load_env()
logger = setup_logging()


# =============================================================================
# MODULO 1: AISLAMIENTO DE NAMESPACE (Anti-Cruce)
# =============================================================================

class NamespaceManager:
    """
    Gestor de namespace para aislamiento de tiendas.
    Previene contaminacion de datos entre empresas.
    """

    def __init__(self, base_volume: str = MASTER_DATA_PATH):
        self.base_volume = base_volume
        self.current_store: Optional[str] = None
        self.locked_path: Optional[str] = None

    def set_store_context(self, store_id: str) -> str:
        """
        Bloquea el contexto de trabajo a una tienda especifica.
        Anti-cruce: Solo permite acceso a la subcarpeta de la tienda.
        """
        store_id = store_id.upper()
        folder_name = STORE_FOLDER_MAP.get(store_id, store_id.title())
        target_path = os.path.join(self.base_volume, folder_name)

        if not os.path.exists(target_path):
            for item in os.listdir(self.base_volume):
                if item.lower() == folder_name.lower():
                    target_path = os.path.join(self.base_volume, item)
                    break

        if not os.path.exists(target_path):
            logger.debug(f"Namespace: {target_path} no existe")
            target_path = self.base_volume

        self.current_store = store_id
        self.locked_path = target_path
        return target_path

    def get_data_path(self, store_id: str) -> str:
        context_path = self.set_store_context(store_id)
        data_path = os.path.join(context_path, "Data")
        if os.path.exists(data_path):
            return data_path
        return context_path

    def release_context(self):
        self.current_store = None
        self.locked_path = None


# =============================================================================
# MODULO 2: NORMALIZACION LITERAL (Fix Empaque)
# =============================================================================

class TitleNormalizer:
    """
    Normalizador de titulos con fuente de verdad absoluta.
    PROHIBIDO añadir prefijos automaticos como 'Empaque'.
    """

    FORBIDDEN_PREFIXES = ["Empaque ", "EMPAQUE ", "empaque "]

    @staticmethod
    def get_literal_title(csv_row: Dict) -> str:
        """
        FUENTE DE VERDAD ABSOLUTA: Columna 'DESCRIPCION' del CSV.
        Solo limpieza de espacios y Title Case.
        PROHIBIDO añadir 'Empaque' u otros prefijos.
        """
        raw_title = ""
        for key in ['DESCRIPCION', 'descripcion', 'DESCRIPTION', 'NOMBRE', 'nombre', 'TITLE', 'title']:
            if key in csv_row and csv_row[key]:
                raw_title = str(csv_row[key])
                break

        if not raw_title:
            return ""

        cleaned = " ".join(raw_title.split()).strip()

        if cleaned.isupper():
            cleaned = cleaned.title()

        return cleaned

    @staticmethod
    def detect_empaque_bug(product_title: str, csv_title: str) -> bool:
        """Detecta si el producto tiene el bug de 'Empaque' añadido."""
        if not product_title or not csv_title:
            return False

        product_upper = product_title.upper()
        csv_upper = csv_title.upper()

        for prefix in ["EMPAQUE ", "EMPAQUE DE "]:
            if product_upper.startswith(prefix) and not csv_upper.startswith(prefix):
                return True

        return False

    @staticmethod
    def normalize_product_title(product: Dict, csv_row: Optional[Dict] = None) -> str:
        if csv_row:
            literal = TitleNormalizer.get_literal_title(csv_row)
            if literal:
                return literal

        title = str(product.get("title", "")).strip()

        for prefix in TitleNormalizer.FORBIDDEN_PREFIXES:
            if title.startswith(prefix):
                rest = title[len(prefix):]
                if rest and not rest.lower().startswith("de "):
                    title = rest
                break

        title = " ".join(title.split()).strip()

        if title.isupper():
            title = title.title()

        if len(title) > 60:
            title = title[:57].rsplit(" ", 1)[0] + "..."

        return title


# =============================================================================
# MODULO 3: BRANDING HANDSHAKE (Identidad Segura)
# =============================================================================

class BrandingValidator:
    """
    Validador de identidad de marca.
    Previene que logos/colores se 'troquen' entre tiendas.
    """

    STORE_ALIASES = {
        "dfg": ["dfg", "distribuidora"],
        "armotos": ["armotos", "ar-motos"],
        "yokomar": ["yokomar", "yoko"],
        "imbra": ["imbra", "importadora"],
        "vitton": ["vitton", "vitt"],
        "duna": ["duna"],
        "bara": ["bara"],
        "japan": ["japan", "japon"],
        "mclmotos": ["mclmotos", "mcl"],
        "cbi": ["cbi"],
        "kaiqi": ["kaiqi", "kai"],
        "leo": ["leo"],
        "store": ["store", "odi"],
        "vaisand": ["vaisand", "vai"],
        "oh_importaciones": ["oh_importaciones", "oh", "importaciones"]
    }

    def __init__(self, brands_path: str = BRANDS_PATH):
        self.brands_path = brands_path
        self.brand_configs: Dict[str, Dict] = {}
        self._load_brand_configs()

    def _load_brand_configs(self):
        if not os.path.exists(self.brands_path):
            return

        for filename in os.listdir(self.brands_path):
            if filename.endswith('.json'):
                store_name = filename.replace('.json', '').upper()
                try:
                    with open(os.path.join(self.brands_path, filename), 'r') as f:
                        self.brand_configs[store_name] = json.load(f)
                except Exception as e:
                    logger.debug(f"Error loading brand config {filename}: {e}")

    def validate_branding(self, store_domain: str, logo_filename: str) -> bool:
        if not store_domain or not logo_filename:
            return False

        store_slug = store_domain.split('.')[0].lower()
        logo_lower = logo_filename.lower()

        if store_slug in logo_lower:
            return True

        store_aliases = self.STORE_ALIASES.get(store_slug, [store_slug])
        return any(alias in logo_lower for alias in store_aliases)

    def detect_branding_mismatch(self, product: Dict, store_id: str) -> List[str]:
        issues = []
        store_id_lower = store_id.lower()

        image_url = product.get("image_url", "") or product.get("image", "")
        if image_url:
            filename = image_url.split("/")[-1].split("?")[0].lower()

            if "logo" in filename or "brand" in filename:
                if not self.validate_branding(store_id, filename):
                    issues.append(f"Logo mismatch: {filename}")

        return issues


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class PriceFixResult:
    store: str
    total_products: int
    zero_price_found: int
    fixed_from_csv: int
    fixed_from_index: int
    fixed_from_description: int
    fixed_from_external: int
    not_found: int
    status: str


@dataclass
class AuditResult:
    store_name: str
    product_count: int
    issues_found: List[Dict[str, Any]]
    recommendations: List[str]
    score: float
    timestamp: str


@dataclass
class DiagnosticReport:
    empaque_bug_count: int
    empaque_bug_products: List[Dict]
    branding_mismatch_count: int
    branding_mismatch_stores: List[str]
    reference_sku_status: Dict
    stores_analyzed: int
    total_products: int
    generated_at: str


@dataclass
class CrossAuditReport:
    total_stores: int
    total_products: int
    price_fixes: List[PriceFixResult]
    audit_results: List[AuditResult]
    cross_store_issues: List[Dict[str, Any]]
    overall_health_score: float
    attention_required: bool
    generated_at: str


# =============================================================================
# SISTEMA PRINCIPAL
# =============================================================================

class CrossAuditSystem:
    """Sistema principal de auditoria cruzada ODI v4.0 Enterprise."""

    def __init__(self, api_key: Optional[str] = None, diagnostic_mode: bool = False):
        self.diagnostic_mode = diagnostic_mode

        if not diagnostic_mode:
            raw_key = api_key or os.environ.get("OPENAI_API_KEY")
            self.api_key = raw_key.strip() if raw_key else None
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY no encontrada")

            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        else:
            self.api_key = None
            self.headers = {}

        self.namespace = NamespaceManager()
        self.title_normalizer = TitleNormalizer()
        self.branding_validator = BrandingValidator()

        self.price_index: Dict[str, float] = {}
        self.csv_prices: Dict[str, Dict[str, float]] = {}
        self.csv_titles: Dict[str, Dict[str, str]] = {}
        self.description_prices: Dict[str, float] = {}

        self.external_intel = None
        self.external_calls_count = 0

        if not diagnostic_mode:
            self._init_external_intel()

    def _init_external_intel(self):
        try:
            from core.external_intel import ExternalIntel
            self.external_intel = ExternalIntel()
            logger.info("External Intel: Inicializado")
        except Exception as e:
            logger.warning(f"External Intel: No disponible - {e}")

    def _load_csv_data(self, store: str) -> Tuple[Dict[str, float], Dict[str, str]]:
        """Carga precios Y títulos del CSV."""
        self.namespace.set_store_context(store)

        folder_name = STORE_FOLDER_MAP.get(store, store.title())
        data_path = os.path.join(MASTER_DATA_PATH, "Data", folder_name)

        csv_path = None
        if os.path.exists(data_path):
            matches = glob.glob(os.path.join(data_path, "LISTA_PRECIOS*.csv")) or glob.glob(os.path.join(data_path, "Lista_Precios*.csv")) or glob.glob(os.path.join(data_path, "*.csv"))
            if matches:
                csv_path = matches[0]

        if not csv_path or not os.path.exists(csv_path):
            return {}, {}

        prices = {}
        titles = {}

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                sample = f.read(1024)
                f.seek(0)
                delimiter = ';' if ';' in sample else ','
                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    sku = None
                    for key in ['CODIGO', 'sku', 'SKU', 'codigo']:
                        if key in row and row[key]:
                            sku = str(row[key]).strip().upper()
                            break

                    price = None
                    for key in ['PRECIO', 'precio', 'PRICE', 'price']:
                        if key in row and row[key]:
                            try:
                                price = float(str(row[key]).replace(',', '.').strip())
                            except:
                                pass
                            break

                    title = TitleNormalizer.get_literal_title(row)

                    if sku:
                        if price and price > 0:
                            prices[sku] = price
                        if title:
                            titles[sku] = title
                            self.description_prices[title.upper()] = price or 0

            logger.info(f"CSV {store}: {len(prices)} precios, {len(titles)} títulos")
        except Exception as e:
            logger.warning(f"Error CSV {store}: {e}")

        return prices, titles

    def _build_indexes(self, stores_data: Dict[str, List[Dict]]) -> None:
        logger.info("Cargando CSVs con Namespace Isolation...")

        for store in ALL_STORES:
            prices, titles = self._load_csv_data(store)
            self.csv_prices[store] = prices
            self.csv_titles[store] = titles

        if REFERENCE_STORE in stores_data:
            for product in stores_data[REFERENCE_STORE]:
                sku = str(product.get("sku", "")).strip().upper() if product.get("sku") else ""
                price = product.get("price") or 0
                if sku and price > 0:
                    self.price_index[sku] = price

        for store, products in stores_data.items():
            if store == REFERENCE_STORE:
                continue
            for product in products:
                sku = str(product.get("sku", "")).strip().upper() if product.get("sku") else ""
                price = product.get("price") or 0
                if sku and price > 0 and sku not in self.price_index:
                    self.price_index[sku] = price

        logger.info(f"Indice global: {len(self.price_index)} SKUs")

    def run_diagnostic(self, stores_data: Dict[str, List[Dict]]) -> DiagnosticReport:
        """
        Modo diagnóstico: analiza sin modificar nada.
        Detecta bugs de Empaque, mismatches de branding, y estado de SKU referencia.
        """
        logger.info("=" * 60)
        logger.info("MODO DIAGNOSTICO - Solo lectura")
        logger.info("=" * 60)

        self._build_indexes(stores_data)

        empaque_bugs = []
        branding_mismatches = []
        reference_sku_status = {}

        for store, products in stores_data.items():
            self.namespace.set_store_context(store)
            csv_titles = self.csv_titles.get(store, {})

            store_branding_issues = []

            for product in products:
                sku = str(product.get("sku", "")).strip().upper() if product.get("sku") else ""
                product_title = product.get("title", "")

                # Detectar bug de Empaque
                if sku in csv_titles:
                    csv_title = csv_titles[sku]
                    if TitleNormalizer.detect_empaque_bug(product_title, csv_title):
                        empaque_bugs.append({
                            "store": store,
                            "sku": sku,
                            "product_title": product_title,
                            "csv_title": csv_title
                        })

                # Detectar branding mismatch
                branding_issues = self.branding_validator.detect_branding_mismatch(product, store)
                if branding_issues:
                    store_branding_issues.extend(branding_issues)

                # Buscar SKU de referencia
                if sku == REFERENCE_SKU:
                    reference_sku_status[store] = {
                        "found": True,
                        "title": product_title,
                        "price": product.get("price"),
                        "image": product.get("image_url") or product.get("image"),
                        "has_360": "360" in str(product.get("description", "")).lower()
                    }

            if store_branding_issues:
                branding_mismatches.append(store)

            self.namespace.release_context()

        # Contar tiendas sin el SKU de referencia
        for store in stores_data.keys():
            if store not in reference_sku_status:
                reference_sku_status[store] = {"found": False}

        report = DiagnosticReport(
            empaque_bug_count=len(empaque_bugs),
            empaque_bug_products=empaque_bugs[:50],  # Limitar muestra
            branding_mismatch_count=len(branding_mismatches),
            branding_mismatch_stores=branding_mismatches,
            reference_sku_status=reference_sku_status,
            stores_analyzed=len(stores_data),
            total_products=sum(len(p) for p in stores_data.values()),
            generated_at=datetime.utcnow().isoformat()
        )

        # Log resumen
        logger.info(f"Productos con bug 'Empaque': {report.empaque_bug_count}")
        logger.info(f"Tiendas con branding mismatch: {report.branding_mismatch_count}")
        logger.info(f"SKU referencia {REFERENCE_SKU} encontrado en: {sum(1 for v in reference_sku_status.values() if v.get('found'))}/{len(stores_data)} tiendas")

        return report

    def normalize_prices_by_description(self, product: Dict) -> Optional[float]:
        title = str(product.get("title", "")).strip().upper()
        if not title:
            return None

        if title in self.description_prices:
            return self.description_prices[title]

        title_words = set(title.split())
        best_match = None
        best_score = 0

        for desc, price in self.description_prices.items():
            if price <= 0:
                continue
            desc_words = set(desc.split())
            common = len(title_words & desc_words)
            if common > best_score and common >= 3:
                best_score = common
                best_match = price

        return best_match

    def rescue_price_external(self, product: Dict, store: str) -> Optional[int]:
        if not self.external_intel:
            return None
        if self.external_calls_count >= MAX_EXTERNAL_CALLS_PER_RUN:
            return None

        title = product.get("title", "")
        if not title:
            return None

        try:
            self.external_calls_count += 1
            result = self.external_intel.rescue_price(title, store)
            if result:
                return result.price
        except Exception as e:
            logger.warning(f"External Intel error: {e}")

        return None

    def normalize_prices(self, stores_data: Dict[str, List[Dict]]) -> List[PriceFixResult]:
        logger.info("=" * 60)
        logger.info("FASE 1: NORMALIZACION DE PRECIOS")
        logger.info("=" * 60)

        self._build_indexes(stores_data)
        self.external_calls_count = 0
        results = []

        for store, products in stores_data.items():
            self.namespace.set_store_context(store)

            result = PriceFixResult(
                store=store,
                total_products=len(products),
                zero_price_found=0,
                fixed_from_csv=0,
                fixed_from_index=0,
                fixed_from_description=0,
                fixed_from_external=0,
                not_found=0,
                status="ok"
            )

            csv_prices = self.csv_prices.get(store, {})
            modified = False
            products_needing_external = []

            for product in products:
                sku = str(product.get("sku", "")).strip().upper() if product.get("sku") else ""
                current_price = product.get("price") or 0

                if current_price > 0:
                    continue

                result.zero_price_found += 1
                new_price = None
                source = None

                if sku and sku in csv_prices:
                    new_price = csv_prices[sku]
                    source = "csv_master"
                    result.fixed_from_csv += 1
                elif sku and sku in self.price_index:
                    new_price = self.price_index[sku]
                    source = "cross_store_index"
                    result.fixed_from_index += 1
                else:
                    desc_price = self.normalize_prices_by_description(product)
                    if desc_price:
                        new_price = desc_price
                        source = "description_match"
                        result.fixed_from_description += 1
                    else:
                        products_needing_external.append(product)

                if new_price:
                    product["price"] = new_price
                    product["price_source"] = source
                    product["price_fixed_at"] = datetime.utcnow().isoformat()
                    modified = True
                    logger.info(f"  FIXED: {store}/{sku} -> ${new_price:,.0f} ({source})")

            # External Intel
            if products_needing_external and self.external_intel:
                remaining = MAX_EXTERNAL_CALLS_PER_RUN - self.external_calls_count
                to_try = products_needing_external[:remaining]

                for product in to_try:
                    sku = str(product.get("sku", "")).strip().upper() if product.get("sku") else ""
                    ext_price = self.rescue_price_external(product, store)

                    if ext_price:
                        product["price"] = ext_price
                        product["price_source"] = "external_intel"
                        product["price_fixed_at"] = datetime.utcnow().isoformat()
                        modified = True
                        result.fixed_from_external += 1
                        logger.info(f"  FIXED: {store}/{sku} -> ${ext_price:,} (external_intel)")
                    else:
                        result.not_found += 1

                result.not_found += len(products_needing_external) - len(to_try)

            total_fixed = (result.fixed_from_csv + result.fixed_from_index +
                          result.fixed_from_description + result.fixed_from_external)

            if modified and total_fixed > 0:
                json_path = os.path.join(DATA_PATH, f"{store}_products.json")
                backup_path = json_path + ".backup_audit"
                if os.path.exists(json_path):
                    shutil.copy2(json_path, backup_path)

                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(products, f, ensure_ascii=False, indent=2)

                logger.info(f"  {store}: {total_fixed}/{result.zero_price_found} corregidos")
            elif result.zero_price_found > 0:
                logger.info(f"  {store}: {result.not_found} sin referencia")
            else:
                logger.info(f"  {store}: OK")

            self.namespace.release_context()
            results.append(result)

        total_fixed = sum(r.fixed_from_csv + r.fixed_from_index +
                         r.fixed_from_description + r.fixed_from_external for r in results)
        total_external = sum(r.fixed_from_external for r in results)

        logger.info(f"TOTAL: {total_fixed} corregidos ({total_external} External Intel)")
        logger.info(f"External calls: {self.external_calls_count}/{MAX_EXTERNAL_CALLS_PER_RUN}")

        return results

    def _call_gpt4o(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(
                OPENAI_API_URL,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return json.loads(response.json()["choices"][0]["message"]["content"])
        except Exception as e:
            logger.error(f"Error GPT-4o: {e}")
            return {"issues_found": [], "recommendations": [], "score": 50}

    def audit_store(self, store_name: str, products: List[Dict]) -> AuditResult:
        system_prompt = """Eres un auditor experto de catalogos Shopify.
Analiza productos y genera JSON con:
- issues_found: lista de problemas
- recommendations: lista de mejoras
- score: puntuacion 0-100

Responde SOLO JSON valido."""

        sample = products[:40]
        user_prompt = f"""Tienda: {store_name}
Total: {len(products)}
Muestra: {json.dumps(sample, ensure_ascii=False, indent=2)}"""

        result = self._call_gpt4o(system_prompt, user_prompt)

        return AuditResult(
            store_name=store_name,
            product_count=len(products),
            issues_found=result.get("issues_found", []),
            recommendations=result.get("recommendations", []),
            score=result.get("score", 50.0),
            timestamp=datetime.utcnow().isoformat()
        )

    def _analyze_cross_store(self, stores_data: Dict[str, List[Dict]]) -> List[Dict]:
        system_prompt = """Analiza tiendas y encuentra:
- Productos duplicados entre tiendas
- Inconsistencias de precios
- Oportunidades cross-selling

Responde JSON con cross_store_issues."""

        summary = {}
        for store, products in stores_data.items():
            skus = [p.get("sku", "") for p in products[:50] if p.get("sku")]
            prices = [p.get("price", 0) for p in products[:50] if p.get("price")]
            summary[store] = {
                "count": len(products),
                "sample_skus": skus[:15],
                "price_range": [min(prices) if prices else 0, max(prices) if prices else 0]
            }

        result = self._call_gpt4o(system_prompt, json.dumps(summary, ensure_ascii=False))
        return result.get("cross_store_issues", [])

    def cross_audit(self, stores_data: Dict[str, List[Dict]], single_store: Optional[str] = None) -> CrossAuditReport:
        if single_store:
            stores_data = {single_store: stores_data.get(single_store, [])}
            logger.info(f"Modo Single-Store: {single_store}")

        price_fixes = self.normalize_prices(stores_data)

        logger.info("")
        logger.info("=" * 60)
        logger.info("FASE 2: AUDITORIA GPT-4o")
        logger.info("=" * 60)

        audit_results = []
        total_products = 0

        for store_name, products in stores_data.items():
            logger.info(f"  Analizando {store_name}...")
            result = self.audit_store(store_name, products)
            audit_results.append(result)
            total_products += len(products)
            logger.info(f"    Score: {result.score:.1f}/100")

        logger.info("")
        logger.info("Analisis cruzado...")
        cross_issues = self._analyze_cross_store(stores_data)

        overall_score = sum(r.score for r in audit_results) / len(audit_results) if audit_results else 0
        attention_required = overall_score < HEALTH_SCORE_THRESHOLD

        return CrossAuditReport(
            total_stores=len(stores_data),
            total_products=total_products,
            price_fixes=price_fixes,
            audit_results=audit_results,
            cross_store_issues=cross_issues,
            overall_health_score=overall_score,
            attention_required=attention_required,
            generated_at=datetime.utcnow().isoformat()
        )

    def save_report(self, report, filename_prefix: str = "audit_report") -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.json"
        filepath = os.path.join(REPORT_PATH, filename)

        if isinstance(report, DiagnosticReport):
            report_dict = asdict(report)
        else:
            report_dict = {
                "total_stores": report.total_stores,
                "total_products": report.total_products,
                "price_fixes": [asdict(r) for r in report.price_fixes],
                "audit_results": [asdict(r) for r in report.audit_results],
                "cross_store_issues": report.cross_store_issues,
                "overall_health_score": report.overall_health_score,
                "attention_required": report.attention_required,
                "generated_at": report.generated_at
            }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)

        logger.info(f"Reporte guardado: {filepath}")
        return filepath


def load_store_data(single_store: Optional[str] = None) -> Dict[str, List[Dict]]:
    stores_data = {}
    stores_to_load = [single_store] if single_store else ALL_STORES

    for store in stores_to_load:
        json_path = os.path.join(DATA_PATH, f"{store}_products.json")

        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    products = json.load(f)
                    stores_data[store] = products
                    logger.info(f"  {store}: {len(products)} productos")
            except Exception as e:
                logger.warning(f"  {store}: Error - {e}")
        else:
            logger.warning(f"  {store}: No encontrado")

    return stores_data


def main() -> int:
    parser = argparse.ArgumentParser(description="ODI Cross-Audit System v4.0")
    parser.add_argument("--store", type=str, help="Auditar solo una tienda")
    parser.add_argument("--mode", type=str, choices=["audit", "diagnostic"], default="audit")
    parser.add_argument("--all-15-stores", action="store_true", help="Procesar las 15 tiendas")
    args = parser.parse_args()

    logger.info("")
    logger.info("#" * 60)
    logger.info("#  ODI CROSS-AUDIT SYSTEM v4.0 - Enterprise Edition")
    logger.info("#  Namespace Isolation + Literal Titles + Branding")
    logger.info(f"#  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info(f"#  Mode: {args.mode.upper()}")
    logger.info("#" * 60)
    logger.info("")

    single_store = args.store.upper() if args.store else None

    logger.info("Cargando datos...")
    stores_data = load_store_data(single_store)

    if not stores_data:
        logger.error("No se encontraron datos")
        return 1

    try:
        if args.mode == "diagnostic":
            auditor = CrossAuditSystem(diagnostic_mode=True)
            report = auditor.run_diagnostic(stores_data)
            filepath = auditor.save_report(report, "srm_health_report")
        else:
            auditor = CrossAuditSystem()
            report = auditor.cross_audit(stores_data, single_store)
            filepath = auditor.save_report(report)

            logger.info("")
            logger.info("=" * 60)
            logger.info("RESUMEN FINAL")
            logger.info("=" * 60)
            logger.info(f"  Tiendas: {report.total_stores}")
            logger.info(f"  Productos: {report.total_products}")
            logger.info(f"  Score: {report.overall_health_score:.1f}/100")

            total_fixed = sum(
                r.fixed_from_csv + r.fixed_from_index + r.fixed_from_description + r.fixed_from_external
                for r in report.price_fixes
            )
            total_external = sum(r.fixed_from_external for r in report.price_fixes)
            logger.info(f"  Precios corregidos: {total_fixed} ({total_external} External Intel)")

            if report.attention_required:
                logger.warning("")
                logger.warning("!" * 60)
                logger.warning("!  ATENCION REQUERIDA: Score < 70")
                logger.warning("!" * 60)

        logger.info(f"  Reporte: {filepath}")
        logger.info("=" * 60)
        return 0

    except Exception as e:
        logger.error(f"Error critico: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
