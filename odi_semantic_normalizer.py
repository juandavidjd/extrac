#!/usr/bin/env python3
"""
ODI Semantic Normalizer v1.1
============================
Capa de normalización semántica para el sistema ODI.

Responsabilidades:
- Embeddings de nombres + descripción
- Clustering semántico de productos
- Detección de duplicados
- Creación de producto padre (SKU Tree)
- Herencia de imágenes + precios
- Parsing de fitment (marca/modelo/cilindraje/año)

v1.1 Changes:
- Added persistent SQLite cache for embeddings (~/.odi/cache/embeddings_cache.db)
- Machine-friendly ODI_STATS output line for robust parsing
- sklearn AgglomerativeClustering compatibility (metric/affinity)

Autor: ODI Team
Versión: 1.1
"""

import os
import sys
import json
import re
import argparse
import hashlib
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Set, Any
from collections import defaultdict
from datetime import datetime
import unicodedata

import pandas as pd
import numpy as np

# OpenAI para embeddings
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("⚠️  OpenAI no instalado. Embeddings no disponibles.")

# Scikit-learn para clustering
try:
    from sklearn.cluster import DBSCAN, AgglomerativeClustering
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("⚠️  Scikit-learn no instalado. Clustering avanzado no disponible.")


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Umbral de similitud para considerar duplicados (0.0-1.0)
DUPLICATE_THRESHOLD = 0.92

# Umbral para agrupar en familias/variantes
VARIANT_THRESHOLD = 0.85

# Modelo de embeddings
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 512  # Reducido para eficiencia

# Patrones de variantes en códigos
VARIANT_CODE_PATTERNS = [
    r'^(.+?)[-_]?([A-Z])(\d{2})$',      # P011-C01, P011-C02 → P011
    r'^(.+?)[-_](\d{1,2})$',            # MOT-1, MOT-2 → MOT
    r'^(.+?)[-_]([SMLX]{1,2})$',        # CASCO-M, CASCO-L → CASCO
    r'^(.+?)(\d{3})(\d{2})$',           # 50100, 50101 → 501
]

# Marcas de motos conocidas
MOTORCYCLE_BRANDS = {
    'honda', 'yamaha', 'suzuki', 'kawasaki', 'bajaj', 'tvs', 'hero',
    'pulsar', 'akt', 'auteco', 'victory', 'um', 'kymco', 'sym',
    'royal enfield', 'ktm', 'bmw', 'ducati', 'harley', 'vespa',
    'piaggio', 'italika', 'ayco', 'UM', 'cf moto', 'benelli',
    'aprilia', 'husqvarna', 'zontes', 'voge', 'keeway'
}

# Patrones de modelos comunes
MODEL_PATTERNS = [
    r'\b(cbf|cb|cbr|crf|xr|xl|nxr|pcx|sh|forza|adv)\s*(\d{2,3})\b',  # Honda
    r'\b(ybr|fz|mt|r\d|xtz|nmax|tmax|aerox)\s*(\d{2,3})\b',          # Yamaha
    r'\b(pulsar|discover|boxer|platino|ct|dominar)\s*(\d{2,3})\b',    # Bajaj
    r'\b(apache|ntorq|jupiter|wego)\s*(\d{2,3})\b',                   # TVS
    r'\b(splendor|passion|glamour|xtreme|xpulse)\s*(\d{2,3})\b',      # Hero
    r'\b(duke|rc|adventure)\s*(\d{2,4})\b',                           # KTM
    r'\b(ninja|z|versys|vulcan)\s*(\d{2,4})\b',                       # Kawasaki
    r'\b(gsx|gixxer|burgman|access|intruder)\s*(\d{2,3})\b',          # Suzuki
]

# Patrones de cilindraje
CC_PATTERNS = [
    r'(\d{2,4})\s*cc\b',
    r'(\d{2,4})\s*c\.?c\.?\b',
    r'\b(\d{2,4})\s*cilindrada\b',
    r'\b(50|70|90|100|110|115|125|135|150|160|180|200|220|250|300|350|400|500|600|650|750|800|900|1000|1100|1200)\b',
]

