import { useState, useEffect } from 'react'

export default function ProductPopup({ product, pageNumber, onClose }) {
  const [quantity, setQuantity] = useState(1)
  const [productDetails, setProductDetails] = useState(null)
  const [loading, setLoading] = useState(true)
  const [addingToCart, setAddingToCart] = useState(false)

  useEffect(() => {
    // Fetch product details from Shopify
    fetch(`/api/product/${product.codigo}`)
      .then(res => res.json())
      .then(data => {
        setProductDetails(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Error fetching product:', err)
        setLoading(false)
      })
  }, [product.codigo])

  const handleAddToCart = async () => {
    if (!productDetails?.variantId) return

    setAddingToCart(true)
    try {
      const response = await fetch('/api/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          variantId: productDetails.variantId,
          quantity: quantity
        })
      })

      if (response.ok) {
        alert(`¡${quantity} unidad(es) agregada(s) al carrito!`)
        onClose()
      }
    } catch (err) {
      console.error('Error adding to cart:', err)
      alert('Error al agregar al carrito')
    }
    setAddingToCart(false)
  }

  const handleBuyNow = () => {
    if (!productDetails?.checkoutUrl) return
    window.open(productDetails.checkoutUrl, '_blank')
  }

  const formatPrice = (price) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0
    }).format(price)
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-armotos-yellow p-4 rounded-t-2xl flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Detalles del Producto</h2>
          <button
            onClick={onClose}
            className="text-gray-700 hover:text-gray-900 text-2xl font-bold"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-armotos-yellow border-t-transparent mx-auto"></div>
              <p className="mt-4 text-gray-600">Cargando producto...</p>
            </div>
          ) : (
            <>
              {/* Product Info */}
              <div className="mb-6">
                <div className="flex items-start gap-4">
                  <div className="bg-gray-100 rounded-lg p-2 text-center">
                    <span className="text-xs text-gray-500">Código</span>
                    <p className="font-bold text-lg">{product.codigo}</p>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-gray-900">
                      {productDetails?.title || `Producto ${product.codigo}`}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">
                      Página {pageNumber} del catálogo
                    </p>
                  </div>
                </div>
              </div>

              {/* Price */}
              <div className="bg-green-50 rounded-xl p-4 mb-6">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Precio:</span>
                  <span className="text-3xl font-bold text-green-600">
                    {productDetails?.price
                      ? formatPrice(productDetails.price)
                      : 'Consultar'}
                  </span>
                </div>
                {productDetails?.comparePrice && (
                  <div className="text-right">
                    <span className="text-sm text-gray-400 line-through">
                      {formatPrice(productDetails.comparePrice)}
                    </span>
                  </div>
                )}
              </div>

              {/* Quantity Selector */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Cantidad:
                </label>
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => setQuantity(Math.max(1, quantity - 1))}
                    className="w-10 h-10 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center text-xl font-bold"
                  >
                    -
                  </button>
                  <span className="text-2xl font-bold w-12 text-center">{quantity}</span>
                  <button
                    onClick={() => setQuantity(quantity + 1)}
                    className="w-10 h-10 rounded-full bg-gray-200 hover:bg-gray-300 flex items-center justify-center text-xl font-bold"
                  >
                    +
                  </button>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-3">
                <button
                  onClick={handleAddToCart}
                  disabled={addingToCart || !productDetails}
                  className="w-full py-3 bg-armotos-yellow text-gray-900 rounded-xl font-bold text-lg hover:bg-yellow-400 transition disabled:opacity-50"
                >
                  {addingToCart ? 'Agregando...' : '🛒 Agregar al Carrito'}
                </button>
                <button
                  onClick={handleBuyNow}
                  disabled={!productDetails}
                  className="w-full py-3 bg-green-600 text-white rounded-xl font-bold text-lg hover:bg-green-700 transition disabled:opacity-50"
                >
                  ⚡ Comprar Ahora
                </button>
              </div>

              {/* Compatibility Info */}
              {productDetails?.compatibility && (
                <div className="mt-6 p-4 bg-gray-50 rounded-xl">
                  <h4 className="font-semibold text-gray-700 mb-2">🏍️ Compatibilidad:</h4>
                  <p className="text-sm text-gray-600">{productDetails.compatibility}</p>
                </div>
              )}

              {/* WhatsApp Contact */}
              <div className="mt-6 text-center">
                <a
                  href={`https://wa.me/573175206953?text=Hola! Me interesa el producto ${product.codigo} de la página ${pageNumber} del catálogo ARMOTOS`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-green-600 hover:text-green-700"
                >
                  <span className="text-2xl">📱</span>
                  <span>¿Dudas? Escríbenos por WhatsApp</span>
                </a>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
