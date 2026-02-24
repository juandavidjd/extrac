"use client";

import type { ChatProduct } from "@/lib/odi-gateway";

interface Props {
  product: ChatProduct;
}

export function ProductCard({ product }: Props) {
  return (
    <article className="border border-[#294468] bg-[rgba(7,18,33,0.6)] rounded-[10px] p-2.5">
      {product.image && (
        <img
          src={product.image}
          alt={product.title}
          loading="lazy"
          className="w-full h-[90px] object-cover rounded-md"
        />
      )}
      <h3 className="mt-1.5 mb-0 text-sm font-medium">{product.title}</h3>
      {product.sku && (
        <p className="text-[#8ca0c6] text-xs m-0">{product.sku}</p>
      )}
      {product.price != null && (
        <p className="text-[#b6e5ff] text-sm my-0.5">
          ${product.price.toLocaleString("es-CO")}
        </p>
      )}
      {product.store && (
        <p className="text-[#8ca0c6] text-xs m-0">{product.store}</p>
      )}
      {product.url && (
        <a
          href={product.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#9fd4ff] text-sm no-underline"
        >
          Ver
        </a>
      )}
    </article>
  );
}
