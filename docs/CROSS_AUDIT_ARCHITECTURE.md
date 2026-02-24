# ODI Cross-Audit System v4.0 - Enterprise Architecture

## Resumen Ejecutivo

Sistema profesional de auditoría cruzada para 15 tiendas Shopify del ecosistema ODI.
Detecta y corrige anomalías de precios, títulos e imágenes con aislamiento de namespace.

**Versión:** 4.0 Enterprise
**Fecha:** 20 Febrero 2026
**Autor:** ODI Engineering
**Score Actual:** 88/100

---

## 1. Arquitectura General

```
+-------------------------------------------------------------------+
|                    ODI CROSS-AUDIT SYSTEM v4.0                    |
+-------------------------------------------------------------------+
|                                                                   |
|  +-------------+  +-------------+  +-------------+                |
|  | Namespace   |  |   Title     |  |  Branding   |                |
|  |  Manager    |  | Normalizer  |  |  Validator  |                |
|  | (Anti-Cruce)|  | (Literal)   |  | (Identity)  |                |
|  +------+------+  +------+------+  +------+------+                |
|         |                |                |                       |
|         +----------------+----------------+                       |
|                          |                                        |
|              +-----------v-----------+                            |
|              |    AUDIT PIPELINE     |                            |
|              |  +-----------------+  |                            |
|              |  | 1. Load CSVs    |  |                            |
|              |  | 2. Load JSONs   |  |                            |
|              |  | 3. Cross-Match  |  |                            |
|              |  | 4. Fix Prices   |  |                            |
|              |  | 5. Fix Titles   |  |                            |
|              |  | 6. Validate     |  |                            |
|              |  | 7. Report       |  |                            |
|              |  +-----------------+  |                            |
|              +-----------------------+                            |
|                          |                                        |
|         +----------------+----------------+                       |
|         v                v                v                       |
|  +-------------+  +-------------+  +-------------+                |
|  |   JSONs     |  |   Reports   |  |  External   |                |
|  | orden_v6/   |  |  reports/   |  |   Intel     |                |
|  +-------------+  +-------------+  +-------------+                |
|                                                                   |
+-------------------------------------------------------------------+
```

---

## 2. Modulos de Seguridad

### 2.1 NamespaceManager (Anti-Cruce)

**Proposito:** Garantiza que los datos de una tienda nunca contaminen otra.

```python
class NamespaceManager:
    def __init__(self):
        self.active_namespace = None
        self.namespace_locks = {}

    def enter_namespace(self, store_id: str):
        """Bloquea namespace para operaciones exclusivas."""
        if self.active_namespace and self.active_namespace != store_id:
            raise NamespaceViolation(f"Intento de cruce: {self.active_namespace} -> {store_id}")
        self.active_namespace = store_id

    def validate_sku_ownership(self, sku: str, store_id: str) -> bool:
        """Verifica que el SKU pertenece al namespace activo."""
        return sku.startswith(store_id) or self._check_master_registry(sku, store_id)
```

**Reglas:**
- Un SKU solo puede ser modificado por su tienda propietaria
- Los CSVs se cargan con prefijo de namespace
- Las operaciones cross-store requieren validacion explicita

### 2.2 TitleNormalizer (Literal)

**Proposito:** Mantiene titulos literales del CSV, sin prefijos automaticos.

```python
class TitleNormalizer:
    FORBIDDEN_PREFIXES = ["Empaque", "Paquete", "Kit de", "Set de"]

    def normalize(self, title: str, csv_title: str = None) -> str:
        """Usa titulo CSV literal, elimina prefijos no autorizados."""
        if csv_title:
            return csv_title.strip()

        for prefix in self.FORBIDDEN_PREFIXES:
            if title.startswith(prefix):
                title = title[len(prefix):].strip()

        return title
```

**Reglas:**
- Si existe titulo en CSV, se usa literal
- Prefijos como "Empaque" se eliminan automaticamente
- No se agregan sufijos de tienda al titulo

### 2.3 BrandingValidator (Identity)

**Proposito:** Valida logos, colores y assets de marca por tienda.

