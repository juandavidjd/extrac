// API Route: /api/pages/[page]
// Serves catalog page images

import fs from 'fs'
import path from 'path'

export default async function handler(req, res) {
  const { page } = req.query

  try {
    // In production, serve from CDN or ODI API
    const imageUrl = `https://api.liveodi.com/catalog/armotos/pages/${page}.png`

    // Proxy the image
    const response = await fetch(imageUrl)

    if (response.ok) {
      const buffer = await response.arrayBuffer()
      res.setHeader('Content-Type', 'image/png')
      res.setHeader('Cache-Control', 'public, max-age=86400')
      res.send(Buffer.from(buffer))
    } else {
      // Return placeholder
      res.redirect('/placeholder.png')
    }
  } catch (error) {
    console.error('Error serving page image:', error)
    res.status(500).json({ error: 'Failed to load page image' })
  }
}

export const config = {
  api: {
    responseLimit: false,
  },
}
