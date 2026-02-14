#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SECURITY GUARD — ODI Hardening v1.9
═══════════════════════════════════════════════════════════════════════════════

Módulo de seguridad fail-closed para ODI.
Verifica permisos y ownership de archivos críticos antes de arrancar.

Uso:
    from core.security_guard import enforce_sovereignty
    enforce_sovereignty()  # Llamar antes de cargar .env o inicializar clientes

Exit Codes:
    42 - Fallo de seguridad (permisos, ownership, archivo faltante)

Fecha: 11 Febrero 2026
Versión: 1.9
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import logging

# Exit code específico para fallos de seguridad
EXIT_CODE_SECURITY = 42

# Rutas críticas que deben existir y tener permisos restrictivos
CRITICAL_PATHS = [
    "/opt/odi/.env",
    "/opt/odi/credentials/odi-sheets.json",
]

# Rutas opcionales (warn si faltan, pero no bloquean)
OPTIONAL_PATHS = [
    "/opt/odi/credentials/google-credentials.json",
    "/opt/odi/credentials/elevenlabs.json",
]

logger = logging.getLogger("odi.security")


def check_file_security(path: str, required: bool = True) -> bool:
    """
    Verifica que un archivo exista y tenga permisos seguros.

    Args:
        path: Ruta absoluta al archivo
        required: Si True, falla si el archivo no existe

    Returns:
        True si el archivo es seguro, False si hay problemas
    """
    current_uid = os.getuid()

    # Verificar existencia
    if not os.path.exists(path):
        if required:
            logger.critical(f"[CRITICAL] Missing required file: {path}")
            return False
        else:
            logger.warning(f"[WARN] Optional file not found: {path}")
            return True  # Opcional, no bloquea

    try:
        st = os.stat(path)
    except OSError as e:
        logger.critical(f"[CRITICAL] Cannot stat {path}: {e}")
        return False

    # Verificar ownership (debe pertenecer al usuario que ejecuta)
    if st.st_uid != current_uid:
        logger.critical(
            f"[SECURITY] Ownership mismatch on {path}: "
            f"file_uid={st.st_uid} != current_uid={current_uid}"
        )
        return False

    # Verificar permisos (grupo y otros NO deben tener acceso)
    mode = st.st_mode & 0o777
    if (mode & 0o077) != 0:
        logger.critical(
            f"[SECURITY] Insecure permissions on {path}: {oct(mode)} "
            f"(group/others have access)"
        )
        return False

    return True


def enforce_sovereignty() -> None:
    """
    Fail-closed: detiene el proceso si detecta credenciales expuestas
    o ownership incorrecto.

    Esta función debe llamarse al inicio del proceso, ANTES de:
    - Cargar dotenv
    - Inicializar clientes de API
    - Conectar a bases de datos

    Si falla, el proceso termina con código 42.
    """
    logger.info("[SECURITY] Iniciando verificación de soberanía...")

    all_secure = True

    # Verificar rutas críticas (fallan si hay problema)
    for path in CRITICAL_PATHS:
        if not check_file_security(path, required=True):
            all_secure = False

    # Verificar rutas opcionales (solo warn)
    for path in OPTIONAL_PATHS:
        check_file_security(path, required=False)

    # Verificar que el directorio de credenciales tenga permisos 700
    cred_dir = "/opt/odi/credentials"
    if os.path.isdir(cred_dir):
        try:
            st = os.stat(cred_dir)
            mode = st.st_mode & 0o777
            if mode != 0o700:
                logger.critical(
                    f"[SECURITY] Credentials directory has wrong permissions: "
                    f"{oct(mode)} (should be 0o700)"
                )
                all_secure = False
        except OSError as e:
            logger.critical(f"[CRITICAL] Cannot stat credentials dir: {e}")
            all_secure = False

    if not all_secure:
        logger.critical("[SECURITY] === SOVEREIGNTY VIOLATED ===")
        logger.critical("[SECURITY] ODI refuses to start with insecure configuration")
        logger.critical("[SECURITY] Fix permissions and ownership, then restart")
        sys.exit(EXIT_CODE_SECURITY)

    logger.info("[OK] Security posture: SOBERANA")


def get_security_status() -> dict:
    """
    Retorna el estado de seguridad sin terminar el proceso.
    Útil para dashboards y monitoreo.
    """
    current_uid = os.getuid()
    status = {
        "sovereign": True,
        "current_uid": current_uid,
        "critical_files": {},
        "optional_files": {},
    }

    for path in CRITICAL_PATHS:
        if os.path.exists(path):
            st = os.stat(path)
            secure = (st.st_uid == current_uid) and ((st.st_mode & 0o077) == 0)
            status["critical_files"][path] = {
                "exists": True,
                "secure": secure,
                "mode": oct(st.st_mode & 0o777),
                "uid": st.st_uid,
            }
            if not secure:
                status["sovereign"] = False
        else:
            status["critical_files"][path] = {"exists": False, "secure": False}
            status["sovereign"] = False

    for path in OPTIONAL_PATHS:
        if os.path.exists(path):
            st = os.stat(path)
            secure = (st.st_uid == current_uid) and ((st.st_mode & 0o077) == 0)
            status["optional_files"][path] = {
                "exists": True,
                "secure": secure,
                "mode": oct(st.st_mode & 0o777),
                "uid": st.st_uid,
            }
        else:
            status["optional_files"][path] = {"exists": False}

    return status


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("=" * 70)
    print("SECURITY GUARD — ODI Hardening v1.9")
    print("=" * 70)

    # En modo test, solo reportar sin salir
    status = get_security_status()

    print(f"\nCurrent UID: {status['current_uid']}")
    print(f"Sovereign: {status['sovereign']}")

    print("\nCritical Files:")
    for path, info in status["critical_files"].items():
        if info["exists"]:
            mark = "✅" if info["secure"] else "❌"
            print(f"  {mark} {path} (mode={info['mode']}, uid={info['uid']})")
        else:
            print(f"  ⚠️  {path} (MISSING)")

    print("\nOptional Files:")
    for path, info in status["optional_files"].items():
        if info["exists"]:
            mark = "✅" if info["secure"] else "❌"
            print(f"  {mark} {path} (mode={info['mode']}, uid={info['uid']})")
        else:
            print(f"  ℹ️  {path} (not found)")

    print("\n" + "=" * 70)
    if status["sovereign"]:
        print("RESULT: ✅ SOBERANA")
    else:
        print("RESULT: ❌ VULNERABLE")
    print("=" * 70)