```python
class BrandingValidator:
    def __init__(self, brands_path: str):
        self.brands = self._load_brand_configs(brands_path)

    def validate_product(self, product: dict, store_id: str) -> List[str]:
        """Retorna lista de violaciones de branding."""
        violations = []
        brand = self.brands.get(store_id)

        if not brand:
            return ["NO_BRAND_CONFIG"]

        # Validar que imagenes no contengan logos de otras tiendas
        for img in product.get("images", []):
            if self._contains_foreign_branding(img, store_id):
                violations.append(f"FOREIGN_LOGO:{img}")

        return violations
```

---

## 3. Flujo de Datos

### 3.1 Fuentes de Datos

| Fuente | Ruta | Formato | Contenido |
|--------|------|---------|-----------|
| CSVs Master | /mnt/volume_sfo3_01/.../Data/{Store}/ | CSV ; | SKU, Descripcion, Precio |
| JSONs Shopify | /opt/odi/data/orden_maestra_v6/ | JSON | Productos completos |
| Brand Configs | /opt/odi/data/brands/ | JSON | Logos, colores, API keys |

### 3.2 Pipeline de Auditoria

```
FASE 1: CARGA
+-- Cargar CSVs con Namespace Isolation
+-- Construir indice global de SKUs
+-- Validar unicidad de SKUs por tienda

FASE 2: NORMALIZACION DE PRECIOS
+-- Para cada producto con precio = 0:
|   +-- Buscar en CSV local (namespace)
|   +-- Si no existe -> External Intel
|   +-- Actualizar JSON con source tracking
+-- Guardar progreso incremental

FASE 3: NORMALIZACION DE TITULOS
+-- Para cada producto:
|   +-- Comparar titulo actual vs CSV
|   +-- Aplicar TitleNormalizer
|   +-- Registrar cambios
+-- Validar con BrandingValidator

FASE 4: GENERACION DE REPORTES
+-- Calcular Health Score
+-- Generar audit_report_{timestamp}.json
+-- Actualizar metricas en ChromaDB
```

---

## 4. External Intel v2.0

Sistema de rescate de precios cuando no hay datos en CSV.

### 4.1 Cadena de Rescate

```
+-------------------------------------------------------------+
|                    EXTERNAL INTEL v2.0                      |
+-------------------------------------------------------------+
|                                                             |
|  PASO 0: CSV Priority                                       |
|  +-- Si SKU existe en CSV con precio -> USAR (no API)       |
|  +-- api_calls_saved++                                      |
|                                                             |
|  PASO 1: Tavily API                                         |
|  +-- Query: "precio {producto} repuesto moto Colombia"      |
|  +-- Timeout: 15s                                           |
|  +-- Si 429 -> Back-off exponencial                         |
|                                                             |
|  PASO 2: Perplexity API (Sanitized)                         |
|  +-- Payload sanitizado (sin caracteres especiales)         |
|  +-- Model: llama-3.1-sonar-small-128k-online               |
|  +-- Si 429 -> Back-off exponencial                         |
|                                                             |
|  PASO 3: Google Custom Search                               |
|  +-- Query: "{producto} precio Colombia repuesto moto"      |
|  +-- Extrae precios de snippets                             |
|  +-- Si 429 -> Back-off exponencial                         |
|                                                             |
|  RESULTADO: Precio mediano + source tracking                |
|                                                             |
+-------------------------------------------------------------+
```

### 4.2 Exponential Back-off

```python
MAX_RETRIES = 3
INITIAL_BACKOFF = 2  # segundos

for attempt in range(MAX_RETRIES):
    response = request()
    if response.status_code == 429:
        wait_time = INITIAL_BACKOFF * (2 ** attempt)  # 2s, 4s, 8s
        time.sleep(wait_time)
        continue
    return response
```

---

## 5. Configuracion

### 5.1 Variables de Entorno

```bash
# /opt/odi/.env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
PERPLEXITY_API_KEY=pplx-...
GOOGLE_SEARCH_API_KEY=AIza...
GOOGLE_CSE_ID=...
```

