"use client";
import { useState, useEffect, useRef, useCallback } from "react";

interface VIVIREvent {
  event_type: string;
  timestamp: string;
  guardian_state: string;
  severity?: number;
  ttl_ms?: number;
  data?: any;
}

interface UseVivirReturn {
  isConnected: boolean;
  guardianState: string;
  ecosystemStats: { total_stores: number; total_products: number };
  lastEvent: VIVIREvent | null;
  notifications: VIVIREvent[];
}

const WS_URL =
  process.env.NEXT_PUBLIC_VIVIR_WS || "wss://api.liveodi.com/ws/vivir";

export function useVivir(): UseVivirReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [guardianState, setGuardianState] = useState("verde");
  const [ecosystemStats, setEcosystemStats] = useState({
    total_stores: 15,
    total_products: 0,
  });
  const [lastEvent, setLastEvent] = useState<VIVIREvent | null>(null);
  const [notifications, setNotifications] = useState<VIVIREvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const payload: VIVIREvent = JSON.parse(event.data);
          setLastEvent(payload);

          if (payload.guardian_state) {
            setGuardianState(payload.guardian_state);
          }

          if (payload.data?.ecosystem) {
            setEcosystemStats(payload.data.ecosystem);
          }

          if (payload.ttl_ms && payload.ttl_ms > 0) {
            const notifId = Date.now();
            const notif = { ...payload, _notifId: notifId };
            setNotifications((prev) => [...prev.slice(-1), notif]);

            setTimeout(() => {
              setNotifications((prev) =>
                prev.filter((n: any) => n._notifId !== notifId)
              );
            }, payload.ttl_ms);
          }
        } catch {}
      };

      ws.onclose = () => {
        setIsConnected(false);
        reconnectTimer.current = setTimeout(connect, 5000);
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    } catch {
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect]);

  return {
    isConnected,
    guardianState,
    ecosystemStats,
    lastEvent,
    notifications,
  };
}
