"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import FlameCenter from "./FlameCenter";
import ConversationLayer from "./ConversationLayer";
import VoiceField from "./VoiceField";
import EphemeralToast from "./EphemeralToast";
import { sendMessage, type ChatResponse } from "@/lib/api";
import { useODIVoice } from "@/lib/useODIVoice";
import { useODISession, type ODIMessage } from "@/lib/useODISession";
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
  shopify_url?: string;
}

interface DisplayMessage {
  id: number;
  role: "user" | "odi";
  text: string;
  products?: Product[];
  timestamp: number;
}

export default function HabitatView() {
  const [loading, setLoading] = useState(false);
  const [muted, setMuted] = useState(false);
  const [needsInteraction, setNeedsInteraction] = useState(false);
  const greetedRef = useRef(false);
  const { speak, stop, isSpeaking } = useODIVoice();
  const { isConnected, guardianState, notifications } = useVivir();
  const {
    session_id, messages: sessionMessages, isLoaded,
    addMessage, updateSessionId, updateGuardian,
  } = useODISession();

  const messages: DisplayMessage[] = sessionMessages.map((m, i) => ({
    id: i + 1,
    role: m.role === "system" ? "odi" as const : m.role as "user" | "odi",
    text: m.content,
    products: m.cards as Product[] || [],
    timestamp: m.timestamp,
  }));

  useEffect(() => {
    const mutePref = typeof window !== "undefined" && localStorage.getItem("odi_muted");
    if (mutePref === "true") setMuted(true);
  }, []);

  // A4: Ramona greeting - only when session loaded and no messages
  useEffect(() => {
    if (!isLoaded || greetedRef.current) return;
    if (sessionMessages.length > 0) {
      greetedRef.current = true;
      return;
    }
    greetedRef.current = true;

    const greeting: ODIMessage = {
      role: "odi",
      content: "Bienvenido a ODI.",
      timestamp: Date.now(),
      narrative: "Bienvenido a ODI.",
      voice: "ramona",
    };
    addMessage(greeting);

    if (!muted) {
      const timer = setTimeout(() => {
        speak(greeting.content, "ramona", greeting.narrative)
          .catch(() => {
            setNeedsInteraction(true);
          });
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [isLoaded]);

  const handleFirstInteraction = useCallback(() => {
    if (!needsInteraction) return;
    setNeedsInteraction(false);
    speak("Bienvenido a ODI.", "ramona")
      .catch(() => {});
  }, [needsInteraction, speak]);

  const toggleMute = () => {
    const next = !muted;
    setMuted(next);
    if (typeof window !== "undefined") localStorage.setItem("odi_muted", String(next));
    if (next) stop();
  };

  const handleSend = useCallback(async (text: string) => {
    if (needsInteraction) {
      setNeedsInteraction(false);
    }

    addMessage({ role: "user", content: text, timestamp: Date.now() });
    setLoading(true);

    try {
      const res: ChatResponse = await sendMessage(text, session_id || undefined);

      if (res.session_id && res.session_id !== session_id) {
        updateSessionId(res.session_id);
      }

      addMessage({
        role: "odi",
        content: res.response,
        timestamp: Date.now(),
        narrative: res.narrative,
        cards: res.productos || [],
        voice: res.voice,
      });

      if (res.guardian_color) {
        updateGuardian(res.guardian_color);
      }

      if (!muted && res.audio_enabled) {
        speak(res.response, res.voice || "ramona", res.narrative).catch(() => {});
      }
    } catch {
      addMessage({
        role: "odi",
        content: "Conexion interrumpida. Intenta de nuevo.",
        timestamp: Date.now(),
      });
    } finally {
      setLoading(false);
    }
  }, [session_id, muted, speak, needsInteraction, addMessage, updateSessionId, updateGuardian]);

  const hasConversation = messages.length > 0 || loading;

  return (
    <div className="relative h-[100dvh] w-full bg-[#050505] overflow-hidden select-none">
      <div
        className={"absolute inset-0 pointer-events-none border-t-2 transition-colors duration-[2000ms] " +
          (guardianState === "verde" ? "border-emerald-500/20" :
           guardianState === "amarillo" ? "border-amber-500/30" :
           guardianState === "rojo" ? "border-red-500/40" :
           "border-red-900/50")
        }
      />

      <button
        onClick={(e) => { e.stopPropagation(); toggleMute(); }}
        className="absolute top-4 right-4 z-50 p-2 text-neutral-600 hover:text-neutral-300 transition-colors"
        aria-label={muted ? "Activar voz" : "Silenciar"}
      >
        {muted ? (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
            <path d="M9.547 3.062A.75.75 0 0110 3.75v12.5a.75.75 0 01-1.264.546L5.203 13.5H2.667a.75.75 0 01-.7-.48A6.985 6.985 0 011.5 10c0-.972.198-1.899.467-3.02a.75.75 0 01.7-.48h2.536l3.533-3.296a.75.75 0 01.811-.142zM13.28 7.22a.75.75 0 10-1.06 1.06L13.94 10l-1.72 1.72a.75.75 0 001.06 1.06L15 11.06l1.72 1.72a.75.75 0 001.06-1.06L16.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L15 8.94l-1.72-1.72z" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
            <path d="M10 3.75a.75.75 0 00-1.264-.546L5.203 6.5H2.667a.75.75 0 00-.7.48 6.985 6.985 0 000 6.04.75.75 0 00.7.48h2.536l3.533 3.296A.75.75 0 0010 16.25V3.75zM15.95 5.05a.75.75 0 00-1.06 1.061 5.5 5.5 0 010 7.778.75.75 0 001.06 1.06 7 7 0 000-9.899z" />
            <path d="M13.829 7.172a.75.75 0 00-1.061 1.06 2.5 2.5 0 010 3.536.75.75 0 001.06 1.06 4 4 0 000-5.656z" />
          </svg>
        )}
      </button>

      <div className="absolute top-5 left-5 z-50">
        <span
          className={"w-1.5 h-1.5 rounded-full block transition-colors duration-1000 " +
            (isConnected ? "bg-emerald-500/60" : "bg-neutral-700")
          }
        />
      </div>

      <div
        className={"absolute left-1/2 -translate-x-1/2 transition-all duration-1000 ease-in-out " +
          (hasConversation
            ? "top-8 scale-50 opacity-60"
            : "top-1/2 -translate-y-1/2 scale-100 opacity-100")
        }
      >
        <FlameCenter
          guardianColor={guardianState as any}
          isThinking={loading}
          isSpeaking={isSpeaking}
        />
      </div>

      {!hasConversation && !needsInteraction && (
        <div className="absolute left-1/2 -translate-x-1/2 top-[58%] text-center animate-[fadeIn_1.5s_ease-out]">
          <p className="text-neutral-500 text-sm tracking-wide">
            Solo hablame.
          </p>
        </div>
      )}

      {needsInteraction && (
        <div
          className="absolute inset-0 z-[60] flex flex-col items-center justify-center cursor-pointer"
          onClick={handleFirstInteraction}
        >
          <div className="animate-pulse">
            <p className="text-neutral-400 text-lg tracking-wide mt-8">
              Toca aqui
            </p>
          </div>
        </div>
      )}

      {hasConversation && (
        <ConversationLayer messages={messages} loading={loading} />
      )}

      <VoiceField onSend={handleSend} disabled={loading} isTTSActive={isSpeaking} />

      <EphemeralToast notifications={notifications} />
    </div>
  );
}
