import { useState, type ReactNode } from "react";
import type { AppState } from "../../types/state";
import type { NavId } from "../../types/nav";
import type { WsStatus } from "../../hooks/useLiveState";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { StatusIndicator } from "../ui/StatusIndicator";
import { IconButton } from "../ui/IconButton";

interface AppShellProps {
  page: NavId;
  onNavigate: (id: NavId) => void;
  clock: string;
  wsStatus: WsStatus;
  state: AppState | null;
  children: ReactNode;
}

export function AppShell({
  page,
  onNavigate,
  clock,
  wsStatus,
  state,
  children,
}: AppShellProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const handleNavigate = (id: NavId) => {
    onNavigate(id);
    setMobileNavOpen(false);
  };

  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)]">
      <div className="fixed left-4 top-4 z-40 md:hidden">
        <IconButton
          aria-label="Toggle navigation"
          active={mobileNavOpen}
          onClick={() => setMobileNavOpen((v) => !v)}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path
              d="M4 7h16M4 12h16M4 17h16"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </IconButton>
      </div>

      {mobileNavOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/45 md:hidden"
          aria-label="Close navigation overlay"
          onClick={() => setMobileNavOpen(false)}
        />
      ) : null}

      <div
        className={`fixed inset-y-0 left-0 z-40 transition-transform duration-200 md:translate-x-0 ${
          mobileNavOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <Sidebar active={page} onNavigate={handleNavigate} />
      </div>

      <div className="md:pl-[var(--sidebar-width)]">
        <Header
          page={page}
          clock={clock}
          wsStatus={wsStatus}
          state={state}
        />

        <main className="px-4 py-5 sm:px-6">{children}</main>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border-subtle)] px-6 py-3">
          <div className="flex flex-wrap items-center gap-4">
            <StatusIndicator
              label={
                wsStatus === "connected"
                  ? "System link online"
                  : "System link down"
              }
              tone={wsStatus === "connected" ? "success" : "danger"}
            />
            <StatusIndicator
              label={
                state?.data_source === "hardware"
                  ? "Live hardware / hybrid"
                  : "Simulation mode"
              }
              tone="warning"
            />
          </div>
          <p className="metric-value text-[0.68rem] text-[var(--text-faint)]">
            tick {state?.tick ?? "—"} ·{" "}
            {state?.server_time
              ? new Date(state.server_time).toISOString().slice(11, 19)
              : "--:--:--"}{" "}
            UTC
          </p>
        </footer>
      </div>
    </div>
  );
}
