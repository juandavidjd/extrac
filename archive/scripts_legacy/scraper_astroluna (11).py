import os
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Ruta de salida
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/crudo"))
os.makedirs(OUTPUT_DIR, exist_ok=True)
DESTINO = os.path.join(OUTPUT_DIR, "astro_luna.csv")

URL = "https://superastro.com.co/historico.php"

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === Inicio de scrapeo de AstroLuna ===")

try:
    resp = requests.get(URL, timeout=15)
    resp.encoding = "utf-8"
    resp.raise_for_status()
except Exception as e:
    print(f"[ERROR] Conexión fallida: {e}")
    exit(1)

soup = BeautifulSoup(resp.text, "html.parser")

# Encuentra todas las tablas en contenedores de ganadores
tablas = soup.select("div.ganadores-historico table")
if len(tablas) < 2:
    print("[ERROR] No se encontró la tabla de AstroLUNA.")
    exit(1)

tabla_luna = tablas[1]  # Segunda tabla = AstroLUNA
rows = tabla_luna.select("tbody tr")

data = []
for tr in rows:
    cols = tr.find_all("td")
    if len(cols) >= 3:
        fecha = cols[0].get_text(strip=True)
        numero = cols[1].get_text(strip=True)
        signo = cols[2].get_text(strip=True)
        data.append([fecha, numero, signo])

if not data:
    print("[WARNING] Tabla encontrada pero sin datos útiles.")
    exit(1)

try:
    with open(DESTINO, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["fecha", "numero", "signo"])
        writer.writerows(data)
    print(f"[OK] AstroLuna: {len(data)} registros exportados a {DESTINO}")
except Exception as e:
    print(f"[ERROR] No se pudo guardar archivo: {e}")
    exit(1)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Scrapeo completado")
