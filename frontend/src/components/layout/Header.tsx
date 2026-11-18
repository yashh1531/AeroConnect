import type { AppState } from "../../types/state";
import type { NavId } from "../../types/nav";
import { PAGE_META } from "../../types/nav";
import type { WsStatus } from "../../hooks/useLiveState";
import { StatusIndicator } from "../ui/StatusIndicator";
import { IconButton } from "../ui/IconButton";

interface HeaderProps {
  page: NavId;
  clock: string;
  wsStatus: WsStatus;
  state: AppState | null;
}

function sourceTone(
  wsStatus: WsStatus,
): "success" | "warning" | "danger" | "neutral" {
  if (wsStatus === "connected") return "success";
  if (wsStatus === "connecting") return "warning";
  return "danger";
}

export function Header({ page, clock, wsStatus, state }: HeaderProps) {
  const meta = PAGE_META[page];
  const sourceLabel = state?.data_source === "hardware" ? "LIVE HARDWARE / HYBRID" : "SIMULATION";

  return (
    <header className="sticky top-0 z-20 flex h-[var(--header-height)] items-center justify-between gap-4 border-b border-[var(--border-subtle)] bg-[var(--bg-base)] px-6 pl-16 md:pl-6">
      <div className="min-w-0">
        <h1 className="truncate text-[1.15rem] font-medium tracking-tight text-[var(--text-primary)]">
          {meta.title}
        </h1>
        <p className="mt-0.5 truncate text-[0.75rem] text-[var(--text-muted)]">
          {meta.description}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <div className="neu-recessed-sm hidden items-center gap-4 px-3.5 py-2 md:flex">
          <div>
            <p className="label-caps">Local time</p>
            <p className="metric-value mt-0.5 text-[0.78rem] text-[var(--text-secondary)]">
              {clock}
            </p>
          </div>
          <div className="h-7 w-px bg-[var(--border-subtle)]" />
          <div>
            <p className="label-caps">Mode</p>
            <p className="mt-0.5 text-[0.72rem] tracking-[0.08em] text-[var(--text-secondary)]">
              {sourceLabel}
            </p>
          </div>
        </div>

        <div className="neu-raised-sm flex items-center gap-3 px-3 py-2">
          <StatusIndicator
            label={
              wsStatus === "connected"
                ? "Link online"
                : wsStatus === "connecting"
                  ? "Link connecting"
                  : "Link offline"
            }
            tone={sourceTone(wsStatus)}
            pulse={wsStatus === "connecting"}
          />
        </div>

        <IconButton aria-label="Console settings" title="Settings (later)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path
              d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"
              stroke="currentColor"
              strokeWidth="1.5"
            />
            <path
              d="M19.4 13a7.8 7.8 0 0 0 .05-2l2-1.15-2-3.46-2.3.7a7.7 7.7 0 0 0-1.73-1L15 3.5h-6l-.42 2.59a7.7 7.7 0 0 0-1.73 1l-2.3-.7-2 3.46L4.55 11a7.8 7.8 0 0 0 0 2l-2 1.15 2 3.46 2.3-.7c.53.42 1.11.76 1.73 1L9 20.5h6l.42-2.59c.62-.24 1.2-.58 1.73-1l2.3.7 2-3.46L19.4 13Z"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          </svg>
        </IconButton>
      </div>
    </header>
  );
}
