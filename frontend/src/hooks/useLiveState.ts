import { useEffect, useRef, useState } from "react";
import { isAppState, type AppState } from "../types/state";

export type WsStatus = "connecting" | "connected" | "disconnected";

interface UseLiveStateResult {
  state: AppState | null;
  wsStatus: WsStatus;
  lastError: string | null;
}

function wsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  // Dev: Vite proxies /ws → backend. Production can point WS_HOST via env later.
  return `${proto}://${window.location.host}/ws`;
}

export function useLiveState(): UseLiveStateResult {
  const [state, setState] = useState<AppState | null>(null);
  const [wsStatus, setWsStatus] = useState<WsStatus>("connecting");
  const [lastError, setLastError] = useState<string | null>(null);
  const retryRef = useRef(0);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let closedByCleanup = false;
    let retryTimer: number | undefined;

    const connect = () => {
      setWsStatus("connecting");
      socket = new WebSocket(wsUrl());

      socket.onopen = () => {
        retryRef.current = 0;
        setWsStatus("connected");
        setLastError(null);
      };

      socket.onmessage = (event) => {
        try {
          const payload: unknown = JSON.parse(event.data as string);
          if (!isAppState(payload)) throw new Error("Malformed simulation state");
          setState(payload);
        } catch {
          setLastError("Failed to parse state payload");
        }
      };

      socket.onerror = () => {
        setLastError("WebSocket error");
      };

      socket.onclose = () => {
        setWsStatus("disconnected");
        if (closedByCleanup) return;
        const delay = Math.min(1000 * 2 ** retryRef.current, 8000);
        retryRef.current += 1;
        retryTimer = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      closedByCleanup = true;
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  return { state, wsStatus, lastError };
}
