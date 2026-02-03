#!/usr/bin/env python3
"""
Generate realistic Yokomar test dataset for ODI pipeline testing.
Creates ~500 products simulating a motorcycle parts distributor.
"""

import csv
import random
from itertools import product

# Base product categories with variations
PRODUCTS = {
    # Cascos (helmets) - high variation
    "cascos": {
        "base_names": [
            "CASCO INTEGRAL LS2 FF800 STORM",
            "CASCO MODULAR LS2 FF906 ADVANT",
            "CASCO ABIERTO LS2 OF562 AIRFLOW",
            "CASCO CROSS LS2 MX437 FAST",
            "CASCO JET LS2 OF558 SPHERE",
            "CASCO INTEGRAL HJC I70",
            "CASCO MODULAR HJC RPHA 90",
            "CASCO INTEGRAL SHAFT SH-881",
            "CASCO ABIERTO SHAFT SH-202",
            "CASCO CROSS SHAFT SH-MX200",
        ],
        "sizes": ["XS", "S", "M", "L", "XL", "XXL"],
        "colors": ["NEGRO MATE", "BLANCO", "ROJO", "AZUL", "NEGRO BRILLANTE", "TITANIO"],
        "price_range": (180000, 650000),
        "sku_prefix": "CAS"
    },

    # Aceites (oils) - medium variation
    "aceites": {
        "base_names": [
            "ACEITE MOTUL 7100 4T 10W40 SINTETICO",
            "ACEITE MOTUL 5100 4T 10W40 SEMI",
            "ACEITE MOTUL 3000 4T 20W50 MINERAL",
            "ACEITE CASTROL POWER 1 4T 10W40",
            "ACEITE CASTROL ACTEVO 4T 20W50",
            "ACEITE YAMALUBE 4T 20W50",
            "ACEITE HONDA GN4 10W30",
            "ACEITE SHELL ADVANCE AX5 20W50",
            "ACEITE MOBIL SUPER MOTO 4T 20W50",
            "ACEITE LIQUI MOLY 4T 10W40",
        ],
        "sizes": ["1L", "4L", "20L"],
        "price_range": (25000, 180000),
        "sku_prefix": "ACE"
    },

    # Llantas (tires)
    "llantas": {
        "base_names": [
            "LLANTA PIRELLI DIABLO ROSSO II",
            "LLANTA PIRELLI ANGEL GT",
            "LLANTA MICHELIN PILOT ROAD 4",
            "LLANTA MICHELIN PILOT STREET",
            "LLANTA DUNLOP SPORTMAX",
            "LLANTA BRIDGESTONE BATTLAX",
            "LLANTA METZELER ROADTEC",
            "LLANTA CONTINENTAL CONTIMOTION",
            "LLANTA IRC NR73",
            "LLANTA KENDA K761",
        ],
        "sizes": ["90/90-18", "100/80-17", "110/70-17", "120/70-17", "140/70-17", "150/60-17", "160/60-17", "180/55-17"],
        "price_range": (85000, 450000),
        "sku_prefix": "LLA"
    },

    # Filtros
    "filtros": {
        "base_names": [
            "FILTRO ACEITE HIFLOFILTRO HF",
            "FILTRO AIRE K&N",
            "FILTRO ACEITE ORIGINAL HONDA",
            "FILTRO ACEITE ORIGINAL YAMAHA",
            "FILTRO AIRE ORIGINAL SUZUKI",
            "FILTRO ACEITE MAHLE",
            "FILTRO COMBUSTIBLE UNIVERSAL",
        ],
        "models": ["138", "140", "141", "145", "147", "153", "160", "164", "170", "183", "196", "204"],
        "price_range": (8000, 65000),
        "sku_prefix": "FIL"
    },

    # Cadenas y sprockets
    "transmision": {
        "base_names": [
            "CADENA DID 520VX3 ORO",
            "CADENA DID 428VX ORO",
            "CADENA RK 520KRX ORO",
            "CADENA RK 428HSB",
            "KIT ARRASTRE DID",
            "KIT ARRASTRE RK",
            "PIÑON DELANTERO JT",
            "CATALINA TRASERA JT",
            "CADENA OSAKI 428H",
        ],
        "sizes": ["118", "120", "124", "126", "130", "132", "134", "136", "140"],
        "price_range": (45000, 320000),
        "sku_prefix": "TRA"
    },

    # Pastillas de freno
    "frenos": {
        "base_names": [
            "PASTILLAS FRENO EBC FA",
            "PASTILLAS FRENO FERODO FDB",
            "PASTILLAS FRENO BREMBO",
            "PASTILLAS FRENO GALFER",
            "DISCO FRENO EBC MD",
            "DISCO FRENO BREMBO SERIE ORO",
            "LIQUIDO FRENOS MOTUL DOT 4",
            "LIQUIDO FRENOS CASTROL DOT 4",
        ],
        "models": ["142", "165", "174", "196", "213", "228", "231", "254", "275", "294", "322", "367", "381"],
        "price_range": (25000, 280000),
        "sku_prefix": "FRE"
    },

    # Bujias
    "bujias": {
        "base_names": [
            "BUJIA NGK CR8E",
            "BUJIA NGK CR9EK",
            "BUJIA NGK CPR8EA-9",
            "BUJIA NGK IRIDIUM CR8EIX",
            "BUJIA DENSO IU27",
            "BUJIA DENSO U24ESR-N",
            "BUJIA BOSCH UR2CC",
            "BUJIA CHAMPION RA8HC",
        ],
        "price_range": (8000, 85000),
        "sku_prefix": "BUJ"
    },

    # Baterias
    "baterias": {
        "base_names": [
            "BATERIA YUASA YTX",
            "BATERIA YUASA YT",
            "BATERIA MOTOBATT MB",
            "BATERIA GS GTX",
            "BATERIA BOSCH M6",
            "BATERIA EXIDE ETX",
        ],
        "sizes": ["5L-BS", "7L-BS", "9-BS", "12-BS", "14-BS", "20L-BS", "30L-BS"],
        "price_range": (65000, 380000),
        "sku_prefix": "BAT"
    },

    # Repuestos varios
    "repuestos": {
        "items": [
            ("BOMBA AGUA PULSAR 200NS", "REP-001", 125000, "Bajaj;Pulsar 200NS"),
            ("BOMBA AGUA PULSAR 200NS", "REP-001A", 125000, "Bajaj;Pulsar NS200"),  # Duplicate
            ("TENSOR CADENA DISCOVER 125", "REP-002", 28000, "Bajaj;Discover 125"),
            ("TENSOR CADENA DISCOVER 125 ST", "REP-002B", 28000, "Bajaj;Discover 125ST"),  # Duplicate
            ("CABLE ACELERADOR CB190R", "REP-003", 22000, "Honda;CB190R"),
            ("CABLE EMBRAGUE CB190R", "REP-004", 24000, "Honda;CB190R"),
            ("CDI GIXXER 150", "REP-005", 185000, "Suzuki;Gixxer 150"),
            ("CDI GIXXER SF", "REP-005B", 185000, "Suzuki;Gixxer SF"),  # Duplicate
            ("REGULADOR VOLTAJE FZ25", "REP-006", 95000, "Yamaha;FZ25"),
            ("ESTATOR BAJAJ PULSAR 200", "REP-007", 165000, "Bajaj;Pulsar 200"),
            ("BOBINA ENCENDIDO AKT 125", "REP-008", 45000, "AKT;AKT 125"),
            ("BOBINA ALTA AKT 125 SPECIAL", "REP-008A", 45000, "AKT;AKT 125 Special"),  # Duplicate
            ("CARBURADOR COMPLETO ECO", "REP-009", 78000, "Honda;ECO Deluxe"),
            ("CARBURADOR COMPLETO ECO DELUXE", "REP-009B", 78000, "Honda;ECO Deluxe 100"),  # Duplicate
            ("CLUTCH COMPLETO XR150", "REP-010", 145000, "Honda;XR150"),
            ("KIT EMBRAGUE XR150L", "REP-010A", 145000, "Honda;XR150L"),  # Duplicate
            ("PIÑON PRIMARIO NS200", "REP-011", 55000, "Bajaj;Pulsar NS200"),
            ("MANIGUETA FRENO UNIVERSAL", "REP-012", 12000, "Universal"),
            ("MANIGUETA CLUTCH UNIVERSAL", "REP-013", 12000, "Universal"),
            ("ESPEJO RETROVISOR NEGRO PAR", "REP-014", 18000, "Universal"),
            ("ESPEJO RETROVISOR CROMADO PAR", "REP-015", 22000, "Universal"),
            ("GUARDAFANGO DELANTERO BWS 125", "REP-016", 45000, "Yamaha;BWS 125"),
            ("GUARDABARRO FRONTAL BWS", "REP-016A", 45000, "Yamaha;BWS"),  # Duplicate
            ("FAROLA DELANTERA LED UNIVERSAL", "REP-017", 85000, "Universal"),
            ("STOP TRASERO LED UNIVERSAL", "REP-018", 35000, "Universal"),
            ("DIRECCIONAL LED PAR", "REP-019", 28000, "Universal"),
            ("SILLIN COMPLETO BOXER CT", "REP-020", 95000, "Bajaj;Boxer CT"),
            ("TANQUE GASOLINA DISCOVER", "REP-021", 185000, "Bajaj;Discover"),
            ("EXHOSTO COMPLETO APACHE 200", "REP-022", 220000, "TVS;Apache RTR 200"),
            ("MOFLE APACHE RTR 200", "REP-022A", 220000, "TVS;Apache 200"),  # Duplicate
            ("GUAYA VELOCIMETRO PLATINO", "REP-023", 15000, "Bajaj;Platino"),
            ("RODAMIENTO RUEDA 6302", "REP-024", 12000, "Universal"),
            ("RODAMIENTO DIRECCION KIT", "REP-025", 35000, "Universal"),
            ("RETENEDOR RUEDA TRASERA", "REP-026", 8000, "Universal"),
            ("EMPAQUE MOTOR ECO SET", "REP-027", 28000, "Honda;ECO"),
            ("JUEGO EMPAQUES MOTOR ECO", "REP-027A", 28000, "Honda;ECO Deluxe"),  # Duplicate
            ("VALVULA ADMISION CB190", "REP-028", 32000, "Honda;CB190R"),
            ("VALVULA ESCAPE CB190", "REP-029", 32000, "Honda;CB190R"),
            ("PISTON COMPLETO PULSAR 180", "REP-030", 85000, "Bajaj;Pulsar 180"),
            ("BIELA PULSAR 180 UG", "REP-031", 95000, "Bajaj;Pulsar 180"),
            ("CIGUEÑAL DISCOVER 100", "REP-032", 145000, "Bajaj;Discover 100"),
        ],
        "sku_prefix": "REP"
    },

    # Accesorios
    "accesorios": {
        "items": [
            ("GUANTES ALPINESTARS SMX-1 AIR V2", "ACC-001", 185000, None),
            ("GUANTES ALPINESTARS SMX-1", "ACC-001A", 185000, None),  # Duplicate
            ("GUANTES DAINESE AEROX", "ACC-002", 165000, None),
            ("CHAQUETA ALPINESTARS T-GP PLUS", "ACC-003", 520000, None),
            ("CHAQUETA DAINESE SUPER SPEED", "ACC-004", 580000, None),
            ("BOTAS ALPINESTARS SMX-6 V2", "ACC-005", 650000, None),
            ("BOTAS DAINESE AXIAL D1", "ACC-006", 720000, None),
            ("PROTECTOR ESPALDA ALPINESTARS", "ACC-007", 145000, None),
            ("CHALECO REFLECTIVO MOTO", "ACC-008", 25000, None),
            ("IMPERMEABLE MOTO COMPLETO", "ACC-009", 65000, None),
            ("IMPERMEABLE MOTOCICLISTA SET", "ACC-009A", 65000, None),  # Duplicate
            ("CANDADO DISCO XENA XX6", "ACC-010", 185000, None),
            ("CANDADO CADENA ABUS", "ACC-011", 145000, None),
            ("FORRO SILLIN IMPERMEABLE", "ACC-012", 18000, None),
            ("PARRILLA TRASERA UNIVERSAL", "ACC-013", 75000, None),
            ("SLIDER CARENAJE PAR", "ACC-014", 85000, None),
            ("PROTECTOR MOTOR UNIVERSAL", "ACC-015", 120000, None),
            ("MALETA LATERAL GIVI", "ACC-016", 380000, None),
            ("MALETA TOP CASE 45L", "ACC-017", 285000, None),
            ("BAUL TRASERO 45 LITROS", "ACC-017A", 285000, None),  # Duplicate
            ("SOPORTE CELULAR MOTO", "ACC-018", 35000, None),
            ("CARGADOR USB MOTO 12V", "ACC-019", 28000, None),
            ("INTERCOMUNICADOR SENA 3S", "ACC-020", 320000, None),
        ],
        "sku_prefix": "ACC"
    }
}

