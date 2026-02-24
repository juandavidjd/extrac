"use client";

import { useState } from "react";
import { requestMicrophone } from "@/lib/useODIListen";
import { useODIVoice } from "@/lib/useODIVoice";

interface Props {
  onActivated: () => void;
}

export default function VoiceOptIn({ onActivated }: Props) {
  const [status, setStatus] = useState<"idle" | "asking" | "denied" | "hidden">("idle");
  const { speak } = useODIVoice();

  if (status === "hidden") return null;

  const handleOptIn = async () => {
    setStatus("asking");

    // Unlock autoplay with silent interaction
    try {
      const ctx = new AudioContext();
      const buf = ctx.createBuffer(1, 1, 22050);
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(ctx.destination);
      src.start();
      ctx.close();
    } catch {}

    const stream = await requestMicrophone();

    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      localStorage.setItem("odi_voice_enabled", "true");
      setStatus("hidden");
      onActivated();
      speak("Ahora puedo escucharte.", "ramona").catch(() => {});
    } else {
      setStatus("denied");
      setTimeout(() => setStatus("hidden"), 3000);
    }
  };

  return (
    <div className="absolute bottom-20 left-0 right-0 z-30 flex justify-center">
      {status === "idle" && (
        <button
          onClick={handleOptIn}
          className="text-neutral-600 text-xs tracking-wide hover:text-neutral-400 transition-colors"
        >
          Activar voz
        </button>
      )}
      {status === "asking" && (
        <p className="text-neutral-600 text-xs tracking-wide animate-pulse">
          Para escucharte necesito tu microfono. No grabo nada.
        </p>
      )}
      {status === "denied" && (
        <p className="text-neutral-600 text-xs tracking-wide">
          Sin problema. Puedes escribirme.
        </p>
      )}
    </div>
  );
}
