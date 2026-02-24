#!/usr/bin/env python3
"""
ODI Cross-Store Image Matcher V18
Matches products to neutral images from other stores by title similarity.
"""
import os
import re
import json
import glob
import time
import logging
import requests
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CrossMatch:
    product_id: int
    product_title: str
    product_sku: str
    image_path: str
    source_store: str
    similarity: float

@dataclass
class CrossMatchResult:
    target_store: str
    total_products: int
    matched: int
    unmatched: int
    matches: List[CrossMatch] = field(default_factory=list)
    unmatched_products: List[dict] = field(default_factory=list)

class CrossStoreMatcher:
    NEUTRAL_SOURCES = {
        'JAPAN': 0.93,
        'DFG': 0.73,
        'VAISAND': 0.73,
        'STORE': 0.60,
        'IMBRA': 0.53,
    }

    BANK_PATH = '/mnt/volume_sfo3_01/profesion/ecosistema_odi/{store}/imagenes'
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

    def __init__(self, target_store: str, brands_dir: str = '/opt/odi/data/brands'):
        self.target_store = target_store.upper()
        self.brands_dir = brands_dir
        self.shop = None
        self.token = None
        self._load_credentials()

    def _load_credentials(self):
        config_path = os.path.join(self.brands_dir, f'{self.target_store.lower()}.json')
        if os.path.exists(config_path):
            with open(config_path) as f:
                data = json.load(f)
            self.shop = data.get('shopify', {}).get('shop')
            self.token = data.get('shopify', {}).get('token')
            logger.info(f'Loaded credentials for {self.target_store}')
        else:
            raise ValueError(f'No config for {self.target_store}')

    def _normalize_title(self, title: str) -> str:
        if not title:
            return ''
        t = title.lower()
        t = re.sub(r'^(empaque|kit|set|juego|par)\s+', '', t)
        t = re.sub(r'\s*(x\s*\d+|paquete|unidad|par|kit).*$', '', t)
        t = re.sub(r'[^\w\s]', ' ', t)
        t = ' '.join(t.split())
        return t

    def _extract_keywords(self, title: str) -> set:
        norm = self._normalize_title(title)
        words = [w for w in norm.split() if len(w) >= 3]
        stopwords = {'para', 'con', 'sin', 'del', 'los', 'las', 'una', 'uno', 'moto', 'motos'}
        return set(w for w in words if w not in stopwords)

    def _similarity(self, s1: str, s2: str) -> float:
        return SequenceMatcher(None, s1, s2).ratio()

    def _keyword_overlap(self, kw1: set, kw2: set) -> float:
        if not kw1 or not kw2:
            return 0.0
        intersection = len(kw1 & kw2)
        union = len(kw1 | kw2)
        return intersection / union if union > 0 else 0.0

    def _scan_neutral_bank(self) -> Dict[str, Tuple[str, str, set]]:
        bank = {}

        for source_store, neutral_pct in self.NEUTRAL_SOURCES.items():
            bank_path = self.BANK_PATH.format(store=source_store)
            if not os.path.exists(bank_path):
                continue

            for ext in self.IMAGE_EXTENSIONS:
                for img_path in glob.glob(f'{bank_path}/*{ext}') + glob.glob(f'{bank_path}/*{ext.upper()}'):
                    filename = os.path.splitext(os.path.basename(img_path))[0]
                    norm_name = self._normalize_title(filename)
                    keywords = self._extract_keywords(filename)

                    if norm_name and norm_name not in bank:
                        bank[norm_name] = (img_path, source_store, keywords)

        logger.info(f'Scanned {len(bank)} neutral images from {len(self.NEUTRAL_SOURCES)} sources')
        return bank

    def _fetch_products_without_images(self) -> List[dict]:
        products = []
        url = f'https://{self.shop}/admin/api/2024-01/products.json?limit=250&fields=id,title,variants,images'
        headers = {'X-Shopify-Access-Token': self.token}

        while url:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            time.sleep(0.6)

            for p in r.json().get('products', []):
                if not p.get('images'):
                    sku = p['variants'][0].get('sku', '') if p.get('variants') else ''
                    products.append({
                        'id': p['id'],
                        'title': p['title'],
                        'sku': sku,
                        'norm_title': self._normalize_title(p['title']),
                        'keywords': self._extract_keywords(p['title'])
                    })

            link = r.headers.get('Link', '')
            url = None
            if 'rel="next"' in link:
                for part in link.split(','):
                    if 'rel="next"' in part:
                        url = part.split('<')[1].split('>')[0]
                        break

        logger.info(f'Found {len(products)} products without images')
        return products

    def _match_product(self, product: dict, bank: Dict) -> Optional[CrossMatch]:
        prod_title = product['norm_title']
        prod_keywords = product['keywords']

        best_match = None
        best_score = 0.0

        for img_name, (img_path, source_store, img_keywords) in bank.items():
            title_sim = self._similarity(prod_title, img_name)
            keyword_sim = self._keyword_overlap(prod_keywords, img_keywords)
            score = (title_sim * 0.6) + (keyword_sim * 0.4)

            if score > best_score and score >= 0.50:
                best_score = score
                best_match = (img_path, source_store)

        if best_match and best_score >= 0.50:
            return CrossMatch(
                product_id=product['id'],
                product_title=product['title'],
                product_sku=product['sku'],
                image_path=best_match[0],
                source_store=best_match[1],
                similarity=best_score
            )

        return None

    def match(self, min_similarity: float = 0.50) -> CrossMatchResult:
        logger.info(f'Starting cross-store matching for {self.target_store}')

        bank = self._scan_neutral_bank()
        products = self._fetch_products_without_images()

        matches = []
        unmatched = []
        used_images = set()

        products_sorted = sorted(products, key=lambda p: len(p['keywords']), reverse=True)

        for product in products_sorted:
            match = self._match_product(product, bank)
            if match and match.image_path not in used_images:
                matches.append(match)
                used_images.add(match.image_path)
            else:
                unmatched.append({
                    'id': product['id'],
                    'title': product['title'],
                    'sku': product['sku']
                })

        result = CrossMatchResult(
            target_store=self.target_store,
            total_products=len(products),
            matched=len(matches),
            unmatched=len(unmatched),
            matches=matches,
            unmatched_products=unmatched
        )

        logger.info(f'Cross-store matching: {len(matches)} matched, {len(unmatched)} unmatched')
        return result

    def save_report(self, result: CrossMatchResult, output_dir: str = '/opt/odi/data'):
        by_source = {}
        for m in result.matches:
            by_source.setdefault(m.source_store, []).append(m)

        report = {
            'target_store': result.target_store,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total_products': result.total_products,
                'matched': result.matched,
                'unmatched': result.unmatched,
                'match_rate': f'{result.matched/result.total_products*100:.1f}%' if result.total_products else '0%'
            },
            'by_source': {k: len(v) for k, v in by_source.items()},
            'matches': [
                {
                    'product_id': m.product_id,
                    'title': m.product_title,
                    'sku': m.product_sku,
                    'image': m.image_path,
                    'source': m.source_store,
                    'similarity': round(m.similarity, 3)
                }
                for m in sorted(result.matches, key=lambda x: -x.similarity)
            ],
            'unmatched_products': result.unmatched_products,
            'ai_generation_needed': len(result.unmatched_products)
        }

        path = os.path.join(output_dir, f'{result.target_store}_cross_store_matching.json')
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f'Report saved: {path}')
        return path


if __name__ == '__main__':
    import sys

    store = sys.argv[1].upper() if len(sys.argv) > 1 else 'OH_IMPORTACIONES'

    matcher = CrossStoreMatcher(store)
    result = matcher.match()
    matcher.save_report(result)

    print(f'\n=== {store} Cross-Store Matching ===')
    print(f'Total products: {result.total_products}')
    print(f'Matched: {result.matched}')
    print(f'Unmatched (need AI): {result.unmatched}')
    if result.total_products:
        print(f'Match rate: {result.matched/result.total_products*100:.1f}%')
