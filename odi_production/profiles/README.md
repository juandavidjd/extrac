# ODI Profiles - Sistema Multi-Empresa

## Arquitectura

```
profiles/
  _template.yaml      # Plantilla para nuevas empresas
  yokomar.yaml        # Perfil Yokomar (repuestos moto CO)
  kaiqi.yaml          # Perfil Kaiqi (repuestos moto CN)
  bara.yaml           # Perfil Bara (repuestos auto)
  ...
```

## Uso

```bash
# Listar perfiles disponibles
python3 odi_industrial_extractor.py --list-profiles

# Procesar con perfil
python3 odi_industrial_extractor.py --profile yokomar

# Con directorio de datos especifico
python3 odi_industrial_extractor.py --profile yokomar --data-dir /path/to/data
```

## Crear Nuevo Perfil

1. Copiar `_template.yaml` a `<empresa>.yaml`
2. Completar seccion `empresa` con datos de la empresa
3. Configurar `archivos` con patrones de CSV y directorio
4. Definir `mapeo_columnas` segun formato del CSV
5. Completar taxonomia de `categorias` (obligatorio)
6. Si aplica, completar `marcas_moto`, `modelos_moto`, `cilindrajes`

## Estructura del Perfil

### empresa (obligatorio)
```yaml
empresa:
  nombre: "YOKOMAR"           # Nombre corto
  nombre_legal: "..."         # Razon social
  nit: "..."                  # Identificacion fiscal
  prefijo_sku: "YOK"          # Prefijo para SKUs (3-4 chars)
  vendor: "YOKOMAR"           # Vendor en Shopify
  industria: "autopartes_moto"
  region: "CO"
```

### archivos (obligatorio)
```yaml
archivos:
  csv_separator: ";"
  encoding: "utf-8-sig"
  base_datos_pattern: "Base_Datos*.csv"
  lista_precios_pattern: "Lista_Precios*.csv"
  directorio_default: "/path/to/data"
```

### mapeo_columnas (obligatorio)
Define nombres alternativos para columnas de entrada:
```yaml
mapeo_columnas:
  codigo: ["CODIGO", "SKU", "REF"]
  descripcion: ["DESCRIPCION", "Title", "NOMBRE"]
  precio: ["PRECIO", "Price"]
  imagen: ["Imagen_URL_Origen", "IMAGE"]
```

### categorias (obligatorio)
Define taxonomia de categorias con keywords:
```yaml
categorias:
  motor:
    nombre: "MOTOR"
    keywords: ["CILINDRO", "PISTON", "BIELA"]
  electrico:
    nombre: "ELECTRICO"
    keywords: ["CDI", "BOBINA", "FARO"]
```

### marcas_moto / modelos_moto / cilindrajes (opcional)
Para industria de motos/autos:
```yaml
marcas_moto:
  prefijos: {"H.": "HONDA", "Y.": "YAMAHA"}
  keywords: {"PULSAR": "BAJAJ"}
  marcas_completas: ["HONDA", "YAMAHA"]

modelos_moto:
  honda: ["XR150", "CB190R"]
  yamaha: ["FZ25", "MT03"]

cilindrajes:
  "125": ["125", "XR125", "CBF125"]
  "150": ["150", "XR150"]
```

## Industrias Soportadas

| Industria | Taxonomia | Ejemplo |
|-----------|-----------|---------|
| `autopartes_moto` | marcas + modelos + cilindrajes | yokomar |
| `autopartes_auto` | marcas + modelos + motorizacion | bara |
| `textiles` | tallas + colores + materiales | vitton |
| `general` | solo categorias | otros |

## Flujo de Datos

```
CSV Original → Extractor → ProductoODI → Normalizer → Shopify
                   ↑
              Profile YAML
```

El perfil YAML actua como "adaptador biologico" que traduce
el formato especifico de cada empresa al formato ODI universal.
