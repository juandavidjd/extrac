
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# KnowledgeIngestor - ODI V16 - CERO SCRIPTS SUELTOS

import os, re, hashlib
from dataclasses import dataclass
from typing import List, Dict
from pathlib import Path
import chromadb
import PyPDF2

@dataclass
class IngestConfig:
    collection_name: str = 'odi_ind_motos'
    chroma_host: str = 'localhost'
    chroma_port: int = 8000
    chunk_size: int = 500
    chunk_overlap: int = 50

FOLDER_CONFIG = {
    'Setter_Closer': {'type': 'kb_sales_training', 'domain': 'ventas', 'tags': ['setter', 'closer', 'ventas', 'srm']},
    'Sisteme_io': {'type': 'kb_tutorial', 'domain': 'funnels', 'tags': ['systeme', 'funnel', 'tutorial']},
    'Dropi': {'type': 'kb_tutorial', 'domain': 'dropshipping', 'tags': ['dropi', 'tutorial']},
    'Comprador_medios': {'type': 'kb_marketing', 'domain': 'media_buying', 'tags': ['facebook', 'ads', 'mediabuyer']},
    'Catalogos': {'type': 'kb_technical', 'domain': 'motos', 'tags': ['catalogo', 'tecnico']},
    'Manuales': {'type': 'kb_manual', 'domain': 'motos', 'tags': ['manual', 'tecnico']},
    'Otros': {'type': 'kb_technical', 'domain': 'motos', 'tags': ['otros', 'tecnico']},
}

class KnowledgeIngestor:
    def __init__(self, config=None):
        self.config = config or IngestConfig()
        self.client = chromadb.HttpClient(host=self.config.chroma_host, port=self.config.chroma_port)
        self.collection = self.client.get_or_create_collection(self.config.collection_name)
        self.stats = {'files': 0, 'chunks': 0, 'errors': 0}
    
    def extract_text_from_pdf(self, pdf_path):
        try:
            reader = PyPDF2.PdfReader(pdf_path)
            return ' '.join(p.extract_text() or '' for p in reader.pages).strip()
        except Exception as e:
            print(f'Error PDF {pdf_path}: {e}')
            return ''
    
    def extract_text_from_txt(self, txt_path):
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f'Error TXT {txt_path}: {e}')
            return ''
    
    def chunk_text(self, text):
        words = text.split()
        if not words:
            return []
        chunks = []
        i = 0
        while i < len(words):
            chunk = ' '.join(words[i:i + self.config.chunk_size])
            if chunk.strip():
                chunks.append(chunk)
            i += self.config.chunk_size - self.config.chunk_overlap
        return chunks
    
    def extract_metadata_from_filename(self, filename, folder):
        config = FOLDER_CONFIG.get(folder, {'type': 'kb_general', 'domain': 'general', 'tags': []})
        meta = {
            'type': config['type'],
            'domain': config['domain'],
            'tags': ','.join(config['tags']),
            'source_file': filename,
            'folder': folder
        }
        if folder == 'Setter_Closer':
            match = re.search(r'Modulo (\d+)', filename, re.IGNORECASE)
            if match:
                meta['module'] = int(match.group(1))
            match = re.search(r'Leccion (\d+)', filename, re.IGNORECASE)
            if match:
                meta['lesson'] = int(match.group(1))
            if 'setter' in filename.lower():
                meta['role'] = 'setter'
            elif 'closer' in filename.lower():
                meta['role'] = 'closer'
        return meta
    
    def ingest_folder(self, path, domain=None, tags=None):
        path = Path(path)
        folder_name = path.name
        print(f'Ingestando {folder_name}...')
        for file in path.iterdir():
            if file.is_file() and file.suffix.lower() in ['.pdf', '.txt']:
                try:
                    self._ingest_file(file, folder_name, domain, tags)
                    self.stats['files'] += 1
                except Exception as e:
                    print(f'Error {file.name}: {e}')
                    self.stats['errors'] += 1
        return self.stats
    
    def _ingest_file(self, file_path, folder, domain=None, tags=None):
        if file_path.suffix.lower() == '.pdf':
            text = self.extract_text_from_pdf(str(file_path))
        else:
            text = self.extract_text_from_txt(str(file_path))
        if not text:
            return
        chunks = self.chunk_text(text)
        if not chunks:
            return
        base_meta = self.extract_metadata_from_filename(file_path.name, folder)
        if domain:
            base_meta['domain'] = domain
        if tags:
            base_meta['tags'] = ','.join(tags)
        ids, docs, metas = [], [], []
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f'{file_path}_{i}'.encode()).hexdigest()
            meta = base_meta.copy()
            meta['chunk_idx'] = i
            meta['word_count'] = len(chunk.split())
            ids.append(chunk_id)
            docs.append(chunk)
            metas.append(meta)
        self.collection.upsert(ids=ids, documents=docs, metadatas=metas)
        self.stats['chunks'] += len(chunks)
        print(f'  {file_path.name}: {len(chunks)} chunks')
    
    def ingest_setter_closer(self, base_path='/mnt/volume_sfo3_01/kb/IND_MOTOS/Setter_Closer'):
        return self.ingest_folder(base_path)
    
    def ingest_systeme_io(self, base_path='/mnt/volume_sfo3_01/kb/IND_MOTOS/Sisteme_io'):
        return self.ingest_folder(base_path)
    
    def ingest_dropi(self, base_path='/mnt/volume_sfo3_01/kb/IND_MOTOS/Dropi'):
        return self.ingest_folder(base_path)
    
    def get_stats(self):
        return self.stats

if __name__ == '__main__':
    ingestor = KnowledgeIngestor()
    print('KnowledgeIngestor listo.')
    print(f'Coleccion: {ingestor.config.collection_name}')
