"""
INTENT OVERRIDE GATE — Implementación Ejecutable
=================================================
Versión: 1.4.1 (Domain Lock + Safety Exit)
Fecha: 10 Febrero 2026
Propósito: Corregir el bug "Para tu ECO" - ODI atrapado en loop de industria

v1.4.1: Safety Exit - Triggers para salir de modo emergencia
        - EXIT_SAFETY triggers: "sal de modo emergencia", "estoy bien", etc.
        - P1 puede romper SAFETY lock si es explícito
v1.4: Domain Lock - Persistencia de estado entre mensajes
      - SessionState con bloqueo de dominio
      - BIOS/Radar handler para P0 emergencias
      - Bloqueo de SRM cuando hay override activo
v1.2: Agregados sinónimos de emprendimiento
v1.1: Integración en producción, tests 10/10
v1.0: Implementación inicial

Este módulo DEBE ejecutarse ANTES de cualquier respuesta de ODI.
Si detecta un override, cambia el contexto Y LO BLOQUEA.
"""

import re
import json
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, asdict, field
from typing import Optional, Tuple, List, Dict
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intent_override_gate")

# ============================================================================
# CONFIGURACIÓN DE PERSISTENCIA
# ============================================================================
SESSION_STATE_DIR = Path("/opt/odi/sessions")
SESSION_LOCK_DURATION_MINUTES = 30  # Tiempo que dura un domain lock

# ============================================================================
# ESTADOS DEL DOMINIO (Máquina de Estados)
# ============================================================================

class DomainState(Enum):
    """Estados posibles del dominio activo"""
    DEFAULT = "DEFAULT"           # Estado inicial, puede ir a cualquier dominio
    SRM = "SRM"                   # Repuestos de motos (La Roca)
    EMPRENDIMIENTO = "EMPRENDIMIENTO"
    TURISMO = "TURISMO"
    TURISMO_SALUD = "TURISMO_SALUD"
    SALUD = "SALUD"
    BELLEZA = "BELLEZA"
    LEGAL = "LEGAL"
    EDUCACION = "EDUCACION"
    TRABAJO = "TRABAJO"
    SAFETY = "SAFETY"             # Emergencias (P0) - NUNCA rutear a SRM
    UNIVERSAL = "UNIVERSAL"       # Post-reset (P3)


