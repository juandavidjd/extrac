#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
generar_catalogo_kaiqi_hibrido.py

Flujo:
1) Recorre la carpeta C:\img\FOTOS_COMPETENCIA con imágenes de repuestos.
2) Para cada imagen:
   - Llama primero a gpt-4.1-mini (visión) con un esquema JSON estrictamente definido.
   - Si el modelo indica baja confianza o "Necesita_Modelo_Grande": vuelve a llamar con gpt-4.1.
3) Clasifica:
   - Si NO es repuesto de moto/motocarguero => va a imagenes_descartadas_no_moto.csv
   - Si sí lo es => se agrega a catalogo_kaiqi_imagenes.csv
4) Registra cualquier error en errores_ia.csv

Requisitos:
- pip install openai pillow pandas
- Variable de entorno OPENAI_API_KEY configurada.
"""

import os
import base64
import json
import re
from io import BytesIO

from PIL import Image
import pandas as pd
from openai import OpenAI

# ==============================
# CONFIGURACIÓN
# ==============================

IMAGE_FOLDER = r"C:\img\FOTOS_COMPETENCIA"
OUTPUT_FOLDER = r"C:\img"

CATALOGO_OUT = os.path.join(OUTPUT_FOLDER, "catalogo_kaiqi_imagenes.csv")
DESCARTES_OUT = os.path.join(OUTPUT_FOLDER, "imagenes_descartadas_no_moto.csv")
ERRORES_OUT = os.path.join(OUTPUT_FOLDER, "errores_ia.csv")

# Modelos
MODEL_MINI = "gpt-4.1-mini"
MODEL_GRANDE = "gpt-4.1"

# ==============================
# INSTRUCCIONES DE ESQUEMA
# ==============================

SCHEMA_INSTRUCCIONES = """
Debes responder ÚNICAMENTE con un objeto JSON válido.

Estás analizando una sola imagen de un posible repuesto de motocicleta o motocarguero.

Tu tarea:
1) Identificar de forma general qué repuesto es.
2) Describir características visibles importantes.
3) Inferir compatibilidad probable (sin inventar modelos raros si no estás seguro).
4) Explicar brevemente la función de la pieza.
5) Proponer un nombre comercial amigable para catálogo.

IMPORTANTE SOBRE TEXTOS GRABADOS:
- La pieza puede tener textos grabados en metal/plástico (ej: JAPAN, números como 54410, códigos cortos).
- Puedes usarlos SOLO como ayuda interna para saber de qué tipo de repuesto se trata.
- PERO está PROHIBIDO copiar esos textos directamente en:
  - Nombre_Comercial_Catalogo
  - Tags_Sugeridos
- Puedes mencionarlos SOLO en el campo "Notas_Sobre_Textos_Grabados".

Clasificación de contenido:
- Si ves claramente que NO es un repuesto de moto ni de motocarguero (por ejemplo: juguete, auto, electrodoméstico, logo, etc.),
  marca:
  - Es_Moto_o_Motocarguero = false
  - Tipo_Contenido = "no_moto" o "no_repuesto"
  Y rellena el resto de campos lo mejor posible, pero será descartado.

Si es repuesto de otro vehículo (carro, camión, bici, etc.), marca:
- Es_Moto_o_Motocarguero = false
- Tipo_Contenido = "otro_vehiculo"

Campos requeridos (JSON final):