# Motos for fitment
MOTOS = [
    ("Honda", "CB190R", "190"),
    ("Honda", "XR150L", "150"),
    ("Honda", "ECO Deluxe", "100"),
    ("Honda", "Navi", "110"),
    ("Yamaha", "FZ25", "250"),
    ("Yamaha", "MT-03", "321"),
    ("Yamaha", "BWS 125", "125"),
    ("Yamaha", "NMAX", "155"),
    ("Bajaj", "Pulsar NS200", "200"),
    ("Bajaj", "Pulsar 180", "180"),
    ("Bajaj", "Discover 125 ST", "125"),
    ("Bajaj", "Boxer CT100", "100"),
    ("Bajaj", "Dominar 400", "400"),
    ("Suzuki", "Gixxer 150", "150"),
    ("Suzuki", "Gixxer SF", "155"),
    ("Suzuki", "GSX-S150", "150"),
    ("TVS", "Apache RTR 200", "200"),
    ("TVS", "Apache RTR 160", "160"),
    ("AKT", "AKT 125 Special", "125"),
    ("AKT", "NKD 125", "125"),
    ("KTM", "Duke 200", "200"),
    ("KTM", "RC 200", "200"),
    ("Kawasaki", "Ninja 400", "400"),
    ("Kawasaki", "Z400", "400"),
    ("BMW", "G310R", "313"),
    ("Royal Enfield", "Himalayan", "411"),
]

