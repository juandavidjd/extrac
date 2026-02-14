#!/usr/bin/env python3
"""
ODI Semantic Normalizer v2.0
Normaliza titulos de repuestos de moto a formato profesional
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict

PIEZAS = {
    "cadena": "Cadena de Transmision",
    "kit cadena": "Kit de Cadena",
    "pinon": "Pinon",
    "corona": "Corona",
    "sprocket": "Sprocket",
    "tensor": "Tensor de Cadena",
    "piston": "Piston",
    "anillo": "Anillos de Piston",
    "biela": "Biela",
    "ciguenal": "Ciguenal",
    "arbol": "Arbol de Levas",
    "valvula": "Valvula",
    "empaque": "Empaque",
    "junta": "Junta",
    "culata": "Culata",
    "cilindro": "Cilindro",
    "camisa": "Camisa de Cilindro",
    "pastilla": "Pastillas de Freno",
    "disco": "Disco de Freno",
    "banda": "Bandas de Freno",
    "caliper": "Caliper",
    "bomba freno": "Bomba de Freno",
    "mordaza": "Mordaza de Freno",
    "amortiguador": "Amortiguador",
    "horquilla": "Horquilla",
    "tijera": "Tijera",
    "balinera": "Balinera",
    "rodamiento": "Rodamiento",
    "retenedor": "Retenedor",
    "bobina": "Bobina",
    "cdi": "CDI",
    "regulador": "Regulador de Voltaje",
    "bateria": "Bateria",
    "faro": "Faro",
    "stop": "Stop",
    "direccional": "Direccional",
    "flasher": "Flasher",
    "aceite": "Aceite",
    "filtro": "Filtro",
    "tapa aceite": "Tapa de Aceite",
    "tanque": "Tanque",
    "silla": "Sillin",
    "guardabarro": "Guardabarro",
    "carenaje": "Carenaje",
    "manubrio": "Manubrio",
    "kit": "Kit",
    "juego": "Juego",
    "cable": "Cable",
    "manguera": "Manguera",
    "tornillo": "Tornillo",
    "tuerca": "Tuerca",
    "rache": "Rache",
    "manigueta": "Manigueta",
    "pedal": "Pedal",
    "palanca": "Palanca",
    "bendix": "Bendix",
    "clutch": "Clutch",
    "embrague": "Embrague",
}

MARCAS = [
    "YAMAHA", "HONDA", "SUZUKI", "KAWASAKI", "BAJAJ", "TVS", "HERO",
    "AKT", "AUTECO", "PULSAR", "BOXER", "DISCOVER", "PLATINO",
    "BWS", "FZ", "YBR", "LIBERO", "CRYPTON", "DT", "RX", "XTZ",
    "CBF", "CB", "CG", "TITAN", "NXR", "BROS", "XR", "CRF",
    "GN", "GS", "GIXXER", "HAYATE", "AX", "BEST", "VIVA",
    "APACHE", "SPORT", "FLAME", "STAR", "SPLENDOR",
    "CARGUERO", "TRIAX", "SIGMA", "ECO", "NKDR", "ACTIVE", "SPECIAL",
    "TORITO", "MOTOCARRO", "SG", "JC", "RE", "KYMCO", "SYM",
]

@dataclass
class FitmentData:
    pieza: str = ""
    pieza_original: str = ""
    especificacion: str = ""
    marca: str = ""
    modelo: str = ""
    cilindrada: str = ""
    posicion: str = ""
    extras: List[str] = field(default_factory=list)

class SemanticNormalizer:
    def __init__(self):
        self.piezas = PIEZAS
        self.marcas = [m.upper() for m in MARCAS]
    
    def parse(self, raw_title: str) -> FitmentData:
        if not raw_title:
            return FitmentData()
        
        title = raw_title.upper().strip()
        title = re.sub(r"[_\-]+", " ", title)
        title = " ".join(title.split())
        
        data = FitmentData(pieza_original=raw_title)
        
        title_lower = title.lower()
        for keyword, nombre in sorted(self.piezas.items(), key=lambda x: -len(x[0])):
            if keyword in title_lower:
                data.pieza = nombre
                break
        
        for marca in self.marcas:
            if marca in title or f" {marca} " in f" {title} ":
                data.marca = marca.title()
                break
        
        cc_match = re.search(r"(\d{2,3})", title)
        if cc_match:
            cc = cc_match.group(1)
            if cc in ["100", "110", "115", "125", "135", "150", "160", "180", "200", "220", "250"]:
                data.cilindrada = cc
        
        teeth = re.search(r"(\d+)T[/xX](\d+)T", title)
        if teeth:
            data.especificacion = f"{teeth.group(1)}T/{teeth.group(2)}T"
        
        chain = re.search(r"(\d{3})[Hh]?\s*[xX]\s*(\d{2,3})", title)
        if chain:
            data.especificacion = f"{chain.group(1)} x {chain.group(2)}"
        
        piston = re.search(r"(STD|0\.25|0\.50|0\.75|1\.00|STANDARD)", title, re.IGNORECASE)
        if piston:
            data.especificacion = piston.group(1).upper()
        
        if any(x in title_lower for x in ["delant", "front"]):
            data.posicion = "Delantero"
        elif any(x in title_lower for x in ["tras", "rear", "posterior"]):
            data.posicion = "Trasero"
        
        return data
    
    def normalize(self, raw_title: str) -> str:
        data = self.parse(raw_title)
        parts = []
        
        if data.pieza:
            parts.append(data.pieza)
        else:
            clean = re.sub(r"^\d+\s+", "", raw_title.strip())
            clean = " ".join(w.capitalize() for w in clean.split()[:4])
            parts.append(clean)
        
        if data.especificacion:
            parts.append(data.especificacion)
        
        if data.posicion:
            parts.append(data.posicion)
        
        title = " ".join(parts)
        
        modelo_parts = []
        if data.marca:
            modelo_parts.append(data.marca)
        if data.cilindrada:
            modelo_parts.append(data.cilindrada)
        
        if modelo_parts:
            title = f"{title} - {' '.join(modelo_parts)}"
        
        return title

class FitmentParser:
    def __init__(self):
        self.normalizer = SemanticNormalizer()
    
    def parse(self, title: str) -> FitmentData:
        return self.normalizer.parse(title)
    
    def normalize(self, title: str) -> str:
        return self.normalizer.normalize(title)

_normalizer = None
def get_normalizer():
    global _normalizer
    if _normalizer is None:
        _normalizer = SemanticNormalizer()
    return _normalizer

def normalize_title(raw_title: str) -> str:
    return get_normalizer().normalize(raw_title)

if __name__ == "__main__":
    tests = [
        "110 LIBERO YAMAHA 14T/44T KETOZ",
        "ARBOL DE LEVAS AK AKT110",
        "PASTILLA FRENO DELANTERA PULSAR 200",
        "0 50 Akt Carguero",
        "Balinera Eje Clutch S. AX100/AX115/AK100/JC100 30b60",
    ]
    n = SemanticNormalizer()
    for t in tests:
        print(f"IN:  {t}")
        print(f"OUT: {n.normalize(t)}")
        print()
