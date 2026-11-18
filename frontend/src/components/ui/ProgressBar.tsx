interface ProgressBarProps {
  value: number | null;
  label?: string;
}

export function ProgressBar({ value, label }: ProgressBarProps) {
  const pct =
    value === null ? null : Math.max(0, Math.min(100, Math.round(value)));

  return (
    <div>
      {label ? (
        <div className="mb-1.5 flex items-center justify-between text-[0.68rem]">
          <span className="text-[var(--text-muted)]">{label}</span>
          <span className="metric-value text-[var(--text-secondary)]">
            {pct === null ? "—" : `${pct}%`}
          </span>
        </div>
      ) : null}
      <div className="neu-recessed-sm h-2.5 overflow-hidden p-0.5">
        <div
          className="h-full rounded-[6px] transition-[width] duration-300"
          style={{
            width: pct === null ? "0%" : `${pct}%`,
            background:
              pct === null
                ? "transparent"
                : "linear-gradient(90deg, #3a3d40, #55595d)",
          }}
        />
      </div>
    </div>
  );
}
