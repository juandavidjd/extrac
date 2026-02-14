#!/usr/bin/env python3
"""Preprocesa catálogo Yokomar para ODI Semantic Normalizer.

Combina Base_Datos_Yokomar.csv + Lista_Precios_Yokomar.csv
y los transforma al formato esperado por el normalizer.
"""
import pandas as pd
import re

# Rutas
DATA_DIR = "/mnt/volume_sfo3_01/profesion/10 empresas ecosistema ODI/Data/Yokomar"
BASE = f"{DATA_DIR}/Base_Datos_Yokomar.csv"
PRECIOS = f"{DATA_DIR}/Lista_Precios_Yokomar.csv"
OUTPUT = "/opt/odi/extractors/YOKOMAR_REAL_INPUT.csv"

def extract_marca_from_description(desc: str) -> str:
    """Extrae marca de moto del código al inicio (ej: 'AK.', 'H.', 'S.')."""
    if not desc:
        return ""

    # Patrones comunes: "XXXX H. MODELO" o "XXXX AK. MODELO"
    marcas = {
        'H.': 'HONDA',
        'S.': 'SUZUKI',
        'Y.': 'YAMAHA',
        'AK.': 'AKT',
        'B.': 'BAJAJ',
        'K.': 'KAWASAKI',
        'KTM.': 'KTM',
        'TVS.': 'TVS',
        'PULSAR': 'BAJAJ',
    }

    for code, marca in marcas.items():
        if f" {code} " in f" {desc} " or desc.startswith(code):
            return marca
    return ""


def extract_modelo_from_description(desc: str) -> str:
    """Extrae modelo de moto de la descripción."""
    if not desc:
        return ""

    # Modelos comunes
    modelos = [
        'XR125', 'XR150', 'XR190', 'CBF150', 'CB110', 'CB125', 'CB190',
        'NXR125', 'NXR150', 'WAVE110', 'BIZ125', 'CG125', 'CG150',
        'AK125', 'AK150', 'AK150TT', 'AKT125', 'BEST125', 'BOXER100',
        'BOXER CT100', 'BOXER UG', 'PLATINO', 'PULSAR135', 'PULSAR150',
        'PULSAR180', 'PULSAR200', 'PULSAR220', 'DISCOVER', 'APACHE',
        'FZ16', 'FZ25', 'YBR125', 'CRYPTON', 'LIBERO', 'DT125', 'DT175',
        'GN125', 'EN125', 'AX100', 'AX4', 'GIXXER', 'VIVA',
        'NINJA', 'Z250', 'ER6N', 'VERSYS', 'KLR650',
        'DUKE200', 'DUKE390', 'RC200',
    ]

    desc_upper = desc.upper()
    for modelo in modelos:
        if modelo in desc_upper:
            return modelo
    return ""


def infer_categoria(desc: str) -> str:
    """Infiere categoría del producto basado en palabras clave."""
    if not desc:
        return "OTROS"

    desc_upper = desc.upper()

    categorias = {
        'MOTOR': ['CILINDRO', 'PISTON', 'ANILLO', 'BIELA', 'CIGÜEÑAL', 'VALVULA',
                  'ARBOL DE LEVAS', 'CAMISA', 'EMPAQUE', 'CULATA', 'TAPA'],
        'ELECTRICO': ['SWITCH', 'BOBINA', 'CDI', 'REGULADOR', 'ESTATOR', 'FARO',
                      'DIRECCIONAL', 'STOP', 'BOMBILLO', 'FLASHER', 'RELAY'],
        'TRANSMISION': ['CADENA', 'PIÑON', 'CATALINA', 'KIT ARRASTRE', 'CLUTCH',
                        'EMBRAGUE', 'DISCO CLUTCH', 'PLATO PRESION'],
        'SUSPENSION': ['AMORTIGUADOR', 'TIJERA', 'TELESCOPIO', 'RESORTE', 'BUJE'],
        'FRENOS': ['PASTILLA', 'DISCO FRENO', 'MORDAZA', 'BOMBA FRENO', 'GUAYA FRENO'],
        'CARROCERIA': ['CARENAJE', 'GUARDABARRO', 'TANQUE', 'SILLA', 'ASIENTO',
                       'MANUBRIO', 'ESPEJO', 'PALANCA'],
        'ACCESORIOS': ['FILTRO', 'BUJIA', 'CABLE', 'GUAYA', 'MANIGUETA', 'PEDAL'],
    }

    for cat, keywords in categorias.items():
        for kw in keywords:
            if kw in desc_upper:
                return cat
    return "OTROS"


def main():
    print("=" * 60)
    print("🏭 PREPROCESADOR YOKOMAR → ODI SEMANTIC NORMALIZER")
    print("=" * 60)

    # Cargar archivos
    print("\n📂 Cargando archivos...")
    df_base = pd.read_csv(BASE, sep=';', encoding='utf-8-sig')
    df_precios = pd.read_csv(PRECIOS, sep=';', encoding='utf-8-sig')

    print(f"   Base datos: {len(df_base)} productos")
    print(f"   Lista precios: {len(df_precios)} productos")

    # JOIN por CODIGO
    print("\n🔗 Combinando archivos por CODIGO...")
    df = pd.merge(df_base, df_precios[['CODIGO', 'PRECIO']], on='CODIGO', how='left')
    print(f"   Después de merge: {len(df)} productos")
    print(f"   Con precio: {df['PRECIO'].notna().sum()}")

    # Transformar al formato del normalizer
    print("\n🔄 Transformando al formato ODI...")

    df_out = pd.DataFrame({
        'sku_odi': [f"YOK-{i+1:05d}" for i in range(len(df))],
        'codigo': df['CODIGO'],
        'nombre': df['DESCRIPCION'],
        'descripcion': df['DESCRIPCION'],
        'precio': df['PRECIO'].fillna(0).astype(int),
        'imagen': df['Imagen_URL_Origen'].fillna(''),
        'categoria': df['DESCRIPCION'].apply(infer_categoria),
        'marca_moto': df['DESCRIPCION'].apply(extract_marca_from_description),
        'modelo_moto': df['DESCRIPCION'].apply(extract_modelo_from_description),
        'cilindraje': ''  # Se podría inferir del modelo
    })

    # Estadísticas
    print("\n📊 Estadísticas:")
    print(f"   Total productos: {len(df_out)}")
    print(f"   Con precio: {(df_out['precio'] > 0).sum()}")
    print(f"   Con imagen: {(df_out['imagen'] != '').sum()}")
    print(f"   Con marca detectada: {(df_out['marca_moto'] != '').sum()}")
    print(f"   Con modelo detectado: {(df_out['modelo_moto'] != '').sum()}")

    print("\n   Distribución por categoría:")
    for cat, count in df_out['categoria'].value_counts().items():
        print(f"      {cat}: {count}")

    print("\n   Distribución por marca:")
    for marca, count in df_out['marca_moto'].value_counts().head(10).items():
        marca_display = marca if marca else "(sin marca)"
        print(f"      {marca_display}: {count}")

    # Guardar
    df_out.to_csv(OUTPUT, sep=';', index=False)
    print(f"\n✅ Archivo generado: {OUTPUT}")

    # Mostrar muestra
    print("\n📋 Muestra de datos (primeros 5):")
    print(df_out[['codigo', 'nombre', 'categoria', 'marca_moto', 'precio']].head().to_string())

    print("\n" + "=" * 60)
    print("🚀 Listo para procesar con: python3 odi_semantic_normalizer.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