def generate_sku(prefix, counter, suffix=""):
    """Generate SKU with format PREFIX-XXX-SUFFIX"""
    sku = f"{prefix}-{counter:03d}"
    if suffix:
        sku += f"-{suffix}"
    return sku

def generate_products():
    """Generate all products for Yokomar test dataset."""
    products = []
    sku_counter = {}

    # Generate cascos (helmets)
    cat = PRODUCTS["cascos"]
    for base_name in cat["base_names"]:
        for size in cat["sizes"]:
            for color in cat["colors"][:3]:  # Limit colors per helmet
                prefix = cat["sku_prefix"]
                sku_counter[prefix] = sku_counter.get(prefix, 0) + 1
                sku = generate_sku(prefix, sku_counter[prefix], size)
                price = random.randint(*cat["price_range"])

                products.append({
                    "codigo": sku,
                    "descripcion": f"{base_name} {color} TALLA {size}",
                    "precio": price,
                    "categoria": "CASCOS",
                    "marca_moto": "",
                    "modelo_moto": "",
                    "cilindraje": ""
                })

    # Generate aceites (oils)
    cat = PRODUCTS["aceites"]
    for base_name in cat["base_names"]:
        for size in cat["sizes"]:
            prefix = cat["sku_prefix"]
            sku_counter[prefix] = sku_counter.get(prefix, 0) + 1
            sku = generate_sku(prefix, sku_counter[prefix])

            # Adjust price by size
            base_price = random.randint(*cat["price_range"])
            if size == "4L":
                price = base_price * 3.5
            elif size == "20L":
                price = base_price * 15
            else:
                price = base_price

            products.append({
                "codigo": sku,
                "descripcion": f"{base_name} {size}",
                "precio": int(price),
                "categoria": "ACEITES Y LUBRICANTES",
                "marca_moto": "",
                "modelo_moto": "",
                "cilindraje": ""
            })

    # Generate llantas (tires)
    cat = PRODUCTS["llantas"]
    for base_name in cat["base_names"]:
        for size in cat["sizes"][:4]:  # Limit sizes
            prefix = cat["sku_prefix"]
            sku_counter[prefix] = sku_counter.get(prefix, 0) + 1
            sku = generate_sku(prefix, sku_counter[prefix])
            price = random.randint(*cat["price_range"])

            products.append({
                "codigo": sku,
                "descripcion": f"{base_name} {size}",
                "precio": price,
                "categoria": "LLANTAS",
                "marca_moto": "",
                "modelo_moto": "",
                "cilindraje": ""
            })

    # Generate filtros
    cat = PRODUCTS["filtros"]
    for base_name in cat["base_names"]:
        for model in cat["models"][:4]:
            prefix = cat["sku_prefix"]
            sku_counter[prefix] = sku_counter.get(prefix, 0) + 1
            sku = generate_sku(prefix, sku_counter[prefix])
            price = random.randint(*cat["price_range"])

            # Assign random moto fitment
            moto = random.choice(MOTOS)

            products.append({
                "codigo": sku,
                "descripcion": f"{base_name}{model}",
                "precio": price,
                "categoria": "FILTROS",
                "marca_moto": moto[0],
                "modelo_moto": moto[1],
                "cilindraje": moto[2]
            })

    # Generate transmision
    cat = PRODUCTS["transmision"]
    for base_name in cat["base_names"]:
        for size in cat["sizes"][:3]:
            prefix = cat["sku_prefix"]
            sku_counter[prefix] = sku_counter.get(prefix, 0) + 1
            sku = generate_sku(prefix, sku_counter[prefix])
            price = random.randint(*cat["price_range"])

            products.append({
                "codigo": sku,
                "descripcion": f"{base_name} {size}L",
                "precio": price,
                "categoria": "TRANSMISION",
                "marca_moto": "",
                "modelo_moto": "",
                "cilindraje": ""
            })

    # Generate frenos
    cat = PRODUCTS["frenos"]
    for base_name in cat["base_names"]:
        for model in cat["models"][:5]:
            prefix = cat["sku_prefix"]
            sku_counter[prefix] = sku_counter.get(prefix, 0) + 1
            sku = generate_sku(prefix, sku_counter[prefix])
            price = random.randint(*cat["price_range"])

            moto = random.choice(MOTOS)

            products.append({
                "codigo": sku,
                "descripcion": f"{base_name}{model}",
                "precio": price,
                "categoria": "FRENOS",
                "marca_moto": moto[0],
                "modelo_moto": moto[1],
                "cilindraje": moto[2]
            })

    # Generate bujias
    cat = PRODUCTS["bujias"]
    for base_name in cat["base_names"]:
        prefix = cat["sku_prefix"]
        sku_counter[prefix] = sku_counter.get(prefix, 0) + 1
        sku = generate_sku(prefix, sku_counter[prefix])
        price = random.randint(*cat["price_range"])

        products.append({
            "codigo": sku,
            "descripcion": base_name,
            "precio": price,
            "categoria": "BUJIAS",
            "marca_moto": "",
            "modelo_moto": "",
            "cilindraje": ""
        })

    # Generate baterias
    cat = PRODUCTS["baterias"]
    for base_name in cat["base_names"]:
        for size in cat["sizes"]:
            prefix = cat["sku_prefix"]
            sku_counter[prefix] = sku_counter.get(prefix, 0) + 1
            sku = generate_sku(prefix, sku_counter[prefix])
            price = random.randint(*cat["price_range"])

            products.append({
                "codigo": sku,
                "descripcion": f"{base_name}{size}",
                "precio": price,
                "categoria": "BATERIAS",
                "marca_moto": "",
                "modelo_moto": "",
                "cilindraje": ""
            })

    # Add repuestos (with intentional duplicates)
    cat = PRODUCTS["repuestos"]
    for item in cat["items"]:
        name, sku, price, fitment = item

        marca = modelo = cc = ""
        if fitment:
            parts = fitment.split(";")
            if len(parts) >= 2:
                marca = parts[0]
                modelo = parts[1]
            if len(parts) >= 3:
                cc = parts[2]

        products.append({
            "codigo": sku,
            "descripcion": name,
            "precio": price,
            "categoria": "REPUESTOS",
            "marca_moto": marca,
            "modelo_moto": modelo,
            "cilindraje": cc
        })

    # Add accesorios (with intentional duplicates)
    cat = PRODUCTS["accesorios"]
    for item in cat["items"]:
        name, sku, price, fitment = item

        products.append({
            "codigo": sku,
            "descripcion": name,
            "precio": price,
            "categoria": "ACCESORIOS",
            "marca_moto": "",
            "modelo_moto": "",
            "cilindraje": ""
        })

    return products

