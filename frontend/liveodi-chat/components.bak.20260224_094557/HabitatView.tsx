"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import FlameCenter from "./FlameCenter";
import ConversationLayer from "./ConversationLayer";
import VoiceField from "./VoiceField";
import OnboardingOverlay from "./OnboardingOverlay";
import VoiceOptIn from "./VoiceOptIn";
import EphemeralToast from "./EphemeralToast";
import { sendMessage, type ChatResponse } from "@/lib/api";
import { useODIVoice } from "@/lib/useODIVoice";
import { useODISession, type ODIMessage } from "@/lib/useODISession";
import { useVivir } from "@/lib/useVivir";

interface ODIProfile {
  industry: "motos" | "salud" | "otro";
  hasBusiness: boolean;
  firstVisit: string;
}

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

const API_URL = process.env.NEXT_PUBLIC_ODI_API_URL || "https://api.liveodi.com";

async function fetchGatewayStats(): Promise<{ products: number; stores: number } | null> {
  try {
    const res = await fetch(`${API_URL}/odi/v1/ecosystem/stores`);
    if (!res.ok) return null;
    const data = await res.json();
    const stores = Array.isArray(data) ? data : data.stores || data.data || [];
    const active = stores.filter((s: any) => (s.products_count || s.active || s.total || 0) > 0);
    const total = stores.reduce((sum: number, s: any) => sum + (s.products_count || s.active || s.total || 0), 0);
    return { products: total, stores: active.length };
  } catch {
    return null;
  }
}

function delay(ms: number): Promise<void> {
  return new Promise(r => setTimeout(r, ms));
}

export default function HabitatView() {
  const [loading, setLoading] = useState(false);
  const [muted, setMuted] = useState(false);
  const [phase, setPhase] = useState<"loading" | "onboarding" | "awakening" | "ready">("loading");
  const [profile, setProfile] = useState<ODIProfile | null>(null);
  const [flameIntensity, setFlameIntensity] = useState(0.5);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [showVoiceOptIn, setShowVoiceOptIn] = useState(false);
  const awakenedRef = useRef(false);
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

  // Load profile and determine phase
  useEffect(() => {
    if (!isLoaded) return;
    const mutePref = typeof window !== "undefined" && localStorage.getItem("odi_muted");
    if (mutePref === "true") setMuted(true);
    const voicePref = typeof window !== "undefined" && localStorage.getItem("odi_voice_enabled");
    if (voicePref === "true") setVoiceEnabled(true);

    const saved = localStorage.getItem("odi_profile");
    if (saved) {
      try {
        const p: ODIProfile = JSON.parse(saved);
        setProfile(p);
        if (sessionMessages.length > 0) {
          setFlameIntensity(1.0);
          setPhase("ready");
        } else {
          setPhase("awakening");
        }
      } catch {
        setPhase("onboarding");
      }
    } else {
      setPhase("onboarding");
    }
  }, [isLoaded]);

  // Awakening sequence
  useEffect(() => {
    if (phase !== "awakening" || awakenedRef.current) return;
    if (!profile) return;
    awakenedRef.current = true;

    const isFirstEver = profile.firstVisit && (Date.now() - new Date(profile.firstVisit).getTime() < 60000);

    (async () => {
      setFlameIntensity(0.5);
      await delay(300);
      setFlameIntensity(1.0);

      if (isFirstEver) {
        await delay(500);
        addMessage({ role: "odi", content: "Hola.", timestamp: Date.now() });
        await delay(800);
        addMessage({ role: "odi", content: "Soy ODI.", timestamp: Date.now() });
        await delay(600);

        const stats = await fetchGatewayStats();
        let contextMsg: string;
        if (profile.industry === "motos" && stats) {
          contextMsg = stats.products.toLocaleString() + " productos de " + stats.stores + " proveedores. \u00BFQu\u00E9 necesitas?";
        } else if (profile.industry === "motos") {
          contextMsg = "\u00BFQu\u00E9 necesitas?";
        } else if (profile.industry === "salud") {
          contextMsg = "Puedo ayudarte con salud dental y bruxismo. \u00BFQu\u00E9 necesitas?";
        } else {
          contextMsg = "\u00BFEn qu\u00E9 puedo ayudarte?";
        }
        addMessage({ role: "odi", content: contextMsg, timestamp: Date.now() });
      } else {
        await delay(300);
        addMessage({ role: "odi", content: "Hola.", timestamp: Date.now() });
        await delay(400);

        let returnMsg: string;
        if (profile.industry === "motos") {
          returnMsg = "\u00BFQu\u00E9 necesitas hoy?";
        } else if (profile.industry === "salud") {
          returnMsg = "\u00BFC\u00F3mo te ayudo hoy?";
        } else {
          returnMsg = "\u00BFEn qu\u00E9 te ayudo?";
        }
        addMessage({ role: "odi", content: returnMsg, timestamp: Date.now() });
      }

      setPhase("ready");

      if (!voiceEnabled) {
        await delay(2000);
        setShowVoiceOptIn(true);
      }
    })();
  }, [phase, profile]);

  const handleOnboardingComplete = (p: ODIProfile) => {
    setProfile(p);
    setPhase("awakening");
  };

  const handleVoiceActivated = () => {
    setVoiceEnabled(true);
    setShowVoiceOptIn(false);
  };

  const toggleMute = () => {
    const next = !muted;
    setMuted(next);
    if (typeof window !== "undefined") localStorage.setItem("odi_muted", String(next));
    if (next) stop();
  };

  const handleSend = useCallback(async (text: string) => {
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
  }, [session_id, muted, speak, addMessage, updateSessionId, updateGuardian]);

  const hasConversation = messages.length > 0 || loading;

  if (phase === "loading") {
    return <div className="h-[100dvh] w-full bg-black" />;
  }

  return (
    <div className="relative h-[100dvh] w-full bg-[#050505] overflow-hidden select-none">
      {phase === "onboarding" && (
        <OnboardingOverlay onComplete={handleOnboardingComplete} />
      )}

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
        style={{ opacity: phase === "onboarding" ? 0.3 : flameIntensity }}
      >
        <FlameCenter
          guardianColor={guardianState as any}
          isThinking={loading}
          isSpeaking={isSpeaking}
        />
      </div>

      {hasConversation && (
        <ConversationLayer messages={messages} loading={loading} />
      )}

      {phase === "ready" && (
        <VoiceField
          onSend={handleSend}
          disabled={loading}
          isTTSActive={isSpeaking}
        />
      )}

      {showVoiceOptIn && phase === "ready" && (
        <VoiceOptIn onActivated={handleVoiceActivated} />
      )}

      <EphemeralToast notifications={notifications} />
    </div>
  );
}