# Patrones de año
YEAR_PATTERNS = [
    r'\b(19[89]\d|20[0-2]\d)\b',         # 1980-2029
    r'\b(\d{2})-(\d{2})\b',               # 98-05
    r'modelo\s*(\d{4})',                   # modelo 2020
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ProductEmbedding:
    """Embedding de un producto."""
    sku_odi: str
    codigo: str
    nombre: str
    descripcion: str
    text_combined: str
    embedding: Optional[List[float]] = None
    embedding_hash: str = ""

    def __post_init__(self):
        if self.embedding:
            self.embedding_hash = hashlib.md5(
                str(self.embedding[:10]).encode()
            ).hexdigest()[:8]


@dataclass
class DuplicateGroup:
    """Grupo de productos duplicados."""
    group_id: str
    canonical_sku: str  # El SKU principal (más completo)
    members: List[str]  # SKUs de los miembros
    similarity_scores: Dict[str, float]  # SKU → score vs canonical
    merge_recommendation: str  # "keep_first", "merge_all", "review"
    confidence: float


@dataclass
class ProductFamily:
    """Familia de productos (SKU Tree)."""
    family_id: str
    parent_sku: str
    parent_nombre: str
    parent_codigo_base: str
    variants: List[Dict[str, Any]]  # Lista de variantes
    shared_attributes: Dict[str, Any]  # Atributos comunes
    variant_attribute: str  # Qué varía (color, tamaño, etc.)
    total_variants: int


@dataclass
class FitmentData:
    """Datos de compatibilidad/fitment."""
    marca: str = ""
    modelo: str = ""
    cilindraje: str = ""
    año_inicio: str = ""
    año_fin: str = ""
    raw_text: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_valid(self) -> bool:
        return bool(self.marca or self.modelo or self.cilindraje)


@dataclass
class NormalizationResult:
    """Resultado de la normalización semántica."""
    total_products: int
    duplicates_found: int
    families_created: int
    products_with_fitment: int
    duplicate_groups: List[DuplicateGroup]
    product_families: List[ProductFamily]
    fitment_data: Dict[str, FitmentData]
    processing_time_seconds: float
    embeddings_generated: int


# =============================================================================
# UTILIDADES DE TEXTO
# =============================================================================

def normalize_text(text: str) -> str:
    """Normaliza texto removiendo acentos y caracteres especiales."""
    if not text:
        return ""
    # Remover acentos
    text = unicodedata.normalize('NFKD', str(text))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    # Lowercase y espacios
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def extract_base_code(codigo: str) -> str:
    """Extrae el código base sin sufijos de variante."""
    if not codigo:
        return ""

    codigo_upper = str(codigo).upper().strip()

    for pattern in VARIANT_CODE_PATTERNS:
        match = re.match(pattern, codigo_upper, re.IGNORECASE)
        if match:
            return match.group(1)

    return codigo_upper


def text_similarity_simple(text1: str, text2: str) -> float:
    """Calcula similitud simple basada en tokens comunes."""
    if not text1 or not text2:
        return 0.0

    tokens1 = set(normalize_text(text1).split())
    tokens2 = set(normalize_text(text2).split())

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    return len(intersection) / len(union) if union else 0.0


# =============================================================================
# FITMENT PARSER
# =============================================================================

class FitmentParser:
    """Parser para extraer información de compatibilidad de productos."""

    def __init__(self):
        self.brand_patterns = self._compile_brand_patterns()

    def _compile_brand_patterns(self) -> List[re.Pattern]:
        """Compila patrones de marcas."""
        patterns = []
        for brand in MOTORCYCLE_BRANDS:
            pattern = re.compile(rf'\b{re.escape(brand)}\b', re.IGNORECASE)
            patterns.append((brand, pattern))
        return patterns

    def parse(self, text: str) -> FitmentData:
        """Extrae datos de fitment de un texto."""
        if not text:
            return FitmentData()

        text_lower = text.lower()
        text_normalized = normalize_text(text)

        fitment = FitmentData(raw_text=text)
        confidence_factors = []

        # 1. Detectar marca
        for brand, pattern in self.brand_patterns:
            if pattern.search(text):
                fitment.marca = brand.upper()
                confidence_factors.append(0.3)
                break

        # 2. Detectar modelo
        for pattern in MODEL_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                model_name = match.group(1).upper()
                model_cc = match.group(2) if len(match.groups()) > 1 else ""
                fitment.modelo = f"{model_name} {model_cc}".strip()
                confidence_factors.append(0.3)
                break

        # 3. Detectar cilindraje
        for pattern in CC_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                cc_value = match.group(1)
                # Validar que sea un cilindraje razonable
                if 50 <= int(cc_value) <= 2000:
                    fitment.cilindraje = f"{cc_value}cc"
                    confidence_factors.append(0.2)
                    break

        # 4. Detectar años
        for pattern in YEAR_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                if len(match.groups()) == 2:
                    # Formato 98-05
                    year1 = int(match.group(1))
                    year2 = int(match.group(2))
                    if year1 < 50:
                        year1 += 2000
                    else:
                        year1 += 1900
                    if year2 < 50:
                        year2 += 2000
                    else:
                        year2 += 1900
                    fitment.año_inicio = str(year1)
                    fitment.año_fin = str(year2)
                else:
                    fitment.año_inicio = match.group(1)
                confidence_factors.append(0.2)
                break

        # Calcular confianza total
        fitment.confidence = min(sum(confidence_factors), 1.0)

        return fitment

    def parse_batch(self, products: pd.DataFrame) -> Dict[str, FitmentData]:
        """Procesa múltiples productos."""
        results = {}

        for idx, row in products.iterrows():
            sku = row.get('sku_odi', str(idx))

            # Combinar nombre + descripción para análisis
            text_parts = []
            if pd.notna(row.get('nombre')):
                text_parts.append(str(row['nombre']))
            if pd.notna(row.get('descripcion')):
                text_parts.append(str(row['descripcion']))

            combined_text = ' '.join(text_parts)
            fitment = self.parse(combined_text)

            if fitment.is_valid():
                results[sku] = fitment

        return results


# =============================================================================
# EMBEDDING CACHE (SQLite)
# =============================================================================

# Default cache location
DEFAULT_CACHE_DIR = Path.home() / ".odi" / "cache"
DEFAULT_CACHE_DB = DEFAULT_CACHE_DIR / "embeddings_cache.db"


class EmbeddingCache:
    """Cache persistente de embeddings usando SQLite con WAL mode."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_CACHE_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create persistent connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            # Enable WAL mode for better concurrent read/write performance
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def _init_db(self):
        """Inicializa la base de datos."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                text_hash TEXT PRIMARY KEY,
                model TEXT,
                dimensions INTEGER,
                embedding TEXT,
                created_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON embeddings(model)")
        conn.commit()

    def get(self, text_hash: str, model: str) -> Optional[List[float]]:
        """Obtiene embedding del cache."""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT embedding FROM embeddings WHERE text_hash = ? AND model = ?",
            (text_hash, model)
        )
        row = cursor.fetchone()
        if row:
            # Deserialize from JSON TEXT
            return json.loads(row[0])
        return None

    def set(self, text_hash: str, model: str, dimensions: int, embedding: List[float]):
        """Guarda embedding en cache."""
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO embeddings
               (text_hash, model, dimensions, embedding, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (text_hash, model, dimensions, json.dumps(embedding), datetime.now().isoformat())
        )
        conn.commit()

    def get_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas del cache."""
        conn = self._get_conn()
        cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
        count = cursor.fetchone()[0]
        return {"total_cached": count, "db_path": str(self.db_path)}

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self._conn:
            self._conn.close()
            self._conn = None


# =============================================================================
# EMBEDDING GENERATOR
# =============================================================================

class EmbeddingGenerator:
    """Genera embeddings usando OpenAI con cache persistente."""

    def __init__(self, api_key: Optional[str] = None, cache_db: Optional[Path] = None):
        if not HAS_OPENAI:
            raise RuntimeError("OpenAI no está instalado")

        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY no configurada")

        self.client = OpenAI(api_key=self.api_key)
        self.model = EMBEDDING_MODEL
        self.dimensions = EMBEDDING_DIMENSIONS

        # Persistent cache (SQLite) + in-memory cache for session
        self.persistent_cache = EmbeddingCache(cache_db)
        self.memory_cache: Dict[str, List[float]] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def _create_text_for_embedding(self, row: pd.Series) -> str:
        """Crea texto combinado para embedding."""
        parts = []

        # Código (importante para matching)
        if pd.notna(row.get('codigo')):
            parts.append(f"codigo:{row['codigo']}")

        # Nombre (muy importante)
        if pd.notna(row.get('nombre')):
            parts.append(str(row['nombre']))

        # Descripción
        if pd.notna(row.get('descripcion')):
            parts.append(str(row['descripcion']))

        # Categoría
        if pd.notna(row.get('categoria')):
            parts.append(f"categoria:{row['categoria']}")

        return ' '.join(parts)

    def generate_single(self, text: str) -> List[float]:
        """Genera embedding para un solo texto."""
        if not text.strip():
            return [0.0] * self.dimensions

        # Cache lookup (memory first, then persistent)
        cache_key = hashlib.md5(text.encode()).hexdigest()

        # 1. Check memory cache
        if cache_key in self.memory_cache:
            self.cache_hits += 1
            return self.memory_cache[cache_key]

        # 2. Check persistent cache
        cached = self.persistent_cache.get(cache_key, self.model)
        if cached:
            self.memory_cache[cache_key] = cached  # Warm up memory cache
            self.cache_hits += 1
            return cached

        # 3. Generate new embedding
        self.cache_misses += 1
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.model,
                dimensions=self.dimensions
            )
            embedding = response.data[0].embedding

            # Save to both caches
            self.memory_cache[cache_key] = embedding
            self.persistent_cache.set(cache_key, self.model, self.dimensions, embedding)

            return embedding
        except Exception as e:
            print(f"⚠️  Error generando embedding: {e}")
            return [0.0] * self.dimensions

    def generate_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Genera embeddings en batch con cache check."""
        all_embeddings: List[Optional[List[float]]] = [None] * len(texts)

        # First pass: check cache for all texts
        texts_to_generate = []  # (original_index, text, cache_key)
        for i, text in enumerate(texts):
            if not text.strip():
                all_embeddings[i] = [0.0] * self.dimensions
                continue

            cache_key = hashlib.md5(text.encode()).hexdigest()

            # Check memory cache
            if cache_key in self.memory_cache:
                all_embeddings[i] = self.memory_cache[cache_key]
                self.cache_hits += 1
                continue

            # Check persistent cache
            cached = self.persistent_cache.get(cache_key, self.model)
            if cached:
                all_embeddings[i] = cached
                self.memory_cache[cache_key] = cached
                self.cache_hits += 1
                continue

            # Need to generate
            texts_to_generate.append((i, text, cache_key))

        if texts_to_generate:
            print(f"   📦 Cache: {self.cache_hits} hits, {len(texts_to_generate)} to generate")

        # Second pass: generate missing embeddings in batches
        for batch_start in range(0, len(texts_to_generate), batch_size):
            batch = texts_to_generate[batch_start:batch_start + batch_size]
            batch_texts = [t[1] for t in batch]

            try:
                response = self.client.embeddings.create(
                    input=batch_texts,
                    model=self.model,
                    dimensions=self.dimensions
                )

                for j, (orig_idx, text, cache_key) in enumerate(batch):
                    embedding = response.data[j].embedding
                    all_embeddings[orig_idx] = embedding

                    # Save to both caches
                    self.memory_cache[cache_key] = embedding
                    self.persistent_cache.set(cache_key, self.model, self.dimensions, embedding)
                    self.cache_misses += 1

            except Exception as e:
                print(f"⚠️  Error en batch {batch_start//batch_size}: {e}")
                for orig_idx, _, _ in batch:
                    if all_embeddings[orig_idx] is None:
                        all_embeddings[orig_idx] = [0.0] * self.dimensions

        # Ensure all embeddings are filled
        return [e if e is not None else [0.0] * self.dimensions for e in all_embeddings]

    def generate_for_dataframe(self, df: pd.DataFrame) -> List[ProductEmbedding]:
        """Genera embeddings para un DataFrame de productos."""
        embeddings = []
        texts = []

        # Preparar textos
        for idx, row in df.iterrows():
            text = self._create_text_for_embedding(row)
            texts.append(text)

        # Reset counters before processing
        self.cache_hits = 0
        self.cache_misses = 0

        print(f"📊 Generando embeddings para {len(texts)} productos...")

        # Generar en batch (with cache optimization)
        raw_embeddings = self.generate_batch(texts)

        # Crear objetos ProductEmbedding
        for i, (idx, row) in enumerate(df.iterrows()):
            pe = ProductEmbedding(
                sku_odi=row.get('sku_odi', str(idx)),
                codigo=str(row.get('codigo', '')),
                nombre=str(row.get('nombre', '')),
                descripcion=str(row.get('descripcion', '')),
                text_combined=texts[i],
                embedding=raw_embeddings[i]
            )
            embeddings.append(pe)

        # Print cache stats
        cache_stats = self.persistent_cache.get_stats()
        print(f"   💾 Cache stats: {self.cache_hits} hits, {self.cache_misses} generated, {cache_stats['total_cached']} total in DB")

        return embeddings


