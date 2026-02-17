import { useState, useMemo } from 'react'

const CATEGORIES = {
  'Frenos': { icon: '🛑', pages: [] },
  'Transmision': { icon: '⚙️', pages: [] },
  'Iluminacion': { icon: '💡', pages: [] },
  'Suspension': { icon: '🔧', pages: [] },
  'Electrico': { icon: '⚡', pages: [] },
  'Llantas': { icon: '🔘', pages: [] },
  'Motor': { icon: '🏎️', pages: [] },
  'Herramientas': { icon: '🔨', pages: [] },
  'Accesorios': { icon: '✨', pages: [] },
}

export default function CategoryNav({ hotspotData, onPageSelect, currentPage }) {
  const [expandedCategory, setExpandedCategory] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')

  // Build page list from hotspot data
  const pages = useMemo(() => {
    if (!hotspotData?.hotspots) return []
    return Object.keys(hotspotData.hotspots)
      .map(k => ({
        number: parseInt(k.replace('page_', '')),
        productCount: hotspotData.hotspots[k].products?.length || 0
      }))
      .sort((a, b) => a.number - b.number)
  }, [hotspotData])

  // Filter pages by search
  const filteredPages = useMemo(() => {
    if (!searchTerm) return pages
    const term = searchTerm.toLowerCase()
    return pages.filter(p =>
      p.number.toString().includes(term)
    )
  }, [pages, searchTerm])

  return (
    <div className="text-white">
      <h2 className="text-lg font-bold mb-4 text-armotos-yellow">📚 Navegación</h2>

      {/* Search */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="Buscar página..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-3 py-2 bg-gray-700 rounded-lg text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-armotos-yellow"
        />
      </div>

      {/* Quick Stats */}
      <div className="bg-gray-700 rounded-lg p-3 mb-4">
        <div className="text-xs text-gray-400">Total páginas</div>
        <div className="text-2xl font-bold text-armotos-yellow">{pages.length}</div>
        <div className="text-xs text-gray-400 mt-1">
          {hotspotData?.summary?.total_found || 0} productos mapeados
        </div>
      </div>

      {/* Page List */}
      <div className="space-y-1 max-h-96 overflow-y-auto pr-2">
        <h3 className="text-sm font-semibold text-gray-400 mb-2">Páginas del Catálogo</h3>
        {filteredPages.map(page => (
          <button
            key={page.number}
            onClick={() => onPageSelect(page.number)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
              currentPage === page.number
                ? 'bg-armotos-yellow text-gray-900 font-semibold'
                : 'hover:bg-gray-700'
            }`}
          >
            <div className="flex items-center justify-between">
              <span>Página {page.number}</span>
              <span className={`text-xs ${
                currentPage === page.number ? 'text-gray-700' : 'text-gray-500'
              }`}>
                {page.productCount} prod.
              </span>
            </div>
          </button>
        ))}
      </div>

      {/* Categories (Future) */}
      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-400 mb-2">Categorías SRM</h3>
        <div className="space-y-1">
          {Object.entries(CATEGORIES).map(([name, { icon }]) => (
            <div
              key={name}
              className="px-3 py-2 rounded-lg text-sm text-gray-400 flex items-center gap-2"
            >
              <span>{icon}</span>
              <span>{name}</span>
              <span className="text-xs ml-auto">Próximamente</span>
            </div>
          ))}
        </div>
      </div>

      {/* WhatsApp Help */}
      <div className="mt-6 p-3 bg-green-900/30 rounded-lg">
        <p className="text-sm text-green-400">¿Necesitas ayuda?</p>
        <a
          href="https://wa.me/573175206953?text=Hola! Necesito ayuda con el catálogo ARMOTOS"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-white hover:text-green-400 flex items-center gap-2 mt-1"
        >
          📱 WhatsApp ARMOTOS
        </a>
      </div>
    </div>
  )
}