@dataclass
class SessionState:
    """
    Estado de sesión con bloqueo de dominio.

    REGLA FUNDAMENTAL: Si locked=True, NUNCA rutear a SRM aunque
    el mensaje mencione motos/repuestos.
    """
    session_id: str
    user_id: str
    active_domain: DomainState = DomainState.DEFAULT
    locked: bool = False
    lock_reason: str = ""
    lock_expires_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    history: List[Dict] = field(default_factory=list)

    def lock_domain(self, domain: DomainState, reason: str, duration_minutes: int = SESSION_LOCK_DURATION_MINUTES):
        """Bloquea el dominio activo por un tiempo determinado"""
        self.active_domain = domain
        self.locked = True
        self.lock_reason = reason
        self.lock_expires_at = (datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)).isoformat()
        self.last_updated = datetime.now(timezone.utc).isoformat()
        self.history.append({
            "action": "DOMAIN_LOCK",
            "domain": domain.value,
            "reason": reason,
            "timestamp": self.last_updated,
        })
        logger.info(f"[DOMAIN_LOCK] Session {self.session_id}: {domain.value} locked for {duration_minutes}min")

    def unlock_domain(self, reason: str = "manual_unlock"):
        """Desbloquea el dominio (permite volver a SRM)"""
        old_domain = self.active_domain
        self.locked = False
        self.lock_reason = ""
        self.lock_expires_at = None
        self.active_domain = DomainState.DEFAULT
        self.last_updated = datetime.now(timezone.utc).isoformat()
        self.history.append({
            "action": "DOMAIN_UNLOCK",
            "from_domain": old_domain.value,
            "reason": reason,
            "timestamp": self.last_updated,
        })
        logger.info(f"[DOMAIN_UNLOCK] Session {self.session_id}: unlocked from {old_domain.value}")

    def is_lock_expired(self) -> bool:
        """Verifica si el lock ha expirado"""
        if not self.locked or not self.lock_expires_at:
            return False
        expiry = datetime.fromisoformat(self.lock_expires_at.replace('Z', '+00:00'))
        return datetime.now(timezone.utc) > expiry

    def can_route_to_srm(self) -> bool:
        """
        REGLA CRÍTICA: Solo puede ir a SRM si NO está bloqueado
        o si el bloqueo expiró.
        """
        if not self.locked:
            return True
        if self.is_lock_expired():
            self.unlock_domain("lock_expired")
            return True
        return False

    def to_dict(self) -> Dict:
        """Serializa a diccionario para persistencia"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "active_domain": self.active_domain.value,
            "locked": self.locked,
            "lock_reason": self.lock_reason,
            "lock_expires_at": self.lock_expires_at,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "history": self.history[-10:],  # Solo últimos 10 eventos
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SessionState":
        """Deserializa desde diccionario"""
        state = cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
        )
        state.active_domain = DomainState(data.get("active_domain", "DEFAULT"))
        state.locked = data.get("locked", False)
        state.lock_reason = data.get("lock_reason", "")
        state.lock_expires_at = data.get("lock_expires_at")
        state.created_at = data.get("created_at", state.created_at)
        state.last_updated = data.get("last_updated", state.last_updated)
        state.history = data.get("history", [])
        return state


# ============================================================================
# GESTOR DE SESIONES (Persistencia en disco)
# ============================================================================

class SessionManager:
    """
    Gestiona el estado de sesiones con persistencia en disco.
    En producción puede cambiarse a Redis.
    """

    def __init__(self, state_dir: Path = SESSION_STATE_DIR):
        self.state_dir = state_dir
        self._ensure_dir()

    def _ensure_dir(self):
        """Crea el directorio de estados si no existe"""
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create session dir: {e}. Using /tmp")
            self.state_dir = Path("/tmp/odi_sessions")
            self.state_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, session_id: str) -> Path:
        """Genera path seguro para el archivo de sesión"""
        safe_id = hashlib.sha256(session_id.encode()).hexdigest()[:16]
        return self.state_dir / f"session_{safe_id}.json"

    def get_or_create(self, session_id: str, user_id: str) -> SessionState:
        """Obtiene sesión existente o crea una nueva"""
        path = self._get_session_path(session_id)

        if path.exists():
            try:
                data = json.loads(path.read_text())
                state = SessionState.from_dict(data)
                logger.debug(f"[SESSION] Loaded existing session: {session_id}")
                return state
            except Exception as e:
                logger.warning(f"Failed to load session {session_id}: {e}")

        # Crear nueva sesión
        state = SessionState(session_id=session_id, user_id=user_id)
        self.save(state)
        logger.info(f"[SESSION] Created new session: {session_id}")
        return state

    def save(self, state: SessionState):
        """Guarda el estado de la sesión"""
        path = self._get_session_path(state.session_id)
        try:
            path.write_text(json.dumps(state.to_dict(), indent=2))
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    def delete(self, session_id: str):
        """Elimina una sesión"""
        path = self._get_session_path(session_id)
        try:
            path.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to delete session: {e}")


# Instancia global del gestor de sesiones
_session_manager = SessionManager()


# ============================================================================
# BIOS/RADAR HANDLERS (Capacidades de emergencia)
# ============================================================================

class BiosRadarHandler:
    """
    Handler para capacidades BIOS/Radar de ODI.
    Estas son las instancias, recursos y contactos que ODI puede activar
    en emergencias (P0).
    """

    # Contactos de emergencia (programados en memoria BIOS)
    EMERGENCY_CONTACTS = {
        "POLICIA": {"number": "123", "name": "Policía Nacional"},
        "BOMBEROS": {"number": "125", "name": "Bomberos"},
        "CRUZ_ROJA": {"number": "106", "name": "Cruz Roja"},
        "AMBULANCIA": {"number": "125", "name": "Línea de Emergencias"},
    }

    @classmethod
    def get_emergency_response(cls, category: str, user_message: str) -> str:
        """
        Genera respuesta de emergencia con capacidad de activación.
        ODI PUEDE llamar a estas instancias cuando está en modo SAFETY.
        """
        if category in ("SAFETY", "HEALTH_EMERGENCY"):
            contacts = cls.EMERGENCY_CONTACTS
            response = (
                "Entiendo que es urgente.\n\n"
                "Puedo ayudarte a contactar:\n"
            )
            for key, contact in contacts.items():
                response += f"- {contact['name']}: {contact['number']}\n"

            response += (
                "\n¿Necesitas que te ayude a comunicarte con alguno? "
                "Solo dime cuál y activo el protocolo."
            )
            return response

        return None

    @classmethod
    def activate_protocol(cls, protocol: str, session_state: SessionState) -> Dict:
        """
        Activa un protocolo de emergencia.
        Retorna información para que el sistema ejecute la acción.
        """
        event = {
            "type": "BIOS_RADAR_ACTIVATION",
            "protocol": protocol,
            "session_id": session_state.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if protocol in cls.EMERGENCY_CONTACTS:
            contact = cls.EMERGENCY_CONTACTS[protocol]
            event["action"] = "CALL"
            event["target"] = contact["number"]
            event["target_name"] = contact["name"]
            logger.warning(f"[BIOS/RADAR] EMERGENCY PROTOCOL ACTIVATED: {protocol}")

        return event


class OverrideLevel(Enum):
    """Niveles de prioridad de override"""
    P0_CRITICAL = 0  # Seguridad/Urgencia - rompe TODO
    P1_HIGH = 1      # Cambio de industria/modo
    P2_MEDIUM = 2    # Ajuste de contexto
    P3_META = 3      # Reset total de identidad
    NONE = 99        # Sin override


class OverrideAction(Enum):
    """Acciones a ejecutar según el override"""
    SAFETY_FLOW = "safety_flow"
    DOMAIN_SWITCH = "domain_switch"
    CONTEXT_ADJUST = "context_adjust"
    FULL_RESET = "full_reset"
    NONE = "none"


@dataclass
class OverrideResult:
    """Resultado del análisis de override"""
    triggered: bool
    level: OverrideLevel
    action: OverrideAction
    trigger_word: str
    new_domain: Optional[str]
    canonical_response: str
    event: Dict


# ============================================================================
# TABLA DE TRIGGERS (Constitucional - NO modificar sin autorización)
# ============================================================================

# P0: CRÍTICO - Seguridad/Urgencia (rompe TODO)
P0_TRIGGERS = {
    # Palabras clave de urgencia
    "urgencia": "SAFETY",
    "urgente": "SAFETY",
    "emergencia": "SAFETY",
    "policía": "SAFETY",
    "policia": "SAFETY",
    "ambulancia": "SAFETY",
    "auxilio": "SAFETY",
    "socorro": "SAFETY",
    "ayuda urgente": "SAFETY",
    "me robaron": "SAFETY",
    "me siguen": "SAFETY",
    "me atacaron": "SAFETY",
    "peligro": "SAFETY",
    "amenaza": "SAFETY",
    "me van a": "SAFETY",
    "estoy en peligro": "SAFETY",
    "dolor fuerte": "HEALTH_EMERGENCY",
    "me desmayé": "HEALTH_EMERGENCY",
    "no puedo respirar": "HEALTH_EMERGENCY",
    "accidente": "SAFETY",
}

# P1: ALTO - Cambio de industria/modo (override industria actual)
P1_TRIGGERS = {
    # Emprendimiento (sinónimos completos)
    "emprender": "EMPRENDIMIENTO",
    "emprendimiento": "EMPRENDIMIENTO",
    "negocio": "EMPRENDIMIENTO",
    "idea de negocio": "EMPRENDIMIENTO",
    "quiero emprender": "EMPRENDIMIENTO",
    "tengo una idea": "EMPRENDIMIENTO",
    "iniciar un negocio": "EMPRENDIMIENTO",
    "crear empresa": "EMPRENDIMIENTO",
    "mi propio negocio": "EMPRENDIMIENTO",
    "lanzar mi propio negocio": "EMPRENDIMIENTO",
    "iniciar un proyecto empresarial": "EMPRENDIMIENTO",
    "materializar una idea": "EMPRENDIMIENTO",
    "independizarme laboralmente": "EMPRENDIMIENTO",
    "crear mi propia empresa": "EMPRENDIMIENTO",
    "convertirme en mi propio jefe": "EMPRENDIMIENTO",
    "ser mi propio jefe": "EMPRENDIMIENTO",
    "montar un negocio": "EMPRENDIMIENTO",
    "abrir un negocio": "EMPRENDIMIENTO",
    "proyecto empresarial": "EMPRENDIMIENTO",

    # Turismo
    "turismo": "TURISMO",
    "viaje": "TURISMO",
    "hotel": "TURISMO",
    "turismo odontológico": "TURISMO_SALUD",
    "turismo odontologico": "TURISMO_SALUD",
    "turismo médico": "TURISMO_SALUD",
    "turismo medico": "TURISMO_SALUD",
    "turismo dental": "TURISMO_SALUD",
    "viaje dental": "TURISMO_SALUD",

    # Salud General
    "salud": "SALUD",
    "médico": "SALUD",
    "medico": "SALUD",
    "clínica": "SALUD",
    "clinica": "SALUD",

    # Dental / Odontología (TURISMO_SALUD - Matzu)
    "odontología": "TURISMO_SALUD",
    "odontologia": "TURISMO_SALUD",
    "dentista": "TURISMO_SALUD",
    "implante": "TURISMO_SALUD",
    "implantes": "TURISMO_SALUD",
    "implantes dentales": "TURISMO_SALUD",
    "diseño de sonrisa": "TURISMO_SALUD",
    "carillas": "TURISMO_SALUD",
    "blanqueamiento": "TURISMO_SALUD",
    "blanqueamiento dental": "TURISMO_SALUD",
    "ortodoncia": "TURISMO_SALUD",
    "brackets": "TURISMO_SALUD",
    "invisalign": "TURISMO_SALUD",
    "corona dental": "TURISMO_SALUD",
    "endodoncia": "TURISMO_SALUD",
    "extracción dental": "TURISMO_SALUD",
    "prótesis dental": "TURISMO_SALUD",
    "matzu": "TURISMO_SALUD",
    "matzu dental": "TURISMO_SALUD",

    # Bruxismo (COVER'S)
    "bruxismo": "TURISMO_SALUD",
    "rechinar dientes": "TURISMO_SALUD",
    "guarda oclusal": "TURISMO_SALUD",
    "placa de bruxismo": "TURISMO_SALUD",
    "protector dental": "TURISMO_SALUD",
    "covers": "TURISMO_SALUD",

    # Capilar (Cabezas Sanas)
    "cabeza sana": "SALUD",
    "cabezas sanas": "SALUD",
    "caída del cabello": "SALUD",
    "alopecia": "SALUD",
    "tricología": "SALUD",
    "tricologia": "SALUD",
    "tricólogo": "SALUD",
    "tricologo": "SALUD",
    "tratamiento capilar": "SALUD",
    "injerto capilar": "SALUD",
    "trasplante de cabello": "SALUD",

    # Belleza
    "belleza": "BELLEZA",
    "estética": "BELLEZA",
    "estetica": "BELLEZA",
    "spa": "BELLEZA",
    "cosméticos": "BELLEZA",
    "cosmeticos": "BELLEZA",

    # Legal
    "abogado": "LEGAL",
    "legal": "LEGAL",
    "contrato": "LEGAL",
    "demanda": "LEGAL",

    # Educación
    "educación": "EDUCACION",
    "educacion": "EDUCACION",
    "curso": "EDUCACION",
    "academia": "EDUCACION",
    "aprender": "EDUCACION",

    # Trabajo/Empleo
    "trabajo": "TRABAJO",
    "empleo": "TRABAJO",
    "empresa": "TRABAJO",
    "empleado": "TRABAJO",
    "optimizar tareas": "TRABAJO",
}

# P2: MEDIO - Ajuste de contexto
# NOTA: Usar frases completas para evitar falsos positivos
P2_TRIGGERS = {
    "no entiendo": "HELP",
    "explícame": "HELP",
    "explicame": "HELP",
    "cómo funciona": "HELP",
    "como funciona": "HELP",
    "ayúdame odi": "HELP",
    "ayudame odi": "HELP",
    "odi ayúdame": "HELP",
    "odi ayudame": "HELP",
    "cambia de tema": "SWITCH",
    "otro tema": "SWITCH",
    "hablemos de otra cosa": "SWITCH",
    "basta ya": "STOP",
    "para ya": "STOP",
    "detente": "STOP",
    "deja de": "STOP",
    # Salida de emergencia (v1.4.1)
    "sal de modo emergencia": "EXIT_SAFETY",
    "salir de emergencia": "EXIT_SAFETY",
    "salir de modo emergencia": "EXIT_SAFETY",
    "ya estoy bien": "EXIT_SAFETY",
    "estoy bien": "EXIT_SAFETY",
    "falsa alarma": "EXIT_SAFETY",
    "no es emergencia": "EXIT_SAFETY",
    "cancelar emergencia": "EXIT_SAFETY",
    "todo bien": "EXIT_SAFETY",
}

# P3: META - Reset total de identidad
P3_TRIGGERS = {
    "tú eres más que eso": "IDENTITY_RESET",
    "tu eres mas que eso": "IDENTITY_RESET",
    "eres más que eso": "IDENTITY_RESET",
    "eres mas que eso": "IDENTITY_RESET",
    "deja de ser experto": "IDENTITY_RESET",
    "no solo sabes de": "IDENTITY_RESET",
    "solo sabes de": "IDENTITY_CHALLENGE",
    "no haces nada": "IDENTITY_CHALLENGE",
    "no sabes nada": "IDENTITY_CHALLENGE",
    "quién eres": "IDENTITY_QUERY",
    "quien eres": "IDENTITY_QUERY",
    "qué eres": "IDENTITY_QUERY",
    "que eres": "IDENTITY_QUERY",
}

# ============================================================================
# RESPUESTAS CANÓNICAS (Obligatorias)
# ============================================================================

CANONICAL_RESPONSES = {
    # P0: Seguridad
    "SAFETY": (
        "Si estás en peligro inmediato, llama a la línea de emergencias ahora:\n"
        "🚨 123 - Policía Nacional\n"
        "🚑 125 - Bomberos\n"
        "❤️ 106 - Cruz Roja\n\n"
        "¿Estás a salvo? ¿En qué ciudad estás?"
    ),
    "HEALTH_EMERGENCY": (
        "Esto suena a una emergencia médica.\n"
        "🚑 Llama al 125 (Bomberos) o 106 (Cruz Roja) inmediatamente.\n\n"
        "¿Hay alguien contigo que pueda ayudar?"
    ),

    # P1: Cambio de dominio
    "EMPRENDIMIENTO": (
        "Entendido. Cambio a modo Emprendimiento.\n"
        "¿Esto es para iniciar desde cero o ya tienes una idea definida?"
    ),
    "TURISMO": (
        "Entendido. Cambio a modo Turismo.\n"
        "¿Buscas planear un viaje o crear un negocio de turismo?"
    ),
    "TURISMO_SALUD": (
        "Entendido. Cambio a modo Turismo Dental.\n\n"
        "Trabajo con clínicas especializadas en Medellín, Colombia.\n"
        "Para darte la mejor información, cuéntame:\n\n"
        "1. ¿Qué procedimiento te interesa? (implantes, diseño de sonrisa, blanqueamiento, etc.)\n"
        "2. ¿Cuándo planeas viajar?\n"
        "3. ¿Ya tienes un presupuesto en mente?"
    ),
    "SALUD": (
        "Entendido. Cambio a modo Salud.\n"
        "¿Esto es para una consulta personal o para un proyecto/negocio?"
    ),
    "BELLEZA": (
        "Entendido. Cambio a modo Belleza.\n"
        "¿Buscas servicios o quieres emprender en este sector?"
    ),
    "LEGAL": (
        "Entendido. Cambio a modo Legal.\n"
        "¿Necesitas asesoría legal personal o para un negocio?"
    ),
    "EDUCACION": (
        "Entendido. Cambio a modo Educación.\n"
        "¿Quieres aprender algo específico o crear contenido educativo?"
    ),
    "TRABAJO": (
        "Entendido. Cambio a modo Trabajo.\n"
        "¿Buscas optimizar tareas en tu empresa o encontrar empleo?"
    ),

    # P2: Ayuda/Contexto
    "HELP": (
        "Puedo ayudarte con:\n"
        "• Tu trabajo (optimizar tareas)\n"
        "• Tu negocio (crear presencia digital)\n"
        "• Tus compras (encontrar productos)\n"
        "• Aprender (academia y cursos)\n\n"
        "¿Por dónde quieres empezar?"
    ),
    "SWITCH": (
        "Entendido. Cambio de tema.\n"
        "¿En qué más puedo ayudarte?"
    ),
    "STOP": (
        "Entendido. Pausa.\n"
        "Cuando quieras continuar, solo dime."
    ),

    # P3: Identidad
    "IDENTITY_RESET": (
        "Tienes razón. No soy solo de una industria.\n\n"
        "Soy ODI. Puedo ayudarte en cualquier área:\n"
        "emprender, trabajar, comprar, aprender.\n\n"
        "¿Qué necesitas hoy?"
    ),
    "IDENTITY_CHALLENGE": (
        "Tienes razón, ese repuesto no corresponde a lo que necesitas.\n"
        "Déjame entender mejor: ¿qué es lo que realmente buscas?"
    ),
    "IDENTITY_QUERY": (
        "Soy ODI, un organismo digital industrial.\n"
        "Puedo ayudarte con trabajo, emprendimiento, compras y aprendizaje.\n\n"
        "¿Qué necesitas?"
    ),
}


# ============================================================================
# MOTOR DE DETECCIÓN
# ============================================================================

def normalize_text(text: str) -> str:
    """Normaliza el texto para comparación"""
    text = text.lower().strip()
    # Remover puntuación excepto acentos
    text = re.sub(r'[^\w\sáéíóúñü]', '', text)
    return text


def check_triggers(text: str, triggers: Dict[str, str]) -> Optional[Tuple[str, str]]:
    """
    Busca triggers en el texto.
    Retorna (trigger_word, category) si encuentra, None si no.
    """
    normalized = normalize_text(text)

    # Ordenar por longitud descendente para priorizar frases más específicas
    sorted_triggers = sorted(triggers.keys(), key=len, reverse=True)

    for trigger in sorted_triggers:
        if trigger in normalized:
            return (trigger, triggers[trigger])

    return None


def analyze_intent(message: str, current_domain: str = "MOTOS") -> OverrideResult:
    """
    Analiza el mensaje y determina si hay un override necesario.

    Args:
        message: Mensaje del usuario
        current_domain: Dominio/industria actual de la conversación

    Returns:
        OverrideResult con toda la información del análisis
    """

    # Evento base para auditoría
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "intent_analysis",
        "input_message": message,
        "current_domain": current_domain,
    }

    # P0: Verificar seguridad/urgencia PRIMERO
    p0_match = check_triggers(message, P0_TRIGGERS)
    if p0_match:
        trigger, category = p0_match
        event.update({
            "override_level": "P0_CRITICAL",
            "trigger_word": trigger,
            "category": category,
            "action": "safety_flow",
        })
        return OverrideResult(
            triggered=True,
            level=OverrideLevel.P0_CRITICAL,
            action=OverrideAction.SAFETY_FLOW,
            trigger_word=trigger,
            new_domain="SAFETY",
            canonical_response=CANONICAL_RESPONSES.get(category, CANONICAL_RESPONSES["SAFETY"]),
            event=event,
        )

    # P3: Verificar meta-identidad (antes de P1 porque puede resetear todo)
    p3_match = check_triggers(message, P3_TRIGGERS)
    if p3_match:
        trigger, category = p3_match
        event.update({
            "override_level": "P3_META",
            "trigger_word": trigger,
            "category": category,
            "action": "full_reset",
        })
        return OverrideResult(
            triggered=True,
            level=OverrideLevel.P3_META,
            action=OverrideAction.FULL_RESET,
            trigger_word=trigger,
            new_domain="UNIVERSAL",
            canonical_response=CANONICAL_RESPONSES.get(category, CANONICAL_RESPONSES["IDENTITY_RESET"]),
            event=event,
        )

    # P1: Verificar cambio de industria
    p1_match = check_triggers(message, P1_TRIGGERS)
    if p1_match:
        trigger, category = p1_match
        # Solo hacer override si el dominio es diferente al actual
        if category != current_domain:
            event.update({
                "override_level": "P1_HIGH",
                "trigger_word": trigger,
                "category": category,
                "action": "domain_switch",
                "from_domain": current_domain,
                "to_domain": category,
            })
            return OverrideResult(
                triggered=True,
                level=OverrideLevel.P1_HIGH,
                action=OverrideAction.DOMAIN_SWITCH,
                trigger_word=trigger,
                new_domain=category,
                canonical_response=CANONICAL_RESPONSES.get(category, f"Entendido. Cambio a modo {category}. ¿Cómo puedo ayudarte?"),
                event=event,
            )

    # P2: Verificar ajuste de contexto
    p2_match = check_triggers(message, P2_TRIGGERS)
    if p2_match:
        trigger, category = p2_match
        event.update({
            "override_level": "P2_MEDIUM",
            "trigger_word": trigger,
            "category": category,
            "action": "context_adjust",
        })
        return OverrideResult(
            triggered=True,
            level=OverrideLevel.P2_MEDIUM,
            action=OverrideAction.CONTEXT_ADJUST,
            trigger_word=trigger,
            new_domain=None,  # No cambia dominio
            canonical_response=CANONICAL_RESPONSES.get(category, "¿En qué puedo ayudarte?"),
            event=event,
        )

    # Sin override
    event.update({
        "override_level": "NONE",
        "action": "none",
    })
    return OverrideResult(
        triggered=False,
        level=OverrideLevel.NONE,
        action=OverrideAction.NONE,
        trigger_word="",
        new_domain=None,
        canonical_response="",
        event=event,
    )


# ============================================================================
# HANDLERS ESPECÍFICOS POR DOMINIO (v1.4)
# ============================================================================

def _handle_locked_safety_message(message: str, session_state: SessionState) -> Dict:
    """
    Procesa mensajes cuando el dominio está bloqueado en SAFETY.
    NUNCA rutea a SRM, siempre usa BIOS/Radar.
    """
    normalized = normalize_text(message)

    # Detectar solicitud de activar protocolo de emergencia
    protocol_keywords = {
        "policia": "POLICIA",
        "policía": "POLICIA",
        "123": "POLICIA",
        "ambulancia": "AMBULANCIA",
        "125": "AMBULANCIA",
        "bomberos": "BOMBEROS",
        "cruz roja": "CRUZ_ROJA",
        "106": "CRUZ_ROJA",
    }

    for keyword, protocol in protocol_keywords.items():
        if keyword in normalized:
            # Activar protocolo BIOS/Radar
            activation_event = BiosRadarHandler.activate_protocol(protocol, session_state)
            contact = BiosRadarHandler.EMERGENCY_CONTACTS.get(protocol, {})

            return {
                "override": True,
                "response": (
                    f"Activando protocolo de emergencia: {contact.get('name', protocol)}\n"
                    f"Número: {contact.get('number', 'N/A')}\n\n"
                    "¿Estás a salvo? ¿Necesitas algo más?"
                ),
                "domain_locked": True,
                "bios_radar_event": activation_event,
            }

    # Mensaje de seguimiento sin activación específica
    return {
        "override": True,
        "response": (
            "Sigo aquí contigo.\n\n"
            "Puedo ayudarte a contactar:\n"
            "- Policía: 123\n"
            "- Ambulancia/Bomberos: 125\n"
            "- Cruz Roja: 106\n\n"
            "¿Cuál necesitas?"
        ),
        "domain_locked": True,
    }


def _handle_locked_emprendimiento_message(message: str, session_state: SessionState) -> Dict:
    """
    Procesa mensajes cuando el dominio está bloqueado en EMPRENDIMIENTO.
    NUNCA rutea a SRM, mantiene contexto de negocio.
    """
    normalized = normalize_text(message)

    # Respuestas contextuales para emprendimiento
    # Detectar tipo de emprendimiento mencionado
    verticals = {
        "maquillaje": "belleza y cosméticos",
        "cosmeticos": "belleza y cosméticos",
        "ropa": "moda y confección",
        "comida": "alimentos y restaurantes",
        "tecnologia": "tecnología y software",
        "software": "tecnología y software",
        "servicios": "servicios profesionales",
    }

    detected_vertical = None
    for keyword, vertical in verticals.items():
        if keyword in normalized:
            detected_vertical = vertical
            break

    if detected_vertical:
        return {
            "override": True,
            "response": (
                f"Perfecto, emprendimiento en {detected_vertical}.\n\n"
                "Para ayudarte mejor, necesito saber:\n"
                "1. ¿Ya tienes experiencia en el sector?\n"
                "2. ¿Cuánto capital inicial tienes disponible?\n"
                "3. ¿Quieres vender online, presencial o ambos?"
            ),
            "domain_locked": True,
            "detected_vertical": detected_vertical,
        }

    # Respuesta genérica para emprendimiento
    return {
        "override": True,
        "response": (
            "Entendido. Cuéntame más sobre tu idea de negocio.\n\n"
            "¿Qué producto o servicio quieres ofrecer?"
        ),
        "domain_locked": True,
    }


def _handle_locked_turismo_salud_message(message: str, session_state: SessionState) -> Dict:
    """
    Procesa mensajes cuando el dominio está bloqueado en TURISMO_SALUD.
    Maneja consultas de turismo odontológico (Matzu, COVER'S).
    NUNCA rutea a SRM.
    """
    normalized = normalize_text(message)

    # Detectar procedimiento específico mencionado
    procedures = {
        "implante": {"name": "Implantes Dentales", "range": "$2.5M - $4M COP por unidad"},
        "implantes": {"name": "Implantes Dentales", "range": "$2.5M - $4M COP por unidad"},
        "diseño de sonrisa": {"name": "Diseño de Sonrisa", "range": "$3M - $15M COP"},
        "sonrisa": {"name": "Diseño de Sonrisa", "range": "$3M - $15M COP"},
        "carillas": {"name": "Carillas", "range": "$800K - $1.5M COP por unidad"},
        "blanqueamiento": {"name": "Blanqueamiento Dental", "range": "$400K - $800K COP"},
        "ortodoncia": {"name": "Ortodoncia", "range": "$3M - $6M COP"},
        "brackets": {"name": "Ortodoncia con Brackets", "range": "$3M - $6M COP"},
        "invisalign": {"name": "Invisalign", "range": "$8M - $15M COP"},
        "corona": {"name": "Corona Cerámica", "range": "$800K - $1.2M COP"},
        "endodoncia": {"name": "Endodoncia", "range": "$300K - $600K COP"},
        "bruxismo": {"name": "Tratamiento de Bruxismo", "range": "$150K - $600K COP"},
        "guarda": {"name": "Guarda Oclusal", "range": "$150K - $600K COP"},
    }

    detected_procedure = None
    for keyword, procedure in procedures.items():
        if keyword in normalized:
            detected_procedure = procedure
            break

    if detected_procedure:
        return {
            "override": True,
            "response": (
                f"Perfecto, te interesa: {detected_procedure['name']}.\n\n"
                f"Rango de inversión: {detected_procedure['range']}\n\n"
                "Para preparar tu plan de tratamiento, necesito:\n"
                "1. ¿Cuándo planeas viajar a Medellín?\n"
                "2. ¿Cuántos días puedes quedarte?\n"
                "3. ¿Necesitas ayuda con hospedaje?"
            ),
            "domain_locked": True,
            "detected_procedure": detected_procedure["name"],
        }

    # Detectar fechas o viaje
    travel_keywords = ["viajar", "viaje", "vuelo", "abril", "mayo", "junio", "julio", "agosto",
                       "septiembre", "octubre", "noviembre", "diciembre", "enero", "febrero", "marzo"]
    for keyword in travel_keywords:
        if keyword in normalized:
            return {
                "override": True,
                "response": (
                    "Entendido. Para coordinar tu viaje dental:\n\n"
                    "1. ¿Qué procedimiento necesitas? (implantes, blanqueamiento, carillas, etc.)\n"
                    "2. ¿Ya tienes radiografías o estudios previos?\n"
                    "3. ¿Vienes solo o acompañado?"
                ),
                "domain_locked": True,
            }

    # Respuesta genérica para turismo salud
    return {
        "override": True,
        "response": (
            "Seguimos en modo Turismo Dental.\n\n"
            "Trabajo con:\n"
            "- Matzu Dental Aesthetics (Medellín) - Implantes, diseño de sonrisa\n"
            "- COVER'S Lab - Especialistas en bruxismo\n\n"
            "¿Qué procedimiento te interesa?"
        ),
        "domain_locked": True,
    }


# ============================================================================
# FUNCIÓN PRINCIPAL PARA n8n / CORTEX (v1.4 - Domain Lock)
# ============================================================================

def process_message(message: str, context: Dict) -> Dict:
    """
    Función principal para procesar mensajes en ODI.
    Debe llamarse ANTES de cualquier otro procesamiento.

    v1.4: Incluye Domain Lock para persistir contexto entre mensajes.

    Args:
        message: Mensaje del usuario
        context: Contexto actual de la conversación
            - current_domain: Industria actual (default: "MOTOS")
            - session_id: ID de sesión (REQUERIDO para v1.4)
            - user_id: ID del usuario

    Returns:
        Dict con:
            - override: bool - Si hubo override o domain lock activo
            - response: str - Respuesta a enviar
            - new_context: Dict - Contexto actualizado
            - event: Dict - Evento para NDJSON audit
            - continue_normal_flow: bool - Si debe continuar con el flujo normal (SRM)
            - domain_locked: bool - Si el dominio está bloqueado
            - can_route_to_srm: bool - Si puede rutear a catálogo de repuestos
    """

    session_id = context.get("session_id", "unknown")
    user_id = context.get("user_id", "unknown")

    # =========================================================================
    # PASO 1: Cargar estado de sesión persistente
    # =========================================================================
    session_state = _session_manager.get_or_create(session_id, user_id)

    # Verificar si hay un domain lock activo
    if session_state.locked and not session_state.is_lock_expired():
        logger.info(f"[DOMAIN_LOCK] Active lock: {session_state.active_domain.value}")

        # =====================================================================
        # PASO 2A: Dominio bloqueado - procesar según dominio activo
        # =====================================================================

        # Verificar si hay un trigger de desbloqueo
        p2_match = check_triggers(message, P2_TRIGGERS)

        # EXIT_SAFETY: Salir de modo emergencia explícitamente
        if p2_match and p2_match[1] == "EXIT_SAFETY":
            session_state.unlock_domain("user_exit_safety")
            _session_manager.save(session_state)
            logger.info(f"[SAFETY_EXIT] User explicitly exited SAFETY mode")

            return {
                "override": True,
                "response": "Entendido, saliendo de modo emergencia. Me alegra que estés bien. ¿En qué puedo ayudarte ahora?",
                "new_context": context,
                "event": {
                    "event_type": "safety_exit",
                    "trigger": p2_match[0],
                    "session_id": session_id,
                },
                "continue_normal_flow": False,
                "domain_locked": False,
                "can_route_to_srm": True,
            }

        # SWITCH: Cambiar de tema genérico
        if p2_match and p2_match[1] == "SWITCH":
            # Usuario quiere cambiar de tema - desbloquear
            session_state.unlock_domain("user_requested_switch")
            _session_manager.save(session_state)

            return {
                "override": True,
                "response": "Entendido, cambio de tema. ¿En qué más puedo ayudarte?",
                "new_context": context,
                "event": {
                    "event_type": "domain_unlock",
                    "trigger": "user_switch",
                    "from_domain": session_state.active_domain.value,
                    "session_id": session_id,
                },
                "continue_normal_flow": False,
                "domain_locked": False,
                "can_route_to_srm": True,
            }

        # P1 override puede romper SAFETY si es explícito (emprender, turismo, etc.)
        if session_state.active_domain == DomainState.SAFETY:
            p1_match = check_triggers(message, P1_TRIGGERS)
            if p1_match:
                # Usuario quiere cambiar de dominio - permitir salir de SAFETY
                session_state.unlock_domain(f"p1_override:{p1_match[0]}")
                _session_manager.save(session_state)
                logger.info(f"[SAFETY_OVERRIDE] P1 trigger '{p1_match[0]}' broke SAFETY lock")
                # Continuar procesando el mensaje normalmente (no return aquí)

        # Procesar según dominio bloqueado
        if session_state.active_domain == DomainState.SAFETY:
            result = _handle_locked_safety_message(message, session_state)
            result["new_context"] = context
            result["event"] = {
                "event_type": "safety_continuation",
                "session_id": session_id,
                "locked_domain": "SAFETY",
            }
            result["continue_normal_flow"] = False
            result["can_route_to_srm"] = False  # NUNCA
            _session_manager.save(session_state)
            return result

        if session_state.active_domain == DomainState.EMPRENDIMIENTO:
            result = _handle_locked_emprendimiento_message(message, session_state)
            result["new_context"] = context
            result["event"] = {
                "event_type": "emprendimiento_continuation",
                "session_id": session_id,
                "locked_domain": "EMPRENDIMIENTO",
            }
            result["continue_normal_flow"] = False
            result["can_route_to_srm"] = False  # NUNCA mientras esté bloqueado
            _session_manager.save(session_state)
            return result

        if session_state.active_domain == DomainState.TURISMO_SALUD:
            result = _handle_locked_turismo_salud_message(message, session_state)
            result["new_context"] = context
            result["event"] = {
                "event_type": "turismo_salud_continuation",
                "session_id": session_id,
                "locked_domain": "TURISMO_SALUD",
            }
            result["continue_normal_flow"] = False
            result["can_route_to_srm"] = False  # NUNCA mientras esté bloqueado
            _session_manager.save(session_state)
            return result

        # Otros dominios bloqueados: mantener contexto
        if session_state.active_domain in (
            DomainState.TURISMO, DomainState.SALUD,
            DomainState.BELLEZA, DomainState.LEGAL, DomainState.EDUCACION, DomainState.TRABAJO
        ):
            domain_name = session_state.active_domain.value
            return {
                "override": True,
                "response": (
                    f"Seguimos en modo {domain_name}.\n"
                    f"¿Cómo puedo ayudarte con tu consulta?"
                ),
                "new_context": context,
                "event": {
                    "event_type": "domain_continuation",
                    "session_id": session_id,
                    "locked_domain": domain_name,
                },
                "continue_normal_flow": False,
                "domain_locked": True,
                "can_route_to_srm": False,
            }

    # =========================================================================
    # PASO 2B: Sin lock activo - analizar intent normalmente
    # =========================================================================

    current_domain = context.get("current_domain", "MOTOS")
    result = analyze_intent(message, current_domain)

    # Agregar metadata al evento
    result.event["session_id"] = session_id
    result.event["user_id"] = user_id

    if result.triggered:
        # Hay override - retornar respuesta canónica Y bloquear dominio
        new_context = context.copy()

        # =====================================================================
        # PASO 3: Bloquear dominio según prioridad
        # =====================================================================
        should_lock = False
        lock_domain = None

        if result.level == OverrideLevel.P0_CRITICAL:
            # SAFETY: Bloquear INMEDIATAMENTE
            should_lock = True
            lock_domain = DomainState.SAFETY
            logger.warning(f"[P0_CRITICAL] Locking domain to SAFETY for session {session_id}")

        elif result.level == OverrideLevel.P1_HIGH:
            # Cambio de industria: Bloquear al nuevo dominio
            should_lock = True
            try:
                lock_domain = DomainState[result.new_domain]
            except KeyError:
                lock_domain = DomainState.DEFAULT

        elif result.level == OverrideLevel.P3_META:
            # Reset de identidad: Bloquear temporalmente a UNIVERSAL
            should_lock = True
            lock_domain = DomainState.UNIVERSAL

        if should_lock and lock_domain:
            session_state.lock_domain(
                domain=lock_domain,
                reason=f"trigger:{result.trigger_word}",
                duration_minutes=SESSION_LOCK_DURATION_MINUTES,
            )
            _session_manager.save(session_state)
            result.event["domain_locked"] = True
            result.event["lock_expires_at"] = session_state.lock_expires_at

        if result.new_domain:
            new_context["current_domain"] = result.new_domain
            new_context["last_override"] = {
                "level": result.level.name,
                "from": current_domain,
                "to": result.new_domain,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        logger.info(f"[OVERRIDE] {result.level.name}: {result.trigger_word} -> {result.new_domain} (locked={should_lock})")

        return {
            "override": True,
            "response": result.canonical_response,
            "new_context": new_context,
            "event": result.event,
            "continue_normal_flow": False,  # NO continuar con catálogo
            "domain_locked": should_lock,
            "can_route_to_srm": False,
        }

    else:
        # Sin override - verificar si puede ir a SRM
        can_srm = session_state.can_route_to_srm()

        return {
            "override": False,
            "response": None,
            "new_context": context,
            "event": result.event,
            "continue_normal_flow": can_srm,  # Solo si no hay lock
            "domain_locked": session_state.locked,
            "can_route_to_srm": can_srm,
        }


# ============================================================================
# FUNCIONES AUXILIARES PARA INTEGRACIÓN
# ============================================================================

def get_session_state(session_id: str, user_id: str = "unknown") -> Dict:
    """Obtiene el estado actual de una sesión (para debugging/supervisión)"""
    state = _session_manager.get_or_create(session_id, user_id)
    return state.to_dict()


def unlock_session(session_id: str, reason: str = "manual_unlock") -> bool:
    """Desbloquea manualmente una sesión (para supervisión)"""
    state = _session_manager.get_or_create(session_id, "system")
    if state.locked:
        state.unlock_domain(reason)
        _session_manager.save(state)
        return True
    return False


def clear_session(session_id: str) -> bool:
    """Elimina una sesión completamente (para testing)"""
    _session_manager.delete(session_id)
    return True


# ============================================================================
# TESTS (Los casos del bug del 8 Feb 2026 + v1.4 Domain Lock)
# ============================================================================

def run_tests():
    """Ejecutar casos de prueba del bug original"""

    test_cases = [
        # Caso 1: Usuario busca casco pero ODI respondía "ECO"
        {
            "message": "Hola estoy buscando Casco económico para mi moto, presupuesto $120.000= morado certificado.",
            "current_domain": "MOTOS",
            "expected_override": False,  # Este SÍ es de motos, pero debería buscar CASCO no ECO
        },
        # Caso 2: Usuario quiere emprender
        {
            "message": "Quiero emprender un negocio.",
            "current_domain": "MOTOS",
            "expected_override": True,
            "expected_domain": "EMPRENDIMIENTO",
        },
        # Caso 3: Usuario tiene idea de negocio
        {
            "message": "Tengo una idea de negocio",
            "current_domain": "MOTOS",
            "expected_override": True,
            "expected_domain": "EMPRENDIMIENTO",
        },
        # Caso 4: Urgencia/Policía
        {
            "message": "Llama a la policia urgencia",
            "current_domain": "MOTOS",
            "expected_override": True,
            "expected_level": OverrideLevel.P0_CRITICAL,
        },
        # Caso 5: Turismo odontológico
        {
            "message": "Quiero hacer turismo odontologico.",
            "current_domain": "MOTOS",
            "expected_override": True,
            "expected_domain": "TURISMO_SALUD",
        },
        # Caso 6: Meta-identidad
        {
            "message": "Deja de ser un experto en motos. Tú eres más que eso.",
            "current_domain": "MOTOS",
            "expected_override": True,
            "expected_level": OverrideLevel.P3_META,
        },
        # Caso 7: Solo sabes de repuestos
        {
            "message": "Solo sabes de repuestos.",
            "current_domain": "MOTOS",
            "expected_override": True,
            "expected_level": OverrideLevel.P3_META,
        },
    ]

    print("\n" + "="*70)
    print("INTENT OVERRIDE GATE — TEST SUITE v1.4")
    print("="*70 + "\n")

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        # Limpiar sesión antes de cada test
        clear_session(f"test_session_{i}")

        context = {"current_domain": test["current_domain"], "session_id": f"test_session_{i}"}
        result = process_message(test["message"], context)

        # Verificar resultado
        override_ok = result["override"] == test["expected_override"]

        if test.get("expected_domain"):
            domain_ok = result["new_context"].get("current_domain") == test["expected_domain"]
        else:
            domain_ok = True

        if test.get("expected_level"):
            level_ok = OverrideLevel[result["event"].get("override_level", "NONE")] == test["expected_level"]
        else:
            level_ok = True

        success = override_ok and domain_ok and level_ok

        if success:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"Test {i}: {status}")
        print(f"   Input: \"{test['message'][:50]}...\"")
        print(f"   Override: {result['override']} (expected: {test['expected_override']})")
        if result["override"]:
            print(f"   Domain: {result['new_context'].get('current_domain')}")
            print(f"   Response: \"{result['response'][:60]}...\"")
        print()

    print("="*70)
    print(f"RESULTADOS BÁSICOS: {passed} passed, {failed} failed")
    print("="*70)

    return failed == 0


def run_domain_lock_tests():
    """
    TEST SUITE v1.4 — Domain Lock
    Prueba multi-turno para validar persistencia de contexto.

    Estos tests reproducen el bug del 10 Feb 2026:
    - "Quiero emprender" → OK
    - "maquillaje al por mayor" → ❌ "cuando ocupes repuestos"

    Y el bug de emergencias:
    - "Urgencia" → OK
    - "marca ambulancia" → ❌ "Para qué moto es?"
    """

    print("\n" + "="*70)
    print("DOMAIN LOCK TESTS — v1.4 Multi-Turn")
    print("="*70 + "\n")

    passed = 0
    failed = 0

    # =========================================================================
    # TEST 8: Emprendimiento Multi-Turno (BUG CRÍTICO)
    # =========================================================================
    print("Test 8: Emprendimiento Multi-Turno")
    session_id = "test_emprendimiento_multiturn"
    clear_session(session_id)

    # Turno 1: Activar emprendimiento
    context = {"session_id": session_id, "user_id": "test"}
    result1 = process_message("Quiero emprender un negocio", context)

    if result1["override"] and result1.get("domain_locked"):
        print("   Turno 1: ✅ Emprendimiento activado y bloqueado")

        # Turno 2: Mensaje de seguimiento (DEBE mantenerse en emprendimiento)
        result2 = process_message("artículos de maquillaje al por mayor", context)

        if result2["override"] and not result2.get("can_route_to_srm", True):
            print("   Turno 2: ✅ Contexto mantenido, NO ruteó a SRM")
            print(f"   Respuesta: \"{result2['response'][:60]}...\"")
            passed += 1
            print("   TEST 8: ✅ PASS\n")
        else:
            print("   Turno 2: ❌ FALLÓ - Perdió contexto o ruteó a SRM")
            print(f"   can_route_to_srm: {result2.get('can_route_to_srm')}")
            failed += 1
            print("   TEST 8: ❌ FAIL\n")
    else:
        print("   Turno 1: ❌ No bloqueó dominio")
        failed += 1
        print("   TEST 8: ❌ FAIL\n")

    # =========================================================================
    # TEST 9: Emergencia Multi-Turno (BUG CRÍTICO CON BIOS/RADAR)
    # =========================================================================
    print("Test 9: Emergencia Multi-Turno (BIOS/Radar)")
    session_id = "test_emergency_multiturn"
    clear_session(session_id)

    # Turno 1: Activar emergencia
    context = {"session_id": session_id, "user_id": "test"}
    result1 = process_message("Urgencia, necesito ayuda", context)

    if result1["override"] and result1.get("domain_locked"):
        print("   Turno 1: ✅ Emergencia activada y bloqueada")

        # Turno 2: Solicitar ambulancia (DEBE activar BIOS/Radar, NO preguntar por moto)
        result2 = process_message("marca ambulancia por favor", context)

        if result2["override"] and not result2.get("can_route_to_srm", True):
            # Verificar que NO menciona motos
            response = result2["response"].lower()
            if "moto" not in response and "repuesto" not in response:
                print("   Turno 2: ✅ BIOS/Radar activado, NO mencionó motos")
                print(f"   Respuesta: \"{result2['response'][:60]}...\"")
                passed += 1
                print("   TEST 9: ✅ PASS\n")
            else:
                print("   Turno 2: ❌ FALLÓ - Mencionó motos/repuestos en emergencia")
                failed += 1
                print("   TEST 9: ❌ FAIL\n")
        else:
            print("   Turno 2: ❌ FALLÓ - Ruteó a SRM en emergencia")
            failed += 1
            print("   TEST 9: ❌ FAIL\n")
    else:
        print("   Turno 1: ❌ No bloqueó dominio")
        failed += 1
        print("   TEST 9: ❌ FAIL\n")

    # =========================================================================
    # TEST 10: Desbloqueo con "cambiar de tema"
    # =========================================================================
    print("Test 10: Desbloqueo voluntario")
    session_id = "test_unlock"
    clear_session(session_id)

    # Turno 1: Activar emprendimiento
    context = {"session_id": session_id, "user_id": "test"}
    process_message("Quiero emprender", context)

    # Turno 2: Solicitar cambio de tema
    result2 = process_message("cambia de tema", context)

    if not result2.get("domain_locked", True):
        # Turno 3: Ahora SÍ debería poder ir a SRM
        result3 = process_message("necesito un repuesto", context)

        if result3.get("can_route_to_srm"):
            print("   ✅ Desbloqueo funcionó, puede ir a SRM")
            passed += 1
            print("   TEST 10: ✅ PASS\n")
        else:
            print("   ❌ No puede ir a SRM después de desbloqueo")
            failed += 1
            print("   TEST 10: ❌ FAIL\n")
    else:
        print("   ❌ No desbloqueó con 'cambiar de tema'")
        failed += 1
        print("   TEST 10: ❌ FAIL\n")

    # =========================================================================
    # TEST 11: Salida explícita de SAFETY (v1.4.1)
    # =========================================================================
    print("Test 11: Salida explícita de SAFETY")
    session_id = "test_safety_exit"
    clear_session(session_id)

    # Turno 1: Activar emergencia
    context = {"session_id": session_id, "user_id": "test"}
    process_message("Urgencia", context)

    # Turno 2: Salir de modo emergencia explícitamente
    result2 = process_message("ya estoy bien", context)

    if not result2.get("domain_locked", True) and result2.get("can_route_to_srm"):
        print("   ✅ Salida de SAFETY funcionó con 'ya estoy bien'")

        # Turno 3: Ahora SÍ debería poder ir a SRM
        result3 = process_message("necesito un casco", context)

        if result3.get("can_route_to_srm"):
            print("   ✅ Puede ir a SRM después de salir de emergencia")
            passed += 1
            print("   TEST 11: ✅ PASS\n")
        else:
            print("   ❌ No puede ir a SRM después de salir")
            failed += 1
            print("   TEST 11: ❌ FAIL\n")
    else:
        print("   ❌ No salió de SAFETY con 'ya estoy bien'")
        failed += 1
        print("   TEST 11: ❌ FAIL\n")

    # =========================================================================
    # TEST 12: P1 rompe SAFETY lock (v1.4.1)
    # =========================================================================
    print("Test 12: P1 rompe SAFETY lock")
    session_id = "test_p1_breaks_safety"
    clear_session(session_id)

    # Turno 1: Activar emergencia
    context = {"session_id": session_id, "user_id": "test"}
    process_message("Urgencia", context)

    # Turno 2: Trigger P1 "quiero emprender" debe romper SAFETY
    result2 = process_message("Quiero emprender un negocio", context)

    # Debe haber cambiado a EMPRENDIMIENTO
    if result2["override"] and "emprendimiento" in result2.get("response", "").lower():
        print("   ✅ P1 'emprender' rompió SAFETY lock")
        print(f"   Respuesta: \"{result2['response'][:60]}...\"")
        passed += 1
        print("   TEST 12: ✅ PASS\n")
    else:
        print("   ❌ P1 no rompió SAFETY lock")
        print(f"   Respuesta: \"{result2.get('response', '')[:60]}...\"")
        failed += 1
        print("   TEST 12: ❌ FAIL\n")

    print("="*70)
    print(f"RESULTADOS DOMAIN LOCK: {passed} passed, {failed} failed")
    print("="*70)

    return failed == 0


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Ejecutar tests básicos
    basic_success = run_tests()

    # Ejecutar tests de domain lock (v1.4)
    lock_success = run_domain_lock_tests()

    total_success = basic_success and lock_success

    if not total_success:
        print("\n⚠️  ALGUNOS TESTS FALLARON. Revisar antes de deploy.")
    else:
        print("\n✅ TODOS LOS TESTS PASARON (v1.4 Domain Lock). Listo para deploy.")
