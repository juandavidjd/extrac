import pandas as pd
from datetime import datetime

def simplificar(num: int) -> int:
    """Suma de dígitos repetida hasta quedar en un dígito (0..9)."""
    while num >= 10:
        num = sum(int(d) for d in str(num))
    return num

def parse_fecha(fecha_str: str) -> tuple[int, int, int]:
    """
    Devuelve (dd, mm, yyyy). Acepta DD/MM/YY, DD/MM/YYYY, con '/', '-' o espacios.
    """
    s = fecha_str.strip().replace("-", "/").replace(" ", "")
    formatos = ["%d/%m/%Y", "%d/%m/%y"]
    for fmt in formatos:
        try:
            dt = datetime.strptime(s, fmt)
            # Normalizamos año a cuatro dígitos
            y = dt.year if "%Y" in fmt else (2000 + dt.year % 100)  # %y → 2000..2099
            return dt.day, dt.month, y
        except ValueError:
            continue
    raise ValueError("Formato de fecha inválido. Usa DD/MM/YY o DD/MM/YYYY (p. ej. 08/08/2025).")

def calcular_posiciones(fecha_str: str):
    """
    Construye las 8 posiciones:
      1: d1+m1   2: d1+m2   3: d1+a1   4: d1+a2
      5: d2+m1   6: d2+m2   7: d2+a1   8: d2+a2
    Donde a1,a2 son los **dos últimos dígitos** del año.
    """
    dd, mm, yyyy = parse_fecha(fecha_str)

    d = f"{dd:02d}"
    m = f"{mm:02d}"
    a = f"{yyyy%100:02d}"       # ← últimos dos dígitos del año

    d1, d2 = int(d[0]), int(d[1])
    m1, m2 = int(m[0]), int(m[1])
    a1, a2 = int(a[0]), int(a[1])

    calculos = [
        ("1º", d1, m1, ""),  # (pos, dia, mes, ano)
        ("2º", d1, m2, ""),
        ("3º", d1, "",  a1),
        ("4º", d1, "",  a2),
        ("5º", d2, m1, ""),
        ("6º", d2, m2, ""),
        ("7º", d2, "",  a1),
        ("8º", d2, "",  a2),
    ]

    filas_pos = []
    combinaciones = []

    for pos, x, y_m, y_a in calculos:
        # y_m es mes si no es "", y_a es año si no es ""
        y = y_m if y_m != "" else y_a
        suma_cruda = int(x) + int(y)
        suma = simplificar(suma_cruda)
        filas_pos.append({
            "posicion": pos,
            "dia": x,
            "mes": y_m if y_m != "" else "",
            "ano": y_a if y_a != "" else "",
            "suma_cruda": suma_cruda,
            "suma": suma,
            "fecha": f"{dd:02d}/{mm:02d}/{yyyy}"
        })
        combinaciones.append(suma)

    return filas_pos, combinaciones

def guardar_archivos(filas_pos, combinaciones, base="todo"):
    df_pos = pd.DataFrame(filas_pos)
    # Excel friendly
    df_pos.to_csv(f"{base}_pos.csv", index=False, encoding="utf-8-sig")

    # Combinaciones en bloques de 4 cifras: 1-4 y 5-8
    bloques = [{"combinacion": "".join(str(n) for n in combinaciones[i:i+4])}
               for i in range(0, len(combinaciones), 4)]
    pd.DataFrame(bloques).to_csv(f"{base}_sum.csv", index=False, encoding="utf-8-sig")

if __name__ == "__main__":
    try:
        fecha = input("Ingrese la fecha (DD/MM/YY o DD/MM/YYYY): ").strip()
        filas_pos, combinaciones = calcular_posiciones(fecha)
        guardar_archivos(filas_pos, combinaciones, base="todo")
        print("\n✅ Posiciones y sumas guardadas en 'todo_pos.csv' y 'todo_sum.csv'.")
    except Exception as e:
        print(f"❌ Error: {e}")
