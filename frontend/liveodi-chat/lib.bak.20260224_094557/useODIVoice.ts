"use client";
import { useRef, useCallback, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_ODI_API_URL || "https://api.liveodi.com";

export function useODIVoice() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const isPlayingRef = useRef(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const speak = useCallback(async (text: string, voice: string = "ramona", narrative?: string): Promise<void> => {
    if (isPlayingRef.current) return;
    isPlayingRef.current = true;
    setIsSpeaking(true);

    const ttsText = narrative || (text.length > 200 ? text.substring(0, 197) + "..." : text);
    const truncated = ttsText.length > 300 ? ttsText.substring(0, 297) + "..." : ttsText;

    try {
      const resp = await fetch(`${API_URL}/odi/chat/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ narrative: truncated, text: truncated, voice }),
      });

      if (!resp.ok) throw new Error("TTS response not ok");

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);

      // Clean up previous audio
      if (audioRef.current) {
        audioRef.current.pause();
        URL.revokeObjectURL(audioRef.current.src);
        audioRef.current = null;
      }

      const audio = new Audio(url);
      audio.volume = 0.85;
      audioRef.current = audio;

      // Revoke blob ONLY when playback ends or errors — never before
      audio.onended = () => {
        URL.revokeObjectURL(url);
        isPlayingRef.current = false;
        setIsSpeaking(false);
        audioRef.current = null;
      };

      audio.onerror = (e) => {
        URL.revokeObjectURL(url);
        isPlayingRef.current = false;
        setIsSpeaking(false);
        audioRef.current = null;
        console.error("Voice playback error:", e);
      };

      await audio.play();
    } catch (err) {
      if (audioRef.current) {
        URL.revokeObjectURL(audioRef.current.src);
        audioRef.current = null;
      }
      isPlayingRef.current = false;
      setIsSpeaking(false);
      throw err;
    }
  }, []);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      URL.revokeObjectURL(audioRef.current.src);
      audioRef.current = null;
    }
    isPlayingRef.current = false;
    setIsSpeaking(false);
  }, []);

  return { speak, stop, isSpeaking, isPlaying: isSpeaking };
}