# =============================================================================
# DUPLICATE DETECTOR
# =============================================================================

class DuplicateDetector:
    """Detecta productos duplicados usando similitud semántica."""

    def __init__(self, threshold: float = DUPLICATE_THRESHOLD):
        self.threshold = threshold

    def detect_with_embeddings(
        self,
        embeddings: List[ProductEmbedding]
    ) -> List[DuplicateGroup]:
        """Detecta duplicados usando embeddings."""
        if not HAS_SKLEARN:
            print("⚠️  Sklearn no disponible, usando detección simple")
            return self.detect_simple(embeddings)

        n = len(embeddings)
        if n < 2:
            return []

        print(f"🔍 Analizando {n} productos para duplicados...")

        # Crear matriz de embeddings
        embedding_matrix = np.array([e.embedding for e in embeddings])

        # Calcular similitud coseno
        similarity_matrix = cosine_similarity(embedding_matrix)

        # Encontrar pares con alta similitud
        duplicate_groups = []
        processed = set()

        for i in range(n):
            if i in processed:
                continue

            # Encontrar todos los productos similares a i
            similar_indices = []
            for j in range(i + 1, n):
                if j in processed:
                    continue
                if similarity_matrix[i, j] >= self.threshold:
                    similar_indices.append(j)

            if similar_indices:
                # Crear grupo de duplicados
                group_members = [i] + similar_indices

                # Determinar el canónico (el más completo)
                canonical_idx = self._select_canonical(
                    [embeddings[idx] for idx in group_members]
                )
                canonical_sku = embeddings[group_members[canonical_idx]].sku_odi

                # Calcular scores
                similarity_scores = {}
                for idx in group_members:
                    if idx != group_members[canonical_idx]:
                        score = similarity_matrix[group_members[canonical_idx], idx]
                        similarity_scores[embeddings[idx].sku_odi] = float(score)

                group = DuplicateGroup(
                    group_id=f"DUP-{len(duplicate_groups)+1:04d}",
                    canonical_sku=canonical_sku,
                    members=[embeddings[idx].sku_odi for idx in group_members],
                    similarity_scores=similarity_scores,
                    merge_recommendation=self._get_merge_recommendation(
                        similarity_scores
                    ),
                    confidence=float(np.mean(list(similarity_scores.values()))) if similarity_scores else 1.0
                )
                duplicate_groups.append(group)

                # Marcar como procesados
                processed.update(group_members)

        return duplicate_groups

    def detect_simple(
        self,
        embeddings: List[ProductEmbedding]
    ) -> List[DuplicateGroup]:
        """Detección simple sin sklearn (basada en texto)."""
        n = len(embeddings)
        duplicate_groups = []
        processed = set()

        for i in range(n):
            if i in processed:
                continue

            similar_indices = []
            for j in range(i + 1, n):
                if j in processed:
                    continue

                # Similitud de texto simple
                sim = text_similarity_simple(
                    embeddings[i].text_combined,
                    embeddings[j].text_combined
                )
                if sim >= 0.7:  # Umbral más bajo para texto
                    similar_indices.append((j, sim))

            if similar_indices:
                group_members = [i] + [idx for idx, _ in similar_indices]
                canonical_idx = self._select_canonical(
                    [embeddings[idx] for idx in group_members]
                )

                similarity_scores = {
                    embeddings[idx].sku_odi: score
                    for idx, score in similar_indices
                }

                group = DuplicateGroup(
                    group_id=f"DUP-{len(duplicate_groups)+1:04d}",
                    canonical_sku=embeddings[group_members[canonical_idx]].sku_odi,
                    members=[embeddings[idx].sku_odi for idx in group_members],
                    similarity_scores=similarity_scores,
                    merge_recommendation="review",
                    confidence=float(np.mean([s for _, s in similar_indices])) if similar_indices else 0.0
                )
                duplicate_groups.append(group)
                processed.update(group_members)

        return duplicate_groups

    def _select_canonical(self, candidates: List[ProductEmbedding]) -> int:
        """Selecciona el producto canónico (más completo)."""
        scores = []
        for i, c in enumerate(candidates):
            score = 0
            # Priorizar productos con más información
            if c.nombre and len(c.nombre) > 10:
                score += 2
            if c.descripcion and len(c.descripcion) > 20:
                score += 3
            if c.codigo and not c.codigo.startswith('P0'):
                score += 1  # Código real vs sintético
            scores.append((score, i))

        return max(scores, key=lambda x: x[0])[1]

    def _get_merge_recommendation(self, scores: Dict[str, float]) -> str:
        """Determina recomendación de merge."""
        if not scores:
            return "keep_first"

        avg_score = np.mean(list(scores.values()))
        if avg_score >= 0.95:
            return "merge_all"
        elif avg_score >= 0.90:
            return "keep_first"
        else:
            return "review"


