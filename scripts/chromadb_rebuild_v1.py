#!/usr/bin/env python3
"""
ChromaDB Rebuild v1.0 - FASE 1 + 2
Wipe completo + Reindex productos + KB chunks
"""
import os
import sys
import json
import re
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

import chromadb
import pandas as pd

# Paths
ORDEN_MAESTRA = Path("/opt/odi/data/orden_maestra_v6")
PROFESION = Path("/mnt/volume_sfo3_01/profesion/ecosistema_odi")
CHROMADB_HOST = "localhost"
CHROMADB_PORT = 8000
COLLECTION_NAME = "odi_ind_motos"

# 15 Tiendas
STORES = [
    "DFG", "ARMOTOS", "OH_IMPORTACIONES", "DUNA", "IMBRA",
    "YOKOMAR", "JAPAN", "BARA", "MCLMOTOS", "CBI",
    "VITTON", "KAIQI", "LEO", "STORE", "VAISAND"
]

class PriceEnricher:
    """Carga y cruza precios desde CSVs y XLSX"""

    def __init__(self):
        self.price_index = {}  # {store: {sku_norm: price}}
        self.stats = defaultdict(int)

    def normalize_sku(self, sku):
        if not sku:
            return ""
        return str(sku).strip().upper().replace(" ", "").replace("/", "-")

    def parse_price(self, price_str):
        """Parsea precio de diferentes formatos"""
        if not price_str:
            return 0
        if isinstance(price_str, (int, float)):
            return float(price_str)
        # Remove $ and thousand separators
        clean = str(price_str).replace("$", "").replace(".", "").replace(",", ".").strip()
        try:
            return float(clean)
        except:
            return 0

    def load_csv_prices(self, store, csv_path):
        """Carga precios desde CSV"""
        if not csv_path.exists():
            return

        try:
            # Detectar delimitador
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                sample = f.read(1024)
                delimiter = ';' if ';' in sample else ','

            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                headers = [h.lower() for h in reader.fieldnames] if reader.fieldnames else []

                # Encontrar columnas
                sku_col = next((h for h in reader.fieldnames if 'codigo' in h.lower() or 'sku' in h.lower() or 'referencia' in h.lower()), None)
                price_col = next((h for h in reader.fieldnames if 'precio' in h.lower() or 'price' in h.lower() or 'valor' in h.lower()), None)

                if not sku_col or not price_col:
                    return

                f.seek(0)
                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    sku = self.normalize_sku(row.get(sku_col, ""))
                    price = self.parse_price(row.get(price_col, 0))

                    if sku and price > 0:
                        if store not in self.price_index:
                            self.price_index[store] = {}
                        self.price_index[store][sku] = price
                        self.stats[f"{store}_csv"] += 1

        except Exception as e:
            print(f"    Error CSV {store}: {e}")

    def load_xlsx_prices(self, store, xlsx_path, skiprows=0, sheet_name=0):
        """Carga precios desde XLSX"""
        if not xlsx_path.exists():
            return

        try:
            df = pd.read_excel(xlsx_path, sheet_name=sheet_name, skiprows=skiprows)
            df.columns = [str(c).lower().strip() for c in df.columns]

            # Encontrar columnas
            sku_col = None
            price_col = None
            desc_col = None
            discount_col = None

            for col in df.columns:
                if 'codigo' in col or 'referencia' in col:
                    sku_col = col
                elif 'precio' in col and 'total' not in col:
                    price_col = col
                elif 'valor' in col:
                    price_col = col
                elif 'descuento' in col or 'dto' in col:
                    discount_col = col
                elif 'descripcion' in col or 'nombre' in col:
                    desc_col = col

            if not price_col:
                return

            for _, row in df.iterrows():
                sku = self.normalize_sku(row.get(sku_col, "")) if sku_col else ""
                price = self.parse_price(row.get(price_col, 0))

                # Aplicar descuento si existe
                if discount_col and pd.notna(row.get(discount_col)):
                    try:
                        discount = float(row.get(discount_col, 0))
                        if discount > 0 and discount <= 1:
                            price = price * (1 - discount)
                        elif discount > 1:
                            price = price * (1 - discount/100)
                    except:
                        pass

                if sku and price > 0:
                    if store not in self.price_index:
                        self.price_index[store] = {}
                    self.price_index[store][sku] = price
                    self.stats[f"{store}_xlsx"] += 1

        except Exception as e:
            print(f"    Error XLSX {store}: {e}")

    def load_all(self):
        """Carga todos los precios disponibles"""
        print("\n[PRICE ENRICHER] Cargando precios...")

        # CSVs
        csv_files = {
            "DFG": PROFESION / "DFG/precios/Lista_Precios_DFG.csv",
            "BARA": PROFESION / "BARA/precios/Lista_Precios_Bara.csv",
            "IMBRA": PROFESION / "IMBRA/precios/Lista_Precios_Imbra.csv",
            "KAIQI": PROFESION / "KAIQI/precios/Lista_Precios_Kaiqi.csv",
            "YOKOMAR": PROFESION / "YOKOMAR/precios/Lista_Precios_Yokomar.csv",
        }

        for store, path in csv_files.items():
            self.load_csv_prices(store, path)

        # XLSX con skiprows específicos
        xlsx_configs = [
            ("BARA", PROFESION / "BARA/catalogo/LISTA DE PRECIOS BARA IMPORTACIONES ENERO 15 2026.xlsx", 8, 0),
            ("VITTON", PROFESION / "VITTON/catalogo/LISTA PRECIOS  INDUSTRIAS VITTON®️  2026 - 2V.xlsx", 2, 0),
            ("OH_IMPORTACIONES", PROFESION / "OH_IMPORTACIONES/catalogo/1-ENERO LISTA DE PRECIOS OH IMPORTACIONES SAS- 2026.xlsx", 5, "OH"),
            ("YOKOMAR", PROFESION / "YOKOMAR/catalogo/LISTA DE PRECIOS ACTUALIZADA YOKOMAR ENERO 28 2026 CON DESCUENTOS.xlsx", 7, "30 dias"),
            ("KAIQI", PROFESION / "KAIQI/catalogo/LISTADO KAIQI FEB 26.xlsx", 8, 0),
        ]

        for store, path, skiprows, sheet in xlsx_configs:
            self.load_xlsx_prices(store, path, skiprows, sheet)

        # Resumen
        total = sum(len(v) for v in self.price_index.values())
        print(f"    Total SKUs con precio: {total}")
        for store in sorted(self.price_index.keys()):
            print(f"      {store}: {len(self.price_index[store])}")

        return self

    def get_price(self, store, sku, current_price=0):
        """Obtiene precio enriquecido"""
        if current_price and current_price > 0:
            return current_price

        sku_norm = self.normalize_sku(sku)
        if store in self.price_index and sku_norm in self.price_index[store]:
            return self.price_index[store][sku_norm]

        return current_price


