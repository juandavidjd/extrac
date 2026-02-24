#!/usr/bin/env python3
"""
ChromaDB Enrichment Query Module V19.1
Uses native chromadb Python client instead of REST API.
"""
import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CATEGORY_TEMPLATES = {
    "piston rings": {"material": "Acero de alta resistencia", "spec": "Anillos de piston con acabado cromado"},
    "piston ring": {"material": "Acero de alta resistencia", "spec": "Anillo de piston con acabado cromado"},
    "bearing": {"material": "Acero al cromo", "spec": "Rodamiento sellado de alta precision"},
    "gasket": {"material": "Material compuesto multicapa", "spec": "Empaque de alta resistencia termica"},
    "brake pad": {"material": "Compuesto semimetalico", "spec": "Pastillas con alto coeficiente de friccion"},
    "brake pads": {"material": "Compuesto semimetalico", "spec": "Pastillas con alto coeficiente de friccion"},
    "brake cable": {"material": "Cable de acero trenzado con funda", "spec": "Guaya de freno con ajuste de tension"},
    "brake disc": {"material": "Acero inoxidable", "spec": "Disco de freno ventilado"},
    "brake": {"material": "Compuesto semimetalico", "spec": "Sistema de frenado de alta eficiencia"},
    "oil filter": {"material": "Papel filtro de alta eficiencia", "spec": "Filtro con valvula anti-retorno"},
    "air filter": {"material": "Espuma/papel filtro multicapa", "spec": "Filtro de alto flujo"},
    "clutch": {"material": "Fibra de friccion reforzada", "spec": "Discos de clutch con ranuras de ventilacion"},
    "clutch cable": {"material": "Cable de acero trenzado", "spec": "Guaya de clutch con ajuste"},
    "motorcycle chain": {"material": "Acero aleado con tratamiento termico", "spec": "Cadena con O-rings sellados"},
    "sprocket": {"material": "Acero templado", "spec": "Dientes de perfil optimizado"},
    "rear sprocket": {"material": "Acero templado", "spec": "Corona con dientes de perfil optimizado"},
    "shock absorber": {"material": "Acero con recubrimiento anticorrosivo", "spec": "Amortiguador con ajuste de precarga"},
    "spark plug": {"material": "Electrodo de niquel/iridio", "spec": "Bujia resistente a altas temperaturas"},
    "control cable": {"material": "Cable de acero trenzado con funda", "spec": "Guaya con terminales de fabrica"},
    "throttle cable": {"material": "Cable de acero trenzado", "spec": "Guaya de acelerador con ajuste"},
    "speedometer cable": {"material": "Cable de acero flexible", "spec": "Guaya de velocimetro con conexion estandar"},
    "light bulb": {"material": "Vidrio resistente a vibraciones", "spec": "Bombillo de alta luminosidad"},
    "LED bulb": {"material": "LEDs de alta eficiencia", "spec": "Bombillo LED de bajo consumo"},
    "cylinder head": {"material": "Aluminio fundido", "spec": "Culata con canales de refrigeracion"},
    "cylinder": {"material": "Aluminio con camisa de hierro", "spec": "Cilindro con acabado de precision"},
    "axle shaft": {"material": "Acero templado", "spec": "Eje de alta resistencia"},
    "rear axle": {"material": "Acero templado", "spec": "Eje trasero de alta resistencia"},
    "front axle": {"material": "Acero templado", "spec": "Eje delantero de alta resistencia"},
    "handlebar switch assembly": {"material": "Plastico ABS y contactos de cobre", "spec": "Comando con interruptores integrados"},
    "steering bearing race": {"material": "Acero al cromo", "spec": "Cuna de direccion de alta precision"},
    "clutch bell housing": {"material": "Aluminio fundido", "spec": "Campana de clutch con ventilacion"},
    "clutch bell": {"material": "Aluminio fundido", "spec": "Campana de clutch con ventilacion"},
    "timing chain": {"material": "Acero aleado", "spec": "Cadenilla de distribucion silenciosa"},
    "rubber bushing": {"material": "Caucho vulcanizado", "spec": "Caucho de alta durabilidad"},
    "footpeg rubber": {"material": "Caucho antideslizante", "spec": "Caucho de reposapie ergonomico"},
    "handlebar grip": {"material": "Caucho ergonomico", "spec": "Grip de manubrio antideslizante"},
    "carbon brush": {"material": "Carbon grafito", "spec": "Escobilla de motor de arranque"},
    "wiring harness": {"material": "Cableado con aislamiento PVC", "spec": "Instalacion electrica completa"},
    "gearbox housing": {"material": "Aluminio fundido", "spec": "Caja de velocidades con sellos"},
    "connecting rod": {"material": "Acero forjado", "spec": "Biela de alta resistencia"},
    "connecting rod kit": {"material": "Acero forjado", "spec": "Kit de biela con rodamientos"},
    "CDI unit": {"material": "Circuito electronico encapsulado", "spec": "CDI con curva de encendido optimizada"},
    "voltage regulator": {"material": "Componentes electronicos", "spec": "Regulador rectificador de voltaje"},
    "ignition coil": {"material": "Bobinado de cobre", "spec": "Bobina de encendido de alto voltaje"},
    "stator": {"material": "Bobinado de cobre esmaltado", "spec": "Estator generador de corriente"},
    "carburetor": {"material": "Aluminio fundido", "spec": "Carburador con ajuste de mezcla"},
    "pump": {"material": "Aluminio y plastico reforzado", "spec": "Bomba con sellos de alta duracion"},
    "oil seal": {"material": "Caucho nitrilico", "spec": "Retenedor con labio de sello"},
    "spring": {"material": "Acero al carbono", "spec": "Resorte con tension calibrada"},
    "valve": {"material": "Acero inoxidable", "spec": "Valvula con asiento rectificado"},
    "rocker arm": {"material": "Acero forjado", "spec": "Balancin con rodillo"},
    "camshaft": {"material": "Acero templado", "spec": "Arbol de levas con perfil optimizado"},
    "crankshaft": {"material": "Acero forjado", "spec": "Ciguenal balanceado"},
    "headlight": {"material": "Plastico y vidrio", "spec": "Faro con reflector parabolico"},
    "tail light": {"material": "Plastico y LEDs", "spec": "Stop con iluminacion LED"},
    "turn signal": {"material": "Plastico y bombillo", "spec": "Direccional con luz ambar"},
    "fender": {"material": "Plastico ABS", "spec": "Guardabarro resistente a impactos"},
    "fairing": {"material": "Plastico ABS", "spec": "Carenaje aerodinamico"},
    "seat": {"material": "Espuma y vinilo", "spec": "Sillin ergonomico con base reforzada"},
    "fuel tank": {"material": "Metal con recubrimiento interno", "spec": "Tanque con proteccion anticorrosion"},
    "handlebar": {"material": "Aluminio o acero", "spec": "Manubrio con geometria ergonomica"},
    "mirror": {"material": "Plastico y vidrio", "spec": "Espejo con amplio campo de vision"},
    "lever": {"material": "Aluminio fundido", "spec": "Palanca con ajuste de distancia"},
    "handlebar lever": {"material": "Aluminio fundido", "spec": "Manigueta con ajuste de distancia"},
    "footpeg": {"material": "Aluminio o acero", "spec": "Estribo antideslizante"},
    "side stand": {"material": "Acero", "spec": "Pata lateral con resorte"},
    "center stand": {"material": "Acero", "spec": "Caballete central reforzado"},
    "brake caliper": {"material": "Aluminio fundido", "spec": "Mordaza con pistones de freno"},
    "complete gasket kit": {"material": "Materiales compuestos", "spec": "Kit completo de empaques"},
    "gasket kit": {"material": "Materiales compuestos", "spec": "Kit de empaques seleccionados"},
    "piston kit": {"material": "Aluminio forjado", "spec": "Kit de piston con anillos"},
    "cylinder sleeve liner": {"material": "Hierro fundido", "spec": "Camisa de cilindro rectificable"},
    "starter bendix": {"material": "Acero templado", "spec": "Bendix de arranque con engrane helicoidal"},
    "cover cap": {"material": "Plastico ABS o aluminio", "spec": "Tapa con ajuste preciso"},
    "side cover": {"material": "Plastico ABS", "spec": "Tapa lateral con acabado OEM"},
}

