import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import { Panel } from "../ui/Panel";
import { EventRow } from "../ui/EventRow";
import type { AppState } from "../../types/state";
import type { WsStatus } from "../../hooks/useLiveState";

interface LogItem {
  id: string;
  time: string;
  message: string;
  source: string;
}

interface RecentEventsProps {
  state: AppState | null;
  wsStatus: WsStatus;
  lastError: string | null;
}

export function RecentEvents({ state, wsStatus, lastError }: RecentEventsProps) {
  const [items, setItems] = useState<LogItem[]>([]);
  const prevWs = useRef<WsStatus | null>(null);
  const lastTickLogged = useRef<number>(-1);
  const simulationItems: LogItem[] = (state?.events ?? []).map((event) => ({
    id: event.id,
    time: new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }),
    message: event.message,
    source: event.type,
  }));
  const displayItems = [...simulationItems, ...items].slice(0, 40);

  useEffect(() => {
    if (prevWs.current === wsStatus) return;
    const prev = prevWs.current;
    prevWs.current = wsStatus;
    if (prev === null && wsStatus === "connecting") return;

    push(setItems, {
      id: `ws-${wsStatus}-${Date.now()}`,
      time: localTime(),
      message: `WebSocket ${wsStatus}`,
      source: "link",
    });
  }, [wsStatus]);

  useEffect(() => {
    if (!lastError) return;
    push(setItems, {
      id: `err-${Date.now()}`,
      time: localTime(),
      message: lastError,
      source: "link",
    });
  }, [lastError]);

  useEffect(() => {
    if (!state) return;
    // Log milestone ticks only (every 10) to avoid flooding the console.
    if (state.tick === 0 || state.tick % 10 !== 0) return;
    if (lastTickLogged.current === state.tick) return;
    lastTickLogged.current = state.tick;
    push(setItems, {
      id: `tick-${state.tick}`,
      time: localTime(),
      message: state.message,
      source: state.data_source,
    });
  }, [state]);

  return (
    <Panel
      title="Recent Events"
      subtitle="Simulation and live-link activity"
      className="h-full"
      bodyClassName="!pt-2"
    >
      <div className="neu-recessed-sm max-h-[220px] overflow-y-auto px-3">
        {displayItems.length === 0 ? (
          <p className="py-6 text-center text-[0.72rem] text-[var(--text-faint)]">
            Waiting for link events…
          </p>
        ) : (
          displayItems.map((item) => (
            <EventRow
              key={item.id}
              time={item.time}
              message={item.message}
              source={item.source}
            />
          ))
        )}
      </div>
    </Panel>
  );
}

function localTime(): string {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function push(
  setItems: Dispatch<SetStateAction<LogItem[]>>,
  item: LogItem,
) {
  setItems((prev) => [item, ...prev].slice(0, 40));
}
