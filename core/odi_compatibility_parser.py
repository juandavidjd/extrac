#!/usr/bin/env python3
"""
ODI Compatibility Parser — Extrae marca, modelo y cilindrada de titulos.

Patrones que debe reconocer:
  "Arbol de Levas AKT 125"          → AKT 125
  "Banda Freno Bajaj Pulsar 200NS"  → Bajaj Pulsar 200NS
  "Cadena 428 Honda CBF 150"        → Honda CBF 150
  "Kit Arrastre Yamaha BWS 125"     → Yamaha BWS 125
  "Piston AK. AKT110"               → AKT 110
  "Clutch B. Pulsar200NS"           → Bajaj Pulsar 200NS
  "Bobina H. C100/BIZ"              → Honda C100, Honda BIZ
  "Arbol De Levas Ak. Akt125/150/Sigma125-2A"
                                     → AKT 125, AKT 150, AKT Sigma 125

Uso:
  parser = CompatibilityParser()
  compatibles = parser.parse("Arbol de Levas AKT 125")
  # [{"marca": "AKT", "modelo": "125", "cc": "125"}]

  shopify_text = parser.format_for_shopify(compatibles)
  # "AKT 125 125cc"
"""

import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger("odi.compatibility")

# ─────────────────────────────────────────────────────────
# DICCIONARIO DE MARCAS
# ─────────────────────────────────────────────────────────

MARCAS_MOTO = {
    # Abreviatura en CSV → Nombre completo
    "AK.": "AKT",
    "AK": "AKT",
    "AKT": "AKT",
    "B.": "Bajaj",
    "BAJ": "Bajaj",
    "BAJAJ": "Bajaj",
    "H.": "Honda",
    "HON": "Honda",
    "HONDA": "Honda",
    "Y.": "Yamaha",
    "YAM": "Yamaha",
    "YAMAHA": "Yamaha",
    "S.": "Suzuki",
    "SUZ": "Suzuki",
    "SUZUKI": "Suzuki",
    "K.": "Kawasaki",
    "KAW": "Kawasaki",
    "KAWASAKI": "Kawasaki",
    "KYM": "Kymco",
    "KYMCO": "Kymco",
    "AYCO": "Ayco",
    "AY.": "Ayco",
    "TVS": "TVS",
    "HERO": "Hero",
    "AUTECO": "Auteco",
    "UM": "UM",
    "JIALING": "Jialing",
    "ZONGSHEN": "Zongshen",
    "LIFAN": "Lifan",
    "SHINERAY": "Shineray",
    "QINGQI": "Qingqi",
    "KELLER": "Keller",
    "VICTORY": "Victory",
    "ITALIKA": "Italika",
}

# Modelos conocidos por marca
MODELOS_CONOCIDOS = {
    "AKT": [
        "NKD", "SL", "AKT110", "AK110", "FLEX125", "JET4", "JET5",
        "SIGMA", "SIGMA110", "SIGMA125", "TT125", "TT150", "RTXS",
        "AKT125", "AKT150", "AKT180", "AKT200", "XM", "EVO",
        "ACTIVE", "ECO", "DELUXE", "SPECIAL", "DYNAMIC", "SCOOTER",
        "FLEX", "NKD125", "TTR", "CR4", "CR5",
    ],
    "Bajaj": [
        "PULSAR", "DISCOVER", "BOXER", "BOXER100", "BOXERCT",
        "PULSAR135", "PULSAR150", "PULSAR180", "PULSAR200",
        "PULSAR200NS", "PULSAR220", "DISCOVER100", "DISCOVER125",
        "DISCOVER150", "PLATINO", "XCD", "CT100", "DOMINAR",
        "NS200", "RS200", "AS200", "NS160", "AVENGER",
    ],
    "Honda": [
        "C100", "BIZ", "SPLENDOR", "WAVE", "CBF150", "CB110",
        "CB190", "XR150", "XL125", "NXR125", "INVICTA",
        "PCX", "NAVI", "DIO", "DREAM", "CGL", "CBR",
        "XRE300", "XR250", "TITAN", "CG125", "ECO",
    ],
    "Yamaha": [
        "BWS", "BWS125", "FZ", "FZ150", "FZ250", "FZN",
        "CRYPTON", "LIBERO", "YBR", "YBR125", "XTZ",
        "XTZ125", "XTZ250", "NMAX", "AEROX", "MT03",
        "MOTOCARRO", "MOTARD", "FAZER", "SZ", "SZRR",
        "FZ16", "FZ25", "R15", "R3", "MT15",
    ],
    "Suzuki": [
        "GN125", "GS125", "EN125", "GIXXER", "GIXXER150",
        "BEST125", "HAYATE", "VIVA", "AX100", "AX4",
        "VSTROM", "DR200", "GN", "GSX", "INTRUDER",
        "ADDRESS", "BURGMAN", "ACCESS", "LETS",
    ],
    "Kawasaki": [
        "NINJA", "Z", "VERSYS", "KLR", "KLX",
        "Z250", "Z400", "Z650", "Z900", "NINJA250",
        "NINJA400", "VULCAN", "ER6N", "W800",
    ],
}

