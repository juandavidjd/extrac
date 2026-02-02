#!/usr/bin/env python3
"""
ODI Business Daemon - Metabolismo Económico
============================================
Detecta catálogos nuevos y dispara el pipeline de negocio automáticamente.

Flujo:
  /Data/{Empresa}/catalogo.pdf → detectado → pipeline 6 pasos → Shopify

Watchea:
  /mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/

Uso:
    python3 odi_business_daemon.py
    systemctl start odi-business-daemon
"""
import os
import sys
import json
import time
import logging
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

import httpx
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

load_dotenv("/opt/odi/.env")

# ============================================
# CONFIGURACIÓN
# ============================================
CONFIG = {
    "watch_path": "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data",
    "images_path": "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Imagenes",
    "pipeline_url": "http://localhost:8804",
    "jobs_path": "/opt/odi/data/business_jobs",
    "logs_path": "/opt/odi/logs",
    "supported_extensions": {".pdf", ".xlsx", ".xls", ".csv"},
}

# Mapeo de carpetas a empresas
EMPRESA_CONFIG = {
    "Kaiqi": {"shop": "KAIQI", "priority": 1},
    "Japan": {"shop": "JAPAN", "priority": 2},
    "Yokomar": {"shop": "YOKOMAR", "priority": 2},
    "Imbra": {"shop": "IMBRA", "priority": 3},
    "Bara": {"shop": "BARA", "priority": 3},
    "Duna": {"shop": "DUNA", "priority": 4},
    "DFG": {"shop": "DFG", "priority": 4},
    "Leo": {"shop": "LEO", "priority": 5},
    "Store": {"shop": "STORE", "priority": 5},
    "Vaisand": {"shop": "VAISAND", "priority": 5},
    "Armotos": {"shop": None, "priority": 1},  # Competencia - solo extracción
}

