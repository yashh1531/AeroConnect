type Tone = "neutral" | "success" | "warning" | "danger";

interface StatusIndicatorProps {
  label: string;
  tone?: Tone;
  pulse?: boolean;
}

const TONE_BG: Record<Tone, string> = {
  neutral: "var(--text-muted)",
  success: "var(--success)",
  warning: "var(--warning)",
  danger: "var(--danger)",
};

export function StatusIndicator({
  label,
  tone = "neutral",
  pulse = false,
}: StatusIndicatorProps) {
  return (
    <span className="inline-flex items-center gap-2 text-[0.72rem] text-[var(--text-secondary)]">
      <span
        className={`h-1.5 w-1.5 rounded-full ${pulse ? "animate-pulse" : ""}`}
        style={{ background: TONE_BG[tone] }}
        aria-hidden
      />
      <span className="tracking-wide">{label}</span>
    </span>
  );
}
