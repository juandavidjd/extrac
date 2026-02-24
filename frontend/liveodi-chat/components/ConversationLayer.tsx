"use client";

import { useState, useEffect, useRef } from "react";
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
  shopify_url?: string;
}

interface Message {
  id: number;
  role: "user" | "odi";
  text: string;
  products?: Product[];
  timestamp: number;
}

interface Props {
  messages: Message[];
  loading: boolean;
}

export default function ConversationLayer({ messages, loading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const toggleExpand = (id: number) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // C1: ALL messages stay in DOM — cards never removed. Fade by age.

  return (
    <div className="absolute inset-0 top-16 bottom-24 overflow-y-auto px-6 flex flex-col justify-end">
      <div className="max-w-2xl mx-auto w-full space-y-4 pb-4">
        {messages.map((msg, i) => {
          const isOdi = msg.role === "odi";
          const age = messages.length - 1 - i;
          const hasProducts = isOdi && msg.products && msg.products.length > 0;
          const baseOpacity = age >= 6 ? 0.15 : age >= 4 ? 0.3 : age === 3 ? 0.5 : age === 2 ? 0.7 : 1;
          const opacity = hasProducts ? Math.max(baseOpacity, 0.4) : baseOpacity;
          const isLong = isOdi && msg.text.length > 300;
          const isExpanded = expandedIds.has(msg.id);
          const displayText = isLong && !isExpanded
            ? msg.text.substring(0, 200) + "..."
            : msg.text;

          return (
            <div
              key={msg.id}
              className="transition-opacity duration-1000"
              style={{ opacity }}
            >
              {isOdi ? (
                <div className="space-y-2">
                  <p className="text-neutral-300 text-sm leading-relaxed whitespace-pre-wrap">
                    {displayText}
                    {isLong && (
                      <button
                        onClick={() => toggleExpand(msg.id)}
                        className="ml-2 text-emerald-500/60 hover:text-emerald-400 text-xs transition-colors"
                      >
                        {isExpanded ? "menos" : "leer m\u00e1s"}
                      </button>
                    )}
                  </p>
                  {msg.products && msg.products.length > 0 && (
                    <div className="grid grid-cols-2 gap-2 mt-2">{msg.products.map((p, i) => <ProductCard key={i} product={p as any} />)}</div>
                  )}
                </div>
              ) : (
                <div className="flex justify-end">
                  <p className="text-emerald-400/80 text-sm leading-relaxed">
                    {msg.text}
                  </p>
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div className="flex items-center gap-1.5 py-2">
            <span className="w-1.5 h-1.5 bg-emerald-500/60 rounded-full animate-pulse" />
            <span className="w-1.5 h-1.5 bg-emerald-500/40 rounded-full animate-pulse [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 bg-emerald-500/20 rounded-full animate-pulse [animation-delay:300ms]" />
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}