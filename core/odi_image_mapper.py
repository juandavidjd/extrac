#!/usr/bin/env python3
"""ODI Image Mapper V18.1 - Maps images from bank to Shopify products
FIXED: Better title matching for stores like STORE where bank uses descriptive names.
"""
import os, re, json, glob, time, base64, logging, requests
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ImageMatch:
    product_id: int
    sku: str
    title: str
    image_path: str
    match_type: str
    confidence: float

@dataclass
class MappingResult:
    store: str
    total_products: int
    products_with_images: int
    products_without_images: int
    images_in_bank: int
    matched: int
    unmatched: int
    matches: List[ImageMatch] = field(default_factory=list)
    unmatched_products: List[dict] = field(default_factory=list)
    unmatched_images: List[str] = field(default_factory=list)

class ImageMapper:
    BANK_PATHS = [
        '/mnt/volume_sfo3_01/profesion/ecosistema_odi/{store}/imagenes',
        '/opt/odi/data/{store}/smart_film_images',
        '/opt/odi/data/{store}/images',
    ]
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

    # Common prefixes/suffixes to remove for title matching
    TITLE_PREFIXES = ['empaque', 'kit', 'set', 'juego', 'par', 'repuesto', 'pieza']
    TITLE_SUFFIXES = ['motocarguero', 'carguero', 'vaisand', 'ceronte', 'odi']

    # Stopwords for keyword extraction
    STOPWORDS = {'de', 'del', 'la', 'el', 'los', 'las', 'para', 'con', 'sin', 'en', 'y', 'o', 'a', 'al', 'por'}

    def __init__(self, store, brands_dir='/opt/odi/data/brands'):
        self.store = store.upper()
        self.brands_dir = brands_dir
        self.shop = self.token = None
        self._load_credentials()

    def _load_credentials(self):
        config_path = os.path.join(self.brands_dir, f'{self.store.lower()}.json')
        if not os.path.exists(config_path):
            for f in glob.glob(f'{self.brands_dir}/*.json'):
                with open(f) as fp:
                    data = json.load(fp)
                name = data.get('name', '').upper().replace(' MOTOS', '').replace(' ', '_')
                if name == self.store:
                    config_path = f
                    break
        if os.path.exists(config_path):
            with open(config_path) as f:
                data = json.load(f)
            self.shop = data.get('shopify', {}).get('shop')
            self.token = data.get('shopify', {}).get('token')
            logger.info(f'Loaded credentials for {self.store}: {self.shop}')
        else:
            raise ValueError(f'No brand config found for {self.store}')

    def _get_bank_paths(self):
        return [p.format(store=self.store) for p in self.BANK_PATHS if os.path.isdir(p.format(store=self.store))]

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text, removing stopwords and short words."""
        # Remove accents
        text = text.lower()
        text = text.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
        # Remove prefixes/suffixes
        for prefix in self.TITLE_PREFIXES:
            if text.startswith(prefix + ' '):
                text = text[len(prefix)+1:]
        for suffix in self.TITLE_SUFFIXES:
            if text.endswith(' ' + suffix):
                text = text[:-len(suffix)-1]
        # Split into words
        words = re.findall(r'[a-z]+', text)
        # Filter stopwords and short words
        keywords = {w for w in words if w not in self.STOPWORDS and len(w) >= 3}
        return keywords

    def _keyword_overlap(self, kw1: Set[str], kw2: Set[str]) -> float:
        """Calculate Jaccard similarity between two keyword sets."""
        if not kw1 or not kw2:
            return 0.0
        intersection = len(kw1 & kw2)
        union = len(kw1 | kw2)
        return intersection / union if union > 0 else 0.0

    def _title_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using SequenceMatcher."""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def _scan_image_bank(self):
        """Scan bank and create index with multiple key types."""
        images = {}  # normalized_name -> (path, keywords, original_name)
        for bank_path in self._get_bank_paths():
            for ext in self.IMAGE_EXTENSIONS:
                for img_path in glob.glob(f'{bank_path}/*{ext}') + glob.glob(f'{bank_path}/*{ext.upper()}'):
                    filename = os.path.splitext(os.path.basename(img_path))[0]
                    norm_name = re.sub(r'[^a-z0-9]', '', filename.lower())
                    keywords = self._extract_keywords(filename)

                    if norm_name not in images:
                        images[norm_name] = {
                            'path': img_path,
                            'keywords': keywords,
                            'original': filename
                        }

                    # Also index without trailing numbers (for _1, _2 variants)
                    base_name = re.sub(r'[_\-]?\d+$', '', filename.lower())
                    base_norm = re.sub(r'[^a-z0-9]', '', base_name)
                    if base_norm and base_norm != norm_name and base_norm not in images:
                        images[base_norm] = images[norm_name]

        logger.info(f'Scanned {len(images)} unique images from bank')
        return images

    def _normalize(self, s):
        return re.sub(r'[^a-z0-9]', '', (s or '').lower())

    def _extract_sku_base(self, sku):
        """Extract base SKU removing common suffixes like 'PAQUETE X 10'"""
        if not sku:
            return ''
        sku = re.sub(r'\s*(paquete|pack|x\s*\d+|unidad|und).*$', '', sku, flags=re.IGNORECASE)
        sku = sku.strip(' -_')
        return self._normalize(sku)

    def _fetch_products_without_images(self):
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
                    keywords = self._extract_keywords(p['title'])
                    products.append({
                        'id': p['id'],
                        'title': p['title'],
                        'sku': sku,
                        'keywords': keywords
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

    def _match_product(self, product, bank):
        sku, title, pid = product.get('sku',''), product.get('title',''), product['id']
        prod_keywords = product.get('keywords', set())

        # Strategy 1: Exact SKU match
        norm_sku = self._normalize(sku)
        if norm_sku and norm_sku in bank:
            return ImageMatch(pid, sku, title, bank[norm_sku]['path'], 'exact_sku', 1.0)

        # Strategy 2: Base SKU match
        base_sku = self._extract_sku_base(sku)
        if base_sku and base_sku in bank:
            return ImageMatch(pid, sku, title, bank[base_sku]['path'], 'base_sku', 0.95)

        # Strategy 3: SKU prefix/suffix matching
        if base_sku and len(base_sku) >= 4:
            for img_name, img_data in bank.items():
                if len(img_name) >= 4:
                    if img_name.startswith(base_sku) or base_sku.startswith(img_name):
                        overlap = min(len(base_sku), len(img_name))
                        conf = overlap / max(len(base_sku), len(img_name))
                        if conf >= 0.6:
                            return ImageMatch(pid, sku, title, img_data['path'], 'prefix_sku', conf)

        # Strategy 4: Code extraction from SKU
        if sku:
            codes = re.findall(r'[a-zA-Z]{2,}\d{2,}[a-zA-Z0-9]*|\d{4,}[a-zA-Z]?', sku)
            for code in codes:
                norm_code = self._normalize(code)
                if len(norm_code) >= 5:
                    for img_name, img_data in bank.items():
                        if norm_code in img_name:
                            return ImageMatch(pid, sku, title, img_data['path'], 'code_in_name', 0.92)

        # Strategy 5: Keyword overlap matching (for descriptive names like STORE)
        if prod_keywords:
            best_match = None
            best_score = 0.0

            for img_name, img_data in bank.items():
                img_keywords = img_data.get('keywords', set())
                if img_keywords:
                    # Calculate keyword overlap (Jaccard)
                    overlap_score = self._keyword_overlap(prod_keywords, img_keywords)

                    # SPECIAL: If ALL image keywords are subset of product, boost score
                    # Image names are shorter, so subset matching is important
                    if img_keywords.issubset(prod_keywords) and len(img_keywords) >= 1:
                        subset_score = 0.4 + (0.15 * len(img_keywords))  # 0.55 for 1kw, 0.70 for 2kw
                        overlap_score = max(overlap_score, subset_score)

                    # Also check string similarity for shorter names
                    title_score = self._title_similarity(title, img_data.get('original', img_name))

                    # Combined score (keyword overlap is more reliable)
                    combined_score = (overlap_score * 0.8) + (title_score * 0.2)

                    if combined_score > best_score and combined_score >= 0.15:
                        best_score = combined_score
                        best_match = (img_data['path'], img_name)

            if best_match and best_score >= 0.15:
                return ImageMatch(pid, sku, title, best_match[0], 'keyword_match', best_score)

        # Strategy 6: Title substring matching (fallback)
        norm_title = self._normalize(title)
        if norm_title and len(norm_title) >= 8:
            for img_name, img_data in bank.items():
                if len(img_name) >= 5 and (img_name in norm_title or norm_title in img_name):
                    conf = min(len(norm_title), len(img_name)) / max(len(norm_title), len(img_name))
                    if conf >= 0.4:
                        return ImageMatch(pid, sku, title, img_data['path'], 'title_substring', conf)

        return None

    def map_images(self):
        bank = self._scan_image_bank()
        products = self._fetch_products_without_images()

        r = requests.get(f'https://{self.shop}/admin/api/2024-01/products/count.json',
                        headers={'X-Shopify-Access-Token': self.token}, timeout=10)
        total = r.json().get('count', 0)

        matches, unmatched_prods, matched_paths = [], [], set()

        # Sort products by keyword count (more keywords = more specific = match first)
        products_sorted = sorted(products, key=lambda p: len(p.get('keywords', set())), reverse=True)

        for p in products_sorted:
            m = self._match_product(p, bank)
            if m and m.image_path not in matched_paths:
                matches.append(m)
                matched_paths.add(m.image_path)
            else:
                unmatched_prods.append({'id': p['id'], 'title': p['title'], 'sku': p['sku']})

        # Find unmatched images
        all_bank_paths = {img_data['path'] for img_data in bank.values()}
        unmatched_imgs = list(all_bank_paths - matched_paths)

        # Count products with images
        with_images = total - len(products)

        result = MappingResult(
            store=self.store,
            total_products=total,
            products_with_images=with_images,
            products_without_images=len(products),
            images_in_bank=len(set(img_data['path'] for img_data in bank.values())),
            matched=len(matches),
            unmatched=len(unmatched_prods),
            matches=matches,
            unmatched_products=unmatched_prods,
            unmatched_images=unmatched_imgs
        )

        logger.info(f'Mapping complete: {len(matches)} matched, {len(unmatched_prods)} unmatched')
        return result

    def upload_matches(self, result: MappingResult, delay: float = 0.8):
        """Upload matched images to Shopify."""
        logger.info(f'Starting upload for {len(result.matches)} matches')
        stats = {'success': 0, 'failed': 0, 'by_type': {}}

        for i, match in enumerate(result.matches):
            try:
                with open(match.image_path, 'rb') as f:
                    img_data = base64.b64encode(f.read()).decode()

                url = f'https://{self.shop}/admin/api/2024-01/products/{match.product_id}/images.json'
                headers = {'X-Shopify-Access-Token': self.token, 'Content-Type': 'application/json'}
                payload = {
                    'image': {
                        'attachment': img_data,
                        'filename': os.path.basename(match.image_path)
                    }
                }

                r = requests.post(url, headers=headers, json=payload, timeout=60)

                if r.status_code in [200, 201]:
                    stats['success'] += 1
                    stats['by_type'][match.match_type] = stats['by_type'].get(match.match_type, 0) + 1
                else:
                    stats['failed'] += 1
                    logger.warning(f'Upload failed for {match.product_id}: {r.status_code}')

            except Exception as e:
                stats['failed'] += 1
                logger.warning(f'Upload error for {match.product_id}: {e}')

            if (i + 1) % 50 == 0:
                logger.info(f'Progress: {i+1}/{len(result.matches)} | Success: {stats["success"]}')

            time.sleep(delay)

        logger.info(f'Upload complete: {stats["success"]} success, {stats["failed"]} failed')
        return stats


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage: python odi_image_mapper.py <STORE> [--upload] [--debug]')
        sys.exit(1)

    store = sys.argv[1].upper()
    do_upload = '--upload' in sys.argv
    debug = '--debug' in sys.argv

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    mapper = ImageMapper(store)
    result = mapper.map_images()

    print(f'\n=== {store} Image Mapping V18.1 ===')
    print(f'Total products: {result.total_products}')
    print(f'Products with images: {result.products_with_images}')
    print(f'Products without images: {result.products_without_images}')
    print(f'Images in bank: {result.images_in_bank}')
    print(f'Matched: {result.matched}')
    print(f'Unmatched: {result.unmatched}')

    if result.matched > 0:
        print(f'\nMatch rate: {result.matched/result.products_without_images*100:.1f}%')
        # Show match types
        types = {}
        for m in result.matches:
            types[m.match_type] = types.get(m.match_type, 0) + 1
        print('\nBy match type:')
        for t, c in sorted(types.items(), key=lambda x: -x[1]):
            print(f'  {t}: {c}')

    if do_upload and result.matched > 0:
        print(f'\nUploading {result.matched} images...')
        stats = mapper.upload_matches(result)
        print(f'\nUpload: {stats["success"]} success, {stats["failed"]} failed')
