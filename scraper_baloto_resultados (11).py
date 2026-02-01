# scraper_baloto_resultados.py

import os
import csv
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

OUTPUT_DIR = "C:/RadarPremios/data/crudo"
os.makedirs(OUTPUT_DIR, exist_ok=True)
CSV_FILENAME = os.path.join(OUTPUT_DIR, "baloto_resultados.csv")

BASE_URL = "https://baloto.com/resultados-baloto/{}"
SORTEO_INICIAL = 2081
SORTEO_FINAL = 2533  # Ajusta según el último publicado

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def obtener_html(url):
    try:
        r = requests.get(url, timeout=15, headers=HEADERS)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[ERROR] Al acceder a {url}: {e}")
        return None

def parsear_resultado(html, sorteo):
    soup = BeautifulSoup(html, 'html.parser')
    contenedor = soup.find("div", id="balotoBgNew")
    if not contenedor:
        print(f"[WARNING] Sorteo {sorteo}: estructura no encontrada")
        return None

    # Extraer fecha
    try:
        fecha_divs = contenedor.select(".gotham-medium.dark-blue")
        for div in fecha_divs:
            if "de" in div.text.lower():
                fecha_texto = div.text.strip()
                break
        else:
            fecha_texto = ""
        fecha = datetime.strptime(fecha_texto, "%d de %B de %Y").strftime("%Y-%m-%d")
    except Exception:
        fecha = ""

    # Extraer bolas
    bolas = contenedor.select(".yellow-ball")
    sb = contenedor.select_one(".red-ball")
    if len(bolas) < 5 or not sb:
        print(f"[WARNING] Sorteo {sorteo}: bolas insuficientes")
        return None

    numeros = [b.get_text(strip=True) for b in bolas][:5]
    superbalota = sb.get_text(strip=True)

    return {
        "sorteo": sorteo,
        "modo": "baloto",
        "fecha": fecha,
        "n1": numeros[0],
        "n2": numeros[1],
        "n3": numeros[2],
        "n4": numeros[3],
        "n5": numeros[4],
        "sb": superbalota
    }

def main():
    print("[🟢] Inicio de scrapeo Baloto")
    print(f"⏳ Scrapeando Baloto desde sorteo {SORTEO_INICIAL} hasta {SORTEO_FINAL}")

    resultados = []
    for sorteo in range(SORTEO_INICIAL, SORTEO_FINAL + 1):
        url = BASE_URL.format(sorteo)
        html = obtener_html(url)
        if not html:
            continue

        resultado = parsear_resultado(html, sorteo)
        if resultado:
            resultados.append(resultado)
        time.sleep(0.8)

    if resultados:
        with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["sorteo", "modo", "fecha", "n1", "n2", "n3", "n4", "n5", "sb"])
            writer.writeheader()
            writer.writerows(resultados)
        print(f"[✅] {len(resultados)} sorteos guardados en {CSV_FILENAME}")
    else:
        print("⚠️ No se encontró información válida para guardar.")
    print("[✅] Finalizado")

if __name__ == "__main__":
    main()