DEFAULT_TEMPLATE = {"material": "Materiales de alta calidad", "spec": "Repuesto con especificaciones OEM"}


@dataclass
class EnrichmentResult:
    found: bool
    source: str
    material: Optional[str] = None
    dimensions: Optional[str] = None
    compatibility: Optional[str] = None
    specifications: Optional[str] = None
    raw_context: Optional[str] = None
    score: float = 0.0


def normalize_title_for_query(title: str) -> str:
    title_clean = title.lower()
    title_clean = re.sub(r"\s+(yb|dfg|gf|xatag|oem|generico)\s*$", "", title_clean, flags=re.IGNORECASE)
    title_clean = re.sub(r"\s*\+\s*\d+\s*$", "", title_clean)
    title_clean = re.sub(r"\s*(std|standard)\s*$", "", title_clean, flags=re.IGNORECASE)
    title_clean = re.sub(r"[^\w\s]", " ", title_clean)
    title_clean = " ".join(title_clean.split())
    return title_clean


def extract_info_from_chunks(chunks: List[str]) -> Dict[str, Optional[str]]:
    combined_text = " ".join(chunks)
    result = {"material": None, "dimensions": None, "compatibility": None, "specifications": None}

    material_match = re.search(r"(?:material|fabricado en|hecho de)[:\s]+([^.;,\n]{5,50})", combined_text, re.IGNORECASE)
    if material_match:
        result["material"] = material_match.group(1).strip()

    dim_match = re.search(r"(?:dimension|medida|diametro|largo|ancho)[:\s]+([^.;,\n]{5,40})", combined_text, re.IGNORECASE)
    if dim_match:
        result["dimensions"] = dim_match.group(1).strip()

    compat_match = re.search(r"(?:compatible con|aplica para|fitment)[:\s]+([^.;\n]{10,100})", combined_text, re.IGNORECASE)
    if compat_match:
        result["compatibility"] = compat_match.group(1).strip()

    spec_match = re.search(r"(?:especificacion|caracteristica|torque|presion)[:\s]+([^.;\n]{5,80})", combined_text, re.IGNORECASE)
    if spec_match:
        result["specifications"] = spec_match.group(1).strip()

    return result


