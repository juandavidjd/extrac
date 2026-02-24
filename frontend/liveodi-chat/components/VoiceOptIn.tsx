"use client";

import { speakText } from "@/lib/odi-gateway";

interface Props {
  onActivated: () => void;
}

export function VoiceOptIn({ onActivated }: Props) {
  async function handleClick() {
    try {
      const ctx = new AudioContext();
      const buf = ctx.createBuffer(1, 1, 22050);
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(ctx.destination);
      src.start();
      await ctx.close();
    } catch {}

    await speakText("Ahora puedo hablar contigo.", "ramona");
    onActivated();
  }

  return (
    <button
      onClick={handleClick}
      className="justify-self-center border-none bg-transparent text-[#666] text-[0.8rem] cursor-pointer hover:text-[#999] transition-colors"
    >
      🎙 Activar voz
    </button>
  );
}
