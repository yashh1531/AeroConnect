import { Panel } from "../ui/Panel";
import { ProgressBar } from "../ui/ProgressBar";
import type { AppState } from "../../types/state";
import type { WsStatus } from "../../hooks/useLiveState";

interface SystemHealthProps {
  state: AppState | null;
  wsStatus: WsStatus;
}

export function SystemHealth({ state, wsStatus }: SystemHealthProps) {
  return (
    <Panel title="System Health" subtitle="Pi node · ground station" className="h-full">
      <div className="space-y-3.5">
        <Row
          name="WebSocket bridge"
          detail={wsStatus}
          tone={wsStatus === "connected" ? "ok" : "bad"}
        />
        <Row
          name="State source"
          detail={state?.data_source ?? "—"}
          tone="warn"
        />
        <Row
          name="Backend status"
          detail={state?.system.network_interface_status ?? "—"}
          tone={state?.system.network_interface_status === "up" ? "ok" : "warn"}
        />

        <div className="pt-1">
          <ProgressBar value={state?.system.cpu_usage ?? null} label="CPU (Pi)" />
        </div>
        <ProgressBar value={state?.system.memory_usage ?? null} label="Memory (Pi)" />
        <BackhaulStatus state={state} />

        <p className="text-[0.68rem] text-[var(--text-faint)]">
          {state ? `${state.system.temperature.toFixed(1)}°C · uptime ${formatUptime(state.system.uptime)} · storage ${state.system.storage_usage.toFixed(0)}%` : "Waiting for system metrics."}
        </p>
      </div>
    </Panel>
  );
}

function BackhaulStatus({ state }: { state: AppState | null }) {
  const backhaul = state?.network.backhaul;
  const status = backhaul?.status;
  const label = status === "up" ? "ONLINE" : status === "degraded" ? "DEGRADED" : status === "down" ? "OFFLINE" : "—";
  const tone = status === "up" ? "ok" : status === "degraded" ? "warn" : "bad";
  const metrics = [
    backhaul?.latency_ms != null ? `RTT ${backhaul.latency_ms.toFixed(1)} ms` : null,
    backhaul?.packet_loss_percent != null ? `loss ${backhaul.packet_loss_percent.toFixed(0)}%` : null,
  ].filter(Boolean).join(" · ");

  return <div className="neu-recessed-sm px-3 py-2.5">
    <div className="flex items-center justify-between gap-3">
      <span className="text-[0.78rem] text-[var(--text-secondary)]">Backhaul</span>
      <RowStatus detail={label} tone={tone} />
    </div>
    <p className="mt-1 text-[0.65rem] text-[var(--text-faint)]">
      {backhaul ? `${backhaul.data_source.toUpperCase()}${metrics ? ` · ${metrics}` : ""}` : "Awaiting backhaul state"}
    </p>
  </div>;
}

function formatUptime(seconds: number) {
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function Row({
  name,
  detail,
  tone,
}: {
  name: string;
  detail: string;
  tone: "ok" | "warn" | "bad";
}) {
  return (
    <div className="neu-recessed-sm flex items-center justify-between gap-3 px-3 py-2">
      <span className="text-[0.78rem] text-[var(--text-secondary)]">{name}</span>
      <RowStatus detail={detail} tone={tone} />
    </div>
  );
}

function RowStatus({ detail, tone }: { detail: string; tone: "ok" | "warn" | "bad" }) {
  const color = tone === "ok" ? "var(--success)" : tone === "warn" ? "var(--warning)" : "var(--danger)";
  return <span className="inline-flex items-center gap-2">
    <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} aria-hidden />
    <span className="metric-value text-[0.72rem] uppercase tracking-wide text-[var(--text-primary)]">{detail}</span>
  </span>;
}
