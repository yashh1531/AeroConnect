import { KpiCard } from "../ui/KpiCard";
import { OperationalMap } from "./OperationalMap";
import { UavStatusPanel } from "./UavStatusPanel";
import { NetworkChart } from "./NetworkChart";
import { CameraFeed } from "./CameraFeed";
import { RfSpectrum } from "./RfSpectrum";
import { SystemHealth } from "./SystemHealth";
import { RecentEvents } from "./RecentEvents";
import type { AppState } from "../../types/state";
import type { WsStatus } from "../../hooks/useLiveState";

interface DashboardProps {
  state: AppState | null;
  wsStatus: WsStatus;
  lastError: string | null;
}

export function Dashboard({ state, wsStatus, lastError }: DashboardProps) {
  return (
    <div className="mx-auto flex w-full max-w-[1680px] flex-col gap-4">
      <div className="neu-recessed-sm flex flex-wrap items-center justify-between gap-2 px-3.5 py-2.5 text-[0.72rem] text-[var(--text-muted)]">
        <span>Disaster-response communications overview</span>
        <span className="metric-value text-[0.68rem]">LAST UPDATE {state?.server_time ? new Date(state.server_time).toLocaleTimeString() : "—"}</span>
      </div>

      <section className="grid grid-cols-2 gap-3 xl:grid-cols-6">
        <KpiCard
          label="UAV Status"
          value={state?.uav.status?.replaceAll("_", " ").toUpperCase() ?? "—"}
          hint={state ? `${state.data_source === "hardware" ? "HARDWARE / HYBRID" : "SIMULATED"} · ${state.uav.deployment_state}` : "Awaiting telemetry"}
          awaiting={!state}
        />
        <KpiCard
          label="GPS"
          value={state?.uav.gps_valid ? "FIX" : state ? "NO FIX" : "—"}
          hint={state ? `Satellites ${state.uav.satellites ?? "—"}` : "Awaiting telemetry"}
          awaiting={!state}
        />
        <KpiCard
          label="5 GHz Backhaul"
          value={state ? backhaulLabel(state.network.backhaul.status) : "—"}
          hint={state?.network.backhaul.latency_ms != null ? `RTT ${state.network.backhaul.latency_ms.toFixed(1)} ms · ${state.network.backhaul.data_source}` : "No RTT reported"}
          awaiting={!state}
        />
        <KpiCard
          label="RF Activity"
          value={state ? String(state.rf.detected_signals) : "—"}
          hint={state ? `${state.rf.activity_level.toFixed(1)}% · ${state.rf.peak_frequency.toFixed(3)} MHz` : "Awaiting RF state"}
          awaiting={!state}
        />
        <KpiCard
          label="Pi Health"
          value={state ? `${state.system.cpu_usage.toFixed(0)}%` : "—"}
          hint={state ? `RAM ${state.system.memory_usage.toFixed(0)}% · ${state.system.temperature.toFixed(1)}°C` : "Awaiting Pi telemetry"}
          awaiting={!state}
        />
        <KpiCard
          label="Connected Users"
          value={state ? `${state.network.connected_users}/${state.network.total_users}` : "—"}
          hint={state?.network.connected_users ? "Service network active" : "Network service offline"}
          awaiting={!state}
        />
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-12 xl:items-stretch">
        <div className="xl:col-span-6">
          <OperationalMap wsStatus={wsStatus} state={state} />
        </div>
        <div className="xl:col-span-3">
          <UavStatusPanel state={state} />
        </div>
        <div className="xl:col-span-3">
          <NetworkChart state={state} />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <CameraFeed state={state} />
        <RfSpectrum state={state} />
        <SystemHealth state={state} wsStatus={wsStatus} />
        <RecentEvents
          state={state}
          wsStatus={wsStatus}
          lastError={lastError}
        />
      </section>
    </div>
  );
}

function backhaulLabel(status: "up" | "degraded" | "down") { return status === "up" ? "ONLINE" : status === "degraded" ? "DEGRADED" : "OFFLINE"; }
