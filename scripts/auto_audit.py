#!/usr/bin/env python3
"""
ODI Auto-Audit Script v1.0
Automatización completa del ciclo de auditoría Cross-Audit.

Flujo:
1. Sincronizar: git push origin [rama_actual]
2. Monitorear: gh run watch hasta que termine
3. Descargar: fetch_audit.py para traer audit-report.json
4. Resumir: Mostrar estado (approved / changes_requested)

Uso:
    python scripts/auto_audit.py

Requiere:
    - Git configurado
    - GitHub CLI (gh) instalado y autenticado
"""

import subprocess
import sys
import json
import time
import os
from pathlib import Path

# Detectar ruta de gh en Windows
GH_PATH = "gh"
if sys.platform == "win32":
    possible_paths = [
        r"C:\Program Files\GitHub CLI\gh.exe",
        r"C:\Program Files (x86)\GitHub CLI\gh.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\GitHub CLI\gh.exe"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            GH_PATH = p
            break


def run_command(cmd: list[str], timeout: int = 300) -> tuple[bool, str, str]:
    """Ejecuta comando y retorna (success, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "Timeout expired"
    except FileNotFoundError as e:
        return False, "", f"Command not found: {e}"


def get_current_branch() -> str | None:
    """Obtiene la rama actual de git."""
    success, stdout, _ = run_command(["git", "branch", "--show-current"])
    return stdout if success else None


def git_push(branch: str) -> bool:
    """Ejecuta git push origin [branch]."""
    print(f"\n[1/4] SINCRONIZANDO: git push origin {branch}")
    success, stdout, stderr = run_command(["git", "push", "origin", branch])

    if success or "Everything up-to-date" in stderr:
        print("    Push completado")
        return True

    print(f"    Error: {stderr}")
    return False


def get_latest_run_id() -> int | None:
    """Obtiene el ID del workflow más reciente."""
    cmd = [
        GH_PATH, "run", "list",
        "--workflow", "cross-audit.yml",
        "--limit", "1",
        "--json", "databaseId,status"
    ]

    success, stdout, stderr = run_command(cmd)

    if not success:
        print(f"    Error obteniendo runs: {stderr}")
        return None

    try:
        runs = json.loads(stdout)
        if runs:
            return runs[0]["databaseId"]
    except json.JSONDecodeError:
        pass

    return None


def wait_for_workflow() -> tuple[bool, str]:
    """Espera a que el workflow termine usando gh run watch."""
    print("\n[2/4] MONITOREANDO: Esperando que el workflow termine...")

    # Esperar un momento para que GitHub registre el nuevo push
    time.sleep(5)

    run_id = get_latest_run_id()
    if not run_id:
        print("    No se encontró workflow en ejecución")
        return False, "not_found"

    print(f"    Watching run ID: {run_id}")

    # Usar gh run watch para monitoreo en tiempo real
    cmd = [GH_PATH, "run", "watch", str(run_id), "--exit-status"]
    success, stdout, stderr = run_command(cmd, timeout=600)  # 10 min timeout

    # Obtener conclusión
    check_cmd = [
        GH_PATH, "run", "view", str(run_id),
        "--json", "conclusion"
    ]
    _, check_out, _ = run_command(check_cmd)

    try:
        data = json.loads(check_out)
        conclusion = data.get("conclusion", "unknown")
    except:
        conclusion = "success" if success else "failure"

    status = "approved" if conclusion == "success" else "changes_requested"
    print(f"    Workflow terminado: {conclusion}")

    return success, status


def download_report(project_root: Path) -> bool:
    """Descarga el reporte de auditoría."""
    print("\n[3/4] DESCARGANDO: Ejecutando fetch_audit.py...")

    fetch_script = project_root / "scripts" / "fetch_audit.py"

    if not fetch_script.exists():
        print(f"    Error: {fetch_script} no existe")
        return False

    success, stdout, stderr = run_command(
        [sys.executable, str(fetch_script)],
        timeout=120
    )

    if stdout:
        # Filtrar solo líneas importantes
        for line in stdout.split('\n'):
            if 'Run ID' in line or 'movido' in line or 'encontrado' in line:
                print(f"    {line}")

    report_path = project_root / "audit-report.json"
    if report_path.exists():
        print(f"    Reporte descargado: {report_path}")
        return True

    print(f"    Error: No se pudo descargar el reporte")
    return False


def show_summary(project_root: Path, status: str) -> None:
    """Muestra resumen del estado de la auditoría."""
    print("\n[4/4] RESUMEN DE AUDITORÍA")
    print("=" * 50)

    if status == "approved":
        print("ESTADO: APPROVED")
        print("El código cumple con los estándares de calidad.")
    else:
        print("ESTADO: CHANGES_REQUESTED")
        print("Se requieren cambios antes de aprobar.")

    print("=" * 50)

    # Intentar leer el reporte para más detalles
    report_path = project_root / "audit-report.json"
    if report_path.exists():
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report = json.load(f)

            print(f"\nTiendas auditadas: {report.get('total_stores', 'N/A')}")
            print(f"Productos totales: {report.get('total_products', 'N/A')}")
            print(f"Score general: {report.get('overall_health_score', 'N/A')}")

            # Mostrar issues cross-store
            issues = report.get("cross_store_issues", [])
            if issues:
                print(f"\nProblemas encontrados: {len(issues)}")
                for issue in issues[:5]:  # Mostrar máximo 5
                    severity = issue.get("severity", "unknown").upper()
                    desc = issue.get("description", str(issue))[:60]
                    print(f"  [{severity}] {desc}")
        except Exception as e:
            print(f"\nNo se pudo leer el reporte: {e}")

    print()


def main():
    """Punto de entrada principal."""
    print("=" * 50)
    print("ODI AUTO-AUDIT v1.0")
    print("Automatización del ciclo de auditoría Cross-Audit")
    print("=" * 50)

    # Determinar raíz del proyecto
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    # Verificar rama actual
    branch = get_current_branch()
    if not branch:
        print("Error: No se pudo determinar la rama actual")
        sys.exit(1)

    print(f"\nProyecto: {project_root}")
    print(f"Rama: {branch}")

    # 1. Sincronizar
    if not git_push(branch):
        print("\nAdvertencia: Push falló, continuando con workflow existente...")

    # 2. Monitorear
    success, status = wait_for_workflow()

    # 3. Descargar (solo si el workflow fue exitoso)
    if success:
        download_report(project_root)

    # 4. Resumir
    show_summary(project_root, status)

    print("\nAuditoría completada para Juan David. Revisa los resultados.")

    return 0 if status == "approved" else 1


if __name__ == "__main__":
    sys.exit(main())