# =============================================================================
# VARIANT DETECTOR (SKU TREE)
# =============================================================================

class VariantDetector:
    """Detecta variantes de productos y crea SKU trees."""

    def __init__(self, similarity_threshold: float = VARIANT_THRESHOLD):
        self.threshold = similarity_threshold

    def detect_by_code_pattern(self, df: pd.DataFrame) -> List[ProductFamily]:
        """Detecta familias basándose en patrones de código."""
        families = []
        code_groups = defaultdict(list)

        # Agrupar por código base
        for idx, row in df.iterrows():
            codigo = str(row.get('codigo', ''))
            base_code = extract_base_code(codigo)
            if base_code:
                code_groups[base_code].append({
                    'idx': idx,
                    'sku_odi': row.get('sku_odi', str(idx)),
                    'codigo': codigo,
                    'nombre': row.get('nombre', ''),
                    'descripcion': row.get('descripcion', ''),
                    'precio': row.get('precio'),
                    'imagen': row.get('imagen', '')
                })

        # Crear familias donde hay múltiples variantes
        for base_code, members in code_groups.items():
            if len(members) < 2:
                continue

            # Determinar el padre (el más completo)
            parent = max(members, key=lambda m: len(str(m.get('nombre', ''))))

            # Detectar qué atributo varía
            variant_attr = self._detect_variant_attribute(members)

            family = ProductFamily(
                family_id=f"FAM-{len(families)+1:04d}",
                parent_sku=parent['sku_odi'],
                parent_nombre=parent['nombre'],
                parent_codigo_base=base_code,
                variants=members,
                shared_attributes={
                    'categoria': members[0].get('categoria', ''),
                    'base_code': base_code
                },
                variant_attribute=variant_attr,
                total_variants=len(members)
            )
            families.append(family)

        return families

    def detect_by_embedding(
        self,
        embeddings: List[ProductEmbedding],
        df: pd.DataFrame
    ) -> List[ProductFamily]:
        """Detecta familias usando similitud de embeddings."""
        if not HAS_SKLEARN:
            return []

        n = len(embeddings)
        if n < 2:
            return []

        # Matriz de embeddings
        embedding_matrix = np.array([e.embedding for e in embeddings])

        # Clustering jerárquico with sklearn version compatibility
        # sklearn >= 1.2 uses 'metric', older versions use 'affinity'
        try:
            # Try new sklearn API first (>= 1.2)
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=1 - self.threshold,
                metric='cosine',
                linkage='average'
            )
            labels = clustering.fit_predict(embedding_matrix)
        except TypeError:
            # Fallback to legacy sklearn API (< 1.2)
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=1 - self.threshold,
                affinity='cosine',
                linkage='average'
            )
            labels = clustering.fit_predict(embedding_matrix)

        # Agrupar por cluster
        cluster_groups = defaultdict(list)
        for i, label in enumerate(labels):
            if label >= 0:
                cluster_groups[label].append(i)

        families = []
        for cluster_id, indices in cluster_groups.items():
            if len(indices) < 2:
                continue

            # Obtener datos de cada miembro
            members = []
            for idx in indices:
                row = df.iloc[idx]
                members.append({
                    'idx': idx,
                    'sku_odi': embeddings[idx].sku_odi,
                    'codigo': embeddings[idx].codigo,
                    'nombre': embeddings[idx].nombre,
                    'descripcion': embeddings[idx].descripcion,
                    'precio': row.get('precio'),
                    'imagen': row.get('imagen', '')
                })

            # Determinar padre
            parent = max(members, key=lambda m: len(m.get('descripcion', '')))

            family = ProductFamily(
                family_id=f"FAM-EMB-{len(families)+1:04d}",
                parent_sku=parent['sku_odi'],
                parent_nombre=parent['nombre'],
                parent_codigo_base=extract_base_code(parent['codigo']),
                variants=members,
                shared_attributes={},
                variant_attribute=self._detect_variant_attribute(members),
                total_variants=len(members)
            )
            families.append(family)

        return families

    def _detect_variant_attribute(self, members: List[Dict]) -> str:
        """Detecta qué atributo varía entre miembros."""
        if len(members) < 2:
            return "unknown"

        # Analizar diferencias en códigos
        codigos = [m.get('codigo', '') for m in members]

        # Buscar sufijos comunes
        suffixes = []
        for codigo in codigos:
            match = re.search(r'[-_]?([A-Z]{1,2}|\d{1,2})$', str(codigo))
            if match:
                suffixes.append(match.group(1))

        if suffixes:
            # Verificar si son tamaños
            sizes = {'S', 'M', 'L', 'XL', 'XXL', 'XS'}
            if all(s.upper() in sizes for s in suffixes):
                return "size"

            # Verificar si son colores (letras)
            if all(s.isalpha() and len(s) <= 2 for s in suffixes):
                return "color"

            # Verificar si son números secuenciales
            if all(s.isdigit() for s in suffixes):
                return "variant_number"

        return "variant"


