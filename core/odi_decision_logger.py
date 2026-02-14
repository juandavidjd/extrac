#!/usr/bin/env python3
"""
ODI Decision Logger v1.0
=========================
Auditoria Cognitiva Nativa del Organismo Digital Industrial.

"ODI no solo decide. ODI rinde cuentas."
"La trazabilidad no depende de la voz."

Registra decisiones criticas en PostgreSQL con hash SHA-256.
No registra cada mensaje — solo eventos que impactan:
- Capital (pagos, bloqueos)
- Etica (cambios de estado Guardian)
- Operacion (cambios de modo)
- Seguridad (emergencias)
"""

import hashlib
import json
import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

logger = logging.getLogger("odi.audit")

# Eventos que se loguean (solo decisiones criticas)
EVENTOS_CRITICOS = {
    "ESTADO_CAMBIO_AMARILLO",
    "ESTADO_CAMBIO_ROJO",
    "ESTADO_CAMBIO_NEGRO",
    "VENTA_AUTORIZADA",
    "VENTA_BLOQUEADA",
    "PAY_INIT_AUTORIZADO",
    "PAY_INIT_BLOQUEADO",
    "EMERGENCIA_ACTIVADA",
    "MODO_CAMBIO",
    "OVERRIDE_MANUAL",
    "PRECIO_ANOMALO",
}


