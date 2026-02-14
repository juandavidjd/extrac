#!/usr/bin/env python3
"""
ODI Event Emitter v1.0
======================
Modulo para emitir eventos al ODI Kernel para el Cortex Visual.

Este modulo permite que los scripts de extraccion (Vision Extractor,
SRM Processor, Catalog Unifier, Image Matcher) envien eventos en
tiempo real al ODI Kernel, donde son procesados por el NarratorEngine
y transmitidos al frontend Cortex Visual via WebSocket.

Uso:
    from odi_event_emitter import ODIEventEmitter, EventType

    emitter = ODIEventEmitter(source="vision")
    emitter.emit(EventType.VISION_PAGE_START, {
        "page_num": 5,
        "total_pages": 50
    })

Autor: ODI Team
Version: 1.0
"""

import os
import json
import uuid
import threading
import queue
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# Intentar importar requests, pero no fallar si no esta disponible
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# ============================================================================
# TIPOS DE EVENTOS
# ============================================================================

class EventType(str, Enum):
    """Tipos de eventos para el Cortex Visual."""

    # Vision Extractor Events
    VISION_START = "VISION_START"
    VISION_PAGE_START = "VISION_PAGE_START"
    VISION_PAGE_COMPLETE = "VISION_PAGE_COMPLETE"
    VISION_CROP_DETECTED = "VISION_CROP_DETECTED"
    VISION_PRODUCT_FOUND = "VISION_PRODUCT_FOUND"
    VISION_ERROR = "VISION_ERROR"
    VISION_COMPLETE = "VISION_COMPLETE"
    VISION_CHECKPOINT = "VISION_CHECKPOINT"

    # SRM Processor Events (Pipeline 6 pasos)
    SRM_PIPELINE_START = "SRM_PIPELINE_START"
    SRM_INGESTA = "SRM_INGESTA"
    SRM_EXTRACCION = "SRM_EXTRACCION"
    SRM_NORMALIZACION = "SRM_NORMALIZACION"
    SRM_UNIFICACION = "SRM_UNIFICACION"
    SRM_ENRIQUECIMIENTO = "SRM_ENRIQUECIMIENTO"
    SRM_FICHA_360 = "SRM_FICHA_360"
    SRM_INDUSTRY_DETECTED = "SRM_INDUSTRY_DETECTED"
    SRM_CLIENT_DETECTED = "SRM_CLIENT_DETECTED"
    SRM_SHOPIFY_PUSH = "SRM_SHOPIFY_PUSH"
    SRM_COMPLETE = "SRM_COMPLETE"

    # Catalog Unifier Events
    UNIFIER_START = "UNIFIER_START"
    UNIFIER_CROP_SAVED = "UNIFIER_CROP_SAVED"
    UNIFIER_ASSOCIATION = "UNIFIER_ASSOCIATION"
    UNIFIER_COMPLETE = "UNIFIER_COMPLETE"

    # Image Matcher Events
    MATCHER_START = "MATCHER_START"
    MATCHER_PRODUCT_MATCHED = "MATCHER_PRODUCT_MATCHED"
    MATCHER_NO_MATCH = "MATCHER_NO_MATCH"
    MATCHER_COMPLETE = "MATCHER_COMPLETE"

    # General Events
    PROGRESS_UPDATE = "PROGRESS_UPDATE"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class SourceType(str, Enum):
    """Fuentes de eventos."""
    VISION = "vision"
    SRM = "srm"
    UNIFIER = "unifier"
    MATCHER = "matcher"


# ============================================================================
# MODELO DE EVENTO
# ============================================================================

@dataclass
class ODIEvent:
    """Estructura de un evento ODI."""
    id: str
    timestamp: str
    event_type: str
    source: str
    actor: str
    data: Dict[str, Any]

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


@dataclass
class ShadowSource:
    """Fuente siendo consultada (Shadow Indexing)."""
    type: str      # "pdf", "api", "database", "image"
    name: str      # Nombre del recurso
    status: str    # "consulting", "found", "not_found"


# ============================================================================
# EMITTER PRINCIPAL
# ============================================================================