# =============================================================================
# INHERITANCE MANAGER
# =============================================================================

class InheritanceManager:
    """Maneja herencia de atributos entre productos relacionados."""

    def apply_inheritance(
        self,
        df: pd.DataFrame,
        families: List[ProductFamily],
        duplicates: List[DuplicateGroup]
    ) -> pd.DataFrame:
        """Aplica herencia de imagen y precio."""
        df = df.copy()

        # 1. Herencia dentro de familias
        for family in families:
            parent_data = None
            for variant in family.variants:
                if variant['sku_odi'] == family.parent_sku:
                    parent_data = variant
                    break

            if not parent_data:
                continue

            # Propagar imagen del padre a variantes sin imagen
            parent_imagen = parent_data.get('imagen', '')
            parent_precio = parent_data.get('precio')

            for variant in family.variants:
                sku = variant['sku_odi']
                idx = df[df['sku_odi'] == sku].index

                if len(idx) == 0:
                    continue

                idx = idx[0]

                # Heredar imagen si falta
                if parent_imagen and (pd.isna(df.at[idx, 'imagen']) or df.at[idx, 'imagen'] == ''):
                    df.at[idx, 'imagen'] = parent_imagen
                    df.at[idx, 'imagen_heredada'] = True

                # Heredar precio si falta
                if parent_precio and (pd.isna(df.at[idx, 'precio']) or df.at[idx, 'precio'] == 0):
                    df.at[idx, 'precio'] = parent_precio
                    df.at[idx, 'precio_heredado'] = True

        # 2. Herencia entre duplicados
        for group in duplicates:
            canonical_row = df[df['sku_odi'] == group.canonical_sku]
            if len(canonical_row) == 0:
                continue

            canonical_row = canonical_row.iloc[0]

            for member_sku in group.members:
                if member_sku == group.canonical_sku:
                    continue

                idx = df[df['sku_odi'] == member_sku].index
                if len(idx) == 0:
                    continue

                idx = idx[0]

                # Heredar imagen
                if canonical_row.get('imagen') and (pd.isna(df.at[idx, 'imagen']) or df.at[idx, 'imagen'] == ''):
                    df.at[idx, 'imagen'] = canonical_row['imagen']
                    df.at[idx, 'imagen_heredada'] = True

                # Heredar precio
                if canonical_row.get('precio') and (pd.isna(df.at[idx, 'precio']) or df.at[idx, 'precio'] == 0):
                    df.at[idx, 'precio'] = canonical_row['precio']
                    df.at[idx, 'precio_heredado'] = True

        return df


