import { Panel } from "../ui/Panel";
import { ProgressBar } from "../ui/ProgressBar";
import type { AppState } from "../../types/state";
import { simulationCommand } from "../../api/simulation";
import { useState } from "react";

interface UavStatusPanelProps {
  state: AppState | null;
}

export function UavStatusPanel({ state }: UavStatusPanelProps) {
  const [error, setError] = useState<string | null>(null);
  const command = async (action: "deploy" | "return" | "reset") => {
    try { setError(null); await simulationCommand(action); } catch (reason) { setError(reason instanceof Error ? reason.message : "Command failed"); }
  };
  const uav = state?.uav;
  const source = state?.data_source;
  const hasGpsPosition = canUseUavPosition(state);
  return (
    <Panel
      title="UAV Status"
      subtitle="Airframe · mission · telemetry"
      className="h-full"
      action={source ? <SourceBadge source={source} /> : undefined}
    >
      <div className="space-y-4">
        <div className="neu-recessed-sm grid grid-cols-2 gap-3 px-3 py-3">
          <Field label="UAV status" value={formatStatus(uav?.status)} awaiting={!uav} />
          <Field label="Deployment" value={uav?.deployment_state ?? "—"} awaiting={!uav} />
          <Field label="Altitude" value={formatReading(uav?.altitude, "m", 0)} awaiting={!uav} />
          <Field label="Ground speed" value={formatReading(uav?.speed, "m/s", 1)} awaiting={!uav} />
          <Field label="Heading" value={formatReading(uav?.heading, "°", 0)} awaiting={!uav} />
          <Field label="Battery" value={formatReading(uav?.battery, "%", 0)} awaiting={!uav} />
          <Field label="GPS" value={gpsStatus(source, uav?.gps_valid)} awaiting={!uav || (source === "hardware" && !uav.gps_valid)} />
          <Field label="Latitude" value={hasGpsPosition ? formatCoordinate(uav?.latitude) : "GPS unavailable / no fix"} awaiting={!uav || !hasGpsPosition} />
          <Field label="Longitude" value={hasGpsPosition ? formatCoordinate(uav?.longitude) : "GPS unavailable / no fix"} awaiting={!uav || !hasGpsPosition} />
        </div>

        <ProgressBar value={uav?.deployment_state === "DEPLOYED" ? 100 : uav?.deployment_state === "DEPLOYING" ? 55 : uav?.deployment_state === "RETURNING" ? 45 : 0} label="Mission progress" />
        <ProgressBar value={state?.network.link_quality ?? null} label="Command link" />

        <div className="neu-raised-sm px-3 py-2.5">
          <p className="label-caps">Backend heartbeat</p>
          <p className="metric-value mt-1 text-[0.9rem]">
            {state ? `tick ${state.tick}` : "—"}
          </p>
          <p className="mt-1 text-[0.68rem] text-[var(--text-faint)]">
            {uav ? `${formatReading(uav.speed, "m/s", 1)} · ${formatStatus(uav.status)}` : "Waiting for telemetry state."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="neu-raised-sm px-2.5 py-1.5 text-[0.68rem]" onClick={() => void command("deploy")}>Deploy</button>
          <button className="neu-raised-sm px-2.5 py-1.5 text-[0.68rem]" onClick={() => void command("return")}>Return</button>
          <button className="neu-raised-sm px-2.5 py-1.5 text-[0.68rem]" onClick={() => void command("reset")}>Reset</button>
        </div>
        {error ? <p className="text-[0.68rem] text-[var(--danger)]">{error}</p> : null}
      </div>
    </Panel>
  );
}

function SourceBadge({ source }: { source: "hardware" | "simulated" }) {
  const hardware = source === "hardware";
  return <span className={`neu-raised-sm px-2 py-1 text-[0.6rem] font-medium tracking-[0.12em] ${hardware ? "text-[var(--success)]" : "text-[var(--text-muted)]"}`}>{hardware ? "HARDWARE" : "SIMULATED"}</span>;
}

function formatReading(value: number | null | undefined, unit: string, decimals: number): string {
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(decimals)} ${unit}` : "—";
}

function formatCoordinate(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(6) : "GPS unavailable / no fix";
}

function formatStatus(status: string | null | undefined): string {
  return status ? status.replaceAll("_", " ") : "—";
}

function hasValidPosition(latitude: number | null | undefined, longitude: number | null | undefined): boolean {
  return typeof latitude === "number" && typeof longitude === "number" && Number.isFinite(latitude) && Number.isFinite(longitude) && latitude >= -90 && latitude <= 90 && longitude >= -180 && longitude <= 180 && !(latitude === 0 && longitude === 0);
}

function canUseUavPosition(state: AppState | null): boolean {
  if (!state || !hasValidPosition(state.uav.latitude, state.uav.longitude)) return false;
  return state.uav.gps_valid;
}

function gpsStatus(source: "hardware" | "simulated" | undefined, gpsValid: boolean | undefined): string {
  if (source === "hardware") return gpsValid ? "GPS FIX" : "NO GPS FIX";
  return source === "simulated" ? "SIMULATED" : "—";
}

function Field({
  label,
  value,
  awaiting,
}: {
  label: string;
  value: string;
  awaiting?: boolean;
}) {
  return (
    <div>
      <p className="label-caps">{label}</p>
      <p
        className={`mt-1 text-[0.9rem] ${
          awaiting ? "awaiting" : "metric-value"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
