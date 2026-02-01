# scraper_utils.py

import os
import csv
from datetime import datetime
from typing import Set, List, Dict


def log(msg: str) -> None:
    """
    Imprime un mensaje con marca de tiempo para trazabilidad clara.
    """
    hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{hora}] {msg}")


def cargar_fechas_existentes(path_csv: str) -> Set[str]:
    """
    Devuelve un set de fechas únicas normalizadas en formato DD/MM/YYYY.
    Soporta fechas en formatos 'YYYY-MM-DD' y 'DD/MM/YYYY'.
    """
    fechas: Set[str] = set()
    if not os.path.exists(path_csv):
        return fechas

    with open(path_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fecha = row.get("fecha", "").strip()
            if not fecha:
                continue
            try:
                if "-" in fecha:
                    dt = datetime.strptime(fecha, "%Y-%m-%d")
                else:
                    dt = datetime.strptime(fecha, "%d/%m/%Y")
                fechas.add(dt.strftime("%d/%m/%Y"))
            except ValueError:
                log(f"[!] Fecha inválida ignorada: {fecha}")
                continue
    return fechas


def cargar_sorteos_existentes(path_csv: str) -> Set[int]:
    """
    Devuelve un set de sorteos existentes como enteros desde un archivo CSV
    con columna "sorteo".
    """
    sorteos: Set[int] = set()
    if not os.path.exists(path_csv):
        return sorteos

    with open(path_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                s = row.get("sorteo")
                if s and s.isdigit():
                    sorteos.add(int(s))
            except Exception as e:
                log(f"[!] Error leyendo sorteo: {e}")
                continue
    return sorteos


def guardar_nuevos(path_csv: str, encabezados: List[str], nuevos_datos: List[Dict[str, str]]) -> None:
    """
    Guarda nuevos datos en modo append. Si el archivo no existe, escribe encabezado.
    Los datos deben ser una lista de diccionarios con claves iguales a encabezados.
    """
    if not nuevos_datos:
        log("[INFO] Sin nuevos registros para guardar.")
        return

    existe = os.path.exists(path_csv)
    try:
        with open(path_csv, "a", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=encabezados)
            if not existe:
                writer.writeheader()
            writer.writerows(nuevos_datos)
        log(f"[✓] {len(nuevos_datos)} nuevos registros guardados")
    except Exception as e:
        log(f"[ERROR] Al guardar nuevos datos: {e}")


# Alias para mantener claridad semántica en los scripts de premios
def cargar_premios_existentes(path_csv: str) -> Set[int]:
    """
    Alias de cargar_sorteos_existentes para archivos de premios.
    """
    return cargar_sorteos_existentes(path_csv)


# Alias para guardar premios (idéntico a guardar_nuevos, solo cambia semánticamente)
def guardar_nuevos_premios(path_csv: str, encabezados: List[str], nuevos_datos: List[Dict[str, str]]) -> None:
    """
    Alias semántico de guardar_nuevos para guardar archivos de premios.
    """
    guardar_nuevos(path_csv, encabezados, nuevos_datos)