def main():
    """Generate and save Yokomar test dataset."""
    print("�icing Generating Yokomar test dataset...")

    products = generate_products()

    # Shuffle to make it more realistic
    random.shuffle(products)

    # Transform to expected format (sku_odi, codigo, nombre, descripcion, precio, categoria)
    transformed = []
    for i, p in enumerate(products):
        transformed.append({
            "sku_odi": f"YOK-{i+1:05d}",  # Unique ODI identifier
            "codigo": p["codigo"],
            "nombre": p["descripcion"],  # nombre = short description
            "descripcion": p["descripcion"],  # full description
            "precio": p["precio"],
            "categoria": p["categoria"],
            "marca_moto": p["marca_moto"],
            "modelo_moto": p["modelo_moto"],
            "cilindraje": p["cilindraje"]
        })

    # Write CSV
    output_file = "YOKOMAR_TEST_INPUT.csv"
    fieldnames = ["sku_odi", "codigo", "nombre", "descripcion", "precio", "categoria", "marca_moto", "modelo_moto", "cilindraje"]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(transformed)

    print(f"✅ Generated {len(products)} products")
    print(f"📁 Output: {output_file}")

    # Stats
    categories = {}
    for p in products:
        cat = p["categoria"]
        categories[cat] = categories.get(cat, 0) + 1

    print("\n📊 Category breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")

    # Count potential duplicates
    desc_counts = {}
    for p in products:
        # Normalize description for duplicate detection
        desc_norm = p["descripcion"].upper().split()[0:3]
        desc_key = " ".join(desc_norm)
        desc_counts[desc_key] = desc_counts.get(desc_key, 0) + 1

    potential_dupes = sum(1 for c in desc_counts.values() if c > 1)
    print(f"\n🔍 Potential duplicate groups: {potential_dupes}")

if __name__ == "__main__":
    main()
