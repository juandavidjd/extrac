/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  basePath: '/armotos',
  images: {
    domains: ['api.liveodi.com', 'cdn.shopify.com'],
    unoptimized: true
  },
  async rewrites() {
    return [
      {
        source: '/api/pages/:path*',
        destination: 'https://api.liveodi.com/catalog/ARMOTOS/pages/:path*'
      },
      {
        source: '/api/hotspots',
        destination: 'https://api.liveodi.com/catalog/ARMOTOS/hotspots'
      }
    ]
  }
}

module.exports = nextConfig
