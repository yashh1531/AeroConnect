import { useEffect, useState } from "react";

export function useLocalClock(intervalMs = 1000): string {
  const [clock, setClock] = useState(() => formatNow());

  useEffect(() => {
    const id = window.setInterval(() => setClock(formatNow()), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);

  return clock;
}

function formatNow(): string {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}
