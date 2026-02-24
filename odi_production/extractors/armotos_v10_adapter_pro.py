#!/usr/bin/env python3
"""ARMOTOS V10 Adapter PRO - Ficha 360° con 7 secciones profesionales"""

import os, sys, json, re, time, base64, logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

sys.path.insert(0, "/opt/odi")
sys.path.insert(0, "/opt/odi/core")

from dotenv import load_dotenv
load_dotenv("/opt/odi/.env")

import requests
import chromadb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stdout)
logger = logging.getLogger("v10_adapter_pro")

@dataclass
class NormalizedProduct:
    sku: str
    title: str
    description: str = ""
    price: float = 0.0
    vendor: str = "ARMOTOS"
    product_type: str = "Repuesto Moto"
    tags: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    status: str = "active"
    ficha_360: str = ""
    raw_data: Dict = field(default_factory=dict)
    categoria: str = ""
    compatibilidad_list: List[str] = field(default_factory=list)
    colores_list: List[str] = field(default_factory=list)

class V10AdapterPro:
    def __init__(self, store: str = "ARMOTOS"):
        self.store = store
        self.data_dir = Path(f"/opt/odi/data/{store}")
        self.json_path = self.data_dir / "json" / "all_products.json"
        self.images_dir = self.data_dir / "images"
        self.products = []
        self.shop = os.getenv(f"{store}_SHOP")
        self.token = os.getenv(f"{store}_TOKEN")
        self.api_version = "2025-07"
        self.chroma_client = chromadb.HttpClient(host="localhost", port=8000)
        self.collection_name = "odi_ind_motos"

        # Categorias por palabra clave
        self.categorias = {
            "cadena": "Transmision", "corona": "Transmision", "pinon": "Transmision", "kit": "Transmision",
            "llanta": "Llantas y Neumaticos", "neumatico": "Llantas y Neumaticos", "camara": "Llantas y Neumaticos",
            "amortiguador": "Suspension", "suspension": "Suspension", "tijera": "Suspension",
            "freno": "Frenos", "pastilla": "Frenos", "disco": "Frenos", "mordaza": "Frenos",
            "filtro": "Filtros", "aceite": "Lubricantes",
            "bujia": "Encendido", "bobina": "Encendido", "cdi": "Encendido",
            "bateria": "Electrico", "regulador": "Electrico", "relay": "Electrico",
            "faro": "Iluminacion", "direccional": "Iluminacion", "stop": "Iluminacion", "bombillo": "Iluminacion",
            "manubrio": "Manubrio y Control", "manilar": "Manubrio y Control", "espejo": "Manubrio y Control",
            "palanca": "Manubrio y Control", "puño": "Manubrio y Control", "acelerador": "Manubrio y Control",
            "escape": "Escape", "silenciador": "Escape", "exosto": "Escape",
            "clutch": "Embrague", "embrague": "Embrague", "discos": "Embrague",
            "pedal": "Pedales y Estribos", "estribo": "Pedales y Estribos", "pata": "Pedales y Estribos",
            "tornillo": "Tornilleria", "tuerca": "Tornilleria", "perno": "Tornilleria",
            "rodamiento": "Rodamientos", "balinera": "Rodamientos",
            "retenedor": "Empaques y Sellos", "empaque": "Empaques y Sellos", "junta": "Empaques y Sellos", "oring": "Empaques y Sellos",
            "piston": "Motor", "biela": "Motor", "cigueñal": "Motor", "valvula": "Motor", "arbol": "Motor",
            "guante": "Indumentaria", "casco": "Indumentaria", "chaqueta": "Indumentaria", "chaleco": "Indumentaria",
            "protector": "Proteccion", "slider": "Proteccion",
            "banco": "Herramientas", "silla": "Herramientas", "gato": "Herramientas", "llave": "Herramientas",
            "carenaje": "Carroceria", "guardabarro": "Carroceria", "tapa": "Carroceria", "cubierta": "Carroceria",
            "tanque": "Combustible", "grifo": "Combustible", "bomba": "Combustible",
            "asiento": "Asientos", "forro": "Asientos",
            "cable": "Cables", "guaya": "Cables",
            "acople": "Acoples y Soportes", "soporte": "Acoples y Soportes", "base": "Acoples y Soportes",
        }

        # Marcas de motos conocidas
        self.marcas_moto = ["YAMAHA", "HONDA", "SUZUKI", "BAJAJ", "TVS", "KAWASAKI", "KTM",
                           "BMW", "DUCATI", "PULSAR", "AKT", "AUTECO", "HERO", "KYMCO",
                           "DISCOVER", "BOXER", "PLATINO", "APACHE", "FZ", "YBR", "XTZ",
                           "GIXXER", "NMAX", "BWIS", "BWS", "CRYPTON", "LIBERO", "RX", "DT",
                           "NKD", "CR", "XR", "CRF", "CBR", "NINJA", "R15", "MT", "DUKE"]

        # Beneficios específicos por categoría
        self.beneficios = {
            "Suspension": [
                "Absorción óptima de impactos en terreno irregular",
                "Caucho de alta densidad resistente al desgaste",
                "Mejora la estabilidad y confort de manejo",
                "Instalación directa sin modificaciones"
            ],
            "Transmision": [
                "Acero de alta resistencia para mayor durabilidad",
                "Transmisión de potencia eficiente sin pérdidas",
                "Reducción de ruido y vibración en operación",
                "Compatible con piñón y corona originales"
            ],
            "Frenos": [
                "Material de fricción de alto rendimiento",
                "Frenado progresivo y seguro en cualquier condición",
                "Resistente a altas temperaturas sin pérdida de eficacia",
                "Compatible con tambor/disco de freno original"
            ],
            "Iluminacion": [
                "Tecnología LED de alta luminosidad y bajo consumo",
                "Mayor visibilidad para seguridad vial día y noche",
                "Resistente al agua, polvo y vibraciones",
                "Larga vida útil superior a bombillos convencionales"
            ],
            "Manubrio y Control": [
                "Ergonomía optimizada para mayor confort de conducción",
                "Material antideslizante para agarre seguro",
                "Absorción de vibraciones del motor y terreno",
                "Fácil instalación en manubrio estándar"
            ],
            "Electrico": [
                "Componentes electrónicos de grado automotriz",
                "Protección contra sobrecarga y cortocircuito",
                "Estabilidad de voltaje para óptimo rendimiento",
                "Compatible con sistema eléctrico original"
            ],
            "Carroceria": [
                "Ajuste preciso a medidas originales del fabricante",
                "Material resistente a impactos y rayos UV",
                "Acabado de fábrica listo para instalar",
                "Protección efectiva de componentes internos"
            ],
            "Herramientas": [
                "Diseño profesional para uso en taller mecánico",
                "Construcción robusta en acero/aluminio de alta resistencia",
                "Ergonomía pensada para trabajo prolongado",
                "Facilita el mantenimiento y reparación de motos"
            ],
            "Indumentaria": [
                "Materiales de protección certificados",
                "Diseño ergonómico para comodidad del motociclista",
                "Ventilación adecuada para clima tropical",
                "Elementos reflectivos para visibilidad nocturna"
            ],
            "Filtros": [
                "Medio filtrante de alta eficiencia",
                "Retención óptima de partículas contaminantes",
                "Flujo de aire/aceite sin restricciones",
                "Prolonga la vida útil del motor"
            ],
            "Escape": [
                "Acero inoxidable resistente a corrosión",
                "Diseño que optimiza el flujo de gases",
                "Reducción de ruido dentro de normas ambientales",
                "Mejora respuesta del motor en aceleración"
            ],
            "Embrague": [
                "Discos de fricción de alto coeficiente",
                "Transmisión suave de potencia sin patinaje",
                "Resistente al calor generado por fricción",
                "Tacto preciso en la palanca de embrague"
            ],
            "Combustible": [
                "Sellado hermético anti-fugas garantizado",
                "Material resistente a combustibles y aditivos",
                "Protección contra corrosión interna",
                "Capacidad y forma según especificaciones OEM"
            ],
            "Cables": [
                "Cable de acero trenzado de alta resistencia",
                "Funda protectora contra humedad y fricción",
                "Recorrido suave sin atascos ni rigidez",
                "Longitud y terminales según especificación original"
            ],
            "Acoples y Soportes": [
                "Fabricado en material de alta resistencia mecánica",
                "Dimensiones exactas para ajuste perfecto",
                "Soporta vibraciones y esfuerzos de operación",
                "Instalación directa sin adaptaciones"
            ],
            "Kits": [
                "Conjunto completo con todos los componentes necesarios",
                "Piezas seleccionadas para compatibilidad perfecta",
                "Ahorro vs compra de piezas individuales",
                "Instrucciones de instalación incluidas"
            ],
            "default": [
                "Repuesto de calidad para su motocicleta",
                "Fabricado bajo estándares industriales",
                "Compatible con modelos especificados",
                "Disponibilidad inmediata para envío"
            ]
        }

        # Descripciones específicas por categoría
        self.descripciones = {
            "Suspension": "Componente de suspensión diseñado para absorber impactos y mejorar el confort de conducción.",
            "Transmision": "Pieza de transmisión de potencia fabricada en acero tratado para máxima durabilidad.",
            "Frenos": "Componente del sistema de frenado con material de fricción de alto rendimiento para seguridad óptima.",
            "Iluminacion": "Sistema de iluminación de alta visibilidad para mayor seguridad en carretera.",
            "Manubrio y Control": "Accesorio de control ergonómico para mayor confort y precisión de manejo.",
            "Electrico": "Componente eléctrico de grado automotriz para funcionamiento confiable.",
            "Carroceria": "Pieza de carrocería con ajuste preciso y acabado de calidad OEM.",
            "Herramientas": "Herramienta profesional diseñada para trabajo en taller de motos.",
            "Indumentaria": "Equipamiento de protección para el motociclista con materiales certificados.",
            "Filtros": "Elemento filtrante de alta eficiencia para protección del motor.",
            "Escape": "Componente de escape en acero resistente para óptimo flujo de gases.",
            "Embrague": "Pieza de embrague con material de fricción de alto coeficiente.",
            "Combustible": "Componente del sistema de combustible con sellado garantizado.",
            "Cables": "Cable de control con recorrido suave y alta resistencia a la tracción.",
            "Acoples y Soportes": "Soporte de fijación con dimensiones exactas para ajuste perfecto.",
            "Kits": "Kit completo con todas las piezas necesarias para la instalación.",
            "default": "Repuesto de calidad fabricado bajo estándares industriales."
        }

    def load_v10_data(self):
        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def clean_price(self, price_str):
        if not price_str or price_str == "N/A": return 0.0
        price_str = str(price_str)
        price_str = re.sub(r"[^\d.,]", "", price_str)
        if "." in price_str and "," not in price_str:
            parts = price_str.split(".")
            if len(parts) == 2 and len(parts[1]) == 3:
                price_str = price_str.replace(".", "")
        price_str = price_str.replace(",", ".")
        try:
            price = float(price_str)
            if 0 < price < 100: price = price * 1000
            return price
        except: return 0.0

    def find_image(self, codigo):
        for ext in [".png", ".jpg"]:
            for c in [codigo.zfill(5), codigo]:
                img = self.images_dir / f"{c}{ext}"
                if img.exists(): return str(img)
        return None

    def detect_categoria(self, nombre: str) -> str:
        nombre_lower = nombre.lower()
        for keyword, cat in self.categorias.items():
            if keyword in nombre_lower:
                return cat
        return "Repuestos Generales"

    def extract_compatibilidad(self, raw_data: Dict) -> List[str]:
        compat = raw_data.get("compatibilidad", [])
        if not compat or compat == "N/A":
            return ["Universal"]
        if isinstance(compat, str):
            # Separar por comas o /
            parts = re.split(r'[,/]', compat)
            return [p.strip() for p in parts if p.strip() and p.strip() != "N/A"]
        if isinstance(compat, list):
            return [str(c) for c in compat if c and str(c) != "N/A"]
        return ["Universal"]

    def extract_colores(self, raw_data: Dict) -> List[str]:
        colores = raw_data.get("colores", [])
        if not colores or colores == "N/A":
            return []
        if isinstance(colores, str):
            return [colores] if colores != "N/A" else []
        if isinstance(colores, list):
            return [str(c) for c in colores if c and str(c) != "N/A"]
        return []

    def normalize_title(self, raw_title: str, raw_data: Dict) -> str:
        """Título normalizado SIN código, CON marca"""
        # Limpiar título
        title = raw_title.strip()
        title = re.sub(r'\s+', ' ', title)  # Normalizar espacios

        # Capitalizar correctamente
        title = title.title()

        # Extraer compatibilidad para agregar al título
        compat = self.extract_compatibilidad(raw_data)
        compat_str = ""
        if compat and compat[0] != "Universal":
            # Tomar primeras 2-3 motos
            motos = compat[:3]
            compat_str = " / ".join(motos)

        # Construir título final
        if compat_str:
            final_title = f"{title} {compat_str} - Armotos"
        else:
            final_title = f"{title} - Armotos"

        return final_title

    def generate_ficha_360(self, product) -> str:
        """Genera Ficha 360° profesional con 7 secciones"""
        raw = product.raw_data
        nombre = raw.get("nombre", product.title)
        codigo = product.sku
        categoria = product.categoria
        precio = product.price

        # Compatibilidad
        compat_list = product.compatibilidad_list
        compat_html = ""
        for moto in compat_list:
            compat_html += f'<li style="padding:4px 0;">✅ {moto}</li>\n'
        if not compat_html:
            compat_html = '<li style="padding:4px 0;">✅ Universal</li>'

        # Colores/Variantes
        colores = product.colores_list
        if colores:
            variantes_html = "<p>" + ", ".join(colores) + "</p>"
        else:
            variantes_html = "<p>Presentación única</p>"

        # Descripción específica por categoría
        desc_categoria = self.descripciones.get(categoria, self.descripciones["default"])
        descripcion = f"{nombre}. {desc_categoria}"
        if raw.get("posicion") and not str(raw.get("posicion")).startswith("X"):
            descripcion += f" Posición: {raw.get('posicion')}."

        # Beneficios específicos por categoría
        beneficios_lista = self.beneficios.get(categoria, self.beneficios["default"])
        beneficios_html = "\n".join([f"    <li>{b}</li>" for b in beneficios_lista])

        ficha = f'''<div class="ficha-360" style="font-family:Arial,sans-serif;color:#333;">

  <div style="background:#E53E3E;color:white;padding:15px;border-radius:8px;margin-bottom:20px;">
    <h1 style="margin:0;font-size:22px;">{product.title}</h1>
    <p style="margin:5px 0 0;font-size:14px;">Ref: {codigo} | {categoria}</p>
  </div>

  <h2 style="color:#E53E3E;border-bottom:2px solid #E53E3E;padding-bottom:5px;">
    📋 Descripción
  </h2>
  <p>{descripcion}</p>

  <h2 style="color:#E53E3E;border-bottom:2px solid #E53E3E;padding-bottom:5px;">
    🔧 Información Técnica
  </h2>
  <table style="width:100%;border-collapse:collapse;margin:10px 0;">
    <tr style="background:#f7f7f7;">
      <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Referencia</td>
      <td style="padding:8px;border:1px solid #ddd;">{codigo}</td>
    </tr>
    <tr>
      <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Marca</td>
      <td style="padding:8px;border:1px solid #ddd;">Armotos</td>
    </tr>
    <tr style="background:#f7f7f7;">
      <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Categoría</td>
      <td style="padding:8px;border:1px solid #ddd;">{categoria}</td>
    </tr>
    <tr>
      <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Precio</td>
      <td style="padding:8px;border:1px solid #ddd;color:#E53E3E;font-weight:bold;">${precio:,.0f} COP</td>
    </tr>
    <tr style="background:#f7f7f7;">
      <td style="padding:8px;border:1px solid #ddd;font-weight:bold;">Condición</td>
      <td style="padding:8px;border:1px solid #ddd;">Nuevo</td>
    </tr>
  </table>

  <h2 style="color:#E53E3E;border-bottom:2px solid #E53E3E;padding-bottom:5px;">
    🏍️ Compatibilidad
  </h2>
  <ul style="columns:2;list-style:none;padding:0;">
    {compat_html}
  </ul>

  <h2 style="color:#E53E3E;border-bottom:2px solid #E53E3E;padding-bottom:5px;">
    🎨 Variantes Disponibles
  </h2>
  {variantes_html}

  <h2 style="color:#E53E3E;border-bottom:2px solid #E53E3E;padding-bottom:5px;">
    ✨ Beneficios
  </h2>
  <ul>
{beneficios_html}
  </ul>

  <h2 style="color:#E53E3E;border-bottom:2px solid #E53E3E;padding-bottom:5px;">
    📦 Recomendaciones
  </h2>
  <p>Instalación por técnico especializado.
  Verifique el modelo exacto de su motocicleta antes de comprar.
  Conserve la factura para efectos de garantía.</p>

  <h2 style="color:#E53E3E;border-bottom:2px solid #E53E3E;padding-bottom:5px;">
    🏪 Proveedor
  </h2>
  <div style="background:#f9f9f9;padding:12px;border-radius:6px;border-left:4px solid #E53E3E;">
    <strong>ARMOTOS</strong><br>
    Repuestos de motos de calidad<br>
    Envío a todo Colombia
  </div>

</div>'''
        return ficha

    def generate_tags(self, product) -> List[str]:
        """Tags profesionales"""
        tags = ["armotos", "repuesto-moto"]

        # Categoria como tag
        if product.categoria:
            cat_tag = product.categoria.lower().replace(" ", "-")
            tags.append(cat_tag)

        # Marcas de moto de compatibilidad
        for moto in product.compatibilidad_list:
            moto_upper = moto.upper()
            for marca in self.marcas_moto:
                if marca in moto_upper:
                    tags.append(marca.lower())
                    break

        return list(set(tags))

    def transform_products(self, raw_products):
        normalized = []
        for raw in raw_products:
            codigo = str(raw.get("codigo", "")).strip()
            if not codigo: continue

            nombre = raw.get("nombre", "Producto")
            precio = self.clean_price(raw.get("precio"))
            image_path = self.find_image(codigo)
            categoria = self.detect_categoria(nombre)
            compat_list = self.extract_compatibilidad(raw)
            colores_list = self.extract_colores(raw)

            product = NormalizedProduct(
                sku=codigo,
                title="",  # Se llena después
                price=precio,
                images=[image_path] if image_path else [],
                raw_data=raw,
                categoria=categoria,
                compatibilidad_list=compat_list,
                colores_list=colores_list
            )

            # Título normalizado (sin código, con marca)
            product.title = self.normalize_title(nombre, raw)

            # Tags profesionales
            product.tags = self.generate_tags(product)

            # Ficha 360° profesional
            product.ficha_360 = self.generate_ficha_360(product)

            # Body = Ficha 360° (el HTML completo)
            product.description = product.ficha_360

            normalized.append(product)

        logger.info(f"Transformed {len(normalized)} products, {sum(1 for p in normalized if p.images)} with images")
        return normalized

    def upload_image(self, product_id, image_path):
        try:
            with open(image_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            url = f"https://{self.shop}/admin/api/{self.api_version}/products/{product_id}/images.json"
            resp = requests.post(url, json={"image": {"attachment": data}},
                headers={"X-Shopify-Access-Token": self.token}, timeout=30)
            return resp.status_code == 200
        except: return False

    def upload_to_shopify(self, products):
        results = {"uploaded": 0, "failed": 0, "with_images": 0}
        url = f"https://{self.shop}/admin/api/{self.api_version}/products.json"
        headers = {"X-Shopify-Access-Token": self.token, "Content-Type": "application/json"}

        for i, product in enumerate(products):
            try:
                payload = {"product": {
                    "title": product.title,
                    "body_html": product.description,
                    "vendor": product.vendor,
                    "product_type": product.categoria or product.product_type,
                    "tags": ", ".join(product.tags),
                    "status": "active",
                    "variants": [{"sku": product.sku, "price": str(product.price), "inventory_management": "shopify", "inventory_quantity": 10}]
                }}
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                if resp.status_code == 201:
                    results["uploaded"] += 1
                    pid = resp.json().get("product", {}).get("id")
                    if product.images and pid:
                        if self.upload_image(pid, product.images[0]):
                            results["with_images"] += 1
                    if (i+1) % 500 == 0:
                        print(f"[PROGRESS] {i+1}/{len(products)} uploaded, {results['with_images']} with images", flush=True)
                elif resp.status_code == 429:
                    logger.warning("Rate limited, waiting...")
                    time.sleep(2)
                else:
                    results["failed"] += 1
                    if results["failed"] <= 5:
                        logger.warning(f"Failed [{product.sku}]: {resp.status_code} - {resp.text[:200]}")
                time.sleep(0.6)
            except Exception as e:
                results["failed"] += 1
                logger.error(f"Error [{product.sku}]: {e}")
        return results

    def index_chromadb(self, products):
        try:
            collection = self.chroma_client.get_or_create_collection(self.collection_name)
            ids, docs, metas = [], [], []
            for p in products:
                ids.append(f"ARMOTOS_{p.sku}")
                docs.append(f"{p.title} {p.categoria} {' '.join(p.compatibilidad_list)} Precio: ${p.price:,.0f} COP")
                metas.append({"type": "product", "store": "ARMOTOS", "sku": p.sku, "title": p.title, "price": p.price, "categoria": p.categoria})
            for i in range(0, len(ids), 500):
                collection.upsert(ids=ids[i:i+500], documents=docs[i:i+500], metadatas=metas[i:i+500])
            logger.info(f"Indexed {len(ids)} to ChromaDB")
            return len(ids)
        except Exception as e:
            logger.error(f"ChromaDB error: {e}")
            return 0

    def audit(self, products, n=10):
        import random
        sample = random.sample(products, min(n, len(products)))
        checks = {
            "sku": 0, "title_no_brackets": 0, "title_has_armotos": 0,
            "price": 0, "ficha_7_sections": 0, "tags_pro": 0,
            "active": 0, "categoria": 0, "body_html_rich": 0, "vendor": 0
        }
        for p in sample:
            if p.sku: checks["sku"] += 1
            if "[" not in p.title: checks["title_no_brackets"] += 1
            if "Armotos" in p.title or "armotos" in p.title.lower(): checks["title_has_armotos"] += 1
            if p.price > 0: checks["price"] += 1
            # Verificar 7 secciones en ficha
            sections = ["Descripción", "Información Técnica", "Compatibilidad", "Variantes", "Beneficios", "Recomendaciones", "Proveedor"]
            if all(s in p.ficha_360 for s in sections): checks["ficha_7_sections"] += 1
            if "armotos" in p.tags and len(p.tags) >= 3: checks["tags_pro"] += 1
            if p.status == "active": checks["active"] += 1
            if p.categoria: checks["categoria"] += 1
            if len(p.description) > 500 and "<table" in p.description: checks["body_html_rich"] += 1
            if p.vendor: checks["vendor"] += 1

        score = sum(checks.values()) / (len(checks) * n) * 10
        grade = "A" if score >= 9 else "B" if score >= 7 else "C"
        return {"score": round(score, 1), "grade": grade, "checks": checks, "sample_size": n}

    def show_example(self, n=1):
        """Muestra ejemplo(s) de producto transformado"""
        raw = self.load_v10_data()
        self.products = self.transform_products(raw[:n])

        for p in self.products:
            print("=" * 80)
            print(f"TÍTULO: {p.title}")
            print(f"SKU: {p.sku}")
            print(f"PRECIO: ${p.price:,.0f} COP")
            print(f"CATEGORÍA: {p.categoria}")
            print(f"TAGS: {', '.join(p.tags)}")
            print(f"COMPATIBILIDAD: {', '.join(p.compatibilidad_list)}")
            print(f"COLORES: {', '.join(p.colores_list) if p.colores_list else 'N/A'}")
            print(f"IMAGEN: {'Sí' if p.images else 'No'}")
            print()
            print("BODY_HTML (Ficha 360°):")
            print("-" * 40)
            print(p.ficha_360)
            print("=" * 80)

        return self.products

    def execute(self):
        logger.info("=== ARMOTOS V10 Pipeline PRO Start ===")
        start = time.time()
        raw = self.load_v10_data()
        logger.info(f"Loaded {len(raw)} raw products")
        self.products = self.transform_products(raw)
        audit = self.audit(self.products)
        logger.info(f"Pre-audit: GRADO {audit['grade']} ({audit['score']}/10)")
        logger.info(f"Checks: {audit['checks']}")

        if audit["grade"] != "A":
            logger.error(f"AUDIT FAILED - Grade {audit['grade']} is not A. Aborting upload.")
            return {"success": False, "audit": audit, "reason": "Audit not GRADO A"}

        upload = self.upload_to_shopify(self.products)
        indexed = self.index_chromadb(self.products)
        elapsed = time.time() - start

        results = {
            "success": True, "store": self.store,
            "total": len(self.products), "uploaded": upload["uploaded"],
            "with_images": upload["with_images"], "failed": upload["failed"],
            "chromadb": indexed, "audit": audit, "seconds": round(elapsed, 1)
        }
        logger.info(f"=== Complete in {elapsed:.1f}s ===")
        return results

if __name__ == "__main__":
    import sys
    adapter = V10AdapterPro("ARMOTOS")

    if len(sys.argv) > 1 and sys.argv[1] == "example":
        # Mostrar ejemplo sin subir
        adapter.show_example(1)
    else:
        # Ejecutar pipeline completo
        r = adapter.execute()
        print(json.dumps(r, indent=2))