class ChromaDBRebuilder:
    """Reconstruye ChromaDB desde cero"""

    def __init__(self):
        self.client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        self.collection = None
        self.price_enricher = PriceEnricher()
        self.stats = {
            "products_indexed": 0,
            "kb_chunks_indexed": 0,
            "prices_enriched": 0,
            "prices_zero": 0,
        }

    def extract_category(self, title):
        """Extrae categoría del título"""
        title_lower = title.lower()

        categories = {
            "arbol de levas": "Árbol de Levas",
            "amortiguador": "Amortiguador",
            "bobina": "Bobina",
            "bujia": "Bujía",
            "cadena": "Cadena",
            "caliper": "Caliper",
            "carburador": "Carburador",
            "cdi": "CDI",
            "cilindro": "Cilindro",
            "clutch": "Clutch",
            "corona": "Corona",
            "disco": "Disco de Freno",
            "empaque": "Empaque",
            "espejo": "Espejo",
            "farola": "Farola",
            "filtro": "Filtro",
            "guaya": "Guaya",
            "kit de arrastre": "Kit de Arrastre",
            "llanta": "Llanta",
            "manigueta": "Manigueta",
            "mofle": "Mofle",
            "motor de arranque": "Motor de Arranque",
            "pastilla": "Pastilla de Freno",
            "piston": "Pistón",
            "piñon": "Piñón",
            "radiador": "Radiador",
            "rectificador": "Rectificador",
            "relay": "Relay",
            "rin": "Rin",
            "rodamiento": "Rodamiento",
            "sillin": "Sillín",
            "stop": "Stop",
            "swiche": "Swiche",
            "tacometro": "Tacómetro",
            "tanque": "Tanque",
            "tensor": "Tensor",
            "valvula": "Válvula",
        }

        for key, cat in categories.items():
            if key in title_lower:
                return cat

        return "Repuesto Moto"

    def extract_compatible_models(self, title):
        """Extrae modelos compatibles del título"""
        models = []
        title_upper = title.upper()

        # Patrones comunes
        patterns = [
            r'\b(AKT\s*\d+)', r'\b(PULSAR\s*\d+)', r'\b(DISCOVER\s*\d+)',
            r'\b(BOXER\s*\d*)', r'\b(AGILITY\s*\d*)', r'\b(BWS\s*\d*)',
            r'\b(FZ\s*\d+)', r'\b(YBR\s*\d+)', r'\b(LIBERO\s*\d*)',
            r'\b(APACHE\s*\d*)', r'\b(GIXXER\s*\d*)', r'\b(NMAX\s*\d*)',
            r'\b(CT\s*\d+)', r'\b(PLATINO\s*\d*)', r'\b(XCD\s*\d*)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, title_upper)
            models.extend(matches)

        return ", ".join(set(models)) if models else ""

    def normalize_title(self, title):
        """Normaliza título para mejor lectura"""
        if not title:
            return ""

        # Capitalizar correctamente
        title = title.strip()
        words = title.split()

        # Palabras que deben quedar en mayúsculas
        uppercase_words = {'AKT', 'TVS', 'BAJAJ', 'HONDA', 'YAMAHA', 'SUZUKI', 'KYMCO', 'BWS', 'FZ', 'YBR'}

        normalized = []
        for word in words:
            if word.upper() in uppercase_words:
                normalized.append(word.upper())
            else:
                normalized.append(word.capitalize())

        return " ".join(normalized)

    def wipe_collection(self):
        """Borra la colección completa"""
        print("\n" + "="*70)
        print("FASE 0: WIPE COLLECTION")
        print("="*70)

        try:
            # Verificar estado actual
            col = self.client.get_collection(COLLECTION_NAME)
            current_count = col.count()
            print(f"Documentos actuales: {current_count}")

            # Borrar
            self.client.delete_collection(COLLECTION_NAME)
            print(f"Colección {COLLECTION_NAME} BORRADA")

        except Exception as e:
            print(f"Colección no existe o error: {e}")

        # Crear nueva
        self.collection = self.client.create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "ODI Industria Motos - Productos + KB Chunks"}
        )
        print(f"Colección {COLLECTION_NAME} CREADA")

    def load_kb_enriched(self, store):
        """Carga datos de _kb_enriched.json si existe"""
        enriched_path = PROFESION / store / "output" / f"{store}_kb_enriched.json"

        if not enriched_path.exists():
            return {}

        try:
            with open(enriched_path) as f:
                data = json.load(f)

            # Indexar por SKU
            enriched = {}
            for item in data:
                sku = item.get("sku", "")
                if sku:
                    enriched[sku] = item

            return enriched
        except:
            return {}

    def process_store(self, store):
        """Procesa una tienda"""
        json_path = ORDEN_MAESTRA / f"{store}_products.json"

        if not json_path.exists():
            print(f"    {store}: JSON no existe")
            return [], []

        with open(json_path) as f:
            products = json.load(f)

        # Cargar enriched data si existe
        enriched_data = self.load_kb_enriched(store)

        product_docs = []
        kb_docs = []

        for p in products:
            sku = p.get("sku", "") or p.get("handle", "") or str(p.get("id", ""))
            title_raw = p.get("title", "") or p.get("title_raw", "")
            price = p.get("price", 0) or 0

            # Enriquecer desde _kb_enriched si existe
            if sku in enriched_data:
                enriched = enriched_data[sku]
                if not price or price == 0:
                    price = enriched.get("price", 0)
                if enriched.get("category"):
                    category = enriched.get("category")
                else:
                    category = self.extract_category(title_raw)
            else:
                category = self.extract_category(title_raw)

            # Enriquecer precio desde CSVs/XLSX
            price = self.price_enricher.get_price(store, sku, price)

            if price and price > 0:
                self.stats["prices_enriched"] += 1
            else:
                self.stats["prices_zero"] += 1

            title = self.normalize_title(title_raw)
            compatible = self.extract_compatible_models(title_raw)

            # === DOCUMENTO PRODUCTO ===
            prod_id = f"prod_{store}_{sku}".replace("/", "_").replace(" ", "_")
            prod_text = f"{title} SKU:{sku} ${int(price)} {store} {category}"
            if compatible:
                prod_text += f" {compatible}"

            product_docs.append({
                "id": prod_id,
                "text": prod_text,
                "metadata": {
                    "type": "product",
                    "store": store,
                    "sku": sku,
                    "price": float(price) if price else 0,
                    "title": title,
                    "category": category,
                    "compatible_models": compatible,
                }
            })

            # === KB CHUNK ===
            kb_id = f"kb_{store}_{sku}".replace("/", "_").replace(" ", "_")
            kb_text = f"Producto: {title}. "
            kb_text += f"Proveedor: {store}. "
            kb_text += f"Referencia: {sku}. "
            kb_text += f"Categoría: {category}. "
            kb_text += f"Precio: ${int(price):,} COP. " if price else ""
            if compatible:
                kb_text += f"Compatibilidad: {compatible}. "
            kb_text += f"Disponible para entrega inmediata."

            kb_docs.append({
                "id": kb_id,
                "text": kb_text,
                "metadata": {
                    "type": "kb_chunk",
                    "store": store,
                    "sku": sku,
                    "price": float(price) if price else 0,
                    "title": title,
                    "category": category,
                    "source": "catalog_product",
                }
            })

        return product_docs, kb_docs


    def index_batch(self, docs, batch_size=500):
        """Indexa documentos en batches con deduplicación"""
        # Deduplicar IDs
        seen = {}
        unique_docs = []
        for d in docs:
            orig_id = d["id"]
            if orig_id in seen:
                seen[orig_id] += 1
                d["id"] = f"{orig_id}_{seen[orig_id]}"
            else:
                seen[orig_id] = 0
            unique_docs.append(d)
        docs = unique_docs
        
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i+batch_size]

            ids = [d["id"] for d in batch]
            texts = [d["text"] for d in batch]
            metadatas = [d["metadata"] for d in batch]

            self.collection.upsert(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )


    def run(self):
        """Ejecuta rebuild completo"""
        print("="*70)
        print("CHROMADB REBUILD v1.0 - FASE 1 + 2")
        print("="*70)
        print(f"Timestamp: {datetime.now().isoformat()}")

        # Cargar precios
        self.price_enricher.load_all()

        # Wipe
        self.wipe_collection()

        # Procesar tiendas
        print("\n" + "="*70)
        print("FASE 1 + 2: INDEXAR PRODUCTOS + KB CHUNKS")
        print("="*70)

        all_products = []
        all_kb_chunks = []

        for store in STORES:
            print(f"\n  [{store}]")
            products, kb_chunks = self.process_store(store)

            if products:
                all_products.extend(products)
                all_kb_chunks.extend(kb_chunks)
                print(f"    Productos: {len(products)}")
                print(f"    KB Chunks: {len(kb_chunks)}")

        # Indexar todo
        print("\n  Indexando productos...")
        self.index_batch(all_products)
        self.stats["products_indexed"] = len(all_products)

        print("  Indexando KB chunks...")
        self.index_batch(all_kb_chunks)
        self.stats["kb_chunks_indexed"] = len(all_kb_chunks)

        # Verificar
        final_count = self.collection.count()

        # Reporte final
        print("\n" + "="*70)
        print("REPORTE FINAL")
        print("="*70)
        print(f"Productos indexados:   {self.stats['products_indexed']}")
        print(f"KB Chunks indexados:   {self.stats['kb_chunks_indexed']}")
        print(f"Total en ChromaDB:     {final_count}")
        print(f"Precios enriquecidos:  {self.stats['prices_enriched']}")
        print(f"Precios $0:            {self.stats['prices_zero']}")
        print("="*70)

        # Test query
        print("\n[TEST] Búsqueda: 'filtro aceite pulsar'")
        results = self.collection.query(
            query_texts=["filtro aceite pulsar"],
            n_results=5,
            where={"type": "product"}
        )

        for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
            print(f"  {i+1}. [{meta['store']}] {meta['title'][:50]} - ${meta['price']:,.0f}")

        print("\n[TEST] Búsqueda KB: 'amortiguador bajaj'")
        results = self.collection.query(
            query_texts=["amortiguador bajaj"],
            n_results=3,
            where={"type": "kb_chunk"}
        )

        for doc in results["documents"][0]:
            print(f"  → {doc[:100]}...")


if __name__ == "__main__":
    rebuilder = ChromaDBRebuilder()
    rebuilder.run()
