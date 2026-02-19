"use client";

interface Product {
  sku?: string;
  nombre?: string;
  title?: string;
  precio_cop?: number;
  price?: string | number;
  imagen_url?: string;
  fitment_summary?: string;
  proveedor?: string;
  store?: string;
  shopify_url?: string;
}

interface Props {
  products: Product[];
  onView360?: (sku: string) => void;
}

export default function ProductCard({ products, onView360 }: Props) {
  if (!products || products.length === 0) return null;

  return (
    <div className="flex gap-2 overflow-x-auto pb-2 mt-2 -mx-1 px-1">
      {products.slice(0, 5).map((p, i) => {
        const name = p.nombre || p.title || "Producto";
        const price = p.precio_cop || Number(p.price) || 0;
        const store = p.proveedor || p.store || "";
        const sku = p.sku || "";

        return (
          <div
            key={i}
            className="flex-shrink-0 w-44 bg-neutral-900/60 backdrop-blur border border-neutral-700/50 rounded-lg p-3 transition-all hover:border-emerald-500/30 hover:scale-[1.02] cursor-pointer"
            onClick={() => sku && onView360?.(sku)}
          >
            {p.imagen_url && (
              <div className="w-full h-24 rounded-md bg-neutral-800 mb-2 overflow-hidden">
                <img
                  src={p.imagen_url}
                  alt={name}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              </div>
            )}
            <div className="text-xs font-medium text-neutral-200 line-clamp-2 leading-tight">
              {name}
            </div>
            <div className="flex items-center justify-between mt-1.5">
              <span className="text-sm font-semibold text-emerald-400">
                ${price.toLocaleString("es-CO")}
              </span>
            </div>
            {store && (
              <span className="text-[10px] text-neutral-500 mt-0.5 block">
                {store}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