{
  "Filename_Original": "string (nombre del archivo tal cual te lo dan)",
  "Es_Moto_o_Motocarguero": true o false,
  "Tipo_Contenido": "repuesto_moto" | "repuesto_motocarguero" | "otro_vehiculo" | "no_repuesto" | "no_moto",
  "Confianza_Global": número entre 0 y 1 (tu nivel de seguridad),
  "Identificacion_Repuesto": "string (nombre técnico/descriptivo de la pieza)",
  "Componente_Taxonomia": "string (una sola palabra o frase corta para la familia, ej: 'Banda de freno', 'Pastilla de freno', 'Bobina de encendido')",
  "Sistema": "string (ej: Frenos, Motor, Transmisión, Eléctrico, Suspensión, Dirección, Carrocería, Accesorios)",
  "SubSistema": "string (ej: Freno delantero de disco, Freno trasero de campana, Encendido, Kit arrastre, etc.)",
  "Caracteristicas_Observadas": "string (materiales, forma, cantidad de piezas, resortes, conectores, color, acabado, etc.)",
  "Compatibilidad_Probable_Texto": "string (descripción corta, ej: 'Motos utilitarias 100-125cc con freno de campana trasero')",
  "Compatibilidad_Probable_JSON": [
    {
      "marca": "string (GENERICA si no estás seguro de la marca)",
      "modelo": "string (puede ser genérico, ej: 'Motos utilitarias 100-125cc')",
      "cilindraje": "string (ej: '100', '125', '100-125', 'desconocido')",
      "posicion": "string (Delantero, Trasero, Ambos, N/A)",
      "lado": "string (Izquierdo, Derecho, N/A)"
    }
  ],
  "Funcion": "string (explica en lenguaje sencillo qué hace esta pieza en la moto/motocarguero)",
  "Nombre_Comercial_Catalogo": "string (nombre corto y vendible, sin marcas registradas específicas si no estás seguro, ej: 'Banda freno trasera moto 100-125cc')",
  "Tags_Sugeridos": "string con palabras clave separadas por coma (ej: 'Frenos, Banda de freno, Freno de campana, Moto utilitaria, 100cc, 125cc')",
  "Notas_Sobre_Textos_Grabados": "string (qué textos viste en aluminio/plástico, aclarando que no se deben usar en título/SKU)",
  "Necesita_Modelo_Grande": true o false (marca true SOLO si ves que la imagen es compleja o tu confianza es menor a 0.7)"
}

