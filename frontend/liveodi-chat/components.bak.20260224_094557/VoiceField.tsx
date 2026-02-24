"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useODIListen } from "@/lib/useODIListen";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
  isTTSActive?: boolean;
}

export default function VoiceField({ onSend, disabled, isTTSActive = false }: Props) {
  const [text, setText] = useState("");
  const [showText, setShowText] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const onSendRef = useRef(onSend);
  onSendRef.current = onSend;
  const typingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const handleTranscript = useCallback((transcript: string) => {
    if (transcript.trim()) {
      onSendRef.current(transcript.trim());
    }
  }, []);

  const { isListening, transcript, startListening, stopListening, isSupported } =
    useODIListen(handleTranscript, true, isTTSActive);

  useEffect(() => {
    if (transcript && isListening) {
      setText(transcript);
      setShowText(true);
    }
  }, [transcript, isListening]);

  useEffect(() => {
    if (!isListening && transcript) {
      const timer = setTimeout(() => {
        setText("");
        setShowText(false);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isListening]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "m") {
        e.preventDefault();
        isListening ? stopListening() : startListening();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isListening, startListening, stopListening]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (showText) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key.length !== 1) return;
      setText("");
      setShowText(true);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 0);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [showText]);

  const resetIdleTimer = useCallback(() => {
    if (typingTimerRef.current) {
      clearTimeout(typingTimerRef.current);
    }
    typingTimerRef.current = setTimeout(() => {
      setText((currentText) => {
        if (!currentText.trim()) {
          setShowText(false);
        }
        return currentText;
      });
    }, 3000);
  }, []);

  useEffect(() => {
    if (showText) {
      resetIdleTimer();
    }
    return () => {
      if (typingTimerRef.current) {
        clearTimeout(typingTimerRef.current);
      }
    };
  }, [text, showText, resetIdleTimer]);

  const handleTextSend = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    if (isListening) stopListening();
    onSend(trimmed);
    setText("");
    setShowText(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleTextSend();
    }
    if (e.key === "Escape") {
      setText("");
      setShowText(false);
    }
  };

  return (
    <div className="absolute bottom-0 left-0 right-0 z-40">
      <div className="max-w-2xl mx-auto px-6 pb-6 pt-4">
        {showText && (
          <div className="flex items-center gap-3 mb-4 animate-[fadeIn_0.3s_ease-out]">
            <input
              ref={inputRef}
              type="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isListening ? "Escuchando..." : "Escribe aqui..."}
              disabled={disabled}
              autoFocus
              className="flex-1 bg-transparent text-neutral-300 text-sm placeholder-neutral-700 border-b border-neutral-800 focus:border-emerald-500/40 pb-2 outline-none transition-colors"
            />
            {text.trim() && (
              <button
                onClick={handleTextSend}
                disabled={disabled}
                className="text-emerald-500/70 hover:text-emerald-400 transition-colors disabled:opacity-30"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                  <path d="M3.105 2.289a.75.75 0 00-.826.95l1.414 4.925A1.5 1.5 0 005.135 9.25h6.115a.75.75 0 010 1.5H5.135a1.5 1.5 0 00-1.442 1.086l-1.414 4.926a.75.75 0 00.826.95 28.896 28.896 0 0015.293-7.154.75.75 0 000-1.115A28.897 28.897 0 003.105 2.289z" />
                </svg>
              </button>
            )}
          </div>
        )}

        {/* Subtle listening indicator — no visible mic button */}
        <div className="flex items-center justify-center h-6">
          {isListening && (
            <div className="flex items-center gap-2 animate-[fadeIn_0.3s_ease-out]">
              <span className="w-1.5 h-1.5 bg-emerald-500/60 rounded-full animate-pulse" />
              <span className="text-neutral-700 text-[10px] tracking-wider uppercase">escuchando</span>
            </div>
          )}
          {showText && (
            <button
              onClick={() => { setText(""); setShowText(false); }}
              className="text-neutral-700 hover:text-neutral-500 text-xs transition-colors"
            >
              Cerrar
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
