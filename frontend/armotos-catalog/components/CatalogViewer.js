import { useState, useRef } from 'react'
import ProductPopup from './ProductPopup'

export default function CatalogViewer({ hotspotData, currentPage, onPageChange }) {
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [hoveredProduct, setHoveredProduct] = useState(null)
  const containerRef = useRef(null)

  const pageKey = `page_${currentPage}`
  const pageData = hotspotData?.hotspots?.[pageKey] || {}
  const products = pageData.products || []

  const goToPage = (delta) => {
    const pages = Object.keys(hotspotData?.hotspots || {})
      .map(k => parseInt(k.replace('page_', '')))
      .sort((a, b) => a - b)

    const currentIndex = pages.indexOf(currentPage)
    const newIndex = Math.max(0, Math.min(pages.length - 1, currentIndex + delta))
    onPageChange(pages[newIndex])
  }

  const handleHotspotClick = (product) => {
    setSelectedProduct(product)
  }

  return (
    <div className="relative">
      {/* Page Navigation */}
      <div className="flex items-center justify-center gap-4 mb-4">
        <button
          onClick={() => goToPage(-1)}
          className="px-4 py-2 bg-armotos-yellow text-gray-900 rounded-lg font-semibold hover:bg-yellow-400 transition"
        >
          ← Anterior
        </button>
        <span className="text-white font-medium">Página {currentPage}</span>
        <button
          onClick={() => goToPage(1)}
          className="px-4 py-2 bg-armotos-yellow text-gray-900 rounded-lg font-semibold hover:bg-yellow-400 transition"
        >
          Siguiente →
        </button>
      </div>

      {/* Catalog Page with Hotspots */}
      <div
        ref={containerRef}
        className="relative mx-auto bg-white rounded-lg shadow-2xl overflow-hidden"
        style={{ maxWidth: '900px' }}
      >
        {/* Page Image */}
        <img
          src={`/api/pages/${currentPage}`}
          alt={`Página ${currentPage} del catálogo`}
          className="w-full h-auto"
          onError={(e) => {
            e.target.src = '/placeholder.png'
          }}
        />

        {/* Hotspot Overlay */}
        <div className="absolute inset-0">
          {products.map((product, index) => {
            const bbox = product.bbox || {}
            const isHovered = hoveredProduct === product.codigo

            return (
              <div
                key={`${product.codigo}-${index}`}
                className={`absolute cursor-pointer transition-all duration-200 ${
                  isHovered
                    ? 'bg-armotos-yellow/40 border-2 border-armotos-yellow'
                    : 'bg-transparent hover:bg-armotos-yellow/20'
                }`}
                style={{
                  left: `${bbox.x || 0}%`,
                  top: `${bbox.y || 0}%`,
                  width: `${bbox.w || 10}%`,
                  height: `${bbox.h || 10}%`,
                }}
                onClick={() => handleHotspotClick(product)}
                onMouseEnter={() => setHoveredProduct(product.codigo)}
                onMouseLeave={() => setHoveredProduct(null)}
                title={`Código: ${product.codigo}`}
              >
                {isHovered && (
                  <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                    {product.codigo} - Click para ver
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Product Count Badge */}
        <div className="absolute top-4 right-4 bg-armotos-yellow text-gray-900 px-3 py-1 rounded-full text-sm font-semibold">
          {products.length} productos
        </div>
      </div>

      {/* Instructions */}
      <div className="text-center mt-4 text-gray-400 text-sm">
        <p>Haz clic en cualquier producto para ver detalles y agregar al carrito</p>
      </div>

      {/* Product Popup */}
      {selectedProduct && (
        <ProductPopup
          product={selectedProduct}
          pageNumber={currentPage}
          onClose={() => setSelectedProduct(null)}
        />
      )}
    </div>
  )
}
