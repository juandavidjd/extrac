"use client";

import { ProductCard } from "./ProductCard";

interface Product {
  sku?: string;
  nombre?: string;
  title?: string;
  precio_cop?: number;
  price?: string | number;
  imagen_url?: string;
  proveedor?: string;
  store?: string;
}

interface Props {
  role: "user" | "odi";
  text: string;
  products?: Product[];
}

export default function MessageBubble({ role, text, products }: Props) {
  const isOdi = role === "odi";

  return (
    <div className={`flex ${isOdi ? "justify-start" : "justify-end"} mb-3`}>
      <div
        className={`max-w-[85%] sm:max-w-[75%] rounded-2xl text-sm leading-relaxed ${
          isOdi
            ? "bg-neutral-800/70 text-neutral-200 rounded-bl-sm"
            : "bg-emerald-600/20 text-neutral-200 border border-emerald-500/20 rounded-br-sm"
        }`}
      >
        <div className="px-4 py-3 whitespace-pre-wrap">{text}</div>
        {isOdi && products && products.length > 0 && (
          <div className="px-3 pb-3">
            <div className="grid grid-cols-2 gap-2 mt-2">{products.map((p, i) => <ProductCard key={i} product={p as any} />)}</div>
          </div>
        )}
      </div>
    </div>
  );
}
