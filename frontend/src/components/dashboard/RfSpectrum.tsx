import { Panel } from "../ui/Panel";
import type { AppState } from "../../types/state";

export function RfSpectrum({ state }: { state: AppState | null }) {
  const rf = state?.rf;
  const source = rf?.data_source === "hardware" ? "HARDWARE" : rf ? "SIMULATED" : "AWAITING";
  const hasSpectrum = (rf?.spectrum_activity.length ?? 0) > 0;

  return (
    <Panel
      title="RF Spectrum"
      subtitle="RTL-SDR · live scan summary"
      className="h-full"
      action={
        <span className="neu-raised-sm px-2 py-1 text-[0.58rem] tracking-[0.12em] text-[var(--text-muted)]">
          {source}
        </span>
      }
    >
      <div className="neu-recessed relative flex h-[148px] items-end gap-[3px] px-3 py-3">
        {hasSpectrum
          ? rf?.spectrum_activity.map((value, index) => (
              <div
                key={index}
                className="flex-1 rounded-[2px]"
                style={{
                  height: `${Math.max(8, value * 100)}%`,
                  background: "#52575c",
                }}
              />
            ))
          : null}
        {!hasSpectrum ? (
          <div className="absolute inset-0 flex items-center justify-center text-center">
            <span className="label-caps max-w-[190px] leading-relaxed text-[var(--text-faint)]">
              {rf?.data_source === "hardware"
                ? "No per-bin spectrum data supplied"
                : "Awaiting RF state"}
            </span>
          </div>
        ) : null}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-[0.68rem]">
        <Metric label="Peak frequency" value={rf ? `${rf.peak_frequency.toFixed(3)} MHz` : "—"} />
        <Metric label="Peak power" value={formatDb(rf?.peak_power_db)} />
        <Metric label="Noise floor" value={rf ? `${rf.noise_floor.toFixed(1)} dB` : "—"} />
        <Metric label="Detection threshold" value={formatDb(rf?.threshold_db)} />
        <Metric label="Activity" value={rf ? `${rf.activity_level.toFixed(2)}%` : "—"} />
        <Metric
          label="Occupied bins"
          value={rf?.occupied_bins !== null && rf?.occupied_bins !== undefined && rf.total_bins !== null ? `${rf.occupied_bins} / ${rf.total_bins}` : "—"}
        />
        <Metric
          label="Scan range"
          value={rf?.scan_start_mhz !== null && rf?.scan_start_mhz !== undefined && rf.scan_end_mhz !== null ? `${rf.scan_start_mhz.toFixed(3)}–${rf.scan_end_mhz.toFixed(3)} MHz` : "—"}
          className="col-span-2"
        />
      </div>

      {rf && rf.occupied_bands.length > 0 ? (
        <div className="mt-3 border-t border-[var(--border-subtle)] pt-2.5">
          <p className="label-caps">Detected frequency ranges</p>
          <div className="mt-2 space-y-1.5">
            {rf.occupied_bands.map((band, index) => (
              <div key={`${band.start_mhz}-${band.end_mhz}-${index}`} className="neu-recessed-sm flex justify-between gap-2 px-2.5 py-1.5">
                <span className="metric-value text-[0.68rem]">{band.start_mhz.toFixed(3)}–{band.end_mhz.toFixed(3)} MHz</span>
                <span className="text-[0.65rem] text-[var(--text-faint)]">peak {band.peak_mhz.toFixed(3)} · {band.peak_power_db.toFixed(1)} dB</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </Panel>
  );
}

function Metric({ label, value, className = "" }: { label: string; value: string; className?: string }) {
  return <div className={`neu-raised-sm px-2.5 py-2 ${className}`}><p className="label-caps">{label}</p><p className="metric-value mt-1 text-[0.72rem]">{value}</p></div>;
}

function formatDb(value: number | null | undefined) {
  return value === null || value === undefined ? "—" : `${value.toFixed(1)} dB`;
}
