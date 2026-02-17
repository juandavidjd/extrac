// API Route: /api/hotspots
// Returns hotspot mapping data

export default async function handler(req, res) {
  try {
    // Fetch hotspot data from ODI API
    const response = await fetch('https://api.liveodi.com/catalog/armotos/hotspots')

    if (response.ok) {
      const data = await response.json()
      res.status(200).json(data)
    } else {
      // Fallback: Return sample data for development
      res.status(200).json({
        store: 'ARMOTOS',
        hotspots: {
          page_2: {
            products: [
              { codigo: '03860', bbox: { x: 10, y: 60, w: 30, h: 25 }, confidence: 0.95 },
              { codigo: '03858', bbox: { x: 55, y: 60, w: 30, h: 25 }, confidence: 0.95 }
            ]
          },
          page_7: {
            products: [
              { codigo: '04417', bbox: { x: 5, y: 15, w: 90, h: 12 }, confidence: 0.95 },
              { codigo: '04418', bbox: { x: 5, y: 27, w: 90, h: 12 }, confidence: 0.95 },
              { codigo: '04419', bbox: { x: 5, y: 39, w: 90, h: 12 }, confidence: 0.95 }
            ]
          }
        },
        summary: {
          total_expected: 2087,
          total_found: 1877,
          accuracy: 89.9
        }
      })
    }
  } catch (error) {
    console.error('Error fetching hotspots:', error)
    res.status(500).json({ error: 'Failed to load hotspot data' })
  }
}
