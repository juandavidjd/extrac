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
        {/* Flame */}
        <FlameIndicator
          guardianColor={guardianState as any}
          isThinking={false}
          isSpeaking={false}
          size={120}
        />

        {/* Identity */}
        <div>
          <h1 className="text-3xl font-serif font-semibold tracking-tight text-neutral-100">
            Soy ODI.
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            Organismo Digital Industrial.
          </p>
        </div>

        {/* Stats - dynamic from Gateway */}
        <div className="text-sm text-neutral-500">
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
                {isConnected ? "vivo" : "..."}
              </span>
            </>
          ) : (
            <span className={isConnected ? "text-emerald-400/60" : "text-neutral-600"}>
              {isConnected ? "vivo" : "..."}
            </span>
          )}
        </div>

        {/* Subtle entry */}
        <div className="w-full max-w-sm">
          <div
            className="flex items-center gap-2 border-b border-neutral-800/50 px-2 py-3 focus-within:border-neutral-600 transition-colors cursor-pointer"
            onClick={() => !inputText.trim() && handleGo()}
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="..."
              className="flex-1 bg-transparent text-neutral-300 placeholder-neutral-700 text-sm focus:outline-none"
            />
            <button
              onClick={handleGo}
              className="p-1 text-neutral-600 hover:text-neutral-400 transition-colors"
              aria-label="Entrar"
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

        {/* Mantra */}
        <p className="text-xs text-neutral-700 italic">
          &ldquo;ODI no se usa. ODI se habita.&rdquo;
        </p>
      </div>
    </main>
  );
}