Reglas:
- JSON plano, sin comentarios.
- No añadas texto fuera del JSON.
- Usa siempre punto decimal en los números (ej: 0.78).
"""

# ==============================
# FUNCIONES AUXILIARES
# ==============================

def encode_image_to_base64(image_path: str) -> str | None:
    """Abre una imagen, la convierte a JPEG y devuelve base64."""
    try:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[ERROR] No se pudo abrir/convertir la imagen {image_path}: {e}")
        return None


def llamar_modelo(modelo: str, base64_img: str, filename: str, client: OpenAI) -> dict | None:
    """Llama al modelo indicado y devuelve un dict con el JSON parseado."""
    try:
        prompt_usuario = (
            "Analiza la siguiente imagen de un posible repuesto de motocicleta o motocarguero. "
            f"El nombre de archivo es: {filename}. "
            "Debes generar el JSON EXACTAMENTE con el esquema indicado en las instrucciones."
        )

        respuesta = client.chat.completions.create(
            model=modelo,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": SCHEMA_INSTRUCCIONES
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_usuario},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_img}",
                                "detail": "low"
                            }
                        }
                    ]
                }
            ],
            temperature=0.2
        )

        contenido = respuesta.choices[0].message.content.strip()
        return json.loads(contenido)
    except Exception as e:
        print(f"[ERROR IA] modelo {modelo} para archivo {filename}: {e}")
        return None


def normalizar_confianza(valor):
    """Asegura que Confianza_Global esté entre 0 y 1, o None."""
    try:
        v = float(valor)
        if v < 0:
            v = 0.0
        if v > 1:
            v = 1.0
        return v
    except Exception:
        return None

# ==============================
# BUCLE PRINCIPAL
# ==============================

def main():
    if not os.path.isdir(IMAGE_FOLDER):
        print(f"❌ Carpeta de imágenes no encontrada: {IMAGE_FOLDER}")
        return

    client = OpenAI()  # Usa OPENAI_API_KEY del entorno

    # Listar imágenes
    extensiones = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
    archivos = [
        f for f in os.listdir(IMAGE_FOLDER)
        if f.lower().endswith(extensiones)
    ]
    archivos.sort()

    total = len(archivos)
    if total == 0:
        print(f"❌ No se encontraron imágenes en {IMAGE_FOLDER}")
        return

    print("=============================================")
    print(f" Iniciando catalogación híbrida de {total} imágenes...")
    print("=============================================")

    registros_catalogo = []
    registros_descartes = []
    registros_errores = []

    for idx, filename in enumerate(archivos, start=1):
        print(f"\n[{idx}/{total}] Procesando → {filename}")
        ruta = os.path.join(IMAGE_FOLDER, filename)

        b64 = encode_image_to_base64(ruta)
        if not b64:
            registros_errores.append({
                "Filename": filename,
                "Error": "No se pudo abrir/convertir la imagen"
            })
            continue

        # 1) Intento con modelo mini
        datos = llamar_modelo(MODEL_MINI, b64, filename, client)

        if not datos:
            # Intentar directamente con modelo grande como fallback
            print("   -> Reintentando con modelo grande por error en mini...")
            datos = llamar_modelo(MODEL_GRANDE, b64, filename, client)

        if not datos:
            registros_errores.append({
                "Filename": filename,
                "Error": "Fallo IA en mini y grande"
            })
            continue

        # Asegurar que tenga filename
        datos.setdefault("Filename_Original", filename)

        confianza = normalizar_confianza(datos.get("Confianza_Global"))
        necesita_grande = bool(datos.get("Necesita_Modelo_Grande"))

        # 2) Decidir si se llama modelo grande
        if (confianza is not None and confianza < 0.75) or necesita_grande:
            print(f"   -> Confianza baja ({confianza}) o marcado para modelo grande. Reprocesando con {MODEL_GRANDE}...")
            datos_grandes = llamar_modelo(MODEL_GRANDE, b64, filename, client)
            if datos_grandes:
                datos_grandes.setdefault("Filename_Original", filename)
                datos = datos_grandes
                confianza = normalizar_confianza(datos.get("Confianza_Global"))

        # 3) Clasificar: moto/motocarguero vs descartado
        es_moto = bool(datos.get("Es_Moto_o_Motocarguero"))
        tipo_contenido = (datos.get("Tipo_Contenido") or "").lower()

        if not es_moto or tipo_contenido in ("no_moto", "no_repuesto", "otro_vehiculo"):
            print("   -> Imagen descartada (no repuesto de moto/motocarguero).")
            registros_descartes.append({
                "Filename": filename,
                "Tipo_Contenido": datos.get("Tipo_Contenido"),
                "Es_Moto_o_Motocarguero": datos.get("Es_Moto_o_Motocarguero"),
                "Motivo": "Clasificado como no_moto/no_repuesto/otro_vehiculo por IA"
            })
        else:
            print("   -> Imagen aceptada como repuesto de moto/motocarguero.")
            registros_catalogo.append(datos)

    # ==============================
    # GUARDAR RESULTADOS
    # ==============================
    if registros_catalogo:
        df_cat = pd.DataFrame(registros_catalogo)
        df_cat.to_csv(CATALOGO_OUT, index=False, encoding="utf-8-sig", sep=";")
        print("\n✅ Catálogo generado:")
        print(f"   → {CATALOGO_OUT}")
        print(f"   → Total registros aceptados: {len(df_cat)}")
    else:
        print("\n⚠ No hubo registros aceptados para el catálogo.")

    if registros_descartes:
        df_desc = pd.DataFrame(registros_descartes)
        df_desc.to_csv(DESCARTES_OUT, index=False, encoding="utf-8-sig", sep=";")
        print(f"🗂 Imágenes descartadas guardadas en: {DESCARTES_OUT} "
              f"(total: {len(df_desc)})")

    if registros_errores:
        df_err = pd.DataFrame(registros_errores)
        df_err.to_csv(ERRORES_OUT, index=False, encoding="utf-8-sig", sep=";")
        print(f"❗ Errores registrados en: {ERRORES_OUT} "
              f"(total: {len(df_err)})")

    print("\n===============================")
    print("   PROCESO FINALIZADO")
    print("===============================")


if __name__ == "__main__":
    main()
