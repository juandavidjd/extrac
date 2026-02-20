================================================================================
                         ODI ECOSYSTEM - EXTRAC
================================================================================

Repositorio de herramientas para el ecosistema de tiendas Shopify ODI.

================================================================================
ESTRUCTURA DEL ECOSISTEMA
================================================================================

SERVIDOR: 64.23.170.118 | DOMINIO: liveodi.com

15 TIENDAS ACTIVAS (18,126 productos):
+---------------+----------+---------------+----------+
| Tienda        | Productos| Tienda        | Productos|
+---------------+----------+---------------+----------+
| DFG           | 7,445    | YOKOMAR       | 1,000    |
| ARMOTOS       | 2,080    | BARA          | 911      |
| OH_IMPORTACION| 1,414    | JAPAN         | 734      |
| VITTON        | 1,261    | MCLMOTOS      | 349      |
| DUNA          | 1,200    | CBI           | 227      |
| IMBRA         | 1,131    | KAIQI         | 138      |
| LEO           | 120      | STORE         | 66       |
| VAISAND       | 50       |               |          |
+---------------+----------+---------------+----------+

CHROMADB: 93,403 documentos indexados

================================================================================
ESTRUCTURA DEL PROYECTO
================================================================================

extrac/
├── .github/
│   └── workflows/
│       └── cross-audit.yml    # GitHub Actions workflow
├── scripts/
│   └── cross_audit.py         # Sistema Cross-Audit con GPT-4o
├── .gitignore
└── README.txt

================================================================================
CROSS-AUDIT SYSTEM
================================================================================

Sistema de auditoría cruzada que usa GPT-4o para:
- Detectar duplicados entre tiendas
- Identificar inconsistencias de precios
- Analizar salud del catálogo
- Generar recomendaciones

ENDPOINT: https://api.openai.com/v1/chat/completions
MODELO: gpt-4o
FORMATO: response_format: { "type": "json_object" }

USO:
    export OPENAI_API_KEY="sk-..."
    python scripts/cross_audit.py

================================================================================
RUTAS EN SERVIDOR
================================================================================

/opt/odi/data/orden_maestra_v6/   - JSONs productos (15 archivos)
/opt/odi/data/brands/             - Configs Shopify
/opt/odi/core/                    - Servicios principales
/mnt/volume_sfo3_01/kb/IND_MOTOS/ - PDFs técnicos

================================================================================
GITHUB
================================================================================

Repo: https://github.com/juandavidjd/extrac

Arquitectura Cross-Audit verificada el 20/02/2026

Sincronización total Claude + Codex completada con éxito.

================================================================================
