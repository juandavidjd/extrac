"use client";
import { useState, useEffect, useCallback } from "react";

interface ODIMessage {
  role: "user" | "odi" | "system";
  content: string;
  timestamp: number;
  narrative?: string;
  cards?: any[];
  voice?: string;
}

interface ODISessionState {
  session_id: string;
  messages: ODIMessage[];
  industry?: string;
  guardian_color: string;
}

const SESSION_KEY = "odi_session_v21";
const SESSION_TTL = 1000 * 60 * 60 * 4; // 4 hours

function generateSessionId(): string {
  return "odi_" + Date.now().toString(36) + "_" + Math.random().toString(36).substring(2, 8);
}

export type { ODIMessage };

export function useODISession() {
  const [state, setState] = useState<ODISessionState>({
    session_id: "",
    messages: [],
    guardian_color: "verde",
  });
  const [isLoaded, setIsLoaded] = useState(false);

  // Load session on mount
  useEffect(() => {
    let initial: ODISessionState = {
      session_id: generateSessionId(),
      messages: [],
      guardian_color: "verde",
    };
    try {
      const saved = localStorage.getItem(SESSION_KEY);
      if (saved) {
        const parsed: ODISessionState = JSON.parse(saved);
        const lastMsg = parsed.messages[parsed.messages.length - 1];
        if (lastMsg && Date.now() - lastMsg.timestamp < SESSION_TTL) {
          initial = parsed;
        } else {
          localStorage.removeItem(SESSION_KEY);
        }
      }
    } catch (e) {
      console.error("[ODI Session] Error loading:", e);
    }
    setState(initial);
    setIsLoaded(true);
  }, []);

  // Save session when state changes
  useEffect(() => {
    if (isLoaded && state.messages.length > 0 && state.session_id) {
      try {
        localStorage.setItem(SESSION_KEY, JSON.stringify(state));
      } catch (e) {
        console.error("[ODI Session] Error saving:", e);
      }
    }
  }, [state, isLoaded]);

  const addMessage = useCallback((msg: ODIMessage) => {
    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, msg],
    }));
  }, []);

  const updateSessionId = useCallback((id: string) => {
    setState((prev) => ({ ...prev, session_id: id }));
  }, []);

  const updateGuardian = useCallback((color: string) => {
    setState((prev) => ({ ...prev, guardian_color: color }));
  }, []);

  const clearSession = useCallback(() => {
    localStorage.removeItem(SESSION_KEY);
    setState({
      session_id: generateSessionId(),
      messages: [],
      guardian_color: "verde",
    });
  }, []);

  return {
    ...state,
    isLoaded,
    addMessage,
    updateSessionId,
    updateGuardian,
    clearSession,
  };
}
