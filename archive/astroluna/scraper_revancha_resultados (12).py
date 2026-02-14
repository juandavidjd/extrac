import os
import csv
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

SORTEO_INICIAL = 2081
SORTEO_FINAL = 2533  # Se ajustará dinámicamente si es necesario
MODO = "revancha"
OUTPUT_FILE = "C:/RadarPremios/data/crudo/revancha_resultados.csv"
BASE_URL = "https://baloto.com/resultados-revancha/{}"


def obtener_html(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[ERROR] Error accediendo a {url}: {e}")
        return None


def extraer_fecha(soup):
    try:
        texto_fecha = soup.select_one(".border-left-blue .gotham-medium.dark-blue:nth-child(3)")
        if texto_fecha:
            return texto_fecha.text.strip()
    except Exception:
        pass
    return ""


def extraer_bolas(soup):
    bolas = soup.select(".yellow-ball.gotham-medium, .red-ball.gotham-medium")
    numeros = [b.text.strip() for b in bolas if b.text.strip().isdigit()]
    return numeros if len(numeros) == 6 else None


def scrape_resultado(sorteo):
    url = BASE_URL.format(sorteo)
    html = obtener_html(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    bolas = extraer_bolas(soup)
    if not bolas or len(bolas) < 6:
        print(f"[WARNING] Sorteo {sorteo}: bolas insuficientes")
        return None

    fecha = extraer_fecha(soup)

    return {
        "sorteo": sorteo,
        "modo": MODO,
        "fecha": fecha,
        "n1": bolas[0],
        "n2": bolas[1],
        "n3": bolas[2],
        "n4": bolas[3],
        "n5": bolas[4],
        "sb": bolas[5],
    }


def main():
    print("[🟢] Inicio de scrapeo Revancha")
    print(f"⏳ Scrapeando Revancha desde sorteo {SORTEO_INICIAL} hasta {SORTEO_FINAL}")

    resultados = []
    for sorteo in range(SORTEO_INICIAL, SORTEO_FINAL + 1):
        try:
            resultado = scrape_resultado(sorteo)
            if resultado:
                resultados.append(resultado)
            time.sleep(0.8)
        except Exception as e:
            print(f"[ERROR] Sorteo {sorteo} falló inesperadamente: {e}")
            continue

    if resultados:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["sorteo", "modo", "fecha", "n1", "n2", "n3", "n4", "n5", "sb"])
            writer.writeheader()
            writer.writerows(resultados)
        print(f"[✅] {len(resultados)} sorteos guardados en {OUTPUT_FILE}")
    else:
        print("⚠️ No se encontró información válida para guardar.")

    print("[✅] Finalizado")


if __name__ == "__main__":
    main()
