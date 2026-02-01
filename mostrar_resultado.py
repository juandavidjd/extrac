import pandas as pd
import os

# Cargar figuras desde el CSV
def cargar_figuras(csv_path):
    df = pd.read_csv(csv_path, header=None)
    figuras = {}
    figura_actual = None
    figura_data = []

    for _, row in df.iterrows():
        if pd.isna(row[0]):
            figura_data.append(row.tolist())
        else:
            if figura_actual is not None:
                figuras[figura_actual] = figura_data
            figura_actual = int(row[0])
            figura_data = [row.tolist()]
    if figura_actual is not None:
        figuras[figura_actual] = figura_data

    return figuras


# Imprimir figura en formato tabular
def imprimir_figura(figura_num, datos):
    print(f"\nFigura {figura_num}")
    print("       a    b    c    d    e    f")
    for idx, fila in enumerate(datos, 1):
        fila_fmt = [str(int(c)) if pd.notna(c) and str(c).strip().isdigit() else " " for c in fila[1:7]]
        print(f"{idx:<3}  " + "  ".join(f"{x:<3}" for x in fila_fmt))


# Cargar combinaciones desde el CSV
def cargar_combinaciones(csv_path):
    df = pd.read_csv(csv_path)
    return df['combinacion'].astype(str).tolist()


# Mostrar resultados cruzando figuras con combinaciones
def mostrar_resultado(figuras_csv, combinaciones_csv):
    figuras = cargar_figuras(figuras_csv)
    combinaciones = cargar_combinaciones(combinaciones_csv)
    usadas = set()

    print("\n--- 📦 FIGURAS GENERADAS ---\n")
    for num, datos in figuras.items():
        valores = [str(int(v)) for fila in datos for v in fila[1:7] if pd.notna(v) and str(v).strip().isdigit()]
        figura_tiene = False
        for comb in combinaciones:
            if all(d in valores for d in comb):
                imprimir_figura(num, datos)
                usadas.add(comb)
                figura_tiene = True
                break

    print("\n--- 🔓 COMBINACIONES SUELTAS (sin figura) ---")
    for comb in combinaciones:
        if comb not in usadas:
            print(f"Suelta: {comb}")


# Rutas de archivos
figuras_csv = "todo_fig.csv"
combinaciones_csv = "todo_sum.csv"

# Ejecutar si se llama directamente
if __name__ == "__main__":
    mostrar_resultado(figuras_csv, combinaciones_csv)
