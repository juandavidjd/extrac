#!/usr/bin/env python3
"""
ODI Fetch Audit Script v1.0
Descarga el último reporte de auditoría de GitHub Actions.

Uso:
    python scripts/fetch_audit.py

Requiere:
    - GitHub CLI (gh) instalado y autenticado
"""

import subprocess
import json
import shutil
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> tuple[bool, str]:
    """Ejecuta un comando y retorna (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()
    except FileNotFoundError:
        return False, "gh CLI no encontrado. Instala con: winget install GitHub.cli"


def get_latest_run_id() -> int | None:
    """Obtiene el ID de la última ejecución del workflow cross-audit."""
    cmd = [
        "gh", "run", "list",
        "--workflow", "cross-audit.yml",
        "--limit", "1",
        "--json", "databaseId"
    ]

    success, output = run_command(cmd)

    if not success:
        print(f"Error obteniendo runs: {output}")
        return None

    try:
        runs = json.loads(output)
        if runs and len(runs) > 0:
            return runs[0]["databaseId"]
        print("No se encontraron ejecuciones del workflow cross-audit.yml")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parseando JSON: {e}")
        return None


def download_audit_report(run_id: int, project_root: Path) -> bool:
    """Descarga el reporte de auditoría."""
    cmd = [
        "gh", "run", "download",
        str(run_id),
        "-n", "cross-audit-report"
    ]

    success, output = run_command(cmd)

    if not success:
        print(f"Error descargando reporte: {output}")
        return False

    # Buscar el archivo descargado y moverlo a la raíz
    downloaded_dir = project_root / "cross-audit-report"
    downloaded_file = downloaded_dir / "audit-report.json"
    target_file = project_root / "audit-report.json"

    if downloaded_file.exists():
        shutil.move(str(downloaded_file), str(target_file))
        # Limpiar directorio temporal
        if downloaded_dir.exists():
            shutil.rmtree(downloaded_dir)
        print(f"Reporte movido a: {target_file}")
        return True

    # Buscar en ubicación alternativa
    alt_file = project_root / "audit-report.json"
    if alt_file.exists():
        print(f"Reporte encontrado en: {alt_file}")
        return True

    print("No se encontró audit-report.json en la descarga")
    return False


def read_audit_report(project_root: Path) -> dict | None:
    """Lee y retorna el contenido del reporte de auditoría."""
    report_path = project_root / "audit-report.json"

    if not report_path.exists():
        print(f"Reporte no encontrado: {report_path}")
        return None

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error leyendo JSON: {e}")
        return None


def print_audit_summary(report: dict) -> None:
    """Imprime un resumen del reporte de auditoría."""
    print("\n" + "=" * 60)
    print("RESUMEN DE AUDITORÍA CROSS-AUDIT")
    print("=" * 60)

    print(f"\nGenerado: {report.get('generated_at', 'N/A')}")
    print(f"Tiendas auditadas: {report.get('total_stores', 0)}")
    print(f"Productos totales: {report.get('total_products', 0):,}")
    print(f"Score general: {report.get('overall_health_score', 0):.1f}/100")

    # Resultados por tienda
    audit_results = report.get("audit_results", [])
    if audit_results:
        print("\n--- Resultados por Tienda ---")
        for result in audit_results:
            store = result.get("store_name", "Unknown")
            score = result.get("score", 0)
            issues = len(result.get("issues_found", []))
            print(f"  {store}: Score {score:.1f}, Issues: {issues}")

    # Problemas cross-store
    cross_issues = report.get("cross_store_issues", [])
    if cross_issues:
        print("\n--- Problemas Cross-Store ---")
        for issue in cross_issues:
            severity = issue.get("severity", "unknown").upper()
            desc = issue.get("description", str(issue))
            print(f"  [{severity}] {desc}")

    print("\n" + "=" * 60)


def main():
    """Punto de entrada principal."""
    # Determinar raíz del proyecto
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    print("ODI Fetch Audit v1.0")
    print(f"Proyecto: {project_root}\n")

    # 1. Obtener ID de la última ejecución
    print("Buscando última ejecución de cross-audit.yml...")
    run_id = get_latest_run_id()

    if not run_id:
        print("No se pudo obtener el ID del workflow")
        sys.exit(1)

    print(f"Run ID encontrado: {run_id}")

    # 2. Descargar el reporte
    print(f"\nDescargando reporte del run {run_id}...")
    if not download_audit_report(run_id, project_root):
        print("No se pudo descargar el reporte")
        sys.exit(1)

    # 3. Leer y mostrar resumen
    print("\nLeyendo reporte...")
    report = read_audit_report(project_root)

    if report:
        print_audit_summary(report)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