# Logging
os.makedirs(CONFIG["logs_path"], exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"{CONFIG['logs_path']}/business_daemon.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# ============================================
# MODELOS
# ============================================
class JobStatus(Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    NORMALIZING = "normalizing"
    ENRICHING = "enriching"
    FITTING = "fitting"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BusinessJob:
    job_id: str
    empresa: str
    shop_key: Optional[str]
    source_file: str
    images_folder: str
    status: str
    created_at: str
    updated_at: str
    products_extracted: int = 0
    products_uploaded: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


# ============================================
# JOB MANAGER
# ============================================
class JobManager:
    """Gestiona los jobs de negocio."""

    def __init__(self, jobs_path: str):
        self.jobs_path = Path(jobs_path)
        self.jobs_path.mkdir(parents=True, exist_ok=True)
        self.active_jobs: Dict[str, BusinessJob] = {}
        self._load_pending_jobs()

    def _load_pending_jobs(self):
        """Carga jobs pendientes del disco."""
        for job_file in self.jobs_path.glob("*.json"):
            try:
                with open(job_file) as f:
                    data = json.load(f)
                if data.get("status") not in ["completed", "failed"]:
                    job = BusinessJob(**data)
                    self.active_jobs[job.job_id] = job
                    log.info(f"Loaded pending job: {job.job_id}")
            except Exception as e:
                log.error(f"Error loading job {job_file}: {e}")

    def create_job(self, empresa: str, source_file: str) -> BusinessJob:
        """Crea un nuevo job de negocio."""
        job_id = hashlib.md5(f"{empresa}:{source_file}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]

        empresa_config = EMPRESA_CONFIG.get(empresa, {})
        images_folder = str(Path(CONFIG["images_path"]) / empresa)

        job = BusinessJob(
            job_id=job_id,
            empresa=empresa,
            shop_key=empresa_config.get("shop"),
            source_file=source_file,
            images_folder=images_folder,
            status=JobStatus.PENDING.value,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        self.active_jobs[job_id] = job
        self._save_job(job)

        log.info(f"Created job {job_id} for {empresa}: {Path(source_file).name}")
        return job

    def update_job(self, job_id: str, **kwargs):
        """Actualiza un job."""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            job.updated_at = datetime.now().isoformat()
            self._save_job(job)

    def _save_job(self, job: BusinessJob):
        """Guarda job a disco."""
        job_file = self.jobs_path / f"{job.job_id}.json"
        with open(job_file, "w") as f:
            json.dump(asdict(job), f, indent=2)

    def get_job(self, job_id: str) -> Optional[BusinessJob]:
        return self.active_jobs.get(job_id)

    def list_jobs(self, status: Optional[str] = None) -> List[BusinessJob]:
        jobs = list(self.active_jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return sorted(jobs, key=lambda x: x.created_at, reverse=True)


# ============================================
# PIPELINE CLIENT
# ============================================
class PipelineClient:
    """Cliente para el servicio de pipeline."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)

    async def submit_job(self, job: BusinessJob) -> Dict[str, Any]:
        """Envía un job al pipeline."""
        try:
            response = await self.client.post(
                f"{self.base_url}/pipeline/start",
                json={
                    "job_id": job.job_id,
                    "empresa": job.empresa,
                    "shop_key": job.shop_key,
                    "source_file": job.source_file,
                    "images_folder": job.images_folder
                }
            )
            return response.json()
        except Exception as e:
            log.error(f"Pipeline submission failed: {e}")
            return {"error": str(e)}

    async def get_status(self, job_id: str) -> Dict[str, Any]:
        """Obtiene estado de un job."""
        try:
            response = await self.client.get(f"{self.base_url}/pipeline/status/{job_id}")
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def close(self):
        await self.client.aclose()


# ============================================
# FILE HANDLER
# ============================================
class CatalogHandler(FileSystemEventHandler):
    """Handler para detectar nuevos catálogos."""

    def __init__(self, job_manager: JobManager, pipeline_client: PipelineClient):
        self.job_manager = job_manager
        self.pipeline_client = pipeline_client
        self.processed_files = set()
        self._load_processed()

    def _load_processed(self):
        """Carga archivos ya procesados."""
        cache_file = Path(CONFIG["jobs_path"]) / "processed_files.txt"
        if cache_file.exists():
            self.processed_files = set(cache_file.read_text().strip().split("\n"))

    def _save_processed(self, filepath: str):
        """Guarda archivo como procesado."""
        self.processed_files.add(filepath)
        cache_file = Path(CONFIG["jobs_path"]) / "processed_files.txt"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "a") as f:
            f.write(filepath + "\n")

    def _detect_empresa(self, filepath: str) -> Optional[str]:
        """Detecta la empresa basado en la ruta."""
        path = Path(filepath)
        for empresa in EMPRESA_CONFIG.keys():
            if empresa.lower() in str(path).lower():
                return empresa
        return None

    def on_created(self, event):
        if event.is_directory:
            return

        filepath = event.src_path
        ext = Path(filepath).suffix.lower()

        if ext not in CONFIG["supported_extensions"]:
            return

        if filepath in self.processed_files:
            log.debug(f"Already processed: {filepath}")
            return

        # Esperar a que el archivo termine de escribirse
        time.sleep(2)

        empresa = self._detect_empresa(filepath)
        if not empresa:
            log.warning(f"Could not detect empresa for: {filepath}")
            return

        log.info(f"New catalog detected: {Path(filepath).name} [{empresa}]")

        # Crear job
        job = self.job_manager.create_job(empresa, filepath)
        self._save_processed(filepath)

        # Enviar al pipeline (async)
        asyncio.create_task(self._submit_to_pipeline(job))

    async def _submit_to_pipeline(self, job: BusinessJob):
        """Envía job al pipeline de forma asíncrona."""
        try:
            result = await self.pipeline_client.submit_job(job)
            if "error" in result:
                self.job_manager.update_job(job.job_id, status=JobStatus.FAILED.value, errors=[result["error"]])
                log.error(f"Job {job.job_id} failed: {result['error']}")
            else:
                self.job_manager.update_job(job.job_id, status=JobStatus.EXTRACTING.value)
                log.info(f"Job {job.job_id} submitted to pipeline")
        except Exception as e:
            self.job_manager.update_job(job.job_id, status=JobStatus.FAILED.value, errors=[str(e)])
            log.error(f"Failed to submit job {job.job_id}: {e}")


# ============================================
# MAIN DAEMON
# ============================================
class ODIBusinessDaemon:
    """Daemon principal de negocio."""

    def __init__(self):
        self.job_manager = JobManager(CONFIG["jobs_path"])
        self.pipeline_client = PipelineClient(CONFIG["pipeline_url"])
        self.handler = CatalogHandler(self.job_manager, self.pipeline_client)
        self.observer = Observer()

    def start(self):
        """Inicia el daemon."""
        log.info("=" * 70)
        log.info("ODI Business Daemon - Metabolismo Económico")
        log.info("=" * 70)
        log.info(f"Watching: {CONFIG['watch_path']}")
        log.info(f"Pipeline: {CONFIG['pipeline_url']}")
        log.info(f"Empresas configuradas: {len(EMPRESA_CONFIG)}")
        log.info("=" * 70)

        # Verificar que existe el path
        watch_path = Path(CONFIG["watch_path"])
        if not watch_path.exists():
            log.error(f"Watch path not found: {watch_path}")
            return

        # Configurar observer
        self.observer.schedule(self.handler, str(watch_path), recursive=True)
        self.observer.start()

        log.info("Business Daemon started. Waiting for catalogs...")

        try:
            while True:
                time.sleep(10)
                # Reportar estado cada minuto
                jobs = self.job_manager.list_jobs()
                pending = len([j for j in jobs if j.status == JobStatus.PENDING.value])
                running = len([j for j in jobs if j.status not in [JobStatus.PENDING.value, JobStatus.COMPLETED.value, JobStatus.FAILED.value]])
                if pending > 0 or running > 0:
                    log.info(f"Jobs: {pending} pending, {running} running")

        except KeyboardInterrupt:
            self.observer.stop()
            log.info("Business Daemon stopped")

        self.observer.join()

    def process_existing(self):
        """Procesa catálogos existentes que no han sido procesados."""
        log.info("Scanning for existing catalogs...")

        watch_path = Path(CONFIG["watch_path"])
        if not watch_path.exists():
            return

        for ext in CONFIG["supported_extensions"]:
            for filepath in watch_path.rglob(f"*{ext}"):
                if str(filepath) in self.handler.processed_files:
                    continue

                empresa = self.handler._detect_empresa(str(filepath))
                if empresa:
                    log.info(f"Found unprocessed: {filepath.name} [{empresa}]")
                    job = self.job_manager.create_job(empresa, str(filepath))
                    self.handler._save_processed(str(filepath))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ODI Business Daemon")
    parser.add_argument("--scan", action="store_true", help="Scan existing catalogs")
    parser.add_argument("--list-jobs", action="store_true", help="List all jobs")

    args = parser.parse_args()

    daemon = ODIBusinessDaemon()

    if args.list_jobs:
        jobs = daemon.job_manager.list_jobs()
        print(f"\nTotal jobs: {len(jobs)}\n")
        for job in jobs[:20]:
            print(f"  [{job.status:12}] {job.job_id} | {job.empresa:10} | {Path(job.source_file).name}")
    elif args.scan:
        daemon.process_existing()
    else:
        daemon.start()


if __name__ == "__main__":
    main()
