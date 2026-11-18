interface EventRowProps {
  time: string;
  message: string;
  source?: string;
}

export function EventRow({ time, message, source = "system" }: EventRowProps) {
  return (
    <div className="flex gap-3 border-b border-[var(--border-subtle)] py-2.5 last:border-b-0">
      <time className="metric-value w-[64px] shrink-0 text-[0.68rem] text-[var(--text-muted)]">
        {time}
      </time>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[0.78rem] text-[var(--text-secondary)]">
          {message}
        </p>
        <p className="label-caps mt-1">{source}</p>
      </div>
    </div>
  );
}