# =============================================================================
# SEMANTIC NORMALIZER (MAIN CLASS)
# =============================================================================

class SemanticNormalizer:
    """
    Normalizador Semántico Principal.

    Orquesta todas las operaciones de normalización:
    - Generación de embeddings
    - Detección de duplicados
    - Agrupación en familias
    - Parsing de fitment
    - Herencia de atributos
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_embeddings: bool = True,
        duplicate_threshold: float = DUPLICATE_THRESHOLD,
        variant_threshold: float = VARIANT_THRESHOLD
    ):
        self.use_embeddings = use_embeddings and HAS_OPENAI
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')

        self.duplicate_threshold = duplicate_threshold
        self.variant_threshold = variant_threshold

        # Componentes
        self.fitment_parser = FitmentParser()
        self.duplicate_detector = DuplicateDetector(threshold=duplicate_threshold)
        self.variant_detector = VariantDetector(similarity_threshold=variant_threshold)
        self.inheritance_manager = InheritanceManager()

        self.embedding_generator = None
        if self.use_embeddings and self.api_key:
            try:
                self.embedding_generator = EmbeddingGenerator(api_key=self.api_key)
            except Exception as e:
                print(f"⚠️  No se pudo inicializar embeddings: {e}")
                self.use_embeddings = False

    def normalize(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        apply_inheritance: bool = True
    ) -> Tuple[pd.DataFrame, NormalizationResult]:
        """
        Ejecuta normalización semántica completa.

        Args:
            input_file: CSV de catálogo (formato ODI)
            output_file: Archivo de salida (opcional)
            apply_inheritance: Aplicar herencia de atributos

        Returns:
            DataFrame normalizado y resultado
        """
        start_time = datetime.now()

        print(f"\n{'='*60}")
        print(f"🧠 ODI SEMANTIC NORMALIZER v1.1")
        print(f"{'='*60}")
        print(f"📂 Input: {input_file}")

        # 1. Cargar datos
        df = self._load_catalog(input_file)
        print(f"📊 Productos cargados: {len(df)}")

        # 2. Generar embeddings
        embeddings = []
        embeddings_generated = 0

        if self.use_embeddings and self.embedding_generator:
            print("\n🔢 Generando embeddings...")
            embeddings = self.embedding_generator.generate_for_dataframe(df)
            embeddings_generated = len(embeddings)
            print(f"✅ {embeddings_generated} embeddings generados")

        # 3. Detectar duplicados
        print("\n🔍 Detectando duplicados...")
        if embeddings:
            duplicate_groups = self.duplicate_detector.detect_with_embeddings(embeddings)
        else:
            # Crear embeddings simples para detección de texto
            simple_embeddings = [
                ProductEmbedding(
                    sku_odi=row.get('sku_odi', str(idx)),
                    codigo=str(row.get('codigo', '')),
                    nombre=str(row.get('nombre', '')),
                    descripcion=str(row.get('descripcion', '')),
                    text_combined=f"{row.get('nombre', '')} {row.get('descripcion', '')}"
                )
                for idx, row in df.iterrows()
            ]
            duplicate_groups = self.duplicate_detector.detect_simple(simple_embeddings)

        print(f"✅ {len(duplicate_groups)} grupos de duplicados encontrados")

        # 4. Detectar familias/variantes
        print("\n👨‍👩‍👧‍👦 Detectando familias de productos...")
        families_by_code = self.variant_detector.detect_by_code_pattern(df)
        print(f"   📌 Por patrón de código: {len(families_by_code)}")

        families_by_embedding = []
        if embeddings:
            families_by_embedding = self.variant_detector.detect_by_embedding(embeddings, df)
            print(f"   📌 Por similitud semántica: {len(families_by_embedding)}")

        all_families = families_by_code + families_by_embedding

        # 5. Parsing de fitment
        print("\n🏍️  Extrayendo datos de fitment...")
        fitment_data = self.fitment_parser.parse_batch(df)
        print(f"✅ {len(fitment_data)} productos con fitment detectado")

        # 6. Aplicar herencia
        if apply_inheritance:
            print("\n🔗 Aplicando herencia de atributos...")
            df = self.inheritance_manager.apply_inheritance(
                df, all_families, duplicate_groups
            )

        # 7. Agregar columnas de normalización
        df = self._add_normalization_columns(
            df, duplicate_groups, all_families, fitment_data
        )

        # 8. Guardar resultado
        if output_file:
            self._save_results(df, output_file, duplicate_groups, all_families, fitment_data)

        # Calcular tiempo
        duration = (datetime.now() - start_time).total_seconds()

        result = NormalizationResult(
            total_products=len(df),
            duplicates_found=sum(len(g.members) - 1 for g in duplicate_groups),
            families_created=len(all_families),
            products_with_fitment=len(fitment_data),
            duplicate_groups=duplicate_groups,
            product_families=all_families,
            fitment_data=fitment_data,
            processing_time_seconds=duration,
            embeddings_generated=embeddings_generated
        )

        self._print_summary(result)

        return df, result

    def _load_catalog(self, file_path: str) -> pd.DataFrame:
        """Carga catálogo CSV."""
        # Detectar separador
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()

        sep = ';' if ';' in first_line else ','

        df = pd.read_csv(file_path, sep=sep, encoding='utf-8')

        # Asegurar columnas necesarias
        required_cols = ['sku_odi', 'codigo', 'nombre']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Columna requerida '{col}' no encontrada")

        return df

    def _add_normalization_columns(
        self,
        df: pd.DataFrame,
        duplicates: List[DuplicateGroup],
        families: List[ProductFamily],
        fitment: Dict[str, FitmentData]
    ) -> pd.DataFrame:
        """Agrega columnas de normalización al DataFrame."""
        df = df.copy()

        # Columnas de duplicados
        df['duplicate_group'] = ''
        df['is_canonical'] = False

        for group in duplicates:
            for member in group.members:
                mask = df['sku_odi'] == member
                df.loc[mask, 'duplicate_group'] = group.group_id
                df.loc[mask, 'is_canonical'] = (member == group.canonical_sku)

        # Columnas de familia
        df['family_id'] = ''
        df['is_parent'] = False

        for family in families:
            for variant in family.variants:
                mask = df['sku_odi'] == variant['sku_odi']
                df.loc[mask, 'family_id'] = family.family_id
                df.loc[mask, 'is_parent'] = (variant['sku_odi'] == family.parent_sku)

        # Columnas de fitment
        df['fitment_marca'] = ''
        df['fitment_modelo'] = ''
        df['fitment_cilindraje'] = ''
        df['fitment_año'] = ''

        for sku, fit in fitment.items():
            mask = df['sku_odi'] == sku
            df.loc[mask, 'fitment_marca'] = fit.marca
            df.loc[mask, 'fitment_modelo'] = fit.modelo
            df.loc[mask, 'fitment_cilindraje'] = fit.cilindraje
            if fit.año_inicio:
                año = fit.año_inicio
                if fit.año_fin:
                    año += f"-{fit.año_fin}"
                df.loc[mask, 'fitment_año'] = año

        return df

    def _save_results(
        self,
        df: pd.DataFrame,
        output_file: str,
        duplicates: List[DuplicateGroup],
        families: List[ProductFamily],
        fitment: Dict[str, FitmentData]
    ):
        """Guarda resultados."""
        # CSV principal
        df.to_csv(output_file, index=False, sep=';', encoding='utf-8')
        print(f"\n💾 Catálogo normalizado: {output_file}")

        # JSON con metadata
        base_name = Path(output_file).stem
        output_dir = Path(output_file).parent

        metadata = {
            'timestamp': datetime.now().isoformat(),
            'total_products': len(df),
            'duplicates': [
                {
                    'group_id': g.group_id,
                    'canonical': g.canonical_sku,
                    'members': g.members,
                    'recommendation': g.merge_recommendation,
                    'confidence': g.confidence
                }
                for g in duplicates
            ],
            'families': [
                {
                    'family_id': f.family_id,
                    'parent_sku': f.parent_sku,
                    'parent_nombre': f.parent_nombre,
                    'variant_count': f.total_variants,
                    'variant_type': f.variant_attribute
                }
                for f in families
            ],
            'fitment_summary': {
                'total_with_fitment': len(fitment),
                'by_brand': self._count_by_field(fitment, 'marca'),
                'by_cc': self._count_by_field(fitment, 'cilindraje')
            }
        }

        metadata_file = output_dir / f"{base_name}_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"💾 Metadata: {metadata_file}")

    def _count_by_field(self, fitment: Dict[str, FitmentData], field: str) -> Dict[str, int]:
        """Cuenta ocurrencias por campo."""
        counts = defaultdict(int)
        for fit in fitment.values():
            value = getattr(fit, field, '')
            if value:
                counts[value] += 1
        return dict(sorted(counts.items(), key=lambda x: -x[1])[:10])

    def _print_summary(self, result: NormalizationResult):
        """Imprime resumen de normalización."""
        print(f"\n{'='*60}")
        print(f"📈 RESUMEN DE NORMALIZACIÓN")
        print(f"{'='*60}")
        print(f"   Total productos:        {result.total_products}")
        print(f"   Embeddings generados:   {result.embeddings_generated}")
        print(f"   Duplicados detectados:  {result.duplicates_found}")
        print(f"   Grupos de duplicados:   {len(result.duplicate_groups)}")
        print(f"   Familias creadas:       {result.families_created}")
        print(f"   Productos con fitment:  {result.products_with_fitment}")
        print(f"   Tiempo de proceso:      {result.processing_time_seconds:.2f}s")
        print(f"{'='*60}")
        # Machine-friendly line for parsing by orchestrator
        print(f"ODI_STATS duplicates={result.duplicates_found} families={result.families_created} fitment={result.products_with_fitment} embeddings={result.embeddings_generated}")
        print()


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ODI Semantic Normalizer v1.1 - Normalización semántica de catálogos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Normalizar catálogo con embeddings
  python odi_semantic_normalizer.py YOKOMAR_catalogo.csv -o YOKOMAR_normalizado.csv

  # Sin embeddings (solo análisis de texto)
  python odi_semantic_normalizer.py YOKOMAR_catalogo.csv --no-embeddings

  # Ajustar umbrales
  python odi_semantic_normalizer.py catalogo.csv --duplicate-threshold 0.90 --variant-threshold 0.80
        """
    )

    parser.add_argument(
        'input_file',
        help='Archivo CSV de catálogo (formato ODI)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Archivo de salida (default: {input}_normalized.csv)'
    )

    parser.add_argument(
        '--no-embeddings',
        action='store_true',
        help='No usar embeddings (solo análisis de texto)'
    )

    parser.add_argument(
        '--duplicate-threshold',
        type=float,
        default=DUPLICATE_THRESHOLD,
        help=f'Umbral de similitud para duplicados (default: {DUPLICATE_THRESHOLD})'
    )

    parser.add_argument(
        '--variant-threshold',
        type=float,
        default=VARIANT_THRESHOLD,
        help=f'Umbral de similitud para variantes (default: {VARIANT_THRESHOLD})'
    )

    parser.add_argument(
        '--no-inheritance',
        action='store_true',
        help='No aplicar herencia de atributos'
    )

    parser.add_argument(
        '--api-key',
        help='OpenAI API key (o usar OPENAI_API_KEY env var)'
    )

    args = parser.parse_args()

    # Verificar archivo de entrada
    if not os.path.exists(args.input_file):
        print(f"❌ Archivo no encontrado: {args.input_file}")
        sys.exit(1)

    # Determinar archivo de salida
    if args.output:
        output_file = args.output
    else:
        input_path = Path(args.input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_normalized.csv")

    # Crear normalizador
    normalizer = SemanticNormalizer(
        api_key=args.api_key,
        use_embeddings=not args.no_embeddings,
        duplicate_threshold=args.duplicate_threshold,
        variant_threshold=args.variant_threshold
    )

    # Ejecutar normalización
    try:
        df, result = normalizer.normalize(
            input_file=args.input_file,
            output_file=output_file,
            apply_inheritance=not args.no_inheritance
        )

        print(f"\n✅ Normalización completada exitosamente")
        print(f"   Archivo: {output_file}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