# Patrones de cilindrada
CC_PATTERNS = [
    re.compile(r'(\d{2,4})\s*(?:CC|cc|c\.c\.|C\.C\.)', re.IGNORECASE),
    re.compile(r'\b(\d{2,4})\s*(?:NS|RS|AS|R|S|F|X)\b'),  # 200NS, 150R
    re.compile(r'[A-Z]+\s*(\d{2,4})\b'),  # AKT 125, PULSAR 200
]


class CompatibilityParser:
    """Extrae compatibilidad (marca + modelo + CC) de titulos de productos."""

    def __init__(self):
        # Precompilar patrones para eficiencia
        self._marca_patterns = self._build_marca_patterns()

    def _build_marca_patterns(self) -> List[tuple]:
        """Construye patrones de busqueda ordenados por especificidad."""
        patterns = []
        # Ordenar por longitud descendente para match mas especifico primero
        sorted_abbrevs = sorted(MARCAS_MOTO.keys(), key=len, reverse=True)

        for abbrev in sorted_abbrevs:
            marca_full = MARCAS_MOTO[abbrev]
            # Patron: abreviatura seguida de modelo/CC
            # AK. AKT125 / AKT 125 / B. PULSAR200NS
            escaped = re.escape(abbrev)
            pattern = re.compile(
                rf'\b{escaped}\s*\.?\s*([A-Z0-9][A-Z0-9/\s-]*?)(?:\s+(?:PARA|CON|Y|DE|EN)\s|\s*$|\s*[-–]\s)',
                re.IGNORECASE
            )
            patterns.append((abbrev, marca_full, pattern))

        return patterns

    def parse(self, title: str, raw_data: dict = None) -> List[Dict]:
        """
        Extrae lista de motos compatibles del titulo.

        Args:
            title: Titulo del producto
            raw_data: Datos crudos del CSV (puede tener columna de moto)

        Returns:
            Lista de dicts: [{"marca": "AKT", "modelo": "125", "cc": "125"}]
        """
        compatibles = []

        if not title:
            return compatibles

        # 1. Buscar en datos crudos primero (columna especifica del CSV)
        if raw_data:
            moto_col = (raw_data.get("moto") or raw_data.get("modelo") or
                        raw_data.get("aplicacion") or raw_data.get("vehiculo") or
                        raw_data.get("compatibilidad") or raw_data.get("aplica"))
            if moto_col and str(moto_col).strip():
                parsed = self._parse_moto_string(str(moto_col))
                if parsed:
                    return parsed

        # 2. Extraer del titulo
        title_upper = title.upper()
        title_clean = self._clean_title(title_upper)

        # Buscar marcas en el titulo
        for abbrev, marca_full, pattern in self._marca_patterns:
            match = pattern.search(title_clean)
            if match:
                modelo_raw = match.group(1).strip()
                parsed = self._parse_modelo(marca_full, modelo_raw)
                compatibles.extend(parsed)

                # Si encontramos match, tambien buscar otras marcas
                # (un producto puede ser compatible con varias)
                title_clean = title_clean[:match.start()] + title_clean[match.end():]

        # 3. Si no encontro con patrones, buscar marcas sueltas
        if not compatibles:
            compatibles = self._search_loose_brands(title_upper)

        # 4. Extraer cilindrada si hay CC pero no marca detectada
        if not compatibles:
            for cc_pattern in CC_PATTERNS:
                cc_match = cc_pattern.search(title_upper)
                if cc_match:
                    cc = cc_match.group(1)
                    # Solo CC sin marca → no podemos asignar
                    # Dejar vacio es mejor que inventar "Universal"
                    logger.debug(f"CC {cc} encontrado pero sin marca: {title[:50]}")
                    break

        # Deduplicar
        return self._deduplicate(compatibles)

    def _clean_title(self, title: str) -> str:
        """Limpia el titulo para mejor matching."""
        # Remover caracteres especiales excepto / y -
        cleaned = re.sub(r'[^\w\s/\-.]', ' ', title)
        # Normalizar espacios
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

    def _search_loose_brands(self, title: str) -> List[Dict]:
        """Busca marcas sueltas cuando los patrones fallan."""
        compatibles = []

        # Lista de marcas principales a buscar
        main_brands = ["AKT", "BAJAJ", "HONDA", "YAMAHA", "SUZUKI",
                       "KAWASAKI", "PULSAR", "DISCOVER", "BWS"]

        for brand in main_brands:
            if brand in title:
                # Buscar CC cercano a la marca
                idx = title.index(brand)
                context = title[idx:min(idx+30, len(title))]

                cc = ""
                for cc_pattern in CC_PATTERNS:
                    cc_match = cc_pattern.search(context)
                    if cc_match:
                        cc = cc_match.group(1)
                        break

                # Mapear submarcas
                if brand == "PULSAR":
                    marca = "Bajaj"
                    modelo = f"Pulsar {cc}" if cc else "Pulsar"
                elif brand == "DISCOVER":
                    marca = "Bajaj"
                    modelo = f"Discover {cc}" if cc else "Discover"
                elif brand == "BWS":
                    marca = "Yamaha"
                    modelo = f"BWS {cc}" if cc else "BWS"
                else:
                    marca = MARCAS_MOTO.get(brand, brand.title())
                    modelo = cc if cc else ""

                compatibles.append({
                    "marca": marca,
                    "modelo": modelo,
                    "cc": cc
                })

        return compatibles

    def _parse_moto_string(self, moto_str: str) -> List[Dict]:
        """Parsea string de moto del CSV (columna dedicada)."""
        results = []
        # Separar por "/" o "," o " - "
        parts = re.split(r'[/,]|\s+-\s+', moto_str)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Buscar marca + modelo
            found = False
            for abbrev, marca in MARCAS_MOTO.items():
                if abbrev.upper() in part.upper():
                    modelo = part.upper().replace(abbrev.upper(), "").strip()
                    modelo = re.sub(r'^[\s.\-]+', '', modelo)  # Limpiar inicio

                    cc = ""
                    for cc_pattern in CC_PATTERNS:
                        cc_match = cc_pattern.search(modelo)
                        if cc_match:
                            cc = cc_match.group(1)
                            break

                    results.append({"marca": marca, "modelo": modelo, "cc": cc})
                    found = True
                    break

            # Si no encontro marca pero tiene numeros, puede ser solo modelo
            if not found and re.search(r'\d{2,4}', part):
                for cc_pattern in CC_PATTERNS:
                    cc_match = cc_pattern.search(part)
                    if cc_match:
                        results.append({
                            "marca": "",
                            "modelo": part,
                            "cc": cc_match.group(1)
                        })
                        break

        return results

    def _parse_modelo(self, marca: str, modelo_raw: str) -> List[Dict]:
        """Parsea string de modelo, manejando multiples modelos con /."""
        results = []

        if not modelo_raw:
            return results

        # Limpiar modelo
        modelo_raw = modelo_raw.strip()
        modelo_raw = re.sub(r'^[\s.\-]+', '', modelo_raw)

        # Separar por "/"
        parts = modelo_raw.split("/")

        base_modelo = ""
        last_cc = ""

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Extraer CC
            cc = ""
            for cc_pattern in CC_PATTERNS:
                cc_match = cc_pattern.search(part)
                if cc_match:
                    cc = cc_match.group(1)
                    break

            # Si no tiene CC explicito, buscar digitos
            if not cc:
                digits = re.search(r'(\d{2,4})', part)
                if digits:
                    cc = digits.group(1)

            # Si es solo un numero, es variacion del modelo base
            if part.isdigit() and base_modelo:
                results.append({
                    "marca": marca,
                    "modelo": f"{base_modelo} {part}",
                    "cc": part
                })
            else:
                # Limpiar parte
                modelo_clean = part
                # Remover prefijos de marca redundantes
                for abbrev in MARCAS_MOTO.keys():
                    if modelo_clean.upper().startswith(abbrev.upper()):
                        modelo_clean = modelo_clean[len(abbrev):].strip()
                        modelo_clean = re.sub(r'^[\s.\-]+', '', modelo_clean)
                        break

                if modelo_clean:
                    base_modelo = re.sub(r'\d+.*$', '', modelo_clean).strip() or modelo_clean
                    last_cc = cc
                    results.append({
                        "marca": marca,
                        "modelo": modelo_clean,
                        "cc": cc
                    })

        return results

    def _deduplicate(self, compatibles: List[Dict]) -> List[Dict]:
        """Elimina duplicados de la lista."""
        seen = set()
        unique = []
        for c in compatibles:
            # Normalizar para comparacion
            key = f"{c['marca'].upper()}-{c['modelo'].upper()}-{c.get('cc', '')}"
            if key not in seen and c['marca']:  # Solo agregar si tiene marca
                seen.add(key)
                unique.append(c)
        return unique

    def format_for_shopify(self, compatibles: List[Dict]) -> str:
        """Formatea compatibilidad para el campo de Shopify."""
        if not compatibles:
            return ""

        lines = []
        for c in compatibles:
            if c.get("cc"):
                lines.append(f"{c['marca']} {c['modelo']} {c['cc']}cc")
            elif c.get("modelo"):
                lines.append(f"{c['marca']} {c['modelo']}")
            else:
                lines.append(c['marca'])

        return ", ".join(lines)

    def format_for_tags(self, compatibles: List[Dict]) -> List[str]:
        """Genera tags de Shopify para compatibilidad."""
        tags = []
        for c in compatibles:
            marca_lower = c["marca"].lower()
            tags.append(marca_lower)

            if c.get("modelo"):
                modelo_clean = re.sub(r'[^\w]', '-', c['modelo'].lower())
                tags.append(f"{marca_lower}-{modelo_clean}")

            if c.get("cc"):
                tags.append(f"{c['cc']}cc")

        return list(set(tags))

    def format_for_html(self, compatibles: List[Dict]) -> str:
        """Formatea compatibilidad como HTML para ficha 360."""
        if not compatibles:
            return "<p>Consultar compatibilidad</p>"

        html = "<ul class='compatibilidad-list'>\n"
        for c in compatibles:
            line = f"  <li><strong>{c['marca']}</strong>"
            if c.get("modelo"):
                line += f" {c['modelo']}"
            if c.get("cc"):
                line += f" ({c['cc']}cc)"
            line += "</li>\n"
            html += line
        html += "</ul>"

        return html


