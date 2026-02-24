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

function normalizeODITranscript(raw: string): string {
  return raw
    .replace(/\bo\s*d\s*i\b/gi, "ODI")
    .replace(/\b(oye|hoy|odi+|ody|oh di|od i|odie|o de i|guey|g[u\u00fc]ey)\b/gi, "ODI")
    .replace(/^(oye|hoy|ody)\s/i, "ODI ")
    .trim();
}

// V24: On-demand mic request — never auto-invoked
export async function requestMicrophone(): Promise<MediaStream | null> {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return stream;
  } catch (err) {
    console.warn("[ODI Listen] Mic permission denied:", err);
    return null;
  }
}

export function useODIListen(
  onTranscript?: (text: string) => void,
  autoListen: boolean = false,
  isTTSActive: boolean = false
): UseODIListenReturn {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(false);
  const recognitionRef = useRef<any>(null);
  const manualStopRef = useRef(false);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingTranscriptRef = useRef("");

  useEffect(() => {
    if (typeof window !== "undefined" &&
        ("SpeechRecognition" in window || "webkitSpeechRecognition" in window)) {
      setIsSupported(true);
    }
  }, []);

  // V24: NO auto getUserMedia — removed B1 auto-request

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
      setTranscript(normalizeODITranscript(text));

      if (finalTranscript) {
        pendingTranscriptRef.current = normalizeODITranscript(finalTranscript);

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
      if (event.error === "no-speech" || event.error === "aborted") return;
      setError(event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      if (!manualStopRef.current) {
        setTimeout(() => {
          try {
            recognition.start();
          } catch {
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

  useEffect(() => {
    if (!autoListen || !isSupported) return;
    if (isTTSActive && isListening) {
      manualStopRef.current = true;
      try { recognitionRef.current?.stop(); } catch {}
      setIsListening(false);
    }
    if (!isTTSActive && !isListening && autoListen) {
      manualStopRef.current = false;
      try {
        recognitionRef.current?.start();
        setIsListening(true);
      } catch {}
    }
  }, [autoListen, isTTSActive, isSupported]);

  const startListening = useCallback(() => {
    if (recognitionRef.current && !isListening) {
      manualStopRef.current = false;
      pendingTranscriptRef.current = "";
      setTranscript("");
      setError(null);
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch {}
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      manualStopRef.current = true;
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);

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
