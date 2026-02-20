"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import MessageBubble from "./MessageBubble";
import MultimodalInput from "./MultimodalInput";
import TypingIndicator from "./TypingIndicator";
import GuardianAura from "./GuardianAura";
import PresenceHeader from "./PresenceHeader";
import EcosystemPanel from "./EcosystemPanel";
import EphemeralToast from "./EphemeralToast";
import FlameIndicator from "./FlameIndicator";
import { sendMessage, type ChatResponse } from "@/lib/api";
import { getSessionId, setSessionId } from "@/lib/session";
import { useODIVoice } from "@/lib/useODIVoice";
import { useVivir } from "@/lib/useVivir";

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

interface Message {
  role: "user" | "odi";
  text: string;
  products?: Product[];
}

export default function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setLocalSessionId] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const [ecosystemOpen, setEcosystemOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { speak, stop, isPlaying } = useODIVoice();
  const {
    isConnected,
    guardianState,
    ecosystemStats,
    notifications,
  } = useVivir();

  useEffect(() => {
    const saved = getSessionId();
    if (saved) setLocalSessionId(saved);
    const mutePref =
      typeof window !== "undefined" && localStorage.getItem("odi_muted");
    if (mutePref === "true") setMuted(true);
  }, []);

  // V19: Saludo Ramona al entrar (una vez por sesión)
  useEffect(() => {
    const hasGreeted = typeof window !== "undefined" && sessionStorage.getItem("odi_greeted");
    if (!hasGreeted && !muted) {
      const timer = setTimeout(() => {
        speak("Repuestos de motos. 33 mil productos de 15 proveedores. Dime que necesitas.", "ramona");
        if (typeof window !== "undefined") {
          sessionStorage.setItem("odi_greeted", "true");
        }
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  const toggleMute = () => {
    const next = !muted;
    setMuted(next);
    if (typeof window !== "undefined") {
      localStorage.setItem("odi_muted", String(next));
    }
    if (next) stop();
  };

  const handleSend = async (text: string) => {
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);

    try {
      const res: ChatResponse = await sendMessage(text, sessionId || undefined);

      if (!sessionId) {
        setLocalSessionId(res.session_id);
        setSessionId(res.session_id);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "odi",
          text: res.response,
          products: res.productos || [],
        },
      ]);

      if (!muted && res.audio_enabled) {
        speak(res.response, res.voice || "ramona");
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "odi", text: "Error de conexion. Intenta de nuevo." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <GuardianAura color={guardianState}>
      <div className="flex h-screen">
        {/* Main area */}
        <div className="flex flex-col flex-1 min-w-0">
          {/* Header */}
          <PresenceHeader
            guardianState={guardianState}
            isConnected={isConnected}
            isThinking={loading}
            isSpeaking={isPlaying}
            muted={muted}
            onToggleMute={toggleMute}
            onToggleEcosystem={() => setEcosystemOpen(!ecosystemOpen)}
            totalStores={ecosystemStats.total_stores}
            totalProducts={ecosystemStats.total_products}
          />

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center gap-4 pb-20">
                <FlameIndicator
                  guardianColor={guardianState as any}
                  isThinking={false}
                  isSpeaking={false}
                  size={64}
                />
                <div>
                  <p className="text-neutral-400 text-sm">
                    {ecosystemStats.total_products > 0
                      ? `${ecosystemStats.total_products.toLocaleString("es-CO")} productos. ${ecosystemStats.total_stores} tiendas.`
                      : "Repuestos de motos. 15 proveedores."}
                  </p>
                  <p className="text-neutral-600 text-xs mt-1">
                    Dime marca, modelo y que necesitas.
                  </p>
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <MessageBubble
                key={i}
                role={msg.role}
                text={msg.text}
                products={msg.products}
              />
            ))}

            {loading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <MultimodalInput onSend={handleSend} disabled={loading} />
        </div>

        {/* Ecosystem panel */}
        <EcosystemPanel
          isOpen={ecosystemOpen}
          onClose={() => setEcosystemOpen(false)}
        />
      </div>

      {/* Ephemeral notifications */}
      <EphemeralToast notifications={notifications} />
    </GuardianAura>
  );
}