# ─────────────────────────────────────────────────────────
# TEST STANDALONE
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = CompatibilityParser()

    test_cases = [
        "Arbol de Levas AKT 125",
        "Banda Freno B. Pulsar200NS",
        "Cadena 428 Honda CBF 150",
        "Kit Arrastre Yamaha BWS 125",
        "Piston AK. AKT110",
        "Clutch B. Pulsar200NS",
        "Bobina H. C100/BIZ",
        "Arbol De Levas Ak. Akt125/150/Sigma125-2A",
        "Filtro de aceite",  # Sin marca → debe quedar vacio
        "PIÑON PRIMARIO BAJAJ BOXER CT 100 - PLATINO 100",
        "Carburador Suzuki GN 125",
        "Velocimetro Yamaha FZ 150",
        "Empaque Motor Completo AKT NKD 125",
    ]

    print("=" * 60)
    print("TEST: CompatibilityParser V22.3")
    print("=" * 60)

    for title in test_cases:
        result = parser.parse(title)
        formatted = parser.format_for_shopify(result)
        tags = parser.format_for_tags(result)

        print(f"\nInput:  {title}")
        print(f"Result: {result}")
        print(f"Shopify: {formatted}")
        print(f"Tags: {tags}")

    # Verificaciones
    print("\n" + "=" * 60)
    print("VERIFICACIONES")
    print("=" * 60)

    # Debe extraer AKT
    assert len(parser.parse("Arbol de Levas AKT 125")) > 0, "Fallo AKT 125"
    print("OK: AKT 125 detectado")

    # Debe extraer Bajaj de abreviatura B.
    result = parser.parse("Banda Freno B. Pulsar200NS")
    assert any(c["marca"] == "Bajaj" for c in result), "Fallo B. → Bajaj"
    print("OK: B. → Bajaj detectado")

    # Debe extraer 2 motos de /
    result = parser.parse("Bobina H. C100/BIZ")
    assert len(result) >= 2, f"Fallo Honda C100/BIZ: solo {len(result)} encontrados"
    print("OK: Honda C100/BIZ → 2 motos")

    # Sin marca → vacio, NO "Universal"
    result = parser.parse("Filtro de aceite")
    assert len(result) == 0, "Fallo: no debe inventar Universal"
    print("OK: Sin marca → vacio (no Universal)")

    print("\n✅ CompatibilityParser: TODOS LOS TESTS OK")
