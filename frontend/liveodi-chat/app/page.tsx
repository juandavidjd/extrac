"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import FlameIndicator from "@/components/FlameIndicator";
import { useVivir } from "@/lib/useVivir";

export default function Home() {
  const router = useRouter();
  const [inputText, setInputText] = useState("");
  const { guardianState, ecosystemStats, isConnected } = useVivir();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleGo = () => {
    const trimmed = inputText.trim();
    if (trimmed) {
      sessionStorage.setItem("odi_initial_message", trimmed);
    }
    router.push("/habitat");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleGo();
    }
  };

  return (
    <main className="flex flex-col items-center justify-center min-h-screen px-6 text-center">
      <div
        className={`flex flex-col items-center gap-8 max-w-md transition-opacity duration-700 ${mounted ? "opacity-100" : "opacity-0"}`}
      >
        {/* Llama viva */}
        <FlameIndicator
          guardianColor={guardianState as any}
          isThinking={false}
          isSpeaking={false}
          size={120}
        />

        {/* Identidad */}
        <div>
          <h1 className="text-3xl font-serif font-semibold tracking-tight text-neutral-100">
            Soy ODI.
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            Organismo Digital Industrial.
          </p>
        </div>

        {/* Stats reales */}
        <div className="bg-neutral-900/50 rounded-xl px-5 py-2.5 text-sm text-neutral-400">
          {ecosystemStats.total_products > 0 ? (
            <>
              {ecosystemStats.total_stores} tiendas &middot;{" "}
              {ecosystemStats.total_products.toLocaleString("es-CO")} productos
              &middot;{" "}
              <span
                className={
                  isConnected ? "text-emerald-400" : "text-neutral-600"
                }
              >
                {isConnected ? "vivo" : "conectando..."}
              </span>
            </>
          ) : (
            <>15 tiendas &middot; conectando...</>
          )}
        </div>

        {/* Input directo */}
        <div className="w-full max-w-sm">
          <div className="flex items-center gap-2 bg-neutral-900 border border-neutral-800 rounded-xl px-4 py-3 focus-within:border-emerald-500/40 transition-colors">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribeme o hablame..."
              className="flex-1 bg-transparent text-neutral-200 placeholder-neutral-600 text-sm focus:outline-none"
              autoFocus
            />
            <button
              onClick={handleGo}
              className="p-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
              aria-label="Ir al habitat"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-4 h-4"
              >
                <path
                  fillRule="evenodd"
                  d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Capacidades */}
        <div className="flex gap-4 text-xs text-neutral-600">
          <span>Puedo hablar</span>
          <span>&middot;</span>
          <span>Puedo escuchar</span>
          <span>&middot;</span>
          <span>Me adapto a ti</span>
        </div>

        {/* Mantra */}
        <p className="text-xs text-neutral-700 italic">
          &ldquo;ODI no se usa. ODI se habita.&rdquo;
        </p>
      </div>
    </main>
  );
}
