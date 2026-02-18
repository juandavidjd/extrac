"use client";

interface Product {
  title: string;
  price: string;
  store: string;
  sku?: string;
}

interface Props {
  products: Product[];
}

export default function ProductCard({ products }: Props) {
  if (!products || products.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 mt-2">
      {products.map((p, i) => (
        <div
          key={i}
          className="bg-neutral-800/50 border border-neutral-700/50 rounded-lg px-4 py-3 transition-colors hover:border-emerald-500/30"
        >
          <div className="text-sm font-medium text-neutral-200">{p.title}</div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-emerald-400 font-semibold">
              ${Number(p.price).toLocaleString("es-CO")} COP
            </span>
            {p.store && (
              <span className="text-xs text-neutral-500">
                {p.store}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
