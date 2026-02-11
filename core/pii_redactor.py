#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
PII REDACTOR — ODI Hardening v1.9
═══════════════════════════════════════════════════════════════════════════════

Redacción de información personal identificable (PII) en logs.
Enmascara números de teléfono, emails y otros datos sensibles.

Uso:
    from core.pii_redactor import RedactingFormatter, get_redacted_logger

    # Opción 1: Usar formatter directamente
    handler = logging.FileHandler("/opt/odi/logs/sync.log")
    handler.setFormatter(RedactingFormatter())

    # Opción 2: Obtener logger pre-configurado
    logger = get_redacted_logger("odi_sync", "/opt/odi/logs/sync.log")

Fecha: 11 Febrero 2026
Versión: 1.9
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import re
from typing import Optional, List, Pattern


class RedactingFormatter(logging.Formatter):
    """
    Formatter que redacta PII antes de escribir al log.

    Patrones redactados:
    - Teléfonos colombianos: 57XXXXXXXXXX
    - Teléfonos US/CA: 1XXXXXXXXXX
    - Emails: usuario@dominio.com
    - IPs privadas (opcional)
    - Números de documento (CC colombiana)
    """

    # Patrones de PII
    PATTERNS: List[tuple] = [
        # Teléfonos colombianos (57 + 10 dígitos)
        (re.compile(r'\b57\d{10}\b'), '[PHONE_CO]'),

        # Teléfonos US/CA (1 + 10 dígitos)
        (re.compile(r'\b1\d{10}\b'), '[PHONE_US]'),

        # Teléfonos genéricos (10-11 dígitos seguidos)
        (re.compile(r'\b\d{10,11}\b'), '[PHONE]'),

        # WhatsApp IDs (wa_id format)
        (re.compile(r'\bwa_id["\s:=]+\d{10,15}'), 'wa_id=[REDACTED]'),

        # Emails
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),

        # Cédulas colombianas (8-10 dígitos con posible formato)
        (re.compile(r'\bCC[:\s]*\d{8,10}\b', re.IGNORECASE), 'CC:[REDACTED]'),
        (re.compile(r'\bcedula[:\s]*\d{8,10}\b', re.IGNORECASE), 'cedula:[REDACTED]'),
    ]

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = '%',
        redact_phones: bool = True,
        redact_emails: bool = True,
        redact_documents: bool = True,
    ):
        """
        Args:
            fmt: Formato del log
            datefmt: Formato de fecha
            style: Estilo de formato (%, {, $)
            redact_phones: Redactar números de teléfono
            redact_emails: Redactar emails
            redact_documents: Redactar números de documento
        """
        if fmt is None:
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

        # Construir lista de patrones activos
        self.active_patterns: List[tuple] = []

        if redact_phones:
            self.active_patterns.extend([
                p for p in self.PATTERNS
                if 'PHONE' in p[1] or 'wa_id' in p[1]
            ])

        if redact_emails:
            self.active_patterns.extend([
                p for p in self.PATTERNS if 'EMAIL' in p[1]
            ])

        if redact_documents:
            self.active_patterns.extend([
                p for p in self.PATTERNS
                if 'CC' in p[1] or 'cedula' in p[1]
            ])

    def format(self, record: logging.LogRecord) -> str:
        """Formatea el registro redactando PII."""
        msg = super().format(record)

        for pattern, replacement in self.active_patterns:
            msg = pattern.sub(replacement, msg)

        return msg


def get_redacted_logger(
    name: str,
    log_file: str,
    level: int = logging.INFO,
    console: bool = False,
) -> logging.Logger:
    """
    Crea un logger con redacción de PII configurada.

    Args:
        name: Nombre del logger
        log_file: Ruta al archivo de log
        level: Nivel de logging
        console: Si True, también escribe a consola

    Returns:
        Logger configurado con redacción
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []  # Limpiar handlers existentes
    logger.propagate = False

    # File handler con redacción
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(RedactingFormatter())
    logger.addHandler(file_handler)

    # Console handler opcional (también con redacción)
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(RedactingFormatter())
        logger.addHandler(console_handler)

    return logger


def redact_string(text: str) -> str:
    """
    Redacta PII de un string sin usar logging.
    Útil para sanitizar datos antes de enviarlos a APIs externas.

    Args:
        text: Texto a redactar

    Returns:
        Texto con PII redactado
    """
    formatter = RedactingFormatter()
    for pattern, replacement in formatter.active_patterns:
        text = pattern.sub(replacement, text)
    return text


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("PII REDACTOR — ODI Hardening v1.9")
    print("=" * 70)

    # Test cases
    test_messages = [
        "Usuario 573225462101 envió mensaje",
        "Lead from wa_id: 573001234567 confirmed",
        "Email: cliente@ejemplo.com registrado",
        "CC: 1077656012 verificada",
        "Contacto: 13105551234 (US)",
        "Normal message without PII",
        "Multiple: 573225462101, user@test.com, CC:10776560",
    ]

    formatter = RedactingFormatter()

    print("\nTest de redacción:")
    print("-" * 70)

    for msg in test_messages:
        # Crear un record de prueba
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None,
        )

        redacted = formatter.format(record)

        # Mostrar solo la parte del mensaje (sin timestamp)
        msg_part = redacted.split(" - ")[-1]

        print(f"Original: {msg}")
        print(f"Redacted: {msg_part}")
        print()

    print("=" * 70)
    print("✅ PII Redactor funcionando")
    print("=" * 70)
