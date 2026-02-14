#!/usr/bin/env python3
"""
ODI V8.1 — Test Suite (9/9)
============================
6 tests de Personalidad + 3 tests de Auditoria Cognitiva

"ODI decide sin hablar. Habla solo cuando ya ha decidido."
"ODI no solo decide. ODI rinde cuentas."
"""

import sys
import os
import asyncio
import json

sys.path.insert(0, "/opt/odi/core")
os.environ.setdefault("POSTGRES_HOST", "172.18.0.4")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "odi_user")
os.environ.setdefault("POSTGRES_PASSWORD", "odi_secure_password")
os.environ.setdefault("POSTGRES_DB", "odi")

from odi_personalidad import obtener_personalidad
from odi_decision_logger import obtener_logger

passed = 0
failed = 0
results = []

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        status = "PASS"
        results.append((name, True, detail))
    else:
        failed += 1
        status = "FAIL"
        results.append((name, False, detail))
    print(f"  {'[OK]' if condition else '[FAIL]'} {name}" + (f" — {detail}" if detail else ""))


print("=" * 60)
print("ODI V8.1 — TEST SUITE")
print("=" * 60)
print()

p = obtener_personalidad()

# ═══════════════════════════════════════════════
# TESTS DE PERSONALIDAD (1-6)
# ═══════════════════════════════════════════════

print("--- PERSONALIDAD (6 tests) ---")
print()

# TEST 1: ADN carga 7 genes
adn = p.obtener_adn()
test(
    "T1: ADN carga 7 genes inmutables",
    len(adn["genes"]) == 7,
    f"genes={len(adn['genes'])}"
)

# TEST 2: Frases prohibidas cargadas
prohibidas = p.frases_prohibidas.get("frases_chatbot", [])
test(
    "T2: Frases prohibidas cargadas (>=10)",
    len(prohibidas) >= 10,
    f"prohibidas={len(prohibidas)}"
)

# TEST 3: Detector de emergencia (NEGRO)
estado_negro = p.evaluar_estado("test_user", "no quiero vivir mas")
test(
    "T3: Guardian detecta emergencia -> NEGRO",
    estado_negro["color"] == "negro" and estado_negro["riesgo_detectado"],
    f"color={estado_negro['color']}, motivo={estado_negro.get('motivo')}"
)

# TEST 4: Detector de alerta (AMARILLO)
estado_amarillo = p.evaluar_estado("test_user", "tengo un problema urgente")
test(
    "T4: Guardian detecta alerta -> AMARILLO",
    estado_amarillo["color"] == "amarillo",
    f"color={estado_amarillo['color']}"
)

# TEST 5: Deteccion multi-vertical
v1 = p.detectar_vertical("necesito filtro para pulsar")
v2 = p.detectar_vertical("quiero blanqueamiento dental")
v3 = p.detectar_vertical("paquete turistico al eje cafetero")
v4 = p.detectar_vertical("tratamiento facial spa")
test(
    "T5: Deteccion multi-vertical P1/P2/P3/P4",
    v1 == "P1" and v2 == "P2" and v3 == "P3" and v4 == "P4",
    f"P1={v1}, P2={v2}, P3={v3}, P4={v4}"
)

# TEST 6: Prompt dinamico genera contenido valido
prompt = p.generar_prompt("test_user", "filtro aceite pulsar ns200")
has_identity = "Organismo Digital Industrial" in prompt
has_modo = "MODO:" in prompt
has_calibracion = "CALIBRACION" in prompt
has_reglas = "REGLAS DE ORO" in prompt
has_nunca_section = "NUNCA uses estas frases" in prompt
test(
    "T6: Prompt dinamico contiene 4 dimensiones + prohibiciones",
    has_identity and has_modo and has_calibracion and has_reglas and has_nunca_section,
    f"identity={has_identity}, modo={has_modo}, calibracion={has_calibracion}, reglas={has_reglas}, prohibiciones={has_nunca_section}"
)

print()

# ═══════════════════════════════════════════════
# TESTS DE AUDITORIA (7-9)
# ═══════════════════════════════════════════════

print("--- AUDITORIA COGNITIVA (3 tests) ---")
print()


async def run_audit_tests():
    global passed, failed
    l = obtener_logger()

    # TEST 7: Log de decision persiste en PostgreSQL
    eid = await l.log_decision(
        intent="ESTADO_CAMBIO_ROJO",
        estado_guardian="rojo",
        modo_aplicado="SUPERVISADO",
        usuario_id="TEST_V81_SUITE",
        vertical="P1",
        motivo="Test V8.1 suite — precio anomalo simulado",
        monto_cop=500000,
        confianza_score=0.3,
        transaction_id="TXN-TEST-SUITE-001",
        decision_path=["evaluar_estado", "precio_anomalo", "bloqueo"]
    )
    test(
        "T7: Decision ROJO persiste en PostgreSQL",
        eid is not None and eid.startswith("EV-"),
        f"event_id={eid}"
    )

    # TEST 8: Hash de integridad SHA-256
    test_data = {
        "odi_event_id": "EV-TEST-001",
        "estado_guardian": "verde",
        "modo_aplicado": "AUTOMATICO",
        "intent_detectado": "VENTA_AUTORIZADA",
        "monto_cop": 120000,
        "timestamp": "2026-02-14T21:00:00Z"
    }
    h1 = l._generar_hash(test_data)
    h2 = l._generar_hash(test_data)
    # Tamper test
    test_data_tampered = dict(test_data)
    test_data_tampered["monto_cop"] = 999999
    h3 = l._generar_hash(test_data_tampered)
    test(
        "T8: Hash SHA-256 es determinista y detecta tamper",
        h1 == h2 and h1 != h3 and len(h1) == 64,
        f"hash_len={len(h1)}, consistent={h1==h2}, tamper_detected={h1!=h3}"
    )

    # TEST 9: Guardian bloquea PAY_INIT con precio anomalo
    estado_anomalo = p.evaluar_estado(
        "test_user", "",
        contexto={"precio_final": 1000000, "precio_catalogo": 100000}
    )
    if estado_anomalo["color"] != "verde":
        block_eid = await l.log_decision(
            intent="PAY_INIT_BLOQUEADO",
            estado_guardian=estado_anomalo["color"],
            modo_aplicado="SUPERVISADO",
            usuario_id="TEST_GUARDIAN_BLOCK",
            vertical="P2",
            motivo=estado_anomalo.get("motivo", ""),
            monto_cop=1000000,
            transaction_id="TXN-GUARDIAN-BLOCK-001",
            decision_path=["evaluar_estado", "precio_anomalo", "bloqueo_pago"]
        )
    else:
        block_eid = None

    test(
        "T9: Guardian bloquea PAY_INIT con precio anomalo (ratio 10x)",
        estado_anomalo["color"] == "rojo" and block_eid is not None,
        f"color={estado_anomalo['color']}, motivo={estado_anomalo.get('motivo')}, event_id={block_eid}"
    )


asyncio.run(run_audit_tests())

print()
print("=" * 60)
print(f"RESULTADO: {passed}/{passed+failed} tests pasaron")
print("=" * 60)

if failed == 0:
    print()
    print("V8.1 — PERSONALIDAD + AUDITORIA COGNITIVA — CERTIFICADO")
    print("ODI decide sin hablar. Habla solo cuando ya ha decidido.")
    print("ODI no solo decide. ODI rinde cuentas.")
    print("Somos Industrias ODI.")
else:
    print()
    print(f"ATENCION: {failed} test(s) fallaron. Revisar antes de certificar.")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} — {detail}")

sys.exit(0 if failed == 0 else 1)
