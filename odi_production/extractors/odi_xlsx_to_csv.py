#!/usr/bin/env python3
"""
==============================================================================
                    ODI XLSX TO CSV CONVERTER v1.0
              Convierte archivos Excel a CSV sin necesidad de Java
==============================================================================

DESCRIPCION:
    Conversor ligero de Excel (XLSX) a CSV usando pandas + openpyxl.
    NO requiere Java (a diferencia de Tabula).
    Ideal para listas de precios y catalogos en formato Excel.

USO:
    python3 odi_xlsx_to_csv.py archivo.xlsx
    python3 odi_xlsx_to_csv.py archivo.xlsx -o salida.csv
    python3 odi_xlsx_to_csv.py archivo.xlsx --sheet "Hoja1"
    python3 odi_xlsx_to_csv.py archivo.xlsx --list-sheets

REQUISITOS:
    pip install pandas openpyxl

AUTOR: ODI Team
VERSION: 1.0
==============================================================================
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    print("Error: pandas requerido. Instalar: pip install pandas openpyxl")
    sys.exit(1)

try:
    import openpyxl
except ImportError:
    print("Error: openpyxl requerido. Instalar: pip install openpyxl")
    sys.exit(1)


# ==============================================================================
# COLORES PARA TERMINAL
# ==============================================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def log(msg: str, level: str = 'info'):
    """Log con formato y colores."""
    colors = {
        'info': Colors.CYAN, 'success': Colors.GREEN,
        'warning': Colors.YELLOW, 'error': Colors.RED,
        'header': Colors.BOLD, 'dim': Colors.DIM
    }
    icons = {'success': '✓', 'warning': '⚠', 'error': '✗', 'info': '→'}
    color = colors.get(level, '')
    icon = icons.get(level, ' ')
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"{color}[{ts}] {icon} {msg}{Colors.RESET}", flush=True)


# ==============================================================================
# FUNCIONES PRINCIPALES
# ==============================================================================

def list_sheets(xlsx_path: str):
    """Lista las hojas disponibles en un archivo Excel."""
    try:
        xl = pd.ExcelFile(xlsx_path)
        print(f"\n{Colors.BOLD}Hojas en {Path(xlsx_path).name}:{Colors.RESET}")
        for i, sheet in enumerate(xl.sheet_names):
            print(f"  {i+1}. {sheet}")
        print()
        return xl.sheet_names
    except Exception as e:
        log(f"Error leyendo archivo: {e}", "error")
        return []


def convert_xlsx_to_csv(
    xlsx_path: str,
    output_path: str = None,
    sheet_name: str = None,
    separator: str = ';',
    encoding: str = 'utf-8-sig',
    normalize_headers: bool = True,
    skip_rows: int = 0,
    header_row: int = 0
):
    """
    Convierte un archivo Excel a CSV.

    Args:
        xlsx_path: Ruta al archivo Excel
        output_path: Ruta de salida para el CSV (opcional)
        sheet_name: Nombre de la hoja a convertir (default: primera)
        separator: Separador CSV (default: ';')
        encoding: Encoding del CSV (default: 'utf-8-sig')
        normalize_headers: Si normalizar encabezados a mayusculas (default: True)
        skip_rows: Filas a saltar al inicio (default: 0)
        header_row: Fila con los encabezados (default: 0)

    Returns:
        Ruta del archivo CSV generado
    """
    xlsx_path = Path(xlsx_path)

    if not xlsx_path.exists():
        log(f"Archivo no encontrado: {xlsx_path}", "error")
        return None

    log(f"Leyendo: {xlsx_path.name}")

    try:
        # Determinar hoja a usar
        xl = pd.ExcelFile(xlsx_path)
        available_sheets = xl.sheet_names

        if sheet_name:
            if sheet_name not in available_sheets:
                log(f"Hoja '{sheet_name}' no encontrada", "error")
                log(f"Hojas disponibles: {', '.join(available_sheets)}", "info")
                return None
            use_sheet = sheet_name
        else:
            use_sheet = available_sheets[0]
            if len(available_sheets) > 1:
                log(f"Multiples hojas detectadas, usando: '{use_sheet}'", "warning")

        log(f"Procesando hoja: '{use_sheet}'")

        # Leer Excel
        df = pd.read_excel(
            xlsx_path,
            sheet_name=use_sheet,
            skiprows=skip_rows,
            header=header_row,
            engine='openpyxl'
        )

        log(f"Filas leidas: {len(df)}", "success")

        # Limpiar DataFrame
        # Eliminar filas completamente vacias
        df = df.dropna(how='all')

        # Eliminar columnas sin nombre (Unnamed)
        unnamed_cols = [c for c in df.columns if 'Unnamed' in str(c)]
        if unnamed_cols:
            df = df.drop(columns=unnamed_cols)
            log(f"Columnas sin nombre eliminadas: {len(unnamed_cols)}", "info")

        # Normalizar encabezados
        if normalize_headers:
            df.columns = [str(c).strip().upper() for c in df.columns]

        log(f"Columnas: {list(df.columns)}", "info")

        # Determinar ruta de salida
        if output_path:
            csv_path = Path(output_path)
        else:
            # Generar nombre basado en el Excel
            csv_name = xlsx_path.stem.replace(' ', '_') + '.csv'
            csv_path = xlsx_path.parent / csv_name

        # Guardar CSV
        df.to_csv(csv_path, sep=separator, index=False, encoding=encoding)

        log(f"CSV generado: {csv_path}", "success")
        log(f"Filas totales: {len(df)}", "success")

        # Mostrar preview
        print(f"\n{Colors.BOLD}Preview (primeras 5 filas):{Colors.RESET}")
        print(df.head().to_string())
        print()

        return str(csv_path)

    except Exception as e:
        log(f"Error procesando Excel: {e}", "error")
        import traceback
        traceback.print_exc()
        return None


def process_price_list(
    xlsx_path: str,
    output_path: str = None,
    codigo_col: str = None,
    precio_col: str = None,
    descripcion_col: str = None
):
    """
    Procesa una lista de precios de Excel y extrae columnas relevantes.
    Intenta detectar automaticamente las columnas de codigo, precio y descripcion.

    Args:
        xlsx_path: Ruta al archivo Excel
        output_path: Ruta de salida para el CSV
        codigo_col: Nombre de columna de codigo (auto-detectar si None)
        precio_col: Nombre de columna de precio (auto-detectar si None)
        descripcion_col: Nombre de columna de descripcion (auto-detectar si None)

    Returns:
        Ruta del archivo CSV generado
    """
    xlsx_path = Path(xlsx_path)

    if not xlsx_path.exists():
        log(f"Archivo no encontrado: {xlsx_path}", "error")
        return None

    log(f"Procesando lista de precios: {xlsx_path.name}")

    try:
        df = pd.read_excel(xlsx_path, engine='openpyxl')
        df.columns = [str(c).strip().upper() for c in df.columns]

        log(f"Columnas detectadas: {list(df.columns)}", "info")

        # Auto-detectar columnas si no se especifican
        def find_column(keywords, cols):
            for kw in keywords:
                for col in cols:
                    if kw in col:
                        return col
            return None

        if not codigo_col:
            codigo_col = find_column(['CODIGO', 'SKU', 'REF', 'REFERENCIA', 'COD'], df.columns)
        if not precio_col:
            precio_col = find_column(['PRECIO', 'PRICE', 'VALOR', 'COSTO', 'PVP'], df.columns)
        if not descripcion_col:
            descripcion_col = find_column(['DESCRIPCION', 'NOMBRE', 'PRODUCTO', 'ARTICULO', 'TITLE'], df.columns)

        # Verificar columnas encontradas
        if codigo_col:
            log(f"Columna CODIGO: {codigo_col}", "success")
        else:
            log("No se detecto columna de CODIGO", "warning")

        if precio_col:
            log(f"Columna PRECIO: {precio_col}", "success")
        else:
            log("No se detecto columna de PRECIO", "warning")

        if descripcion_col:
            log(f"Columna DESCRIPCION: {descripcion_col}", "success")
        else:
            log("No se detecto columna de DESCRIPCION", "warning")

        # Construir DataFrame de salida
        output_cols = []
        rename_map = {}

        if codigo_col:
            output_cols.append(codigo_col)
            rename_map[codigo_col] = 'CODIGO'
        if descripcion_col:
            output_cols.append(descripcion_col)
            rename_map[descripcion_col] = 'DESCRIPCION'
        if precio_col:
            output_cols.append(precio_col)
            rename_map[precio_col] = 'PRECIO'

        if not output_cols:
            log("No se encontraron columnas relevantes, exportando todo", "warning")
            df_out = df
        else:
            df_out = df[output_cols].copy()
            df_out = df_out.rename(columns=rename_map)

        # Limpiar datos
        df_out = df_out.dropna(how='all')

        # Limpiar precios (eliminar caracteres no numericos excepto punto)
        if 'PRECIO' in df_out.columns:
            df_out['PRECIO'] = df_out['PRECIO'].apply(lambda x:
                float(str(x).replace('$', '').replace(',', '').replace(' ', '').strip() or 0)
                if pd.notna(x) else 0
            )

        # Determinar ruta de salida
        if output_path:
            csv_path = Path(output_path)
        else:
            csv_name = 'Lista_Precios_' + xlsx_path.stem.replace(' ', '_') + '.csv'
            csv_path = xlsx_path.parent / csv_name

        # Guardar
        df_out.to_csv(csv_path, sep=';', index=False, encoding='utf-8-sig')

        log(f"Lista de precios exportada: {csv_path}", "success")
        log(f"Productos con precio: {(df_out.get('PRECIO', 0) > 0).sum()}", "success")

        # Preview
        print(f"\n{Colors.BOLD}Preview:{Colors.RESET}")
        print(df_out.head(10).to_string())
        print()

        return str(csv_path)

    except Exception as e:
        log(f"Error: {e}", "error")
        import traceback
        traceback.print_exc()
        return None


# ==============================================================================
# CLI
# ==============================================================================

def print_banner():
    print(f"""
{Colors.BOLD}+{'='*62}+
|{' '*12}ODI XLSX TO CSV CONVERTER v1.0{' '*19}|
|{' '*10}Convierte Excel a CSV sin Java{' '*21}|
+{'='*62}+{Colors.RESET}
""")


def main():
    parser = argparse.ArgumentParser(
        description='Convierte archivos Excel (XLSX) a CSV sin necesidad de Java',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s archivo.xlsx                    # Convertir a CSV (mismo directorio)
  %(prog)s archivo.xlsx -o salida.csv      # Especificar archivo de salida
  %(prog)s archivo.xlsx --sheet "Hoja2"    # Usar hoja especifica
  %(prog)s archivo.xlsx --list-sheets      # Listar hojas disponibles
  %(prog)s archivo.xlsx --price-mode       # Modo lista de precios
"""
    )

    parser.add_argument('xlsx_file', nargs='?', help='Archivo Excel a convertir')
    parser.add_argument('-o', '--output', help='Archivo CSV de salida')
    parser.add_argument('--sheet', help='Nombre de la hoja a convertir')
    parser.add_argument('--list-sheets', action='store_true', help='Listar hojas disponibles')
    parser.add_argument('--price-mode', action='store_true',
                       help='Modo lista de precios (auto-detecta columnas)')
    parser.add_argument('--separator', default=';', help='Separador CSV (default: ;)')
    parser.add_argument('--skip-rows', type=int, default=0, help='Filas a saltar al inicio')
    parser.add_argument('--no-normalize', action='store_true',
                       help='No normalizar encabezados a mayusculas')

    args = parser.parse_args()

    print_banner()

    if not args.xlsx_file:
        parser.print_help()
        sys.exit(0)

    if args.list_sheets:
        list_sheets(args.xlsx_file)
        sys.exit(0)

    if args.price_mode:
        result = process_price_list(args.xlsx_file, args.output)
    else:
        result = convert_xlsx_to_csv(
            args.xlsx_file,
            args.output,
            sheet_name=args.sheet,
            separator=args.separator,
            normalize_headers=not args.no_normalize,
            skip_rows=args.skip_rows
        )

    if result:
        log("Conversion completada", "success")
        log(f"Siguiente paso: python3 odi_industrial_extractor.py --profile yokomar --precios {result}")
        sys.exit(0)
    else:
        log("Conversion fallida", "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
