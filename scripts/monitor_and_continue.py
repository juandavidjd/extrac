#!/usr/bin/env python3
"""
Monitor DFG Upload y Auto-arranque de tiendas restantes
- Monitorea cada 60 segundos
- Cuando DFG completa, arranca upload_remaining_stores.py
- Solo procesa las 10 tiendas CSV (PDF al final)
"""

import os
import subprocess
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/opt/odi/.env')

LOG_FILE = '/opt/odi/logs/monitor_upload.log'
DFG_UPLOAD_LOG = '/opt/odi/logs/upload_maestra.log'
REMAINING_SCRIPT = '/opt/odi/scripts/upload_remaining_stores.py'

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def check_dfg_complete():
    """Verifica si DFG upload terminó"""
    try:
        with open(DFG_UPLOAD_LOG, 'r') as f:
            content = f.read()

        # Check for completion markers
        if 'Completed:' in content and '[OH_IMPORTACIONES]' in content:
            return True, "DFG completed, moving to next store"

        if 'RESUMEN FINAL' in content:
            return True, "Upload script finished"

        # Check last progress
        lines = content.strip().split('\n')
        for line in reversed(lines[-20:]):
            if 'Progress:' in line:
                # Extract progress: "Progress: 4600/7445 (4597 ok, 3 err)"
                parts = line.split()
                for p in parts:
                    if '/' in p:
                        current, total = p.split('/')
                        try:
                            current = int(current)
                            total = int(total)
                            if current >= total - 10:  # Almost done
                                return True, f"DFG at {current}/{total}"
                            return False, f"DFG progress: {current}/{total}"
                        except:
                            pass

        return False, "DFG still uploading"

    except Exception as e:
        return False, f"Error checking: {e}"

def check_process_running(name):
    """Verifica si un proceso está corriendo"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False

def start_remaining_upload():
    """Inicia upload de tiendas restantes"""
    log("="*60)
    log("INICIANDO UPLOAD DE 10 TIENDAS CSV")
    log("="*60)

    # Start the upload script
    subprocess.Popen(
        ['python3', '-u', REMAINING_SCRIPT],
        stdout=open('/opt/odi/logs/upload_remaining.log', 'w'),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )

    log("Upload de tiendas restantes iniciado")
    log("Log: /opt/odi/logs/upload_remaining.log")

def main():
    log("="*60)
    log("MONITOR DE UPLOAD - INICIADO")
    log("="*60)
    log("Monitoreando DFG upload cada 60 segundos...")
    log("")

    dfg_completed = False
    remaining_started = False

    while True:
        # Check DFG status
        complete, status = check_dfg_complete()

        if not dfg_completed:
            log(f"DFG: {status}")

        if complete and not dfg_completed:
            dfg_completed = True
            log("")
            log("*** DFG UPLOAD COMPLETADO ***")
            log("")

            # Check if remaining upload already running
            if check_process_running('upload_remaining_stores'):
                log("Upload de tiendas restantes ya está corriendo")
            else:
                start_remaining_upload()
                remaining_started = True

        # If remaining started, monitor it
        if remaining_started:
            if check_process_running('upload_remaining_stores'):
                # Show last few lines of progress
                try:
                    result = subprocess.run(
                        ['tail', '-3', '/opt/odi/logs/upload_remaining.log'],
                        capture_output=True,
                        text=True
                    )
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            log(f"REMAINING: {line.strip()}")
                except:
                    pass
            else:
                log("Upload de tiendas restantes COMPLETADO")
                log("")
                log("="*60)
                log("TODAS LAS TIENDAS CSV PROCESADAS")
                log("="*60)
                log("Tiendas PDF pendientes: ARMOTOS, MCLMOTOS, CBI, VITTON")
                log("(Esperando que terminen las extracciones)")
                break

        # Also check extraction progress
        armotos_running = check_process_running('ARMOTOS.*pdf_extractor')
        mclmotos_running = check_process_running('mclmotos_extractor')

        if not dfg_completed:
            extractions = []
            if armotos_running:
                extractions.append("ARMOTOS")
            if mclmotos_running:
                extractions.append("MCLMOTOS")
            if extractions:
                log(f"Extracciones activas: {', '.join(extractions)}")

        time.sleep(60)

if __name__ == '__main__':
    main()
