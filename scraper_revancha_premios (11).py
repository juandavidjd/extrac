import requests
from bs4 import BeautifulSoup
import csv
import os
import time

CSV_PATH = "../data/crudo/revancha_premios.csv"
URL_TEMPLATE = "https://www.baloto.com/resultados-revancha/{sorteo}"
INICIO_SORTEO = 2081
FIN_SORTEO = 2533

def obtener_html(url, retries=3):
    for intento in range(retries):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return r.text
        except:
            time.sleep(2)
    return None

def extraer_fecha(soup):
    try:
        fecha_tag = soup.select_one("div.col-md-6 .gotham-medium.dark-blue:nth-of-type(3)")
        return fecha_tag.text.strip()
    except:
        return None

def parsear_tabla(soup, sorteo, fecha):
    tabla = soup.select_one("table.table-striped")
    if not tabla:
        print(f"[WARNING] Sorteo {sorteo}: tabla no encontrada")
        return []

    premios = []
    filas = tabla.select("tbody tr")
    for fila in filas:
        columnas = fila.select("td")
        if len(columnas) != 4:
            continue

        categoria_raw = fila.select_one("td div.yellow-ball-results").text.strip()
        tiene_sb = fila.select_one("td div.pink-ball-results") is not None
        aciertos = f"{categoria_raw}+SB" if tiene_sb else categoria_raw

        premio = columnas[1].text.strip()
        ganadores = columnas[2].text.strip()
        premio_x_ganador = columnas[3].text.strip()

        premios.append({
            "sorteo": sorteo,
            "modo": "revancha",
            "fecha": fecha,
            "aciertos": aciertos,
            "premio_total": premio,
            "ganadores": ganadores,
            "premio_por_ganador": premio_x_ganador
        })

    return premios

def guardar_csv(premios):
    encabezados = ["sorteo", "modo", "fecha", "aciertos", "premio_total", "ganadores", "premio_por_ganador"]
    with open(CSV_PATH, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=encabezados)
        writer.writeheader()
        for row in premios:
            writer.writerow(row)

def main():
    print("🟢 Inicio de scrapeo premios Revancha")
    print(f"⏳ Scrapeando desde sorteo {INICIO_SORTEO} hasta {FIN_SORTEO}")
    todos = []

    for sorteo in range(INICIO_SORTEO, FIN_SORTEO + 1):
        url = URL_TEMPLATE.format(sorteo=sorteo)
        html = obtener_html(url)
        if not html:
            print(f"[ERROR] Sorteo {sorteo}: sin respuesta")
            continue

        soup = BeautifulSoup(html, "html.parser")
        fecha = extraer_fecha(soup)
        if not fecha:
            print(f"[WARNING] Sorteo {sorteo}: sin fecha")
            continue

        premios = parsear_tabla(soup, sorteo, fecha)
        if premios:
            todos.extend(premios)
            print(f"[✓] Sorteo {sorteo}: {len(premios)} premios")
        else:
            print(f"[WARNING] Sorteo {sorteo}: sin premios válidos")

        time.sleep(0.8)

    if todos:
        guardar_csv(todos)
        print(f"\n✅ {len(todos)} premios guardados en {CSV_PATH}")
    else:
        print("\n⚠️ No se encontraron premios para guardar.")

if __name__ == "__main__":
    main()