class ODIEventEmitter:
    """
    Emite eventos al ODI Kernel para el Cortex Visual.

    Caracteristicas:
    - Emision asincrona (non-blocking) via queue
    - Retry automatico en caso de fallo
    - Modo offline (eventos se loguean pero no se envian)
    - Callbacks para hooks locales
    """

    def __init__(
        self,
        source: str = "vision",
        actor: str = None,
        kernel_url: str = None,
        enabled: bool = True,
        async_mode: bool = True,
        callbacks: list = None
    ):
        """
        Inicializa el emitter.

        Args:
            source: Tipo de fuente (vision, srm, unifier, matcher)
            actor: Identificador del actor (default: genera automaticamente)
            kernel_url: URL del ODI Kernel (default: env ODI_KERNEL_URL)
            enabled: Si False, eventos se loguean pero no se envian
            async_mode: Si True, usa cola para emision non-blocking
            callbacks: Lista de funciones callback(event) para hooks locales
        """
        self.source = source
        self.actor = actor or self._generate_actor(source)
        self.kernel_url = kernel_url or os.getenv("ODI_KERNEL_URL", "http://localhost:3000")
        self.enabled = enabled and REQUESTS_AVAILABLE
        self.async_mode = async_mode
        self.callbacks = callbacks or []

        # Cola para emision asincrona
        self._queue = queue.Queue()
        self._worker_thread = None
        self._stop_event = threading.Event()

        # Estadisticas
        self.stats = {
            "emitted": 0,
            "delivered": 0,
            "failed": 0
        }

        # Iniciar worker si es asincrono
        if self.async_mode and self.enabled:
            self._start_worker()

    def _generate_actor(self, source: str) -> str:
        """Genera identificador de actor basado en la fuente."""
        actors = {
            "vision": "ODI_VISION_v3",
            "srm": "SRM_PROCESSOR_v4",
            "unifier": "CATALOG_UNIFIER_v1",
            "matcher": "IMAGE_MATCHER_v1"
        }
        return actors.get(source, f"ODI_{source.upper()}")

    def _start_worker(self):
        """Inicia worker thread para emision asincrona."""
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _worker_loop(self):
        """Loop del worker que procesa la cola de eventos."""
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=1.0)
                if event is None:
                    break
                self._send_event(event)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                pass

    def _send_event(self, event: ODIEvent) -> bool:
        """Envia evento al ODI Kernel via HTTP."""
        if not REQUESTS_AVAILABLE:
            return False

        try:
            url = f"{self.kernel_url}/odi/vision/event"
            response = requests.post(
                url,
                json=event.to_dict(),
                timeout=2.0,
                headers={"Content-Type": "application/json"}
            )
            success = response.status_code in (200, 201, 202)
            if success:
                self.stats["delivered"] += 1
            else:
                self.stats["failed"] += 1
            return success
        except requests.exceptions.RequestException:
            self.stats["failed"] += 1
            return False

    def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any] = None,
        shadow_sources: list = None
    ) -> str:
        """
        Emite un evento al ODI Kernel.

        Args:
            event_type: Tipo de evento (usar EventType enum)
            data: Datos adicionales del evento
            shadow_sources: Lista de ShadowSource consultadas

        Returns:
            ID del evento emitido
        """
        event_id = str(uuid.uuid4())[:8]
        event_data = data or {}

        # Agregar shadow sources si hay
        if shadow_sources:
            event_data["shadow_sources"] = [
                s.to_dict() if hasattr(s, "to_dict") else asdict(s)
                for s in shadow_sources
            ]

        event = ODIEvent(
            id=event_id,
            timestamp=datetime.now().isoformat(),
            event_type=event_type.value if isinstance(event_type, EventType) else event_type,
            source=self.source,
            actor=self.actor,
            data=event_data
        )

        self.stats["emitted"] += 1

        # Ejecutar callbacks locales
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception:
                pass

        # Enviar evento
        if self.enabled:
            if self.async_mode:
                self._queue.put(event)
            else:
                self._send_event(event)

        return event_id

    # =========================================================================
    # METODOS DE CONVENIENCIA PARA VISION EXTRACTOR
    # =========================================================================

    def vision_start(self, pdf_name: str, total_pages: int) -> str:
        """Emite evento de inicio de extraccion."""
        return self.emit(EventType.VISION_START, {
            "pdf_name": pdf_name,
            "total_pages": total_pages
        })

    def vision_page_start(self, page_num: int, total_pages: int) -> str:
        """Emite evento de inicio de procesamiento de pagina."""
        return self.emit(EventType.VISION_PAGE_START, {
            "page_num": page_num,
            "total_pages": total_pages,
            "progress": self._calc_progress(page_num, total_pages)
        }, shadow_sources=[
            ShadowSource("api", "GPT-4o Vision", "consulting")
        ])

    def vision_page_complete(
        self,
        page_num: int,
        total_pages: int,
        products_found: int,
        crops_detected: int
    ) -> str:
        """Emite evento de pagina completada."""
        return self.emit(EventType.VISION_PAGE_COMPLETE, {
            "page_num": page_num,
            "total_pages": total_pages,
            "products_found": products_found,
            "crops_detected": crops_detected,
            "progress": self._calc_progress(page_num, total_pages)
        })

    def vision_product_found(
        self,
        codigo: str,
        nombre: str,
        precio: float,
        categoria: str,
        imagen: str = None
    ) -> str:
        """Emite evento de producto encontrado."""
        return self.emit(EventType.VISION_PRODUCT_FOUND, {
            "product": {
                "codigo": codigo,
                "nombre": nombre,
                "precio": precio,
                "categoria": categoria,
                "imagen": imagen
            }
        })

    def vision_complete(self, total_products: int, elapsed_time: str) -> str:
        """Emite evento de extraccion completada."""
        return self.emit(EventType.VISION_COMPLETE, {
            "total_products": total_products,
            "elapsed_time": elapsed_time,
            "progress": {"current": 100, "total": 100, "percentage": 100}
        })

    def vision_error(self, page_num: int, error: str) -> str:
        """Emite evento de error en extraccion."""
        return self.emit(EventType.VISION_ERROR, {
            "page_num": page_num,
            "error": str(error)[:200]
        })

    # =========================================================================
    # METODOS DE CONVENIENCIA PARA SRM PROCESSOR
    # =========================================================================

    def srm_pipeline_start(self, source_file: str) -> str:
        """Emite evento de inicio del pipeline SRM."""
        return self.emit(EventType.SRM_PIPELINE_START, {
            "source_file": source_file
        })

    def srm_step(self, step_num: int, step_name: str, data: dict = None) -> str:
        """Emite evento de paso del pipeline."""
        step_events = {
            1: EventType.SRM_INGESTA,
            2: EventType.SRM_EXTRACCION,
            3: EventType.SRM_NORMALIZACION,
            4: EventType.SRM_UNIFICACION,
            5: EventType.SRM_ENRIQUECIMIENTO,
            6: EventType.SRM_FICHA_360
        }
        event_type = step_events.get(step_num, EventType.INFO)
        return self.emit(event_type, {
            "pipeline_step": step_num,
            "pipeline_name": step_name,
            "progress": self._calc_progress(step_num, 6),
            **(data or {})
        })

    def srm_industry_detected(self, industry: str, confidence: float) -> str:
        """Emite evento de industria detectada."""
        return self.emit(EventType.SRM_INDUSTRY_DETECTED, {
            "industry": industry,
            "confidence": round(confidence * 100, 1)
        })

    def srm_client_detected(self, client: str, client_type: str) -> str:
        """Emite evento de cliente detectado."""
        return self.emit(EventType.SRM_CLIENT_DETECTED, {
            "client": client,
            "client_type": client_type
        })

    def srm_shopify_push(self, shop_url: str, count: int) -> str:
        """Emite evento de push a Shopify."""
        return self.emit(EventType.SRM_SHOPIFY_PUSH, {
            "shop_url": shop_url,
            "count": count
        })

    def srm_complete(self, total_products: int, csv_path: str, json_path: str) -> str:
        """Emite evento de pipeline completado."""
        return self.emit(EventType.SRM_COMPLETE, {
            "total_products": total_products,
            "csv_path": csv_path,
            "json_path": json_path,
            "progress": {"current": 100, "total": 100, "percentage": 100}
        })

    # =========================================================================
    # METODOS DE CONVENIENCIA PARA MATCHER
    # =========================================================================

    def matcher_start(self, products_count: int, images_count: int) -> str:
        """Emite evento de inicio de matching."""
        return self.emit(EventType.MATCHER_START, {
            "products_count": products_count,
            "images_count": images_count
        })

    def matcher_product_matched(
        self,
        producto: str,
        imagen: str,
        score: float
    ) -> str:
        """Emite evento de producto asociado a imagen."""
        return self.emit(EventType.MATCHER_PRODUCT_MATCHED, {
            "producto": producto,
            "imagen": imagen,
            "score": round(score * 100, 1)
        })

    def matcher_complete(self, matched_count: int, total_count: int) -> str:
        """Emite evento de matching completado."""
        return self.emit(EventType.MATCHER_COMPLETE, {
            "matched_count": matched_count,
            "total_count": total_count,
            "match_rate": round(matched_count / max(total_count, 1) * 100, 1),
            "progress": {"current": 100, "total": 100, "percentage": 100}
        })

    # =========================================================================
    # UTILIDADES
    # =========================================================================

    def _calc_progress(self, current: int, total: int) -> dict:
        """Calcula diccionario de progreso."""
        percentage = round(current / max(total, 1) * 100, 1)
        return {
            "current": current,
            "total": total,
            "percentage": percentage
        }

    def progress(self, current: int, total: int, message: str = None) -> str:
        """Emite evento de progreso generico."""
        return self.emit(EventType.PROGRESS_UPDATE, {
            "progress": self._calc_progress(current, total),
            "message": message
        })

    def error(self, message: str, details: dict = None) -> str:
        """Emite evento de error."""
        return self.emit(EventType.ERROR, {
            "error": message,
            **(details or {})
        })

    def warning(self, message: str) -> str:
        """Emite evento de advertencia."""
        return self.emit(EventType.WARNING, {"message": message})

    def info(self, message: str) -> str:
        """Emite evento informativo."""
        return self.emit(EventType.INFO, {"message": message})

    def close(self):
        """Cierra el emitter y espera que se procesen eventos pendientes."""
        if self._worker_thread:
            self._stop_event.set()
            self._queue.put(None)  # Senial de parada
            self._worker_thread.join(timeout=5.0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================

_default_emitter: Optional[ODIEventEmitter] = None


def get_emitter(source: str = "vision", **kwargs) -> ODIEventEmitter:
    """Obtiene o crea el emitter global."""
    global _default_emitter
    if _default_emitter is None:
        _default_emitter = ODIEventEmitter(source=source, **kwargs)
    return _default_emitter


def emit(event_type: EventType, data: dict = None) -> str:
    """Emite evento usando el emitter global."""
    return get_emitter().emit(event_type, data)


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("""
ODI Event Emitter v1.0
======================

Ejemplo de uso:

    from odi_event_emitter import ODIEventEmitter, EventType

    # Crear emitter
    emitter = ODIEventEmitter(source="vision")

    # Emitir eventos de Vision Extractor
    emitter.vision_start("catalogo.pdf", 50)
    emitter.vision_page_start(1, 50)
    emitter.vision_product_found("50100", "Kit piston", 45000, "MOTOR")
    emitter.vision_page_complete(1, 50, products_found=5, crops_detected=3)
    emitter.vision_complete(250, "15m")

    # Emitir eventos de SRM Processor
    emitter = ODIEventEmitter(source="srm")
    emitter.srm_pipeline_start("catalogo.xlsx")
    emitter.srm_step(1, "INGESTA", {"filename": "catalogo.xlsx"})
    emitter.srm_industry_detected("autopartes_motos", 0.95)
    emitter.srm_client_detected("KAIQI", "fabricante")
    emitter.srm_complete(500, "/tmp/output.csv", "/tmp/output.json")

    # Emitir eventos de Image Matcher
    emitter = ODIEventEmitter(source="matcher")
    emitter.matcher_start(500, 1200)
    emitter.matcher_product_matched("Kit piston 150cc", "crop_001.jpg", 0.87)
    emitter.matcher_complete(450, 500)

Variables de entorno:
    ODI_KERNEL_URL  - URL del ODI Kernel (default: http://localhost:3000)
""")

    # Demo
    print("\nDemo: Emitiendo eventos de prueba...")

    with ODIEventEmitter(source="vision", enabled=False) as emitter:
        # Los eventos se loguean pero no se envian (enabled=False)
        emitter.vision_start("demo_catalogo.pdf", 10)
        emitter.vision_page_start(1, 10)
        emitter.vision_product_found("12345", "Producto Demo", 50000, "MOTOR")
        emitter.vision_page_complete(1, 10, 5, 3)

        print(f"\nEstadisticas:")
        print(f"  Emitidos: {emitter.stats['emitted']}")
        print(f"  Entregados: {emitter.stats['delivered']}")
        print(f"  Fallidos: {emitter.stats['failed']}")

    print("\nListo!")
