"use client";
import { useRef, useCallback, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_ODI_API_URL || "https://api.liveodi.com";

export function useODIVoice() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const speak = useCallback(async (text: string, voice: string = "ramona") => {
    if (isPlaying) return;

    const truncated = text.length > 500 ? text.substring(0, 497) + "..." : text;

    try {
      const resp = await fetch(`${API_URL}/odi/chat/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: truncated, voice }),
      });

      if (!resp.ok) return;

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);

      if (audioRef.current) {
        audioRef.current.pause();
        URL.revokeObjectURL(audioRef.current.src);
      }

      const audio = new Audio(url);
      audio.volume = 0.85;
      audioRef.current = audio;
      setIsPlaying(true);

      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(url);
      };

      audio.onerror = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(url);
      };

      await audio.play();
    } catch (err) {
      console.log("[ODI Voice] Audio no disponible:", err);
      setIsPlaying(false);
    }
  }, [isPlaying]);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  }, []);

  return { speak, stop, isPlaying };
}
