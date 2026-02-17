import { useState, useEffect } from 'react'
import Head from 'next/head'
import CatalogViewer from '../components/CatalogViewer'
import CategoryNav from '../components/CategoryNav'

export default function Home() {
  const [hotspotData, setHotspotData] = useState(null)
  const [currentPage, setCurrentPage] = useState(2)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/hotspots')
      .then(res => res.json())
      .then(data => {
        setHotspotData(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Error loading hotspots:', err)
        setLoading(false)
      })
  }, [])

  const totalPages = hotspotData ? Object.keys(hotspotData.hotspots || {}).length : 0

  return (
    <>
      <Head>
        <title>ARMOTOS - Catálogo Interactivo</title>
        <meta name="description" content="Catálogo interactivo de repuestos ARMOTOS" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-gray-900">
        {/* Header */}
        <header className="bg-armotos-yellow py-4 px-6 shadow-lg">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-gray-900">ARMOTOS</h1>
              <span className="text-gray-700">Catálogo Interactivo</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">
                Página {currentPage} de {totalPages || '...'}
              </span>
            </div>
          </div>
        </header>

        <div className="flex">
          {/* Sidebar - Category Navigation */}
          <aside className="w-64 bg-gray-800 min-h-screen p-4 hidden lg:block">
            <CategoryNav
              hotspotData={hotspotData}
              onPageSelect={setCurrentPage}
              currentPage={currentPage}
            />
          </aside>

          {/* Main Content */}
          <main className="flex-1 p-4">
            {loading ? (
              <div className="flex items-center justify-center h-96">
                <div className="text-white text-xl">Cargando catálogo...</div>
              </div>
            ) : (
              <CatalogViewer
                hotspotData={hotspotData}
                currentPage={currentPage}
                onPageChange={setCurrentPage}
              />
            )}
          </main>
        </div>

        {/* Footer */}
        <footer className="bg-gray-800 py-4 px-6 text-center text-gray-400">
          <p>© 2026 ARMOTOS - Repuestos de Calidad para tu Motocicleta</p>
          <p className="text-sm mt-1">Powered by ODI</p>
        </footer>
      </div>
    </>
  )
}
