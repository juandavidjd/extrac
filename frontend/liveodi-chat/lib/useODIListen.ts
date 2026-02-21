"use client";
import { useState, useRef, useCallback, useEffect } from "react";

interface UseODIListenReturn {
  isListening: boolean;
  transcript: string;
  startListening: () => void;
  stopListening: () => void;
  isSupported: boolean;
  error: string | null;
}

function normalizeTranscript(raw: string): string {
  return raw
    .replace(/\b(oye|hoy|o di|guey|g[üu]ey|odie|ody|oh di|o de i|o d)\b/gi, "ODI")
    .replace(/\bODI\b/gi, "ODI");
}

export function useODIListen(
  onTranscript?: (text: string) => void
): UseODIListenReturn {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const manualStopRef = useRef(false);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingTranscriptRef = useRef("");

  const isSupported =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  useEffect(() => {
    if (!isSupported) return;

    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.lang = "es-CO";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      let finalTranscript = "";
      let interimTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      const text = finalTranscript || interimTranscript;
      setTranscript(normalizeTranscript(text));

      // Silence timer: si hay finalTranscript, esperar 2s sin más input → enviar
      if (finalTranscript) {
        pendingTranscriptRef.current = normalizeTranscript(finalTranscript);

        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
        }
        silenceTimerRef.current = setTimeout(() => {
          if (pendingTranscriptRef.current && onTranscript) {
            onTranscript(pendingTranscriptRef.current);
            pendingTranscriptRef.current = "";
            setTranscript("");
          }
        }, 2000);
      }
    };

    recognition.onerror = (event: any) => {
      // "no-speech" and "aborted" are not real errors in continuous mode
      if (event.error === "no-speech" || event.error === "aborted") return;
      setError(event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      // Auto-restart if not manually stopped
      if (!manualStopRef.current) {
        setTimeout(() => {
          try {
            recognition.start();
          } catch {
            // Already started or other error — ignore
            setIsListening(false);
          }
        }, 300);
      } else {
        setIsListening(false);
      }
    };

    recognitionRef.current = recognition;

    return () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    };
  }, [isSupported]);

  const startListening = useCallback(() => {
    if (recognitionRef.current && !isListening) {
      manualStopRef.current = false;
      pendingTranscriptRef.current = "";
      setTranscript("");
      setError(null);
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch {
        // Already started
      }
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      manualStopRef.current = true;
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);

      // Send any pending transcript before stopping
      if (pendingTranscriptRef.current && onTranscript) {
        onTranscript(pendingTranscriptRef.current);
        pendingTranscriptRef.current = "";
      }

      recognitionRef.current.stop();
      setIsListening(false);
    }
  }, [isListening, onTranscript]);

  return {
    isListening,
    transcript,
    startListening,
    stopListening,
    isSupported,
    error,
  };
}
