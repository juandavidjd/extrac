"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import TypingIndicator from "./TypingIndicator";
import GuardianAura from "./GuardianAura";
import { sendMessage, type ChatResponse } from "@/lib/api";
import { getSessionId, setSessionId } from "@/lib/session";

interface Message {
  role: "user" | "odi";
  text: string;
}

export default function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [guardianColor, setGuardianColor] = useState("verde");
  const [sessionId, setLocalSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const saved = getSessionId();
    if (saved) setLocalSessionId(saved);
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  const handleSend = async (text: string) => {
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);

    try {
      const res: ChatResponse = await sendMessage(text, sessionId || undefined);
      setGuardianColor(res.guardian_color);

      if (!sessionId) {
        setLocalSessionId(res.session_id);
        setSessionId(res.session_id);
      }

      setMessages((prev) => [...prev, { role: "odi", text: res.response }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "odi",
          text: "Error de conexion. Intenta de nuevo.",
        },
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
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-sm font-medium text-neutral-300 tracking-wide">
            ODI
          </span>
        </div>
        <span className="text-xs text-neutral-600">organismo digital</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-4 pb-20">
            <div className="w-3 h-3 rounded-full bg-emerald-500/60 animate-pulse" />
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
