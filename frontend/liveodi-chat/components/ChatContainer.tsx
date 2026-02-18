"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import TypingIndicator from "./TypingIndicator";
import GuardianAura from "./GuardianAura";
import FlameIndicator from "./FlameIndicator";
import { sendMessage, type ChatResponse } from "@/lib/api";
import { getSessionId, setSessionId } from "@/lib/session";
import { useODIVoice } from "@/lib/useODIVoice";

interface Message {
  role: "user" | "odi";
  text: string;
}

export default function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [guardianColor, setGuardianColor] = useState<
    "verde" | "amarillo" | "rojo" | "negro"
  >("verde");
  const [sessionId, setLocalSessionId] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { speak, stop, isPlaying } = useODIVoice();

  useEffect(() => {
    const saved = getSessionId();
    if (saved) setLocalSessionId(saved);
    const mutePref = typeof window !== "undefined" && localStorage.getItem("odi_muted");
    if (mutePref === "true") setMuted(true);
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
      setGuardianColor(
        (res.guardian_color as "verde" | "amarillo" | "rojo" | "negro") ||
          "verde"
      );

      if (!sessionId) {
        setLocalSessionId(res.session_id);
        setSessionId(res.session_id);
      }

      setMessages((prev) => [...prev, { role: "odi", text: res.response }]);

      // V13.1: Reproducir voz (async, no bloquea)
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
    <GuardianAura color={guardianColor}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-800/50">
        <div className="flex items-center gap-2">
          <FlameIndicator
            guardianColor={guardianColor}
            isThinking={loading}
            isSpeaking={isPlaying}
            size={32}
          />
          <span className="text-sm font-medium text-neutral-300 tracking-wide">
            ODI
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={toggleMute}
            className="text-neutral-500 hover:text-neutral-300 transition-colors"
            aria-label={muted ? "Activar voz" : "Silenciar voz"}
            title={muted ? "Activar voz" : "Silenciar voz"}
          >
            {muted ? (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path d="M9.547 3.062A.75.75 0 0110 3.75v12.5a.75.75 0 01-1.264.546L5.203 13.5H2.667a.75.75 0 01-.7-.48A6.985 6.985 0 011.5 10c0-.972.198-1.899.467-3.02a.75.75 0 01.7-.48h2.536l3.533-3.296a.75.75 0 01.811-.142zM13.28 7.22a.75.75 0 10-1.06 1.06L13.94 10l-1.72 1.72a.75.75 0 001.06 1.06L15 11.06l1.72 1.72a.75.75 0 001.06-1.06L16.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L15 8.94l-1.72-1.72z" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path d="M10 3.75a.75.75 0 00-1.264-.546L5.203 6.5H2.667a.75.75 0 00-.7.48 6.985 6.985 0 000 6.04.75.75 0 00.7.48h2.536l3.533 3.296A.75.75 0 0010 16.25V3.75zM15.95 5.05a.75.75 0 00-1.06 1.061 5.5 5.5 0 010 7.778.75.75 0 001.06 1.06 7 7 0 000-9.899z" />
                <path d="M13.829 7.172a.75.75 0 00-1.061 1.06 2.5 2.5 0 010 3.536.75.75 0 001.06 1.06 4 4 0 000-5.656z" />
              </svg>
            )}
          </button>
          <span className="text-xs text-neutral-600">organismo digital</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-4 pb-20">
            <FlameIndicator
              guardianColor="verde"
              isThinking={false}
              isSpeaking={false}
              size={64}
            />
            <div>
              <p className="text-neutral-400 text-sm">
                Repuestos de motos. 16,681 productos. 15 proveedores.
              </p>
              <p className="text-neutral-600 text-xs mt-1">
                Dime marca, modelo y que necesitas.
              </p>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} text={msg.text} />
        ))}

        {loading && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={loading} />
    </GuardianAura>
  );
}
