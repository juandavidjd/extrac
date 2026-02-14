# scraper_astroluna.py

import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from scraper_utils import cargar_fechas_existentes, guardar_nuevos, log
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Ruta de salida
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/crudo"))
os.makedirs(OUTPUT_DIR, exist_ok=True)
DESTINO = os.path.join(OUTPUT_DIR, "astro_luna.csv")
URL = "https://superastro.com.co/historico.php"

log("=== Inicio de scrapeo de AstroLuna ===")

# Configura Selenium en modo sin cabeza
options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920x1080")

try:
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(URL)
    time.sleep(3)
    html = driver.page_source
    driver.quit()
except Exception as e:
    log(f"[ERROR] Fallo al iniciar navegador: {e}")
    exit(1)

soup = BeautifulSoup(html, "html.parser")

# Encuentra tablas dentro del contenedor de AstroLUNA
tablas = soup.select("div.ganadores-historico table")
if len(tablas) < 2:
    log("[ERROR] No se encontró la tabla de AstroLUNA.")
    exit(1)

tabla_luna = tablas[1]
rows = tabla_luna.select("tbody tr")

# Carga fechas existentes
fechas_existentes = cargar_fechas_existentes(DESTINO)
nuevos = []

for tr in rows:
    cols = tr.find_all("td")
    if len(cols) >= 3:
        fecha_raw = cols[0].get_text(strip=True)
        try:
            fecha = datetime.strptime(fecha_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            log(f"[!] Fecha inválida ignorada: {fecha_raw}")
            continue

        numero = cols[1].get_text(strip=True)
        signo = cols[2].get_text(strip=True)

        if fecha not in fechas_existentes:
            nuevos.append({
                "fecha": fecha,
                "numero": numero,
                "signo": signo
            })

# Guarda nuevos registros si existen
if nuevos:
    try:
        guardar_nuevos(DESTINO, ["fecha", "numero", "signo"], nuevos)
        log(f"[✓] AstroLuna: {len(nuevos)} nuevos registros guardados")
    except Exception as e:
        log(f"[ERROR] No se pudo guardar archivo: {e}")
else:
    log("[INFO] AstroLuna: sin nuevos registros")

log("✅ Scrapeo completado")
