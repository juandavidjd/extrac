import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os

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
            if len(partes) >= 5:
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
        print(f"❌ Error obteniendo fecha para sorteo {sorteo}: {e}")
    return None

def main():
    if not os.path.exists("resultados.csv") or not os.path.exists("premios.csv"):
        print("❌ Archivos resultados.csv o premios.csv no encontrados.")
        return

    df_resultados = pd.read_csv("resultados.csv")
    df_premios = pd.read_csv("premios.csv")

    sorteos = df_resultados["sorteo"].dropna().astype(int).unique()
    sorteos = sorted(sorteos)

    cambios = 0

    for sorteo in sorteos:
        fila_res = df_resultados[df_resultados["sorteo"] == sorteo]
        if fila_res["fecha"].isnull().all() or fila_res["fecha"].astype(str).str.strip().eq("").all():
            print(f"🔎 Buscando fecha para sorteo {sorteo}...")
            fecha = obtener_fecha_sorteo(sorteo)
            if fecha:
                df_resultados.loc[df_resultados["sorteo"] == sorteo, "fecha"] = fecha
                df_premios.loc[df_premios["sorteo"] == sorteo, "fecha"] = fecha
                print(f"✅ Fecha para sorteo {sorteo}: {fecha}")
                cambios += 1
            else:
                print(f"⚠️ No se pudo obtener fecha para sorteo {sorteo}")
            time.sleep(1.5)

    if cambios > 0:
        df_resultados.to_csv("resultados.csv", index=False)
        df_premios.to_csv("premios.csv", index=False)
        print(f"\n✅ Fechas restauradas en {cambios} sorteos.")
    else:
        print("\nℹ️ No había fechas por restaurar o ya estaban completas.")

if __name__ == "__main__":
    main()
