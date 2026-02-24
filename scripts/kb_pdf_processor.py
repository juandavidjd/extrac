#!/usr/bin/env python3
"""
KB PDF Processor v1.0
Procesa catálogos y manuales de motos usando Gemini Vision.
Indexa chunks en ChromaDB colección odi_ind_motos.
"""
import os
import sys
import json
import time
import re
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

# Imports
import google.generativeai as genai
import chromadb
from chromadb.config import Settings
from pdf2image import convert_from_path
from PIL import Image

# Config
KB_DIR = Path("/mnt/volume_sfo3_01/kb/IND_MOTOS")
CATALOGS_DIR = KB_DIR / "Catalogos"
MANUALES_DIR = KB_DIR / "Manuales"
ENCICLOPEDIA_DIR = KB_DIR / "Enciclopedia"
OTROS_DIR = KB_DIR / "Otros"

CHROMADB_HOST = "localhost"
CHROMADB_PORT = 8000
COLLECTION_NAME = "odi_ind_motos"

BATCH_SIZE = 5
BATCH_SLEEP = 10  # seconds between batches
PAGE_SLEEP = 1    # seconds between pages (rate limit)

# Gemini config
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

# Prompts
CATALOG_PROMPT = """Analiza esta página de catálogo de partes de moto.

Extrae:
1. MODELO de moto (ej: AGILITY 125, APACHE RTR 200, ADVANCE 110)
2. SISTEMA (motor, frenos, suspensión, transmisión, eléctrico, carrocería, dirección, escape, otro)
3. Lista de PIEZAS visibles con sus NÚMEROS DE PARTE
4. AÑOS de compatibilidad si se mencionan

Responde en JSON:
{
  "modelo": "...",
  "sistema": "...",
  "piezas": [
    {"nombre": "...", "numero_parte": "..."},
    ...
  ],
  "años": "...",
  "descripcion_diagrama": "breve descripción del diagrama/explosión si hay"
}

Si la página no tiene contenido útil (portada, índice, página en blanco), responde:
{"skip": true, "razon": "..."}
"""

MANUAL_PROMPT = """Analiza esta página de manual de servicio de moto.

Extrae:
1. MODELO de moto
2. PROCEDIMIENTO (qué se está explicando: cambio de aceite, ajuste de frenos, etc)
3. TORQUES mencionados (valores en Nm o kg-m)
4. HERRAMIENTAS necesarias
5. PASOS principales del procedimiento

Responde en JSON:
{
  "modelo": "...",
  "procedimiento": "...",
  "torques": ["valor1", "valor2"],
  "herramientas": ["herr1", "herr2"],
  "pasos": ["paso1", "paso2", "..."],
  "notas_importantes": "..."
}

Si la página no tiene contenido útil, responde:
{"skip": true, "razon": "..."}
"""


