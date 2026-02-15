#!/usr/bin/env python3
"""
ODI Override Protocol v1.0
===========================
Protocolo de Override Humano Seguro.

"ROJO no se edita. ROJO se supera con huella humana."

Permite intervención humana trazable con:
- JWT + TOTP (2FA)
- Roles: ARQUITECTO / SUPERVISOR / CUSTODIO
- Encadenamiento de eventos (prev_event_id)
- Hash SHA-256 inmutable
- TTL configurable (default 10 min)
"""

import os
import json
import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("odi.override")

# ═══════════════════════════════════════════════
# ROLES Y PERMISOS
# ═══════════════════════════════════════════════

ROLE_PERMISSIONS = {
    "ARQUITECTO": {
        "vertical_scope": "*",
        "can_override_rojo": True,
        "can_override_amarillo": True,
        "can_escalate_negro": True,
        "can_authorize_payment": True,
    },
    "SUPERVISOR": {
        "vertical_scope": "assigned",
        "can_override_rojo": True,
        "can_override_amarillo": True,
        "can_escalate_negro": False,
        "can_authorize_payment": True,
    },
    "CUSTODIO": {
        "vertical_scope": "assigned",
        "can_override_rojo": True,
        "can_override_amarillo": True,
        "can_escalate_negro": False,
        "can_authorize_payment": True,
    },
}

VALID_DECISIONS = {
    "VERDE_OVERRIDE_SUPERVISADO",
    "AMARILLO_OVERRIDE_SUPERVISADO",
    "ESCALAMIENTO_NEGRO",
}

# ═══════════════════════════════════════════════
# AUTENTICACIÓN
# ═══════════════════════════════════════════════

class OverrideAuth:
    """Validación JWT + TOTP para overrides"""

    def __init__(self):
        self._jwt_secret = os.getenv("ODI_JWT_SECRET", "")
        self._jwt_issuer = os.getenv("ODI_JWT_ISSUER", "odi")
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                host=os.getenv("POSTGRES_HOST", "172.18.0.4"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                user=os.getenv("POSTGRES_USER", "odi_user"),
                password=os.getenv("POSTGRES_PASSWORD", "odi_secure_password"),
                database=os.getenv("POSTGRES_DB", "odi"),
                min_size=1, max_size=3
            )
        return self._pool

    async def validate_jwt(self, token: str) -> Optional[Dict]:
        """Valida JWT y retorna claims si válido"""
        import jwt
        try:
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=["HS256"],
                issuer=self._jwt_issuer
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT expirado")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("JWT inválido: %s", e)
            return None

    async def validate_totp(self, human_id: str, totp_code: str) -> bool:
        """Valida código TOTP contra secreto almacenado"""
        import pyotp
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT totp_secret, is_active FROM odi_humans WHERE human_id = $1",
                    human_id
                )
                if not row or not row["is_active"]:
                    return False
                totp = pyotp.TOTP(row["totp_secret"])
                return totp.verify(totp_code, valid_window=1)
        except Exception as e:
            logger.error("Error validando TOTP: %s", e)
            return False

    def generate_jwt(self, human_id: str, role: str, vertical_scope: str,
                     expiry_minutes: int = 10) -> str:
        """Genera JWT para un humano autorizado"""
        import jwt
        now = datetime.now(timezone.utc)
        payload = {
            "sub": human_id,
            "role": role,
            "vertical_scope": vertical_scope,
            "iss": self._jwt_issuer,
            "iat": now,
            "exp": now + timedelta(minutes=expiry_minutes),
        }
        return jwt.encode(payload, self._jwt_secret, algorithm="HS256")


# ═══════════════════════════════════════════════
# MOTOR DE OVERRIDE
# ═══════════════════════════════════════════════