class ODIDecisionLogger:
    """
    Logger de decisiones criticas del organismo.
    Persiste en PostgreSQL. Hash SHA-256 por registro.
    """

    def __init__(self):
        self._pool = None
        self._secret = os.getenv("ODI_AUDIT_SECRET", os.getenv("ODI_SECRET", "odi_default_secret_cambiar"))
        self._adn_version = "8.0.0"
        logger.info("ODI Decision Logger v1.0 inicializado")

    async def _get_pool(self):
        """Obtiene o crea pool de conexiones a PostgreSQL"""
        if self._pool is None:
            try:
                import asyncpg
                self._pool = await asyncpg.create_pool(
                    host=os.getenv("POSTGRES_HOST", "172.18.0.4"),
                    port=int(os.getenv("POSTGRES_PORT", "5432")),
                    user=os.getenv("POSTGRES_USER", "odi_user"),
                    password=os.getenv("POSTGRES_PASSWORD", "odi_secure_password"),
                    database=os.getenv("POSTGRES_DB", "odi"),
                    min_size=1,
                    max_size=5
                )
            except Exception as e:
                logger.error("Error conectando a PostgreSQL: %s", e)
                self._pool = None
        return self._pool

    def _generar_event_id(self) -> str:
        """Genera ID unico de evento: EV-YYYY-MM-DD-XXXXXX"""
        ahora = datetime.now(timezone.utc)
        seq = uuid.uuid4().hex[:6].upper()
        return f"EV-{ahora.strftime('%Y-%m-%d')}-{seq}"

    def _generar_hash(self, data: Dict[str, Any]) -> str:
        """
        Genera hash SHA-256 de integridad.
        Concatena campos criticos + secreto del servidor.
        Si alguien altera un registro, el hash no coincide.
        """
        payload = (
            f"{data.get('odi_event_id', '')}"
            f"{data.get('estado_guardian', '')}"
            f"{data.get('modo_aplicado', '')}"
            f"{data.get('intent_detectado', '')}"
            f"{data.get('monto_cop', 0)}"
            f"{data.get('timestamp', '')}"
            f"{self._secret}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def log_decision(self,
                           intent: str,
                           estado_guardian: str,
                           modo_aplicado: str,
                           usuario_id: str,
                           vertical: str = "P1",
                           motivo: str = "",
                           monto_cop: int = 0,
                           confianza_score: float = 0.0,
                           transaction_id: str = "",
                           decision_path: Optional[List[str]] = None,
                           override_by: str = "",
                           metadata: Optional[dict] = None) -> Optional[str]:
        """
        Registra una decision critica del organismo.
        Retorna: odi_event_id si exitoso, None si falla.
        Solo registra si el intent esta en EVENTOS_CRITICOS.
        """
        if intent not in EVENTOS_CRITICOS:
            logger.debug("Evento no critico, no se loguea: %s", intent)
            return None

        event_id = self._generar_event_id()
        ts_dt = datetime.now(timezone.utc)
        timestamp = ts_dt.isoformat()

        registro = {
            "odi_event_id": event_id,
            "timestamp": timestamp,
            "_timestamp_dt": ts_dt,
            "transaction_id": transaction_id,
            "usuario_id": usuario_id,
            "vertical": vertical,
            "estado_guardian": estado_guardian,
            "modo_aplicado": modo_aplicado,
            "intent_detectado": intent,
            "decision_motivo": motivo,
            "monto_cop": monto_cop,
            "confianza_score": confianza_score,
            "adn_version": self._adn_version,
            "decision_path": " -> ".join(decision_path) if decision_path else "",
            "override_flag": bool(override_by),
            "override_by": override_by or None,
            "metadata": metadata
        }

        registro["hash_integridad"] = self._generar_hash(registro)

        try:
            pool = await self._get_pool()
            if pool is None:
                self._log_fallback(registro)
                return event_id

            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO odi_decision_logs (
                        odi_event_id, timestamp, transaction_id, usuario_id, vertical,
                        estado_guardian, modo_aplicado, intent_detectado,
                        decision_motivo, monto_cop, confianza_score,
                        adn_version, decision_path, hash_integridad,
                        override_flag, override_by, metadata
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                        $12, $13, $14, $15, $16, $17
                    )
                """,
                    registro["odi_event_id"],
                    registro["_timestamp_dt"],
                    registro["transaction_id"] or None,
                    registro["usuario_id"],
                    registro["vertical"],
                    registro["estado_guardian"],
                    registro["modo_aplicado"],
                    registro["intent_detectado"],
                    registro["decision_motivo"],
                    registro["monto_cop"],
                    registro["confianza_score"],
                    registro["adn_version"],
                    registro["decision_path"],
                    registro["hash_integridad"],
                    registro["override_flag"],
                    registro["override_by"],
                    json.dumps(registro["metadata"]) if registro["metadata"] else None
                )

            logger.info("Decision logueada: %s | %s | %s | %s",
                        event_id, intent, estado_guardian, motivo)
            return event_id

        except Exception as e:
            logger.error("Error persistiendo decision: %s", e)
            self._log_fallback(registro)
            return event_id

    def _log_fallback(self, registro: Dict[str, Any]):
        """
        Fallback: Si PostgreSQL falla, guardar en archivo JSON.
        La verdad vive en PostgreSQL, pero no perdemos datos.
        """
        fallback_dir = "/opt/odi/data/audit_fallback"
        os.makedirs(fallback_dir, exist_ok=True)
        filepath = os.path.join(fallback_dir, f"{registro['odi_event_id']}.json")
        try:
            safe_registro = {k: v for k, v in registro.items() if not k.startswith("_")}
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(safe_registro, f, indent=2, ensure_ascii=False)
            logger.warning("Decision guardada en fallback: %s", filepath)
        except Exception as e:
            logger.critical("CRITICO: No se pudo guardar decision: %s", e)

    async def verificar_integridad(self, odi_event_id: str) -> bool:
        """
        Verifica que un registro no ha sido manipulado.
        Recalcula el hash y compara con el almacenado.
        """
        try:
            pool = await self._get_pool()
            if pool is None:
                return False

            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM odi_decision_logs WHERE odi_event_id = $1",
                    odi_event_id
                )
                if not row:
                    return False

                data = {
                    "odi_event_id": row["odi_event_id"],
                    "estado_guardian": row["estado_guardian"],
                    "modo_aplicado": row["modo_aplicado"],
                    "intent_detectado": row["intent_detectado"],
                    "monto_cop": row["monto_cop"],
                    "timestamp": row["timestamp"].isoformat(),
                }
                hash_recalculado = self._generar_hash(data)
                return hash_recalculado == row["hash_integridad"]

        except Exception as e:
            logger.error("Error verificando integridad: %s", e)
            return False

    async def obtener_resumen(self) -> Dict[str, Any]:
        """Retorna resumen de auditoria para endpoint /audit/status"""
        try:
            pool = await self._get_pool()
            if pool is None:
                return {"error": "PostgreSQL no disponible"}

            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM odi_audit_resumen")
                total = await conn.fetchval("SELECT COUNT(*) FROM odi_decision_logs")
                ultimo = await conn.fetchval(
                    "SELECT MAX(timestamp) FROM odi_decision_logs")

                return {
                    "total_decisiones": total,
                    "ultimo_evento": ultimo.isoformat() if ultimo else None,
                    "por_estado": [dict(r) for r in rows],
                    "logger_version": "1.0",
                    "adn_version": self._adn_version
                }
        except Exception as e:
            return {"error": str(e)}


# SINGLETON
_instancia_logger = None

def obtener_logger() -> ODIDecisionLogger:
    """Retorna la instancia singleton del Decision Logger"""
    global _instancia_logger
    if _instancia_logger is None:
        _instancia_logger = ODIDecisionLogger()
    return _instancia_logger
