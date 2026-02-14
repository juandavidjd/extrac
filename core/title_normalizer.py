#!/usr/bin/env python3
"""
Normalizador de títulos profesionales para productos
"""
import re

# Patrones de limpieza
NOISE_PATTERNS = [
    r"^\d+\s*[-_]\s*",  # Números al inicio
    r"\s*[-_]\s*\d+$",  # Números al final
    r"\bREF\b\.?\s*",   # REF
    r"\bCOD\b\.?\s*",   # COD
    r"\*+",             # Asteriscos
    r"\.{2,}",          # Puntos múltiples
]

# Mapeo de abreviaciones
ABBR_MAP = {
    "KIT": "Kit",
    "JGO": "Juego",
    "JUEGO": "Juego", 
    "PAR": "Par",
    "UNID": "Unidad",
    "PZA": "Pieza",
    "PZAS": "Piezas",
}

# Sistemas de moto
SISTEMAS = {
    "motor": ["motor", "piston", "cilindro", "biela", "ciguenal", "valvula", "arbol", "empaque", "junta"],
    "transmision": ["cadena", "piñon", "sprocket", "kit transmision", "corona", "tensor"],
    "frenos": ["freno", "pastilla", "disco", "banda", "caliper", "bomba freno"],
    "suspension": ["amortiguador", "suspension", "horquilla", "tijera", "direccion"],
    "electrico": ["bobina", "cdi", "regulador", "bateria", "luz", "faro", "stop", "direccional"],
    "carroceria": ["plastico", "carenaje", "guardabarro", "tanque", "silla", "manubrio"],
    "lubricantes": ["aceite", "lubricante", "grasa", "filtro aceite"],
}

def detect_sistema(title):
    """Detectar sistema de moto del producto"""
    title_lower = title.lower()
    for sistema, keywords in SISTEMAS.items():
        if any(kw in title_lower for kw in keywords):
            return sistema
    return "general"

def normalize_title(raw_title, marca=None, modelo=None):
    """
    Normalizar título crudo a formato profesional
    
    MAL: "110 LIBERO YAMAHA 14T/44T KETOZ"
    BIEN: "Kit Cadena Transmisión 14T/44T - Yamaha Libero 110"
    """
    if not raw_title:
        return ""
    
    title = raw_title.strip()
    
    # Limpiar ruido
    for pattern in NOISE_PATTERNS:
        title = re.sub(pattern, " ", title, flags=re.IGNORECASE)
    
    # Normalizar espacios
    title = " ".join(title.split())
    
    # Capitalizar correctamente
    words = title.split()
    normalized_words = []
    
    for word in words:
        word_upper = word.upper()
        
        # Mantener códigos técnicos
        if re.match(r"^\d+[A-Z]+$|^[A-Z]+\d+", word_upper):
            normalized_words.append(word_upper)
        # Reemplazar abreviaciones
        elif word_upper in ABBR_MAP:
            normalized_words.append(ABBR_MAP[word_upper])
        # Capitalizar primera letra
        else:
            normalized_words.append(word.capitalize())
    
    title = " ".join(normalized_words)
    
    # Agregar marca/modelo si no están
    if marca and marca.lower() not in title.lower():
        title = f"{title} - {marca}"
    if modelo and modelo.lower() not in title.lower():
        title = f"{title} {modelo}"
    
    return title

def extract_specs(title):
    """Extraer especificaciones técnicas del título"""
    specs = {}
    
    # Tamaños de diente
    teeth_match = re.search(r"(\d+)T[/x](\d+)T", title, re.IGNORECASE)
    if teeth_match:
        specs["piñon"] = f"{teeth_match.group(1)}T"
        specs["corona"] = f"{teeth_match.group(2)}T"
    
    # Cilindrada
    cc_match = re.search(r"(\d{2,4})\s*(?:CC|C\.C\.|cm3)?", title, re.IGNORECASE)
    if cc_match:
        cc = int(cc_match.group(1))
        if 50 <= cc <= 1000:
            specs["cilindrada"] = f"{cc}cc"
    
    # Diámetros
    diam_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm|MM)", title)
    if diam_match:
        specs["diametro"] = f"{diam_match.group(1)}mm"
    
    return specs

if __name__ == "__main__":
    # Test
    tests = [
        "110 LIBERO YAMAHA 14T/44T KETOZ",
        "KIT CADENA 428H X 120 BWS",
        "PASTILLA FRENO DELANTERA AKT 125",
        "PISTON 0.25 BAJAJ PULSAR 200",
    ]
    for t in tests:
        print(f"IN:  {t}")
        print(f"OUT: {normalize_title(t)}")
        print(f"SIS: {detect_sistema(t)}")
        print()
