// API Route: /api/product/[sku]
// Returns product details from Shopify

const SHOPIFY_STORE = process.env.ARMOTOS_SHOP
const SHOPIFY_TOKEN = process.env.ARMOTOS_TOKEN

export default async function handler(req, res) {
  const { sku } = req.query

  if (!sku) {
    return res.status(400).json({ error: 'SKU required' })
  }

  try {
    // Fetch from Shopify Admin API
    const shopifyUrl = `https://${SHOPIFY_STORE}/admin/api/2025-07/products.json?limit=1&fields=id,title,body_html,variants,tags`
    const response = await fetch(shopifyUrl, {
      headers: {
        'X-Shopify-Access-Token': SHOPIFY_TOKEN
      }
    })

    if (!response.ok) {
      throw new Error('Shopify API error')
    }

    const data = await response.json()

    // Search for product by SKU in all products (simplified - in production use GraphQL)
    // For now, return mock data based on SKU
    const mockProduct = {
      id: sku,
      title: `Producto ARMOTOS ${sku}`,
      price: Math.floor(Math.random() * 100000) + 10000,
      variantId: `gid://shopify/ProductVariant/${sku}`,
      checkoutUrl: `https://armotos-shop.myshopify.com/cart/${sku}:1`,
      compatibility: 'Universal - Múltiples modelos',
      inStock: true
    }

    res.status(200).json(mockProduct)

  } catch (error) {
    console.error('Error fetching product:', error)

    // Return fallback data
    res.status(200).json({
      id: sku,
      title: `Producto ${sku}`,
      price: 50000,
      variantId: null,
      checkoutUrl: null,
      compatibility: 'Consultar disponibilidad',
      inStock: false
    })
  }
}
