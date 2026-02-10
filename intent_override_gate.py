"""
INTENT OVERRIDE GATE — Implementación Ejecutable
=================================================
Versión: 1.0
Fecha: 10 Febrero 2026
Propósito: Corregir el bug "Para tu ECO" - ODI atrapado en loop de industria

Este módulo DEBE ejecutarse ANTES de cualquier respuesta de ODI.
Si detecta un override, cambia el contexto inmediatamente.
"""

import re
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, List, Dict

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intent_override_gate")


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
    # Emprendimiento
    "emprender": "EMPRENDIMIENTO",
    "emprendimiento": "EMPRENDIMIENTO",
    "negocio": "EMPRENDIMIENTO",
    "idea de negocio": "EMPRENDIMIENTO",
    "quiero emprender": "EMPRENDIMIENTO",
    "tengo una idea": "EMPRENDIMIENTO",
    "iniciar un negocio": "EMPRENDIMIENTO",
    "crear empresa": "EMPRENDIMIENTO",
    "mi propio negocio": "EMPRENDIMIENTO",

    # Turismo
    "turismo": "TURISMO",
    "viaje": "TURISMO",
    "hotel": "TURISMO",
    "turismo odontológico": "TURISMO_SALUD",
    "turismo odontologico": "TURISMO_SALUD",
    "turismo médico": "TURISMO_SALUD",
    "turismo medico": "TURISMO_SALUD",

    # Salud
    "salud": "SALUD",
    "médico": "SALUD",
    "medico": "SALUD",
    "clínica": "SALUD",
    "clinica": "SALUD",
    "odontología": "SALUD",
    "odontologia": "SALUD",
    "dentista": "SALUD",
    "tratamiento": "SALUD",

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
        "Entendido. Turismo + Salud es una combinación interesante.\n"
        "¿Buscas tratamiento dental + viaje, o quieres emprender en este sector?"
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
# FUNCIÓN PRINCIPAL PARA n8n / CORTEX
# ============================================================================

def process_message(message: str, context: Dict) -> Dict:
    """
    Función principal para procesar mensajes en ODI.
    Debe llamarse ANTES de cualquier otro procesamiento.

    Args:
        message: Mensaje del usuario
        context: Contexto actual de la conversación
            - current_domain: Industria actual (default: "MOTOS")
            - session_id: ID de sesión
            - user_id: ID del usuario

    Returns:
        Dict con:
            - override: bool - Si hubo override
            - response: str - Respuesta a enviar (si override=True)
            - new_context: Dict - Contexto actualizado
            - event: Dict - Evento para NDJSON audit
            - continue_normal_flow: bool - Si debe continuar con el flujo normal
    """

    current_domain = context.get("current_domain", "MOTOS")
    session_id = context.get("session_id", "unknown")
    user_id = context.get("user_id", "unknown")

    # Analizar intent
    result = analyze_intent(message, current_domain)

    # Agregar metadata al evento
    result.event["session_id"] = session_id
    result.event["user_id"] = user_id

    if result.triggered:
        # Hay override - retornar respuesta canónica
        new_context = context.copy()
        if result.new_domain:
            new_context["current_domain"] = result.new_domain
            new_context["last_override"] = {
                "level": result.level.name,
                "from": current_domain,
                "to": result.new_domain,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        logger.info(f"[OVERRIDE] {result.level.name}: {result.trigger_word} -> {result.new_domain}")

        return {
            "override": True,
            "response": result.canonical_response,
            "new_context": new_context,
            "event": result.event,
            "continue_normal_flow": False,  # NO continuar con catálogo
        }

    else:
        # Sin override - continuar con flujo normal
        return {
            "override": False,
            "response": None,
            "new_context": context,
            "event": result.event,
            "continue_normal_flow": True,  # Sí continuar con catálogo/búsqueda
        }


# ============================================================================
# TESTS (Los casos del bug del 8 Feb 2026)
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
    print("INTENT OVERRIDE GATE — TEST SUITE")
    print("="*70 + "\n")

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        context = {"current_domain": test["current_domain"]}
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
    print(f"RESULTADOS: {passed} passed, {failed} failed")
    print("="*70)

    return failed == 0


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Ejecutar tests
    success = run_tests()

    if not success:
        print("\n⚠️  ALGUNOS TESTS FALLARON. Revisar antes de deploy.")
    else:
        print("\n✅ TODOS LOS TESTS PASARON. Listo para deploy.")
