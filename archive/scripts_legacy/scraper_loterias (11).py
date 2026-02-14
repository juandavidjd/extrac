import os
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Ruta absoluta para guardar archivos
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/crudo"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Loterías oficialmente definidas
LOTERIAS = {
    'tolima':    'https://www.astroluna.co/tolima',
    'huila':     'https://www.astroluna.co/huila',
    'manizales': 'https://www.astroluna.co/manizales',
    'quindio':   'https://www.astroluna.co/quindio',
    'medellin':  'https://www.astroluna.co/medellin',
    'boyaca':    'https://www.astroluna.co/boyaca'
}

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] === Inicio de scrapeo de loterías ===")

for name, url in LOTERIAS.items():
    try:
        resp = requests.get(url, timeout=15)
        resp.encoding = 'utf-8'
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
        continue

    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table')
    if not table:
        print(f"[WARNING] {name}: no se encontró tabla de resultados")
        continue

    rows = table.select('tbody tr')
    data = []
    for tr in rows:
        cols = tr.find_all('td')
        if len(cols) >= 2:
            fecha = cols[0].get_text(strip=True)
            numero = cols[1].get_text(strip=True)
            data.append((fecha, numero))

    if not data:
        print(f"[WARNING] {name}: tabla encontrada pero sin datos útiles")
        continue

    filepath = os.path.join(OUTPUT_DIR, f"{name}.csv")
    try:
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['fecha', 'numero'])
            writer.writerows(data)
        print(f"[OK] {name}: {len(data)} registros exportados a {filepath}")
    except Exception as e:
        print(f"[ERROR] {name}: error al escribir el archivo: {e}")

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Scrapeo completado")
