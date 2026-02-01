import pandas as pd
import random

archivo_excel = "todo_.xlsx"

def simplificar(valor):
    while valor > 9:
        valor = sum(int(d) for d in str(valor))
    return valor

def calcular_posiciones(fecha_str):
    dia, mes, anio = fecha_str.split("/")
    dia = int(dia)
    mes = int(mes)
    anio = int(anio)
    anio_str = f"{anio:02d}"  # asegura 2 dígitos

    posiciones = [
        (dia, mes),
        (dia, int(mes)),
        (dia, int(anio_str[0])),
        (dia, int(anio_str[1])),
        (7, dia),
        (7, int(anio_str[0])),
        (7, int(anio_str[1])),
        (7, int(anio_str[1]))  # repetido a propósito
    ]
    return posiciones

def actualizar_hojas(combinaciones, fecha_str):
    posiciones = calcular_posiciones(fecha_str)
    posicion_data = []

    for i, (a, b) in enumerate(posiciones, 1):
        suma = simplificar(a + b)
        fila = {
            "posicion": f"{i}º",
            "dia": a if i <= 4 else "",
            "mes": b if i <= 4 else "",
            "ano": b if i > 4 else "",
            "suma": suma,
            "fecha": fecha_str
        }
        posicion_data.append(fila)

    suma_data = [{"combinaciones": c} for c in combinaciones]

    with pd.ExcelWriter(archivo_excel, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        pd.DataFrame(posicion_data).to_excel(writer, sheet_name="posicion", index=False)
        pd.DataFrame(suma_data).to_excel(writer, sheet_name="suma", index=False)

def cargar_moldes():
    df = pd.read_excel(archivo_excel, sheet_name="figuras", header=None)
    moldes = []
    molde = []

    for row in df.itertuples(index=False):
        if all(pd.isna(cell) for cell in row):
            if molde:
                moldes.append(molde)
                molde = []
            continue
        line = []
        for cell in row:
            if pd.isna(cell) or str(cell).strip() == "":
                line.append("")
            else:
                try:
                    line.append(str(int(cell)))
                except:
                    line.append("")
        molde.append(line)

    if molde:
        moldes.append(molde)

    return moldes

def imprimir_figura(figura_num, molde, cifras):
    print(f"\nFigura {figura_num + 1}")

    filas = len(molde)
    columnas = max(len(f) for f in molde)
    cell_map = [["" for _ in range(columnas)] for _ in range(filas)]

    idx = 0
    for i, fila in enumerate(molde):
        for j, cell in enumerate(fila):
            if cell != "" and idx < len(cifras):
                cell_map[i][j] = str(cifras[idx])
                idx += 1

    # Encabezado
    header = "     " + "   ".join(chr(98 + i) for i in range(columnas))  # b, c, d...
    print(header)

    top = "    " + "┌" + "┬".join(["───"] * columnas) + "┐"
    print(top)

    for i, row in enumerate(cell_map):
        row_str = f"{i+1:<4}│" + "│".join(f"{cell:>3}" if cell else "   " for cell in row) + "│"
        print(row_str)
    bottom = "    " + "└" + "┴".join(["───"] * columnas) + "┘"
    print(bottom)

def generar_combinaciones(cantidad=50):
    combinaciones = []
    while len(combinaciones) < cantidad:
        comb = [random.randint(0, 12) for _ in range(4)]
        # simplifica a un solo dígito
        comb = [simplificar(n) for n in comb]
        combinaciones.append("".join(str(n) for n in comb))
    return combinaciones

def main():
    print("🧮 PROCESO DE FIGURAS INICIADO")
    fecha_str = input("Ingrese la fecha en formato DD/MM/YY (por ejemplo 07/08/25): ").strip()
    print(f"📅 Fecha ingresada: {fecha_str}")

    combinaciones = generar_combinaciones()
    actualizar_hojas(combinaciones, fecha_str)

    moldes = cargar_moldes()
    print("\n--- 📦 FIGURAS GENERADAS ---")
    combinaciones_cifradas = [list(map(int, list(c))) for c in combinaciones]
    usadas = 0

    for i, molde in enumerate(moldes):
        if usadas < len(combinaciones_cifradas):
            cifras = combinaciones_cifradas[usadas]
            imprimir_figura(i, molde, cifras)
            usadas += 1
        else:
            imprimir_figura(i, molde, [])

    if usadas < len(combinaciones):
        print("\n--- 🔓 COMBINACIONES SUELTAS (sin figura) ---")
        for comb in combinaciones[usadas:]:
            print(f"Suelta: {comb}")

if __name__ == "__main__":
    main()