async def query_chromadb_for_enrichment(
    title: str,
    product_type: str,
    similarity_threshold: float = 0.7,
    max_results: int = 3
) -> EnrichmentResult:
    """Query ChromaDB using native Python client."""
    query_text = normalize_title_for_query(title)

    try:
        import chromadb
        client = chromadb.HttpClient(host="localhost", port=8000)

        all_chunks = []

        for collection_name in ["odi_ind_motos"]:
            try:
                collection = client.get_collection(collection_name)
                results = collection.query(
                    query_texts=[query_text],
                    n_results=max_results,
                    include=["documents", "distances"]
                )

                if results and results.get("documents") and results["documents"][0]:
                    documents = results["documents"][0]
                    distances = results.get("distances", [[]])[0]

                    for doc, dist in zip(documents, distances):
                        similarity = max(0, 1 - (dist / 2))
                        if similarity >= similarity_threshold:
                            all_chunks.append({"doc": doc, "similarity": similarity})
            except Exception as e:
                logger.debug(f"Collection {collection_name} query failed: {e}")
                continue

        if all_chunks:
            all_chunks.sort(key=lambda x: x["similarity"], reverse=True)
            top_chunks = all_chunks[:max_results]
            avg_score = sum(c["similarity"] for c in top_chunks) / len(top_chunks)

            docs = [c["doc"] for c in top_chunks]
            extracted = extract_info_from_chunks(docs)

            return EnrichmentResult(
                found=True,
                source="chromadb",
                material=extracted["material"],
                dimensions=extracted["dimensions"],
                compatibility=extracted["compatibility"],
                specifications=extracted["specifications"],
                raw_context="\n".join([d[:200] for d in docs]),
                score=avg_score
            )

    except Exception as e:
        logger.debug(f"ChromaDB query error: {e}")

    return get_category_fallback(product_type)


def get_category_fallback(product_type: str) -> EnrichmentResult:
    template = CATEGORY_TEMPLATES.get(product_type)

    if not template:
        for key, val in CATEGORY_TEMPLATES.items():
            if key in product_type or product_type in key:
                template = val
                break

    if not template:
        template = DEFAULT_TEMPLATE
        source = "default"
    else:
        source = "category_template"

    return EnrichmentResult(
        found=False,
        source=source,
        material=template.get("material"),
        specifications=template.get("spec"),
        score=0.0
    )


def query_chromadb_sync(title: str, product_type: str) -> EnrichmentResult:
    import asyncio
    try:
        return asyncio.get_event_loop().run_until_complete(
            query_chromadb_for_enrichment(title, product_type)
        )
    except Exception:
        return get_category_fallback(product_type)
