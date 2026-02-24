"use client";

import { useEcosystem } from "@/lib/useEcosystem";

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function EcosystemPanel({ isOpen, onClose }: Props) {
  const { stores, totalProducts, totalStores, loading } = useEcosystem();

  return (
    <>
      {/* Backdrop mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div
        className={`fixed right-0 top-0 h-full w-80 bg-neutral-950 border-l border-neutral-800 z-40 transition-transform duration-300 overflow-y-auto ${
          isOpen ? "translate-x-0" : "translate-x-full"
        } lg:relative lg:translate-x-0 ${isOpen ? "lg:block" : "lg:hidden"}`}
      >
        <div className="p-4">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-neutral-200">
              Ecosistema ODI
            </h2>
            <button
              onClick={onClose}
              className="text-neutral-500 hover:text-neutral-300 lg:hidden"
              aria-label="Cerrar panel"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-5 h-5"
              >
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-2 mb-4">
            <div className="bg-neutral-900 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-emerald-400">
                {totalStores}
              </div>
              <div className="text-xs text-neutral-500">tiendas</div>
            </div>
            <div className="bg-neutral-900 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-emerald-400">
                {totalProducts.toLocaleString("es-CO")}
              </div>
              <div className="text-xs text-neutral-500">productos</div>
            </div>
          </div>

          {/* Stores list */}
          {loading ? (
            <div className="text-neutral-500 text-sm text-center py-4">
              Cargando ecosistema...
            </div>
          ) : (
            <div className="space-y-1">
              {stores.map((store) => (
                <div
                  key={store.id}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-neutral-900 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: store.palette.primary }}
                    />
                    <span className="text-sm text-neutral-300 group-hover:text-neutral-100">
                      {store.name}
                    </span>
                  </div>
                  <span className="text-xs text-neutral-600">
                    {store.products_count.toLocaleString("es-CO")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
