#!/usr/bin/env python3
"""
ODI External Intelligence Module v2.0
Rescata precios con CSV Priority, Exponential Back-off, y Payload Sanitization.

Cadena de rescate:
0. CSV Priority (NO consume API)
1. Tavily API - Busqueda web especializada
2. Perplexity API - Validacion con IA (sanitized payload)
3. Google Custom Search - Respaldo con back-off

Uso:
    from core.external_intel import ExternalIntel
    intel = ExternalIntel()
    price = intel.rescue_price("filtro aceite pulsar 200", "YOKOMAR", csv_prices)
"""

import os
import re
import json
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import requests

logger = logging.getLogger("odi_intel")

# =============================================================================
# CONFIGURACION
# =============================================================================

TAVILY_API_URL = "https://api.tavily.com/search"
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"

MIN_PRICE_COP = 5000
MAX_PRICE_COP = 15000000

# Backoff config
MAX_RETRIES = 3
INITIAL_BACKOFF = 2  # seconds


@dataclass
class PriceResult:
    """Resultado de busqueda de precio."""
    price: int
    source: str
    confidence: float
    raw_response: str
    search_query: str


class ExternalIntel:
    """Sistema de inteligencia externa v2.0 con CSV Priority y Back-off."""

    def __init__(self):
        self.tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
        self.perplexity_key = os.environ.get("PERPLEXITY_API_KEY", "").strip()
        self.google_key = os.environ.get("GOOGLE_SEARCH_API_KEY", "").strip()
        self.google_cse_id = os.environ.get("GOOGLE_CSE_ID", "").strip()

        # Stats
        self.api_calls_saved = 0
        self.api_calls_made = 0
        self.backoff_retries = 0

        self._validate_keys()

    def _validate_keys(self) -> None:
        missing = []
        if not self.tavily_key:
            missing.append("TAVILY_API_KEY")
        if not self.perplexity_key:
            missing.append("PERPLEXITY_API_KEY")
        if not self.google_key:
            missing.append("GOOGLE_SEARCH_API_KEY")
        if missing:
            logger.warning(f"APIs no configuradas: {', '.join(missing)}")

    # =========================================================================
    # SANITIZACION DE PAYLOAD
    # =========================================================================

    @staticmethod
    def sanitize_title(title: str) -> str:
        """
        Sanitiza el título para evitar errores 400 en APIs.
        Elimina caracteres especiales problemáticos.
        """
        if not title:
            return ""

        # Eliminar caracteres que causan problemas en JSON/APIs
        sanitized = title.strip()

        # Reemplazar caracteres problemáticos
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)  # Control chars
        sanitized = re.sub(r'["\'\\\n\r\t]', ' ', sanitized)  # Quotes and escapes
        sanitized = re.sub(r'\s+', ' ', sanitized)  # Multiple spaces

        # Limitar longitud
        if len(sanitized) > 150:
            sanitized = sanitized[:147] + "..."

        return sanitized.strip()

    # =========================================================================
    # EXPONENTIAL BACKOFF
    # =========================================================================

    def _request_with_backoff(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Ejecuta request con exponential back-off para errores 429.
        """
        backoff = INITIAL_BACKOFF

        for attempt in range(MAX_RETRIES):
            try:
                if method == "GET":
                    response = requests.get(url, **kwargs)
                else:
                    response = requests.post(url, **kwargs)

                if response.status_code == 429:
                    self.backoff_retries += 1
                    wait_time = backoff * (2 ** attempt)
                    logger.warning(f"Rate limit 429, waiting {wait_time}s (attempt {attempt+1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                    continue

                return response

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout en attempt {attempt+1}/{MAX_RETRIES}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(backoff)
                continue
            except Exception as e:
                logger.error(f"Request error: {e}")
                return None

        return None

    # =========================================================================
    # NORMALIZACION DE PRECIOS
    # =========================================================================

    def normalize_price(self, raw_text: str) -> Optional[int]:
        if not raw_text:
            return None

        text = raw_text.upper().strip()
        is_usd = any(x in text for x in ["USD", "DOLLAR", "US$", "U$"])

        cleaned = re.sub(r"[\$COPUSD\s]+", "", text)
        cleaned = re.sub(r"[A-Z]+", "", cleaned)

        if cleaned.count(".") >= 2:
            cleaned = cleaned.replace(".", "")
        elif "." in cleaned and "," in cleaned:
            if cleaned.index(".") < cleaned.index(","):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "." in cleaned:
            parts = cleaned.split(".")
            if len(parts) == 2 and len(parts[1]) == 3:
                cleaned = cleaned.replace(".", "")
        elif "," in cleaned:
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[1]) == 3:
                cleaned = cleaned.replace(",", "")

        cleaned = re.sub(r"[^\d.]", "", cleaned)

        try:
            price = float(cleaned)
            if is_usd:
                price = price * 4000
            price_int = int(price)

            if MIN_PRICE_COP <= price_int <= MAX_PRICE_COP:
                return price_int
            if price_int < 1000 and price_int > 5:
                return price_int * 1000
            return None
        except (ValueError, TypeError):
            return None

    def extract_prices_from_text(self, text: str) -> List[int]:
        prices = []
        patterns = [
            r"\$[\d.,]+",
            r"COP\s*[\d.,]+",
            r"[\d.,]+\s*(?:pesos|cop|mil)",
            r"precio[:\s]*[\d.,]+",
            r"[\d]{2,3}[.,][\d]{3}",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                price = self.normalize_price(match)
                if price:
                    prices.append(price)
        return list(set(prices))

    # =========================================================================
    # CSV PRIORITY (NO CONSUME API)
    # =========================================================================

    def check_csv_price(self, sku: str, csv_prices: Dict[str, float]) -> Optional[PriceResult]:
        """
        CSV Priority: Si el SKU existe en CSV con precio, NO consume API.
        """
        if not csv_prices or not sku:
            return None

        sku_upper = sku.strip().upper()

        if sku_upper in csv_prices:
            price = csv_prices[sku_upper]
            if price and price > 0:
                self.api_calls_saved += 1
                return PriceResult(
                    price=int(price),
                    source="csv_local",
                    confidence=1.0,
                    raw_response="CSV Master",
                    search_query=sku
                )

        return None

    # =========================================================================
    # TAVILY API
    # =========================================================================

    def search_tavily(self, product_name: str, store: str = "") -> Optional[PriceResult]:
        if not self.tavily_key:
            return None

        sanitized_name = self.sanitize_title(product_name)
        query = f"precio {sanitized_name} repuesto moto Colombia COP"

        try:
            self.api_calls_made += 1
            response = self._request_with_backoff(
                "POST",
                TAVILY_API_URL,
                json={
                    "api_key": self.tavily_key,
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": True,
                    "include_raw_content": False,
                    "max_results": 5
                },
                timeout=15
            )

            if not response:
                return None

            response.raise_for_status()
            data = response.json()

            answer = data.get("answer", "")
            results = data.get("results", [])
            all_text = answer + " " + " ".join([r.get("content", "") for r in results])
            prices = self.extract_prices_from_text(all_text)

            if prices:
                prices.sort()
                median_price = prices[len(prices) // 2]
                return PriceResult(
                    price=median_price,
                    source="tavily",
                    confidence=0.7,
                    raw_response=answer[:200],
                    search_query=query
                )
            return None
        except Exception as e:
            logger.error(f"Error Tavily: {e}")
            return None

    # =========================================================================
    # PERPLEXITY API (SANITIZED PAYLOAD)
    # =========================================================================

    def search_perplexity(self, product_name: str, store: str = "") -> Optional[PriceResult]:
        if not self.perplexity_key:
            return None

        # SANITIZE payload to avoid 400 errors
        sanitized_name = self.sanitize_title(product_name)

        prompt = f"Busca el precio de mercado en Colombia (COP) para este repuesto de moto: {sanitized_name}. Responde SOLO con el precio en formato numerico sin simbolos. Ejemplo: 45000"

        try:
            self.api_calls_made += 1

            payload = {
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
                "temperature": 0.1
            }

            # Debug: Log payload if needed
            logger.debug(f"Perplexity payload: {json.dumps(payload, ensure_ascii=False)[:200]}")

            response = self._request_with_backoff(
                "POST",
                PERPLEXITY_API_URL,
                headers={
                    "Authorization": f"Bearer {self.perplexity_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=20
            )

            if not response:
                return None

            if response.status_code == 400:
                logger.error(f"Perplexity 400 Bad Request - Payload issue with: {sanitized_name[:50]}")
                return None

            response.raise_for_status()
            data = response.json()
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            price = self.normalize_price(answer)

            if price:
                return PriceResult(
                    price=price,
                    source="perplexity",
                    confidence=0.8,
                    raw_response=answer[:200],
                    search_query=sanitized_name
                )
            return None
        except Exception as e:
            logger.error(f"Error Perplexity: {e}")
            return None

    # =========================================================================
    # GOOGLE CUSTOM SEARCH (WITH BACKOFF)
    # =========================================================================

    def search_google(self, product_name: str, store: str = "") -> Optional[PriceResult]:
        if not self.google_key or not self.google_cse_id:
            return None

        sanitized_name = self.sanitize_title(product_name)
        query = f"{sanitized_name} precio Colombia repuesto moto"

        try:
            self.api_calls_made += 1
            response = self._request_with_backoff(
                "GET",
                GOOGLE_CSE_URL,
                params={
                    "key": self.google_key,
                    "cx": self.google_cse_id,
                    "q": query,
                    "num": 5
                },
                timeout=15
            )

            if not response:
                return None

            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            all_text = " ".join([
                item.get("snippet", "") + " " + item.get("title", "")
                for item in items
            ])
            prices = self.extract_prices_from_text(all_text)

            if prices:
                prices.sort()
                median_price = prices[len(prices) // 2]
                return PriceResult(
                    price=median_price,
                    source="google",
                    confidence=0.6,
                    raw_response=all_text[:200],
                    search_query=query
                )
            return None
        except Exception as e:
            logger.error(f"Error Google: {e}")
            return None

    # =========================================================================
    # CADENA DE RESCATE PRINCIPAL v2.0
    # =========================================================================

    def rescue_price(
        self,
        product_name: str,
        store: str = "",
        csv_prices: Optional[Dict[str, float]] = None,
        sku: Optional[str] = None,
        has_image_match: bool = False
    ) -> Optional[PriceResult]:
        """
        Cadena de rescate de precio v2.0.
        0. CSV Priority (NO consume API)
        1. Tavily (busqueda web)
        2. Perplexity (IA - sanitized)
        3. Google (respaldo con backoff)

        Prioriza productos con has_image_match=True (DRAFTs listos para activar).
        """

        # PASO 0: CSV Priority - NO consume API
        if csv_prices and sku:
            csv_result = self.check_csv_price(sku, csv_prices)
            if csv_result:
                logger.info(f"  CSV Priority: {sku} -> ${csv_result.price:,} (API saved)")
                return csv_result

        logger.info(f"Rescatando precio: {product_name[:50]}{'...' if len(product_name) > 50 else ''}")

        # Paso 1: Tavily
        result = self.search_tavily(product_name, store)
        if result:
            logger.info(f"  Tavily: ${result.price:,} (conf: {result.confidence})")
            return result

        # Paso 2: Perplexity (sanitized)
        result = self.search_perplexity(product_name, store)
        if result:
            logger.info(f"  Perplexity: ${result.price:,} (conf: {result.confidence})")
            return result

        # Paso 3: Google (con backoff)
        result = self.search_google(product_name, store)
        if result:
            logger.info(f"  Google: ${result.price:,} (conf: {result.confidence})")
            return result

        logger.warning(f"  Sin precio encontrado para: {product_name[:50]}")
        return None

    def get_stats(self) -> Dict[str, int]:
        """Retorna estadísticas de uso de API."""
        return {
            "api_calls_saved": self.api_calls_saved,
            "api_calls_made": self.api_calls_made,
            "backoff_retries": self.backoff_retries
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


def test_intel():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
    load_env()

    intel = ExternalIntel()

    # Test sanitization
    test_titles = [
        'FILTRO "ACEITE" PULSAR',
        "CADENA\nREFORZADA\t428H",
        "BALINERA 6205 (C3) DFG/TMR",
    ]

    print("\n=== Test de Sanitizacion ===")
    for title in test_titles:
        sanitized = intel.sanitize_title(title)
        print(f"  '{title}' -> '{sanitized}'")

    # Test CSV Priority
    csv_prices = {"M110053": 22500.0, "TEST123": 15000.0}

    print("\n=== Test CSV Priority ===")
    result = intel.check_csv_price("M110053", csv_prices)
    if result:
        print(f"  M110053: ${result.price:,} ({result.source}) - API NOT consumed")

    print(f"\nStats: {intel.get_stats()}")


if __name__ == "__main__":
    test_intel()
