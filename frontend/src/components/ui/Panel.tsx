import type { ReactNode } from "react";

interface PanelProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}

export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
  bodyClassName = "",
}: PanelProps) {
  return (
    <section className={`neu-panel flex flex-col overflow-hidden ${className}`}>
      <header className="flex items-start justify-between gap-3 border-b border-[var(--border-subtle)] px-4 py-3">
        <div>
          <h2 className="text-[0.95rem] font-medium text-[var(--text-primary)]">
            {title}
          </h2>
          {subtitle ? (
            <p className="mt-0.5 text-[0.7rem] text-[var(--text-muted)]">
              {subtitle}
            </p>
          ) : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </header>
      <div className={`flex-1 p-4 ${bodyClassName}`}>{children}</div>
    </section>
  );
}
