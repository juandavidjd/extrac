import os
import csv
from datetime import datetime

CSV_PATH = "C:/RadarPremios/data/crudo/revancha_premios.csv"

MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
}

def convertir_fecha(fecha_str):
    fecha_str = fecha_str.strip()

    # Ya está en formato ISO
    try:
        datetime.strptime(fecha_str, "%Y-%m-%d")
        return fecha_str
    except ValueError:
        pass

    # Caso: dd/mm/yyyy
    try:
        return datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        pass

    # Caso: '28 de Julio de 2025'
    try:
        partes = fecha_str.lower().split(" de ")
        if len(partes) == 3:
            dia = partes[0].zfill(2)
            mes = MESES.get(partes[1], "01")
            anio = partes[2]
            return f"{anio}-{mes}-{dia}"
    except Exception:
        pass

    # Si falla todo
    return fecha_str

def normalizar_fechas(path):
    if not os.path.exists(path):
        print(f"[ERROR] Archivo no encontrado: {path}")
        return

    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames

    if "fecha" not in headers:
        print("[ERROR] No se encontró la columna 'fecha'")
        return

    cambios = 0
    for row in rows:
        original = row["fecha"]
        nueva = convertir_fecha(original)
        if nueva != original:
            row["fecha"] = nueva
            cambios += 1

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[✅] {cambios} fechas normalizadas en {path}")

if __name__ == "__main__":
    normalizar_fechas(CSV_PATH)