### 5.2 Cron Schedule

```bash
# /etc/cron.d/odi-cross-audit
0 0,6,12,18 * * * root /usr/bin/python3 /opt/odi/scripts/cross_audit.py --mode audit --all-15-stores >> /var/log/odi_system_audit.log 2>&1
```

### 5.3 CLI Commands

```bash
# Auditoria completa (produccion)
python3 /opt/odi/scripts/cross_audit.py --mode audit --all-15-stores

# Diagnostico sin modificar (solo lectura)
python3 /opt/odi/scripts/cross_audit.py --mode diagnostic

# Una tienda especifica
python3 /opt/odi/scripts/cross_audit.py --store YOKOMAR

# Rescate JAPAN (micro-batch)
python3 /opt/odi/scripts/japan_price_rescue.py
```

---

## 6. Metricas y Reportes

### 6.1 Health Score

```
Health Score = (productos_con_precio / total_productos) * 100

Umbrales:
- >= 90: EXCELENTE (verde)
- >= 70: BUENO (amarillo)
- < 70: CRITICO (rojo)
```

### 6.2 Archivos de Reporte

| Archivo | Contenido |
|---------|-----------|
| audit_report_{timestamp}.json | Reporte completo con GPT-4o analysis |
| srm_health_report_{timestamp}.json | Diagnostico sin modificaciones |
| production_sync_log.json | Conteo de productos por tienda |
| price_assignment_report.json | Resultados de asignacion por descripcion |

---

## 7. Tiendas del Ecosistema

| ID | Nombre | Productos | CSV Disponible |
|----|--------|-----------|----------------|
| DFG | DFG | 7,443 | Parcial (sin precios) |
| ARMOTOS | Armotos | 2,080 | Si |
| OH_IMPORT | Oh Importaciones | 2,840 | Si |
| YOKOMAR | Yokomar | 1,843 | Si (810 precios) |
| VITTON | Vitton | 1,257 | No |
| DUNA | Duna | 1,200 | No (sin precios) |
| IMBRA | Imbra | 1,121 | Si (1,094 precios) |
| BARA | Bara | 1,036 | Si (908 precios) |
| JAPAN | Japan | 734 | No (sin precios) |
| KAIQI | Kaiqi | 535 | Si (361 precios) |
| MCLMOTOS | Mclmotos | 349 | No |
| CBI | Cbi | 227 | Parcial (12 precios) |
| LEO | Leo | 120 | Parcial (6 precios) |
| STORE | Store | 66 | No |
| VAISAND | Vaisand | 50 | No |

---

## 8. Troubleshooting

### 8.1 APIs Rate Limited (429)

```bash
# Verificar estado de APIs
curl -s https://api.tavily.com/health

# Esperar reset automatico (cron 06:00 UTC)
# O ejecutar manualmente despues de reset:
python3 /opt/odi/scripts/japan_price_rescue.py
```

### 8.2 Namespace Violation

```bash
# Si aparece error de cruce de namespace:
# 1. Verificar que el SKU pertenece a la tienda correcta
# 2. Revisar el CSV fuente
grep "SKU_PROBLEMATICO" /mnt/volume_sfo3_01/.../Data/*/
```

### 8.3 Conexion SSH Inestable

```bash
# Usar ServerAliveInterval para conexiones largas
ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=10 root@64.23.170.118
```

---

## 9. Roadmap

| Version | Feature | Estado |
|---------|---------|--------|
| v4.0 | Namespace Isolation | Completado |
| v4.0 | Title Normalizer | Completado |
| v4.0 | Branding Validator | Completado |
| v4.1 | Webhook Shopify Sync | Planificado |
| v4.2 | ML Price Prediction | Planificado |
| v5.0 | Real-time Monitoring | Planificado |

---

## 10. Contacto

**Repositorio:** https://github.com/juandavidjd/extrac
**Servidor:** 64.23.170.118 (liveodi.com)
**Documentacion:** /opt/odi/docs/

---

*Generado: 21 Febrero 2026 | ODI Cross-Audit System v4.0 Enterprise*
