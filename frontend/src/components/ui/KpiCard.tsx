interface KpiCardProps {
  label: string;
  value: string;
  unit?: string;
  hint?: string;
  awaiting?: boolean;
}

export function KpiCard({
  label,
  value,
  unit,
  hint,
  awaiting = false,
}: KpiCardProps) {
  return (
    <article className="neu-raised flex min-h-[96px] flex-col justify-between px-4 py-3.5">
      <p className="label-caps">{label}</p>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span
          className={`metric-value text-[1.65rem] leading-none ${
            awaiting ? "awaiting text-[1.25rem]" : ""
          }`}
        >
          {value}
        </span>
        {unit && !awaiting ? (
          <span className="text-[0.7rem] text-[var(--text-muted)]">{unit}</span>
        ) : null}
      </div>
      {hint ? (
        <p className="mt-2 text-[0.65rem] text-[var(--text-faint)]">{hint}</p>
      ) : null}
    </article>
  );
}
