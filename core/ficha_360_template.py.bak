#!/usr/bin/env python3
"""
Template Ficha 360° Estándar - 7 secciones con emojis
Usado para TODAS las empresas del ecosistema ODI
"""

# Blacklist de frases genéricas (Gate)
BLACKLIST_PHRASES = [
    'consultar compatibilidad',
    'compatible según ficha técnica',
    'ver ficha técnica',
    'consultar ficha',
    'repuesto de calidad',
    'producto de calidad',
    'alta calidad',
    'excelente producto',
    'descripción del producto',
    'sin descripción',
    'n/a',
    'no disponible',
]

def is_generic(text):
    if not text:
        return True
    text_lower = text.lower().strip()
    for phrase in BLACKLIST_PHRASES:
        if phrase in text_lower:
            return True
    return len(text.strip()) < 5

def detect_category(title):
    title_lower = title.lower()
    categories = {
        'filtro': 'filtro',
        'aceite': 'aceite',
        'freno': 'freno',
        'pastilla': 'freno',
        'cadena': 'cadena',
        'kit': 'kit',
        'bujia': 'bujia',
        'suspension': 'suspension',
        'amortiguador': 'suspension',
        'espejo': 'espejo',
        'faro': 'electrico',
        'direccional': 'electrico',
        'cable': 'cable',
        'empaque': 'empaque',
        'resorte': 'suspension',
        'palanca': 'control',
        'manigueta': 'control',
    }
    for key, cat in categories.items():
        if key in title_lower:
            return cat
    return 'general'

def get_info_tecnica(title, category):
    info_map = {
        'filtro': 'Filtro de alta eficiencia para protección del motor.',
        'aceite': 'Lubricante de grado automotriz para máximo rendimiento.',
        'freno': 'Sistema de frenado certificado para uso en motocicletas.',
        'cadena': 'Cadena de transmisión reforzada con tratamiento térmico.',
        'bujia': 'Bujía de encendido con electrodo de alta conductividad.',
        'suspension': 'Componente de suspensión para absorción de impactos.',
        'espejo': 'Espejo retrovisor con cristal de alta definición.',
        'electrico': 'Componente eléctrico con conexiones reforzadas.',
        'cable': 'Cable de transmisión con recubrimiento resistente.',
        'empaque': 'Empaque de sellado con material resistente a temperatura.',
        'control': 'Componente de control ergonómico.',
        'kit': 'Kit completo con todos los componentes necesarios.',
        'general': 'Repuesto fabricado bajo estándares de calidad automotriz.',
    }
    return info_map.get(category, info_map['general'])

def get_beneficios(category):
    beneficios_map = {
        'filtro': ['Filtra impurezas efectivamente', 'Prolonga vida del motor', 'Fácil reemplazo'],
        'freno': ['Frenado seguro y eficiente', 'Resistente al desgaste', 'Instalación directa'],
        'cadena': ['Alta resistencia a la tracción', 'Transmisión suave', 'Larga durabilidad'],
        'suspension': ['Absorción de impactos', 'Manejo estable', 'Confort de conducción'],
        'electrico': ['Conexión segura', 'Alta visibilidad', 'Larga vida útil'],
    }
    return beneficios_map.get(category, ['Durabilidad garantizada', 'Ajuste exacto', 'Fácil instalación'])

def build_ficha_360(title, sku, compatibilidad, empresa='ODI', extra_info=None):
    """
    Genera HTML de Ficha 360° con 7 secciones estándar
    """
    extra = extra_info or {}
    
    # Detect category from title
    category = detect_category(title)
    
    # 1. DESCRIPCIÓN
    descripcion = extra.get('descripcion', f'{title}. Repuesto original para motocicleta.')
    
    # 2. INFO TÉCNICA
    info_tecnica = extra.get('info_tecnica', get_info_tecnica(title, category))
    
    # 3. COMPATIBILIDAD - NO modificar si viene llena
    if is_generic(compatibilidad):
        compatibilidad = 'Universal'
    
    # 4. ESPECIFICACIONES
    specs = extra.get('especificaciones', {
        'SKU': sku,
        'Marca': empresa,
        'Condición': 'Nuevo',
    })
    if 'SKU' not in specs:
        specs['SKU'] = sku
    if 'Marca' not in specs:
        specs['Marca'] = empresa
    
    # 5. BENEFICIOS
    beneficios = extra.get('beneficios', get_beneficios(category))
    
    # 6. INSTALACIÓN
    instalacion = extra.get('instalacion', 'Se recomienda instalación por técnico certificado. Verificar compatibilidad antes de instalar.')
    
    # 7. PROVEEDOR
    proveedor = extra.get('proveedor', {
        'nombre': empresa,
        'garantia': '30 días por defectos de fábrica',
        'envio': 'Envío a toda Colombia. 2-5 días hábiles.',
        'soporte': 'Asesoría técnica por WhatsApp',
    })
    
    # BUILD HTML
    nl = chr(10)
    html = f'''<div class="ficha-360">
<h2>📋 Descripción</h2>
<p>{descripcion}</p>

<h2>🔧 Info Técnica</h2>
<p>{info_tecnica}</p>

<h2>🏍️ Compatibilidad</h2>
<p><strong>{compatibilidad}</strong></p>

<h2>📐 Especificaciones</h2>
<ul>
'''
    for key, val in specs.items():
        html += f'<li><strong>{key}:</strong> {val}</li>{nl}'
    
    html += f'''</ul>

<h2>✅ Beneficios</h2>
<ul>
'''
    for b in beneficios:
        html += f'<li>{b}</li>{nl}'
    
    html += f'''</ul>

<h2>🔩 Instalación</h2>
<p>{instalacion}</p>

<h2>ℹ️ Proveedor</h2>
<ul>
<li><strong>Proveedor:</strong> {proveedor.get('nombre', empresa)}</li>
<li><strong>Garantía:</strong> {proveedor.get('garantia', '30 días')}</li>
<li><strong>Envío:</strong> {proveedor.get('envio', 'Colombia')}</li>
<li><strong>Soporte:</strong> {proveedor.get('soporte', 'WhatsApp')}</li>
</ul>
</div>'''
    
    return html


if __name__ == '__main__':
    # Test
    html = build_ficha_360(
        'Resorte Pedal Freno AKT 100',
        '04101',
        'AKT 100',
        'ARMOTOS'
    )
    print(html)
