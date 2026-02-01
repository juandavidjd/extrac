import subprocess
import os
import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

SCRIPTS = [
    "scraper_loterias.py",
    "scraper_astroluna.py",
    "scraper_baloto_resultados.py",
    "scraper_baloto_premios.py",
    "limpiar_csvs.py",
    "cargar_db.py"
]

def log(msg):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")

def ejecutar_script(nombre):
    log(f"▶ Ejecutando: {nombre}")
    try:
        subprocess.run(["python", nombre], check=True)
        log(f"✅ Finalizado: {nombre}")
    except subprocess.CalledProcessError as e:
        log(f"❌ Error al ejecutar {nombre}: {e}")

def obtener_fecha_sorteo(sorteo):
    url = f"https://www.baloto.com/resultados-baloto/{sorteo}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        fecha_tag = soup.select_one(".resultado-info h3")
        if fecha_tag:
            texto = fecha_tag.text.strip()
            partes = texto.split()
            if len(partes) >= 4:
                meses = {
                    "enero": "01", "febrero": "02", "marzo": "03",
                    "abril": "04", "mayo": "05", "junio": "06",
                    "julio": "07", "agosto": "08", "septiembre": "09",
                    "octubre": "10", "noviembre": "11", "diciembre": "12"
                }
                dia = partes[1]
                mes = meses.get(partes[3].lower())
                año = partes[4]
                if mes:
                    return f"{año}-{mes}-{dia.zfill(2)}"
    except Exception as e:
        log(f"❌ Error obteniendo fecha sorteo {sorteo}: {e}")
    return None

def restaurar_fechas():
    resultados_path = "resultados.csv"
    premios_path = "premios.csv"

    if not os.path.exists(resultados_path) or not os.path.exists(premios_path):
        log("⚠️ Archivos resultados.csv o premios.csv no encontrados. Se omite restauración de fechas.")
        return

    df_resultados = pd.read_csv(resultados_path)
    df_premios = pd.read_csv(premios_path)

    sorteos = df_resultados["sorteo"].dropna().astype(int).unique()
    sorteos = sorted(sorteos)

    cambios = 0
    for sorteo in sorteos:
        if df_resultados[df_resultados["sorteo"] == sorteo]["fecha"].isnull().all():
            log(f"🔎 Buscando fecha para sorteo {sorteo}...")
            fecha = obtener_fecha_sorteo(sorteo)
            if fecha:
                df_resultados.loc[df_resultados["sorteo"] == sorteo, "fecha"] = fecha
                df_premios.loc[df_premios["sorteo"] == sorteo, "fecha"] = fecha
                log(f"✅ Fecha restaurada para sorteo {sorteo}: {fecha}")
                cambios += 1
            else:
                log(f"⚠️ No se encontró fecha para sorteo {sorteo}")
            time.sleep(1.5)

    if cambios > 0:
        df_resultados.to_csv(resultados_path, index=False)
        df_premios.to_csv(premios_path, index=False)
        log(f"✅ Restauración completa: {cambios} sorteos actualizados con fecha.")
    else:
        log("ℹ️ No había fechas faltantes o no se pudo restaurar ninguna.")

def main():
    log("=== Inicio de actualización general ===")
    log(f"Directorio actual: {os.getcwd()}")
    for script in SCRIPTS:
        ejecutar_script(script)
    log("📅 Restaurando fechas faltantes en resultados y premios...")
    restaurar_fechas()
    log("=== Actualización completa ===")

if __name__ == "__main__":
    main()
