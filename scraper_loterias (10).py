import os
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from scraper_utils import guardar_nuevos

# Ruta absoluta para guardar archivos
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/crudo"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# URLs oficiales de resultados de loterías
LOTERIAS = {
    'tolima':    'https://www.astroluna.co/tolima',
    'huila':     'https://www.astroluna.co/huila',
    'manizales': 'https://www.astroluna.co/manizales',
    'quindio':   'https://www.astroluna.co/quindio',
    'medellin':  'https://www.astroluna.co/medellin',
    'boyaca':    'https://www.astroluna.co/boyaca'
}

def log(msg: str) -> None:
    hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{hora}] {msg}")

def normalizar_fecha(fecha_raw: str) -> str:
    """
    Convierte fechas como 'lunes 28 julio 2025' en 'DD/MM/YYYY'
    usando reemplazo manual de nombres de mes.
    """
    meses = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
    }

    try:
        partes = fecha_raw.strip().lower().split()
        if partes[0] in ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"):
            partes = partes[1:]  # quitar el nombre del día

        if len(partes) != 3:
            raise ValueError("Formato inesperado")

        dia, mes_texto, anio = partes
        mes = meses.get(mes_texto)
        if not mes:
            raise ValueError(f"Mes desconocido: {mes_texto}")

        return f"{int(dia):02d}/{mes}/{anio}"
    except Exception:
        log(f"[!] Fecha inválida ignorada: {fecha_raw}")
        return None

def cargar_fechas_existentes(path_csv: str) -> set:
    fechas = set()
    if not os.path.exists(path_csv):
        return fechas
    with open(path_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fecha = row.get("fecha", "").strip()
            if fecha:
                fechas.add(fecha)
    return fechas

# === INICIO DEL SCRAPEO ===
log("=== Inicio de scrapeo de loterías ===")

for nombre, url in LOTERIAS.items():
    try:
        resp = requests.get(url, timeout=15)
        resp.encoding = 'utf-8'
        resp.raise_for_status()
    except Exception as e:
        log(f"[ERROR] {nombre}: {e}")
        continue

    soup = BeautifulSoup(resp.text, 'html.parser')
    tabla = soup.find('table')
    if not tabla:
        log(f"[WARNING] {nombre}: no se encontró tabla de resultados")
        continue

    filas = tabla.select('tbody tr')
    nuevos = []
    archivo_csv = os.path.join(OUTPUT_DIR, f"{nombre}.csv")
    fechas_existentes = cargar_fechas_existentes(archivo_csv)

    for tr in filas:
        columnas = tr.find_all('td')
        if len(columnas) >= 2:
            fecha_raw = columnas[0].get_text(strip=True)
            numero = columnas[1].get_text(strip=True)
            fecha_norm = normalizar_fecha(fecha_raw)
            if fecha_norm and fecha_norm not in fechas_existentes:
                nuevos.append({"fecha": fecha_norm, "numero": numero})

    if not nuevos:
        log(f"[INFO] {nombre}: sin nuevos registros")
        continue

    try:
        guardar_nuevos(archivo_csv, ["fecha", "numero"], nuevos)
        log(f"[✓] {nombre}: {len(nuevos)} nuevos registros guardados")
    except Exception as e:
        log(f"[ERROR] {nombre}: fallo al guardar CSV: {e}")

log("✅ Scrapeo completado")