class KBProcessor:
    def __init__(self):
        self.chroma = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        self.collection = self.chroma.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "ODI Industria Motos - Productos + KB"}
        )
        self.stats = {
            "pdfs_processed": 0,
            "pdfs_failed": 0,
            "chunks_created": 0,
            "pages_skipped": 0
        }
        self.log_file = Path("/opt/odi/logs/kb_processor.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        with open(self.log_file, "a") as f:
            f.write(line + "\n")

    def extract_model_from_filename(self, filename):
        """Extrae modelo del nombre del PDF"""
        name = Path(filename).stem
        # Limpiar prefijos comunes
        name = re.sub(r'^CATALOGO[-_\s]*DE[-_\s]*PARTES[-_\s]*', '', name, flags=re.I)
        name = re.sub(r'^CATALOGO[-_\s]*', '', name, flags=re.I)
        name = re.sub(r'^MANUAL[-_\s]*DE[-_\s]*SERVICIO[-_\s]*', '', name, flags=re.I)
        name = re.sub(r'^MANUAL[-_\s]*', '', name, flags=re.I)
        name = re.sub(r'^PLANTILLA[-_\s]*', '', name, flags=re.I)
        # Limpiar sufijos
        name = re.sub(r'[-_\s]*FORMATO[-_\s]*MOBILITY.*$', '', name, flags=re.I)
        name = re.sub(r'[-_\s]*\d{1,2}[-_]\d{1,2}[-_]\d{2,4}.*$', '', name)  # fechas
        name = re.sub(r'[-_\s]*MY\d{2,4}.*$', '', name, flags=re.I)  # model years
        name = re.sub(r'[-_\s]*\d+$', '', name)  # números finales
        return name.strip().replace('-', ' ').replace('_', ' ')

    def generate_chunk_id(self, pdf_name, page_num, chunk_type):
        """Genera ID único para chunk"""
        base = f"{chunk_type}_{pdf_name}_{page_num}"
        return hashlib.md5(base.encode()).hexdigest()[:16]

    def process_page_with_gemini(self, image_path, prompt):
        """Envía página a Gemini Vision"""
        try:
            img = Image.open(image_path)
            response = model.generate_content([prompt, img])

            # Extraer JSON de la respuesta
            text = response.text
            # Buscar JSON en la respuesta
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
            return None
        except Exception as e:
            self.log(f"    Error Gemini: {e}")
            return None

    def process_catalog_pdf(self, pdf_path):
        """Procesa un PDF de catálogo"""
        filename = Path(pdf_path).name
        model_hint = self.extract_model_from_filename(filename)
        chunks = []

        try:
            # Convertir PDF a imágenes
            with tempfile.TemporaryDirectory() as tmpdir:
                images = convert_from_path(pdf_path, dpi=150)
                self.log(f"    {len(images)} páginas")

                for i, img in enumerate(images, 1):
                    img_path = Path(tmpdir) / f"page_{i}.png"
                    img.save(img_path, "PNG")

                    # Procesar con Gemini
                    result = self.process_page_with_gemini(img_path, CATALOG_PROMPT)

                    if result and not result.get("skip"):
                        modelo = result.get("modelo", model_hint)
                        sistema = result.get("sistema", "general")
                        piezas = result.get("piezas", [])
                        años = result.get("años", "")
                        diagrama = result.get("descripcion_diagrama", "")

                        # Construir texto del chunk
                        piezas_text = "; ".join([
                            f"{p['nombre']} ({p['numero_parte']})"
                            for p in piezas if p.get('nombre')
                        ])

                        text = f"Catálogo de partes {modelo}. Sistema: {sistema}. "
                        if piezas_text:
                            text += f"Piezas: {piezas_text}. "
                        if años:
                            text += f"Compatibilidad: {modelo} {años}. "
                        if diagrama:
                            text += f"Diagrama: {diagrama}."

                        chunk_id = f"kb_cat_{self.generate_chunk_id(filename, i, 'catalog')}"

                        chunks.append({
                            "id": chunk_id,
                            "text": text,
                            "metadata": {
                                "type": "kb_catalog",
                                "source": "catalog_pdf",
                                "model": modelo,
                                "system": sistema,
                                "filename": filename,
                                "page": i,
                                "part_numbers": [p.get("numero_parte", "") for p in piezas]
                            }
                        })
                    else:
                        self.stats["pages_skipped"] += 1

                    time.sleep(PAGE_SLEEP)

                    # Progress cada 10 páginas
                    if i % 10 == 0:
                        self.log(f"    Página {i}/{len(images)}...")

            return chunks

        except Exception as e:
            self.log(f"    ERROR: {e}")
            return []

    def process_manual_pdf(self, pdf_path):
        """Procesa un PDF de manual"""
        filename = Path(pdf_path).name
        model_hint = self.extract_model_from_filename(filename)
        chunks = []

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                images = convert_from_path(pdf_path, dpi=150)
                self.log(f"    {len(images)} páginas")

                for i, img in enumerate(images, 1):
                    img_path = Path(tmpdir) / f"page_{i}.png"
                    img.save(img_path, "PNG")

                    result = self.process_page_with_gemini(img_path, MANUAL_PROMPT)

                    if result and not result.get("skip"):
                        modelo = result.get("modelo", model_hint)
                        proc = result.get("procedimiento", "servicio general")
                        torques = result.get("torques", [])
                        herramientas = result.get("herramientas", [])
                        pasos = result.get("pasos", [])
                        notas = result.get("notas_importantes", "")

                        text = f"Manual de servicio {modelo}. Procedimiento: {proc}. "
                        if torques:
                            text += f"Torque: {', '.join(torques)}. "
                        if herramientas:
                            text += f"Herramientas: {', '.join(herramientas)}. "
                        if pasos:
                            text += f"Pasos: {'; '.join(pasos[:5])}. "  # Max 5 pasos
                        if notas:
                            text += f"Notas: {notas}."

                        chunk_id = f"kb_man_{self.generate_chunk_id(filename, i, 'manual')}"

                        chunks.append({
                            "id": chunk_id,
                            "text": text,
                            "metadata": {
                                "type": "kb_manual",
                                "source": "manual_pdf",
                                "model": modelo,
                                "procedure": proc,
                                "filename": filename,
                                "page": i
                            }
                        })
                    else:
                        self.stats["pages_skipped"] += 1

                    time.sleep(PAGE_SLEEP)

                    if i % 10 == 0:
                        self.log(f"    Página {i}/{len(images)}...")

            return chunks

        except Exception as e:
            self.log(f"    ERROR: {e}")
            return []

    def index_chunks(self, chunks):
        """Indexa chunks en ChromaDB"""
        if not chunks:
            return

        ids = [c["id"] for c in chunks]
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # Upsert en batches de 100
        for i in range(0, len(chunks), 100):
            batch_ids = ids[i:i+100]
            batch_texts = texts[i:i+100]
            batch_metas = metadatas[i:i+100]

            self.collection.upsert(
                ids=batch_ids,
                documents=batch_texts,
                metadatas=batch_metas
            )

        self.stats["chunks_created"] += len(chunks)

    def process_catalog_batch(self, pdf_files):
        """Procesa batch de catálogos"""
        batch_chunks = []

        for pdf_path in pdf_files:
            filename = Path(pdf_path).name
            self.log(f"  Procesando: {filename}")

            chunks = self.process_catalog_pdf(pdf_path)

            if chunks:
                batch_chunks.extend(chunks)
                self.stats["pdfs_processed"] += 1
                self.log(f"  Procesado: {filename} — {len(chunks)} chunks generados")
            else:
                self.stats["pdfs_failed"] += 1
                self.log(f"  FALLIDO: {filename}")

        # Indexar batch
        if batch_chunks:
            self.index_chunks(batch_chunks)
            self.log(f"  Batch indexado: {len(batch_chunks)} chunks en ChromaDB")

    def process_manual_batch(self, pdf_files):
        """Procesa batch de manuales"""
        batch_chunks = []

        for pdf_path in pdf_files:
            filename = Path(pdf_path).name
            self.log(f"  Procesando: {filename}")

            chunks = self.process_manual_pdf(pdf_path)

            if chunks:
                batch_chunks.extend(chunks)
                self.stats["pdfs_processed"] += 1
                self.log(f"  Procesado: {filename} — {len(chunks)} chunks generados")
            else:
                self.stats["pdfs_failed"] += 1
                self.log(f"  FALLIDO: {filename}")

        if batch_chunks:
            self.index_chunks(batch_chunks)
            self.log(f"  Batch indexado: {len(batch_chunks)} chunks en ChromaDB")

    def run_catalogs(self, limit=None):
        """Procesa todos los catálogos"""
        self.log("=" * 70)
        self.log("KB PROCESSOR - CATÁLOGOS")
        self.log("=" * 70)

        pdf_files = sorted(CATALOGS_DIR.glob("*.pdf"))
        if limit:
            pdf_files = pdf_files[:limit]

        self.log(f"Total catálogos: {len(pdf_files)}")
        self.log(f"Batch size: {BATCH_SIZE}")

        # Procesar en batches
        for i in range(0, len(pdf_files), BATCH_SIZE):
            batch = pdf_files[i:i+BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(pdf_files) + BATCH_SIZE - 1) // BATCH_SIZE

            self.log(f"\n--- Batch {batch_num}/{total_batches} ---")
            self.process_catalog_batch(batch)

            if i + BATCH_SIZE < len(pdf_files):
                self.log(f"Sleep {BATCH_SLEEP}s...")
                time.sleep(BATCH_SLEEP)

        self.print_stats()

    def run_manuals(self, limit=None):
        """Procesa todos los manuales"""
        self.log("=" * 70)
        self.log("KB PROCESSOR - MANUALES")
        self.log("=" * 70)

        pdf_files = sorted(MANUALES_DIR.glob("*.pdf"))
        if limit:
            pdf_files = pdf_files[:limit]

        self.log(f"Total manuales: {len(pdf_files)}")
        self.log(f"Batch size: {BATCH_SIZE}")

        for i in range(0, len(pdf_files), BATCH_SIZE):
            batch = pdf_files[i:i+BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(pdf_files) + BATCH_SIZE - 1) // BATCH_SIZE

            self.log(f"\n--- Batch {batch_num}/{total_batches} ---")
            self.process_manual_batch(batch)

            if i + BATCH_SIZE < len(pdf_files):
                self.log(f"Sleep {BATCH_SLEEP}s...")
                time.sleep(BATCH_SLEEP)

        self.print_stats()

    def print_stats(self):
        self.log("\n" + "=" * 70)
        self.log("ESTADÍSTICAS FINALES")
        self.log("=" * 70)
        self.log(f"PDFs procesados:    {self.stats['pdfs_processed']}")
        self.log(f"PDFs fallidos:      {self.stats['pdfs_failed']}")
        self.log(f"Chunks creados:     {self.stats['chunks_created']}")
        self.log(f"Páginas saltadas:   {self.stats['pages_skipped']}")

        # Contar en ChromaDB
        count = self.collection.count()
        self.log(f"Total en ChromaDB:  {count}")
        self.log("=" * 70)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="KB PDF Processor")
    parser.add_argument("--catalogs", action="store_true", help="Procesar catálogos")
    parser.add_argument("--manuals", action="store_true", help="Procesar manuales")
    parser.add_argument("--all", action="store_true", help="Procesar todo")
    parser.add_argument("--limit", type=int, help="Limitar número de PDFs")
    parser.add_argument("--test", action="store_true", help="Test con 2 PDFs")
    args = parser.parse_args()

    processor = KBProcessor()

    if args.test:
        processor.log("=== MODO TEST: 2 PDFs ===")
        processor.run_catalogs(limit=2)
    elif args.catalogs or args.all:
        processor.run_catalogs(limit=args.limit)

    if args.manuals or args.all:
        processor.run_manuals(limit=args.limit)

    if not any([args.catalogs, args.manuals, args.all, args.test]):
        print("Uso: kb_pdf_processor.py [--catalogs] [--manuals] [--all] [--test] [--limit N]")


if __name__ == "__main__":
    main()
