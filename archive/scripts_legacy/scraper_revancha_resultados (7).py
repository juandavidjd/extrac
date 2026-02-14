import os
import time
import requests
import locale
from bs4 import BeautifulSoup
from datetime import datetime
from scraper_utils import log, cargar_sorteos_existentes, guardar_nuevos

OUTPUT_DIR = "C:/RadarPremios/data/crudo"
os.makedirs(OUTPUT_DIR, exist_ok=True)
CSV_FILENAME = os.path.join(OUTPUT_DIR, "revancha_resultados.csv")

BASE_URL = "https://baloto.com/resultados-revancha/{}"
SORTEO_INICIAL = 2081
MAX_REINTENTOS = 3
DELAY_REINTENTOS = 2.5
DELAY_LOOP = 0.6

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Config regional
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
        log(f"[!] Sorteo {sorteo}: fecha no encontrada")
    except Exception as e:
        log(f"[!] Sorteo {sorteo}: error extrayendo fecha: {e}")
    return None


def parsear_resultado(html, sorteo):
    soup = BeautifulSoup(html, 'html.parser')
    contenedor = soup.find("div", class_="col-md-6 order-1 order-md-1 order-lg-1")
    if not contenedor:
        log(f"[!] Sorteo {sorteo}: contenedor de resultados no encontrado")
        return None

    fecha = extraer_fecha(soup, sorteo)
    if not fecha:
        return None

    bolas = contenedor.select(".yellow-ball")
    sb = contenedor.select_one(".red-ball")
    if len(bolas) < 5 or not sb:
        log(f"[!] Sorteo {sorteo} tiene bolas incompletas")
        return None

    numeros = [b.get_text(strip=True) for b in bolas][:5]
    superbalota = sb.get_text(strip=True)

    return {
        "sorteo": sorteo,
        "modo": "revancha",
        "fecha": fecha,
        "n1": numeros[0],
        "n2": numeros[1],
        "n3": numeros[2],
        "n4": numeros[3],
        "n5": numeros[4],
        "sb": superbalota
    }


def main():
    log("=== Inicio de scrapeo de resultados Revancha ===")
    sorteos_existentes = cargar_sorteos_existentes(CSV_FILENAME)
    sorteo_actual = max(sorteos_existentes) if sorteos_existentes else SORTEO_INICIAL - 1
    nuevos_resultados = []

    while True:
        sorteo_actual += 1
        url = BASE_URL.format(sorteo_actual)
        log(f"⏳ Sorteo {sorteo_actual} -> {url}")
        html = obtener_html(url)
        if not html:
            break

        resultado = parsear_resultado(html, sorteo_actual)
        if not resultado:
            break

        if sorteo_actual in sorteos_existentes:
            log(f"[✓] Sorteo {sorteo_actual} ya registrado ({resultado['fecha']})")
            continue

        nuevos_resultados.append(resultado)
        time.sleep(DELAY_LOOP)

    guardar_nuevos(
        CSV_FILENAME,
        ["sorteo", "modo", "fecha", "n1", "n2", "n3", "n4", "n5", "sb"],
        nuevos_resultados
    )

    log("✅ Scrapeo completado")


if __name__ == "__main__":
    main()
