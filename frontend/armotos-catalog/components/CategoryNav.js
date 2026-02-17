import { useState, useEffect, useMemo } from 'react'

export default function CategoryNav({ hotspotData, onPageSelect, currentPage }) {
  const [expandedCategory, setExpandedCategory] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [srmIndex, setSrmIndex] = useState(null)

  // Fetch SRM index
  useEffect(() => {
    fetch('/armotos/api/srm-index')
      .then(res => res.json())
      .then(data => setSrmIndex(data))
      .catch(err => console.error('Failed to load SRM index:', err))
  }, [])

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

  // Filter pages by search or category
  const filteredPages = useMemo(() => {
    if (!searchTerm) return pages
    const term = searchTerm.toLowerCase()
    return pages.filter(p => p.number.toString().includes(term))
  }, [pages, searchTerm])

  const handleCategoryClick = (catName) => {
    if (expandedCategory === catName) {
      setExpandedCategory(null)
    } else {
      setExpandedCategory(catName)
      // Navigate to first page of category
      if (srmIndex?.categories?.[catName]?.first_page) {
        onPageSelect(srmIndex.categories[catName].first_page)
      }
    }
  }

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
          {srmIndex?.total_products || 0} productos mapeados
        </div>
      </div>

      {/* SRM Categories */}
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-gray-400 mb-2">Categorías SRM</h3>
        <div className="space-y-1">
          {srmIndex?.categories && Object.entries(srmIndex.categories).map(([name, data]) => (
            <div key={name}>
              <button
                onClick={() => handleCategoryClick(name)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition flex items-center gap-2 ${
                  expandedCategory === name
                    ? 'bg-armotos-yellow text-gray-900 font-semibold'
                    : 'hover:bg-gray-700'
                }`}
              >
                <span>{data.icon}</span>
                <span className="flex-1">{name}</span>
                <span className={`text-xs ${expandedCategory === name ? 'text-gray-700' : 'text-gray-500'}`}>
                  {data.count}
                </span>
                <span className={`text-xs ${expandedCategory === name ? 'text-gray-700' : 'text-gray-500'}`}>
                  {expandedCategory === name ? '▼' : '▶'}
                </span>
              </button>

              {/* Expanded category pages */}
              {expandedCategory === name && (
                <div className="ml-4 mt-1 space-y-1 max-h-40 overflow-y-auto">
                  {data.pages.slice(0, 20).map(pageNum => (
                    <button
                      key={pageNum}
                      onClick={() => onPageSelect(pageNum)}
                      className={`w-full text-left px-2 py-1 rounded text-xs transition ${
                        currentPage === pageNum
                          ? 'bg-gray-600 text-armotos-yellow'
                          : 'hover:bg-gray-700 text-gray-300'
                      }`}
                    >
                      Pág. {pageNum}
                    </button>
                  ))}
                  {data.pages.length > 20 && (
                    <div className="text-xs text-gray-500 px-2">
                      +{data.pages.length - 20} más...
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Page List (when searching) */}
      {searchTerm && (
        <div className="space-y-1 max-h-48 overflow-y-auto pr-2 mb-4">
          <h3 className="text-sm font-semibold text-gray-400 mb-2">Resultados</h3>
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
                <span className={`text-xs ${currentPage === page.number ? 'text-gray-700' : 'text-gray-500'}`}>
                  {page.productCount} prod.
                </span>
              </div>
            </button>
          ))}
        </div>
      )}

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
