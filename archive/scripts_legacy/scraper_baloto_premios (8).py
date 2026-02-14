# scraper_baloto_premios.py

import os
import time
import locale
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from scraper_utils import log, cargar_premios_existentes, guardar_nuevos_premios

# Configuración general
OUTPUT_DIR = "C:/RadarPremios/data/crudo"
os.makedirs(OUTPUT_DIR, exist_ok=True)
CSV_FILENAME = os.path.join(OUTPUT_DIR, "baloto_premios.csv")

BASE_URL = "https://baloto.com/resultados-baloto/{}"
SORTEO_INICIAL = 2081
MAX_REINTENTOS = 3
DELAY_REINTENTOS = 2.5
DELAY_LOOP = 0.6

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Configuración regional
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'es_CO.UTF-8')
    except:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain')


def obtener_html(url):
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            r = requests.get(url, timeout=15, headers=HEADERS)
            r.raise_for_status()
            return r.text
        except requests.exceptions.RequestException as e:
            log(f"[REINTENTO {intento}] Error al acceder {url}: {e}")
            if intento < MAX_REINTENTOS:
                time.sleep(DELAY_REINTENTOS)
    log(f"[ERROR] Fallo permanente al acceder a {url}")
    return None


def extraer_fecha(soup, sorteo):
    try:
        fecha_divs = soup.select(".gotham-medium.dark-blue")
        for div in fecha_divs:
            texto = div.get_text(strip=True)
            if "de" in texto.lower():
                return datetime.strptime(texto, "%d de %B de %Y").strftime("%Y-%m-%d")
    except Exception as e:
        log(f"[!] Error extrayendo fecha en sorteo {sorteo}: {e}")
    return None


def extraer_tabla_premios(soup, sorteo, fecha):
    tabla = soup.select_one("table.table-striped")
    if not tabla:
        log(f"[!] Sorteo {sorteo}: tabla de premios no encontrada")
        return []

    premios = []
    filas = tabla.select("tbody tr")
    for fila in filas:
        columnas = fila.select("td")
        if len(columnas) != 4:
            continue

        aciertos = ""
        yellow = fila.select_one(".yellow-ball-results")
        pink = fila.select_one(".pink-ball-results")

        if yellow:
            aciertos = yellow.get_text(strip=True)
        if pink:
            aciertos += "+SB"

        premio_total = columnas[1].get_text(strip=True).replace('\xa0', ' ')
        ganadores = columnas[2].get_text(strip=True)
        premio_por_ganador = columnas[3].get_text(strip=True)

        premios.append({
            "sorteo": sorteo,
            "modo": "baloto",
            "fecha": fecha,
            "aciertos": aciertos,
            "premio_total": premio_total,
            "ganadores": ganadores,
            "premio_por_ganador": premio_por_ganador
        })

    return premios


def main():
    log("=== Inicio de scrapeo de premios Baloto ===")
    sorteos_existentes = cargar_premios_existentes(CSV_FILENAME)
    sorteo_actual = max(sorteos_existentes) if sorteos_existentes else SORTEO_INICIAL - 1
    nuevos_premios = []

    while True:
        sorteo_actual += 1
        if sorteo_actual in sorteos_existentes:
            continue

        url = BASE_URL.format(sorteo_actual)
        log(f"⏳ Sorteo {sorteo_actual} -> {url}")

        html = obtener_html(url)
        if not html:
            break

        soup = BeautifulSoup(html, 'html.parser')
        fecha = extraer_fecha(soup, sorteo_actual)
        if not fecha:
            break

        premios = extraer_tabla_premios(soup, sorteo_actual, fecha)
        if premios:
            nuevos_premios.extend(premios)
            log(f"[✓] {len(premios)} premios extraídos")
        else:
            log(f"[!] Sorteo {sorteo_actual}: sin premios válidos")

        time.sleep(DELAY_LOOP)

    guardar_nuevos_premios(
        CSV_FILENAME,
        ["sorteo", "modo", "fecha", "aciertos", "premio_total", "ganadores", "premio_por_ganador"],
        nuevos_premios
    )

    log("✅ Scrapeo completado")


if __name__ == "__main__":
    main()
