#!/usr/bin/env python3
"""
ODI Feedback Loop Processor
===========================
Procesa feedback en tiempo real y dispara acciones automaticas.

Funcionalidades:
- Escucha eventos de Redis (queries, feedbacks, indexed)
- Dispara webhooks a n8n/Systeme.io
- Genera alertas cuando hay feedback negativo
- Actualiza metricas en tiempo real
- Re-entrena/ajusta basado en feedback

Uso:
    python odi_feedback_loop.py
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from collections import defaultdict
import time

from dotenv import load_dotenv
import redis
import httpx
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel

# Load config
load_dotenv("/opt/odi/config/.env")

# Configuration
CONFIG = {
    "redis_host": os.getenv("REDIS_HOST", "localhost"),
    "redis_port": int(os.getenv("REDIS_PORT", "6379")),
    "redis_db": int(os.getenv("REDIS_DB", "0")),
    "feedback_webhook_url": os.getenv("FEEDBACK_WEBHOOK_URL", ""),
    "feedback_webhook_secret": os.getenv("FEEDBACK_WEBHOOK_SECRET", ""),
    "logs_path": os.getenv("LOGS_PATH", "/opt/odi/logs"),
    "alert_threshold_rating": 2,  # Rating <= this triggers alert
    "alert_threshold_count": 3,   # Number of low ratings before alert
    "metrics_window_minutes": 60,  # Window for metrics calculation
}

# Logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"{CONFIG['logs_path']}/feedback_loop.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

console = Console()


@dataclass
class FeedbackEvent:
    """Evento de feedback."""
    query_id: str
    rating: int
    comment: Optional[str]
    correct_answer: Optional[str]
    timestamp: str
    source: str = "api"


@dataclass
class QueryEvent:
    """Evento de query."""
    query_id: str
    question: str
    voice: str
    sources_count: int
    timestamp: str


@dataclass
class IndexEvent:
    """Evento de indexacion."""
    file: str
    chunks: int
    timestamp: str


@dataclass
class ODIMetrics:
    """Metricas en tiempo real de ODI."""
    queries_total: int = 0
    queries_last_hour: int = 0
    avg_rating: float = 0.0
    low_rating_count: int = 0
    documents_indexed: int = 0
    last_index_time: Optional[str] = None
    feedback_count: int = 0
    webhook_success: int = 0
    webhook_failed: int = 0


class ODIFeedbackLoop:
    """Procesador principal del feedback loop."""

    def __init__(self):
        self.redis = redis.Redis(
            host=CONFIG["redis_host"],
            port=CONFIG["redis_port"],
            db=CONFIG["redis_db"],
            decode_responses=True
        )

        self.pubsub = self.redis.pubsub()
        self.metrics = ODIMetrics()
        self.recent_feedbacks: List[FeedbackEvent] = []
        self.running = True

        # HTTP client for webhooks
        self.http_client: Optional[httpx.AsyncClient] = None

    async def start(self):
        """Inicia el feedback loop."""
        logger.info("Starting ODI Feedback Loop...")

        # Subscribe to Redis channels
        self.pubsub.subscribe("odi:indexed", "odi:feedback_new", "odi:alert")

        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Load initial metrics
        await self._load_initial_metrics()

        # Start tasks
        await asyncio.gather(
            self._listen_redis(),
            self._process_feedback_queue(),
            self._metrics_reporter(),
            self._alert_checker()
        )

    async def stop(self):
        """Detiene el feedback loop."""
        self.running = False
        if self.http_client:
            await self.http_client.aclose()
        self.pubsub.close()
        logger.info("ODI Feedback Loop stopped")

    async def _load_initial_metrics(self):
        """Carga metricas iniciales desde Redis."""
        try:
            # Total queries
            self.metrics.queries_total = self.redis.llen("odi:queries")

            # Total feedbacks
            self.metrics.feedback_count = self.redis.llen("odi:feedbacks")

            # Calculate average rating from recent feedbacks
            feedbacks_raw = self.redis.lrange("odi:feedbacks", 0, 99)
            if feedbacks_raw:
                ratings = []
                for fb in feedbacks_raw:
                    try:
                        data = json.loads(fb)
                        ratings.append(data.get("rating", 3))
                    except:
                        pass
                if ratings:
                    self.metrics.avg_rating = sum(ratings) / len(ratings)

            logger.info(f"Loaded metrics: {self.metrics.queries_total} queries, {self.metrics.feedback_count} feedbacks")

        except Exception as e:
            logger.error(f"Error loading initial metrics: {e}")

    async def _listen_redis(self):
        """Escucha eventos de Redis."""
        logger.info("Listening to Redis channels...")

        while self.running:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]

                    if channel == "odi:indexed":
                        await self._handle_index_event(data)
                    elif channel == "odi:feedback_new":
                        await self._handle_feedback_event(data)
                    elif channel == "odi:alert":
                        await self._handle_alert(data)

                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in Redis listener: {e}")
                await asyncio.sleep(1)

    async def _process_feedback_queue(self):
        """Procesa la cola de feedbacks."""
        logger.info("Processing feedback queue...")

        while self.running:
            try:
                # Check for new feedbacks in list
                feedback_raw = self.redis.lpop("odi:feedback_queue")

                if feedback_raw:
                    feedback_data = json.loads(feedback_raw)
                    await self._process_feedback(feedback_data)
                else:
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error processing feedback: {e}")
                await asyncio.sleep(1)

    async def _process_feedback(self, feedback_data: Dict[str, Any]):
        """Procesa un feedback individual."""
        try:
            event = FeedbackEvent(
                query_id=feedback_data.get("query_id", "unknown"),
                rating=feedback_data.get("rating", 3),
                comment=feedback_data.get("comment"),
                correct_answer=feedback_data.get("correct_answer"),
                timestamp=feedback_data.get("timestamp", datetime.now().isoformat())
            )

            # Update metrics
            self.metrics.feedback_count += 1
            self.recent_feedbacks.append(event)

            # Keep only last 100
            if len(self.recent_feedbacks) > 100:
                self.recent_feedbacks = self.recent_feedbacks[-100:]

            # Recalculate average
            if self.recent_feedbacks:
                self.metrics.avg_rating = sum(f.rating for f in self.recent_feedbacks) / len(self.recent_feedbacks)

            # Check for low rating
            if event.rating <= CONFIG["alert_threshold_rating"]:
                self.metrics.low_rating_count += 1
                logger.warning(f"Low rating received: {event.rating} for query {event.query_id}")

                # Check if we should alert
                if self.metrics.low_rating_count >= CONFIG["alert_threshold_count"]:
                    await self._send_alert({
                        "type": "low_rating_threshold",
                        "count": self.metrics.low_rating_count,
                        "recent_feedback": asdict(event)
                    })

            # Send to webhook
            await self._send_webhook("feedback", asdict(event))

            logger.info(f"Processed feedback for query {event.query_id}: rating={event.rating}")

        except Exception as e:
            logger.error(f"Error processing feedback: {e}")

    async def _handle_index_event(self, data: str):
        """Maneja evento de indexacion."""
        try:
            event_data = json.loads(data)
            event = IndexEvent(
                file=event_data.get("file", "unknown"),
                chunks=event_data.get("chunks", 0),
                timestamp=event_data.get("timestamp", datetime.now().isoformat())
            )

            self.metrics.documents_indexed += event.chunks
            self.metrics.last_index_time = event.timestamp

            logger.info(f"Index event: {event.file} ({event.chunks} chunks)")

            # Notify webhook
            await self._send_webhook("indexed", asdict(event))

        except Exception as e:
            logger.error(f"Error handling index event: {e}")

    async def _handle_feedback_event(self, data: str):
        """Maneja evento de feedback desde pubsub."""
        try:
            feedback_data = json.loads(data)
            await self._process_feedback(feedback_data)
        except Exception as e:
            logger.error(f"Error handling feedback event: {e}")

    async def _handle_alert(self, data: str):
        """Maneja alerta."""
        try:
            alert_data = json.loads(data)
            logger.warning(f"Alert received: {alert_data}")
            await self._send_webhook("alert", alert_data)
        except Exception as e:
            logger.error(f"Error handling alert: {e}")

    async def _send_alert(self, alert_data: Dict[str, Any]):
        """Envia una alerta."""
        alert_data["timestamp"] = datetime.now().isoformat()
        alert_data["service"] = "odi-feedback-loop"

        # Publish to Redis
        self.redis.publish("odi:alert", json.dumps(alert_data))

        # Send webhook
        await self._send_webhook("alert", alert_data)

        logger.warning(f"Alert sent: {alert_data.get('type')}")

    async def _send_webhook(self, event_type: str, data: Dict[str, Any]):
        """Envia datos a webhook externo."""
        webhook_url = CONFIG.get("feedback_webhook_url")

        if not webhook_url:
            return

        try:
            payload = {
                "type": f"odi_{event_type}",
                "data": data,
                "timestamp": datetime.now().isoformat()
            }

            response = await self.http_client.post(
                webhook_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-ODI-Secret": CONFIG.get("feedback_webhook_secret", ""),
                    "X-ODI-Event": event_type
                }
            )

            if response.status_code < 400:
                self.metrics.webhook_success += 1
                logger.debug(f"Webhook sent successfully: {event_type}")
            else:
                self.metrics.webhook_failed += 1
                logger.warning(f"Webhook failed: {response.status_code}")

        except Exception as e:
            self.metrics.webhook_failed += 1
            logger.error(f"Error sending webhook: {e}")

    async def _metrics_reporter(self):
        """Reporta metricas periodicamente."""
        while self.running:
            try:
                # Update queries count
                self.metrics.queries_total = self.redis.llen("odi:queries")

                # Store metrics in Redis for API access
                self.redis.set("odi:metrics", json.dumps(asdict(self.metrics)))

                # Log summary every minute
                logger.info(
                    f"Metrics: queries={self.metrics.queries_total}, "
                    f"avg_rating={self.metrics.avg_rating:.2f}, "
                    f"feedbacks={self.metrics.feedback_count}"
                )

                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error in metrics reporter: {e}")
                await asyncio.sleep(10)

    async def _alert_checker(self):
        """Verifica condiciones de alerta periodicamente."""
        while self.running:
            try:
                # Reset low rating counter every hour
                await asyncio.sleep(3600)
                if self.metrics.low_rating_count > 0:
                    logger.info(f"Resetting low rating counter (was {self.metrics.low_rating_count})")
                    self.metrics.low_rating_count = 0

            except Exception as e:
                logger.error(f"Error in alert checker: {e}")
                await asyncio.sleep(60)


def display_dashboard(metrics: ODIMetrics):
    """Muestra dashboard en consola."""
    table = Table(title="ODI Feedback Loop Dashboard")

    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Queries", str(metrics.queries_total))
    table.add_row("Total Feedbacks", str(metrics.feedback_count))
    table.add_row("Avg Rating", f"{metrics.avg_rating:.2f}")
    table.add_row("Low Ratings (this hour)", str(metrics.low_rating_count))
    table.add_row("Docs Indexed", str(metrics.documents_indexed))
    table.add_row("Webhook Success", str(metrics.webhook_success))
    table.add_row("Webhook Failed", str(metrics.webhook_failed))

    return Panel(table, title="[bold blue]ODI Feedback Loop[/bold blue]")


async def main():
    """Main entry point."""
    console.print("[bold blue]ODI Feedback Loop Starting...[/bold blue]\n")

    loop = ODIFeedbackLoop()

    try:
        await loop.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
        await loop.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await loop.stop()
        raise


if __name__ == "__main__":
    asyncio.run(main())