class ODIOverrideEngine:
    """
    Motor de Override Humano.
    Crea nuevos eventos enlazados a bloqueos originales.
    """

    def __init__(self):
        self._auth = OverrideAuth()
        self._audit_secret = os.getenv(
            "ODI_AUDIT_SECRET",
            os.getenv("ODI_SECRET", "odi_default_secret_cambiar")
        )
        self._ttl_minutes = int(os.getenv("ODI_OVERRIDE_TTL_MINUTES", "10"))
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                host=os.getenv("POSTGRES_HOST", "172.18.0.4"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                user=os.getenv("POSTGRES_USER", "odi_user"),
                password=os.getenv("POSTGRES_PASSWORD", "odi_secure_password"),
                database=os.getenv("POSTGRES_DB", "odi"),
                min_size=1, max_size=5
            )
        return self._pool

    def _new_event_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        suffix = secrets.token_hex(3).upper()
        return f"OV-{ts}-{suffix}"

    def _hash_override(self, data: Dict[str, Any]) -> str:
        """Hash SHA-256 del override con canonicalización"""
        core = {
            "original_event_id": data.get("original_event_id", ""),
            "new_event_id": data.get("new_event_id", ""),
            "human_id": data.get("human_id", ""),
            "role": data.get("role", ""),
            "decision": data.get("decision", ""),
            "reason": data.get("reason", ""),
            "evidence": json.dumps(
                data.get("evidence", {}),
                separators=(",", ":"),
                sort_keys=True,
                ensure_ascii=False
            ),
        }
        payload = json.dumps(core, separators=(",", ":"), sort_keys=True) + self._audit_secret
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def execute_override(
        self,
        jwt_token: str,
        totp_code: str,
        original_event_id: str,
        target_decision: str,
        reason: str,
        evidence: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Ejecuta un override humano.
        Retorna: (success: bool, result: dict)
        """
        # PASO 1: Validar JWT
        claims = await self._auth.validate_jwt(jwt_token)
        if not claims:
            return False, {"error": "JWT inválido o expirado"}

        human_id = claims.get("sub")
        role = claims.get("role")
        vertical_scope = claims.get("vertical_scope", "*")

        # PASO 2: Validar TOTP
        totp_valid = await self._auth.validate_totp(human_id, totp_code)
        if not totp_valid:
            return False, {"error": "Código TOTP inválido"}

        # PASO 3: Validar decisión
        if target_decision not in VALID_DECISIONS:
            return False, {"error": f"Decisión no válida: {target_decision}"}

        # PASO 4: Obtener evento original
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            original = await conn.fetchrow(
                "SELECT * FROM odi_decision_logs WHERE odi_event_id = $1",
                original_event_id
            )

        if not original:
            return False, {"error": f"Evento {original_event_id} no encontrado"}

        estado_original = original["estado_guardian"]
        vertical_original = original.get("vertical") or "P1"

        # PASO 5: Validar permisos
        perms = ROLE_PERMISSIONS.get(role)
        if not perms:
            return False, {"error": f"Rol desconocido: {role}"}

        if perms["vertical_scope"] == "assigned" and vertical_scope != "*":
            if vertical_original != vertical_scope:
                return False, {
                    "error": f"Sin permisos para vertical {vertical_original}. Scope: {vertical_scope}"
                }

        # Regla NEGRO: solo ARQUITECTO puede escalar
        if estado_original == "negro":
            if not perms["can_escalate_negro"]:
                return False, {"error": "Solo ARQUITECTO puede intervenir en NEGRO"}
            if target_decision != "ESCALAMIENTO_NEGRO":
                return False, {
                    "error": "NEGRO no se convierte en VERDE. Solo ESCALAMIENTO_NEGRO permitido."
                }

        if estado_original == "rojo" and not perms["can_override_rojo"]:
            return False, {"error": f"Rol {role} no puede hacer override de ROJO"}

        if estado_original == "amarillo" and not perms["can_override_amarillo"]:
            return False, {"error": f"Rol {role} no puede hacer override de AMARILLO"}

        # PASO 6: Crear nuevo evento
        new_event_id = self._new_event_id()
        timestamp = datetime.now(timezone.utc)

        override_data = {
            "original_event_id": original_event_id,
            "new_event_id": new_event_id,
            "human_id": human_id,
            "role": role,
            "decision": target_decision,
            "reason": reason,
            "evidence": evidence,
        }
        hash_integridad = self._hash_override(override_data)

        # PASO 7: Persistir (transacción atómica)
        new_estado = "verde" if "VERDE" in target_decision else "amarillo"
        if target_decision == "ESCALAMIENTO_NEGRO":
            new_estado = "negro"

        # Hash for decision log
        log_payload = (
            f"{new_event_id}{new_estado}SUPERVISADOOVERRIDE_MANUAL"
            f"{original['monto_cop'] or 0}{timestamp.isoformat()}"
            f"{self._audit_secret}"
        )
        log_hash = hashlib.sha256(log_payload.encode("utf-8")).hexdigest()

        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("""
                    INSERT INTO odi_overrides (
                        original_event_id, new_event_id, human_id, role,
                        vertical, decision, reason, evidence, hash_integridad
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                    original_event_id, new_event_id, human_id, role,
                    vertical_original, target_decision, reason,
                    json.dumps(evidence, ensure_ascii=False),
                    hash_integridad
                )

                await conn.execute("""
                    INSERT INTO odi_decision_logs (
                        odi_event_id, timestamp, usuario_id, vertical,
                        estado_guardian, modo_aplicado, intent_detectado,
                        decision_motivo, monto_cop, hash_integridad,
                        override_by, prev_event_id, event_type, metadata
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14
                    )
                """,
                    new_event_id,
                    timestamp,
                    original["usuario_id"],
                    vertical_original,
                    new_estado,
                    "SUPERVISADO",
                    "OVERRIDE_MANUAL",
                    f"Override por {human_id} ({role}): {reason}",
                    original["monto_cop"] or 0,
                    log_hash,
                    human_id,
                    original_event_id,
                    "OVERRIDE",
                    json.dumps({
                        "override": {
                            "original_event_id": original_event_id,
                            "decision": target_decision,
                            "evidence_hash": hashlib.sha256(
                                json.dumps(evidence, sort_keys=True).encode()
                            ).hexdigest(),
                        }
                    })
                )

        logger.info("Override ejecutado: %s -> %s por %s (%s)",
                     original_event_id, new_event_id, human_id, target_decision)

        return True, {
            "override_event_id": new_event_id,
            "original_event_id": original_event_id,
            "decision": target_decision,
            "human_id": human_id,
            "role": role,
            "hash_integridad": hash_integridad,
            "ttl_minutes": self._ttl_minutes,
            "expires_at": (timestamp + timedelta(minutes=self._ttl_minutes)).isoformat(),
        }

    async def validate_override_for_payment(self, override_event_id: str) -> Tuple[bool, str]:
        """
        Valida un override para permitir reintento de pago.
        Verifica: existe, es tipo OVERRIDE, no expirado, decisión correcta.
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT odi_event_id, timestamp, event_type, estado_guardian,
                          prev_event_id
                   FROM odi_decision_logs
                   WHERE odi_event_id = $1 AND event_type = 'OVERRIDE'""",
                override_event_id
            )

        if not row:
            return False, "Override no encontrado o no es tipo OVERRIDE"

        created = row["timestamp"]
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - created).total_seconds() / 60
        if elapsed > self._ttl_minutes:
            return False, f"Override expirado ({elapsed:.1f} min > {self._ttl_minutes} min)"

        if row["estado_guardian"] == "negro":
            return False, "NEGRO no autoriza pagos, solo escalamiento"

        if row["estado_guardian"] != "verde":
            return False, f"Estado {row['estado_guardian']} no autoriza pago"

        return True, row["prev_event_id"]


# ═══════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════

_instancia = None

def obtener_override_engine() -> ODIOverrideEngine:
    global _instancia
    if _instancia is None:
        _instancia = ODIOverrideEngine()
    return _instancia

def obtener_auth() -> OverrideAuth:
    return obtener_override_engine()._auth
