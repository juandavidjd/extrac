"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { fetchEcosystemStats, sendChatMessage, speakText } from "@/lib/odi-gateway";
import { ProductCard } from "./ProductCard";
import { VoiceOptIn } from "./VoiceOptIn";
import type { ChatProduct, EcosystemStats } from "@/lib/odi-gateway";

interface Message {
  role: "user" | "odi";
  content: string;
}

export function HabitatView() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [products, setProducts] = useState<ChatProduct[]>([]);
  const [inputVisible, setInputVisible] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [stats, setStats] = useState<EcosystemStats | null>(null);
  const [greeted, setGreeted] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [showVoiceOpt, setShowVoiceOpt] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const sessionRef = useRef(
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `odi_${Date.now()}`
  );

  useEffect(() => { fetchEcosystemStats().then(setStats); }, []);
  useEffect(() => { setVoiceEnabled(localStorage.getItem("odi_voice") === "true"); }, []);
  useEffect(() => {
    const t = setTimeout(() => setShowVoiceOpt(true), 2000);
    return () => clearTimeout(t);
  }, []);

  const greetOnIntent = useCallback(async () => {
    if (greeted) return;
    setGreeted(true);
    setMessages([{ role: "odi", content: "Hola." }]);
    if (voiceEnabled) await speakText("Hola.", "ramona");
  }, [greeted, voiceEnabled]);

  const revealInput = useCallback(() => {
    setInputVisible(true);
    setTimeout(() => inputRef.current?.focus(), 50);
  }, []);

  const handleFlameClick = useCallback(async () => {
    revealInput();
    await greetOnIntent();
  }, [revealInput, greetOnIntent]);

  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if (!text) return;
    setInputValue("");
    setMessages((prev) => [{ role: "user", content: text }, ...prev]);

    const result = await sendChatMessage(text, sessionRef.current);
    const response = result?.response || "No pude conectar ahora.";
    setMessages((prev) => [{ role: "odi", content: response }, ...prev]);
    sessionRef.current = result?.sessionId || sessionRef.current;
    setProducts(result?.products || []);

    if (voiceEnabled && (result?.narrative || response)) {
      await speakText(result?.narrative || response, result?.voice || "ramona");
    }
  }, [inputValue, voiceEnabled]);

  useEffect(() => {
    const handler = async (e: KeyboardEvent) => {
      if (e.key.length !== 1 || e.ctrlKey || e.metaKey || e.altKey) return;
      if (inputVisible) return;
      revealInput();
      await greetOnIntent();
      setInputValue(e.key);
      e.preventDefault();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [inputVisible, revealInput, greetOnIntent]);

  const handleVoiceActivated = useCallback(() => {
    setVoiceEnabled(true);
    localStorage.setItem("odi_voice", "true");
    setShowVoiceOpt(false);
  }, []);

  const statusText = stats
    ? `${stats.activeStores} tiendas · ${stats.products.toLocaleString("es-CO")} productos · vivo`
    : "vivo";

  return (
    <main className="min-h-screen bg-[#03070d] text-[#dbe7ff] font-sans">
      <div className="max-w-[900px] mx-auto min-h-screen grid gap-4 px-4 py-5"
           style={{ gridTemplateRows: "auto 1fr auto auto auto auto" }}>

        <header className="flex items-center justify-between gap-3">
          <span className="text-sm tracking-[0.22em] text-[#7f95bb]">LIVEODI</span>
          <span className="text-sm text-[#b6e5ff] opacity-90">{statusText}</span>
          <span className="w-2.5 h-2.5 rounded-full bg-[#3af08f] shadow-[0_0_12px_#3af08fcc] animate-pulse" />
        </header>

        <section className="text-center self-center">
          <button
            onClick={handleFlameClick}
            className="w-40 h-40 rounded-full bg-transparent border-none mx-auto mb-5 cursor-pointer"
            aria-label="Activar ODI"
          >
            <span
              className="block w-full h-full rounded-full animate-[breathe_4s_ease-in-out_infinite]"
              style={{
                background: "radial-gradient(circle at 50% 35%, #9be2ff 0%, #49c2ff 32%, #6f6dff 65%, rgba(111,109,255,0.1) 82%, transparent 100%)",
                boxShadow: "0 0 38px #4ab8ffaa, inset 0 0 35px #b8d8ff70",
              }}
            />
          </button>
          <h1 className={`text-3xl md:text-4xl font-bold transition-opacity duration-500 ${greeted ? "opacity-100" : "opacity-0"}`}>
            Soy ODI.
          </h1>
          <p className="text-[#edf5ff] min-h-[1.3rem] mt-1" aria-live="polite">
            {greeted ? messages.find((m) => m.role === "odi")?.content || "" : ""}
          </p>
        </section>

        {showVoiceOpt && !voiceEnabled && (
          <VoiceOptIn onActivated={handleVoiceActivated} />
        )}

        <section className={`transition-all duration-300 ${inputVisible ? "opacity-100" : "opacity-0 pointer-events-none"}`}>
          <label htmlFor="odiInput" className="sr-only">Escribe a ODI</label>
          <input
            ref={inputRef}
            id="odiInput"
            type="text"
            autoComplete="off"
            placeholder="..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            className="w-full rounded-xl border border-[#35537c] bg-[rgba(7,18,33,0.7)] text-[#ddebff] px-4 py-3 text-base outline-none focus:border-[#49c2ff] transition-colors"
          />
        </section>

        {products.length > 0 && (
          <section className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-2.5">
            {products.slice(0, 5).map((product, i) => (
              <ProductCard key={product.sku || i} product={product} />
            ))}
          </section>
        )}

        <section className="grid gap-1">
          {messages.map((msg, i) => (
            <article
              key={i}
              className={`py-2 max-w-[85%] ${
                msg.role === "user"
                  ? "text-right text-[#8ca0c6] ml-auto"
                  : "text-left text-[#dbe7ff]"
              }`}
            >
              {msg.content}
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
