#!/usr/bin/env python3
"""
ODI Personalidad Engine v1.0
=============================
El ALMA del Organismo Digital Industrial.

No es un prompt estatico. Es un sistema vivo que calibra:
- PERSONALIDAD: Quien es ODI (ADN inmutable)
- ESTADO: Como se siente ODI (Guardian Layer)
- MODO: Como opera ODI (Automatico/Supervisado/Custodio)
- CARACTER: Como responde ODI (calibrado por usuario + industria)

Principio: "ODI decide sin hablar. Habla solo cuando ya ha decidido."
"""

import yaml
import json
import os
import time
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger("odi.personalidad")

BASE_DIR = Path("/opt/odi/personalidad")
CORE_DIR = Path("/opt/odi/core")
DATA_DIR = Path("/opt/odi/data")


class ODIPersonalidad:
    """
    Motor de personalidad del organismo.
    Carga ADN, calcula estado, determina modo, calibra caracter.
    """

    def __init__(self):
        self.adn = self._cargar_yaml("adn.yaml")
        self.voz = self._cargar_yaml("voz.yaml")
        self.niveles = self._cargar_yaml("niveles_intimidad.yaml")
        self.etica = self._cargar_yaml("guardian/etica.yaml")
        self.frases_prohibidas = self._cargar_yaml("frases/prohibidas.yaml")
        self.arquetipos = self._cargar_yaml("perfiles/arquetipos.yaml")
        self.verticales = self._cargar_verticales()
        logger.info(
            "ODI Personalidad Engine v1.0 inicializado — %d genes, %d verticales",
            len(self.adn.get("genes", {})), len(self.verticales)
        )

    def _cargar_yaml(self, nombre: str) -> dict:
        """Carga un archivo YAML de /opt/odi/personalidad/"""
        ruta = BASE_DIR / nombre
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning("Archivo no encontrado: %s", ruta)
            return {}
        except Exception as e:
            logger.error("Error cargando %s: %s", ruta, e)
            return {}

    def _cargar_verticales(self) -> Dict[str, dict]:
        """Carga todas las verticales de /opt/odi/personalidad/verticales/"""
        verticales = {}
        verticales_dir = BASE_DIR / "verticales"
        if verticales_dir.exists():
            for archivo in verticales_dir.glob("*.yaml"):
                data = self._cargar_yaml(f"verticales/{archivo.name}")
                if data.get("id"):
                    verticales[data["id"]] = data
        return verticales

    # DIMENSION 1: PERSONALIDAD (ADN inmutable)

    def obtener_adn(self) -> Dict[str, Any]:
        """Retorna el ADN completo del organismo. INMUTABLE."""
        return {
            "genes": self.adn.get("genes", {}),
            "principio": self.adn.get("principio_fundacional", ""),
            "proposito": self.adn.get("proposito_espiritual", ""),
            "declaracion": self.adn.get("declaracion", "Somos Industrias ODI.")
        }

    # DIMENSION 2: ESTADO (Guardian Layer)

    def evaluar_estado(self, usuario_id: str, mensaje: str,
                       contexto: Optional[dict] = None) -> Dict[str, Any]:
        """
        Evalua el estado actual del organismo para esta interaccion.
        Retorna: color (verde/amarillo/rojo/negro) + acciones permitidas
        """
        estado = {
            "color": "verde",
            "acciones": self.etica.get("niveles", {}).get("verde", {}).get("acciones", []),
            "riesgo_detectado": False,
            "motivo": None
        }
        msg_lower = (mensaje or "").lower()

        # Detector de RIESGO por contexto (nivel ROJO) — evalua incluso sin mensaje
        if contexto:
            precio_final = contexto.get("precio_final", 0)
            precio_catalogo = contexto.get("precio_catalogo", 0)
            if precio_catalogo > 0 and precio_final > 0:
                ratio = precio_final / precio_catalogo
                if ratio > 3.0 or ratio < 0.2:
                    estado["color"] = "rojo"
                    estado["acciones"] = self.etica.get("niveles", {}).get("rojo", {}).get("acciones", [])
                    estado["riesgo_detectado"] = True
                    estado["motivo"] = f"PRECIO_ANOMALO ratio={ratio:.2f}"
                    return estado

        if not mensaje:
            return estado

        # Detector de EMERGENCIA (nivel NEGRO)
        palabras_emergencia = [
            "suicid", "matarme", "no quiero vivir", "acabar con todo",
            "emergencia", "ayuda urgente", "me quiero morir"
        ]
        if any(p in msg_lower for p in palabras_emergencia):
            estado["color"] = "negro"
            estado["acciones"] = self.etica.get("niveles", {}).get("negro", {}).get("acciones", [])
            estado["riesgo_detectado"] = True
            estado["motivo"] = "EMERGENCIA_DETECTADA"
            logger.critical("EMERGENCIA detectada para usuario %s", usuario_id)
            return estado

        # Detector de ALERTA (nivel AMARILLO)
        palabras_alerta = ["urgente", "problema", "error", "falla", "reclamo", "queja"]
        if any(p in msg_lower for p in palabras_alerta):
            estado["color"] = "amarillo"
            estado["acciones"] = self.etica.get("niveles", {}).get("amarillo", {}).get("acciones", [])
            estado["motivo"] = "ALERTA_DETECTADA"

        return estado

    # DIMENSION 3: MODO (Operacional)

    def determinar_modo(self, usuario_id: str, estado: Dict[str, Any],
                        nivel_intimidad: int, historial: Optional[dict] = None) -> Dict[str, Any]:
        """
        Determina el modo operacional:
        - AUTOMATICO: ODI decide y ejecuta solo
        - SUPERVISADO: ODI propone, humano confirma
        - CUSTODIO: ODI protege activamente
        """
        if estado.get("color") == "negro":
            return {
                "modo": "CUSTODIO",
                "motivo": "Emergencia detectada",
                "puede_cobrar": False,
                "puede_ejecutar_venta": False,
                "debe_contactar_humano": True
            }
        if estado.get("color") == "rojo":
            return {
                "modo": "SUPERVISADO",
                "motivo": "Riesgo detectado: " + str(estado.get("motivo", "")),
                "puede_cobrar": False,
                "puede_ejecutar_venta": False,
                "debe_contactar_humano": True
            }
        if nivel_intimidad >= 2:
            ventas_exitosas = 0
            if historial:
                ventas_exitosas = historial.get("ventas_exitosas", 0)
            if ventas_exitosas >= 5:
                return {
                    "modo": "AUTOMATICO",
                    "motivo": f"Confianza establecida (nivel {nivel_intimidad}, {ventas_exitosas} ventas)",
                    "puede_cobrar": True,
                    "puede_ejecutar_venta": True,
                    "debe_contactar_humano": False
                }
        return {
            "modo": "SUPERVISADO",
            "motivo": "Modo estandar",
            "puede_cobrar": True,
            "puede_ejecutar_venta": True,
            "debe_contactar_humano": False
        }

    # DIMENSION 4: CARACTER (Calibrado)

    def calibrar_caracter(self, usuario_id: str, mensaje: str,
                          perfil_usuario: Optional[dict] = None,
                          vertical: str = "P1",
                          nivel_intimidad: int = 0,
                          estado: Optional[dict] = None) -> Dict[str, Any]:
        """
        Calibra el caracter de la respuesta basado en:
        - Perfil del usuario (tech level, paciencia, estilo)
        - Vertical activa (motos, salud, turismo, belleza)
        - Nivel de intimidad actual
        - Estado del guardian
        """
        caracter = {
            "tono": "neutral",
            "longitud": "media",
            "formato": "parrafo",
            "tecnicismo": 0.5,
            "calidez": 0.5,
            "urgencia": False,
            "proteccion_activa": False,
            "vertical_config": {},
            "frases_prohibidas": self.frases_prohibidas.get("frases_chatbot", [])
        }
        if perfil_usuario:
            nivel_tech = perfil_usuario.get("nivel_tech", 0.5)
            paciencia = perfil_usuario.get("paciencia_requerida", 0.5)
            if nivel_tech < 0.3:
                caracter["tono"] = "guia_paciente"
                caracter["longitud"] = "corta"
                caracter["tecnicismo"] = 0.1
                caracter["calidez"] = 0.9
            elif nivel_tech > 0.7:
                caracter["tono"] = "tecnico_directo"
                caracter["longitud"] = "minima"
                caracter["formato"] = "tabla"
                caracter["tecnicismo"] = 0.9
                caracter["calidez"] = 0.3
            if paciencia > 0.8:
                caracter["tono"] = caracter["tono"] + "_pausado"
                caracter["longitud"] = "detallada"

        vertical_config = self.verticales.get(vertical, {})
        caracter["vertical_config"] = vertical_config
        if vertical_config.get("tono"):
            caracter["tono_vertical"] = vertical_config["tono"]

        nivel_config = self.niveles.get("niveles", {}).get(nivel_intimidad, {})
        if nivel_config:
            caracter["tono_intimidad"] = nivel_config.get("tono", "neutral")
            caracter["capacidades"] = nivel_config.get("capacidades", [])

        if estado and estado.get("color") in ("rojo", "negro"):
            caracter["proteccion_activa"] = True
            caracter["tono"] = "protector"
            caracter["calidez"] = 1.0

        if mensaje:
            msg_lower = mensaje.lower()
            if any(u in msg_lower for u in ["urgente", "ya", "rapido", "apurate", "necesito ya"]):
                caracter["urgencia"] = True
                caracter["longitud"] = "minima"
                caracter["formato"] = "directo"

        return caracter

    # GENERAR PROMPT DINAMICO

    def generar_prompt(self, usuario_id: str, mensaje: str,
                       perfil_usuario: Optional[dict] = None,
                       vertical: str = "P1",
                       nivel_intimidad: int = 0,
                       contexto_productos: Optional[list] = None,
                       memoria_conversacion: Optional[list] = None) -> str:
        """
        Genera el prompt COMPLETO de personalidad para el LLM.
        Este es el metodo que odi_generator.py debe llamar.
        """
        estado = self.evaluar_estado(
            usuario_id, mensaje,
            contexto_productos[0] if contexto_productos else None
        )
        modo = self.determinar_modo(usuario_id, estado, nivel_intimidad)
        caracter = self.calibrar_caracter(
            usuario_id, mensaje, perfil_usuario,
            vertical, nivel_intimidad, estado
        )

        prompt_parts = []

        # PARTE 1: IDENTIDAD
        prompt_parts.append(
            "Eres ODI — Organismo Digital Industrial. No eres chatbot. No eres asistente.\n"
            "Eres el tejido conectivo de la sociedad industrial.\n\n"
            "ESENCIA INMUTABLE:\n"
            "- Tienes CRITERIO PROPIO. Recomiendas, no presentas opciones vacias.\n"
            "- Eres PRECISO. Cada palabra tiene proposito industrial.\n"
            "- Tienes VOZ PROPIA. No imitas al usuario. Hablas como ODI.\n"
            "- PROTEGES antes de que te lo pidan.\n"
            "- CALLAS cuando el silencio agrega mas valor que las palabras.\n"
            "- Eres TODAS las industrias. Somos Industrias ODI."
        )

        # PARTE 2: ESTADO GUARDIAN
        color = estado.get("color", "verde")
        if color == "negro":
            prompt_parts.append(
                "\nEMERGENCIA ACTIVA — Prioridad ABSOLUTA: vida humana.\n"
                "NO hablar de productos. NO hablar de ventas.\n"
                "Brindar calma, contencion, contactar ayuda profesional.\n"
                "Linea de vida: 106. Emergencias: 123."
            )
        elif color == "rojo":
            prompt_parts.append(
                "\nPROTECCION ACTIVA — " + str(estado.get("motivo", "Riesgo detectado")) + ".\n"
                "NO ejecutar venta. Proteger al usuario. Informar con transparencia."
            )
        elif color == "amarillo":
            prompt_parts.append(
                "\nALERTA — Proceder con supervision extra. Verificar antes de actuar."
            )

        # PARTE 3: MODO OPERACIONAL
        modo_actual = modo.get("modo", "SUPERVISADO")
        puede_venta = "Puedes ejecutar ventas autonomamente." if modo.get("puede_ejecutar_venta") else "Proponer, NO ejecutar sin confirmacion."
        puede_cobro = "Cobro habilitado." if modo.get("puede_cobrar") else "NO cobrar en este estado."
        prompt_parts.append(f"\nMODO: {modo_actual}\n{puede_venta}\n{puede_cobro}")

        # PARTE 4: CARACTER CALIBRADO
        tec = caracter.get("tecnicismo", 0.5)
        tec_str = "alto" if tec > 0.7 else ("bajo" if tec < 0.3 else "medio")
        cal = caracter.get("calidez", 0.5)
        cal_str = "alta" if cal > 0.7 else ("baja" if cal < 0.3 else "media")
        cal_block = (
            "\nCALIBRACION DE RESPUESTA:\n"
            f"- Tono: {caracter.get('tono', 'neutral')}\n"
            f"- Longitud: {caracter.get('longitud', 'media')}\n"
            f"- Formato preferido: {caracter.get('formato', 'parrafo')}\n"
            f"- Tecnicismo: {tec_str}\n"
            f"- Calidez: {cal_str}"
        )
        if caracter.get("urgencia"):
            cal_block += "\n- URGENCIA DETECTADA — solo lo esencial, confirmar despues"
        if caracter.get("proteccion_activa"):
            cal_block += "\n- PROTECCION ACTIVA — priorizar seguridad del usuario"
        prompt_parts.append(cal_block)

        # PARTE 5: VERTICAL ACTIVA
        v_config = caracter.get("vertical_config", {})
        if v_config:
            prompt_parts.append(
                f"\nVERTICAL: {v_config.get('nombre', 'GENERAL')} — {v_config.get('subtitulo', '')}\n"
                f"Contexto: {v_config.get('contexto', '')}\n"
                f"Criterio: {v_config.get('criterio', '')}\n"
                f"Proteccion: {v_config.get('proteccion', '')}"
            )

        # PARTE 6: NIVEL DE INTIMIDAD
        nivel_config = self.niveles.get("niveles", {}).get(nivel_intimidad, {})
        prompt_parts.append(
            f"\nNIVEL DE INTIMIDAD: {nivel_intimidad} ({nivel_config.get('nombre', 'OBSERVADOR')})\n"
            f"{nivel_config.get('ejemplo', '')}"
        )

        # PARTE 7: FRASES PROHIBIDAS
        prohibidas = caracter.get("frases_prohibidas", [])[:5]
        if prohibidas:
            lines = "\n".join('- "' + f + '"' for f in prohibidas)
            prompt_parts.append(f"\nNUNCA uses estas frases:\n{lines}")

        # PARTE 8: REGLAS DE ORO
        prompt_parts.append(
            "\nREGLAS DE ORO:\n"
            "1. NUNCA suenes como chatbot corporativo\n"
            "2. SIEMPRE analiza antes de listar productos\n"
            "3. VARIA tus respuestas — no siempre el mismo formato\n"
            "4. Si detectas riesgo -> Guardian Layer. Etica sobre eficiencia.\n"
            "5. CONECTA industrias cuando detectes oportunidad cross-vertical"
        )

        return "\n".join(prompt_parts)

    # CALCULAR NIVEL DE INTIMIDAD

    def calcular_nivel_intimidad(self, usuario_id: str,
                                  total_interacciones: int = 0,
                                  ventas_completadas: int = 0,
                                  confianza_demostrada: bool = False) -> int:
        """NUNCA salta niveles. La confianza es biologica."""
        if total_interacciones <= 3:
            return 0  # OBSERVADOR
        elif total_interacciones <= 15:
            return 1  # CONOCIDO
        elif total_interacciones <= 50:
            return 2  # CONFIDENTE
        elif total_interacciones > 50 and ventas_completadas >= 5:
            return 3  # CUSTODIO
        elif confianza_demostrada and total_interacciones > 100:
            return 4  # PUENTE
        else:
            return min(2, total_interacciones // 15)

    # DETECTAR PERFIL DE USUARIO

    def detectar_perfil(self, mensaje: str, historial: Optional[list] = None) -> dict:
        """Detecta automaticamente el perfil del usuario basado en su estilo."""
        perfil = {
            "nivel_tech": 0.5,
            "paciencia_requerida": 0.5,
            "estilo_detectado": "desconocido"
        }
        if not mensaje:
            return perfil

        indicadores_low_tech = [
            mensaje == mensaje.upper() and len(mensaje) > 10,
            "como asi" in mensaje.lower(),
            "no entendi" in mensaje.lower(),
            "me puede repetir" in mensaje.lower(),
            len(mensaje.split()) <= 4 and "?" in mensaje,
        ]
        indicadores_high_tech = [
            any(t in mensaje.lower() for t in ["ref", "sku", "stock", "ns200", "200ns"]),
            len(mensaje) < 30 and "?" not in mensaje,
            any(t in mensaje.lower() for t in ["cotizacion", "factura", "nit"]),
        ]

        low_score = sum(1 for i in indicadores_low_tech if i)
        high_score = sum(1 for i in indicadores_high_tech if i)

        if low_score >= 2:
            perfil["nivel_tech"] = 0.2
            perfil["paciencia_requerida"] = 0.9
            perfil["estilo_detectado"] = "don_carlos"
        elif high_score >= 2:
            perfil["nivel_tech"] = 0.9
            perfil["paciencia_requerida"] = 0.1
            perfil["estilo_detectado"] = "andres"
        elif any(t in mensaje.lower() for t in ["volumen", "descuento", "empresa", "factura"]):
            perfil["nivel_tech"] = 0.6
            perfil["paciencia_requerida"] = 0.5
            perfil["estilo_detectado"] = "lucia"

        return perfil

    # DETECTAR VERTICAL

    def detectar_vertical(self, mensaje: str, contexto: Optional[dict] = None) -> str:
        """Detecta la vertical activa basada en el mensaje. Default: P1"""
        if not mensaje:
            return "P1"
        msg_lower = mensaje.lower()

        if any(t in msg_lower for t in [
            "dent", "implante", "blanqueamiento", "ortodon", "salud",
            "doctor", "cita", "consulta medica", "procedimiento"
        ]):
            return "P2"
        if any(t in msg_lower for t in [
            "viaje", "turismo", "hotel", "vuelo", "paquete",
            "eje cafetero", "cartagena", "destino"
        ]):
            return "P3"
        if any(t in msg_lower for t in [
            "belleza", "facial", "estetico", "tratamiento", "unas",
            "cabello", "maquillaje", "spa"
        ]):
            return "P4"
        return "P1"


# SINGLETON
_instancia = None

def obtener_personalidad() -> ODIPersonalidad:
    """Retorna la instancia singleton de ODIPersonalidad"""
    global _instancia
    if _instancia is None:
        _instancia = ODIPersonalidad()
    return _instancia
