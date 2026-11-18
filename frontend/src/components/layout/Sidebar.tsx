import type { NavId } from "../../types/nav";
import { NAV_ITEMS } from "../../types/nav";

interface SidebarProps {
  active: NavId;
  onNavigate: (id: NavId) => void;
}

export function Sidebar({ active, onNavigate }: SidebarProps) {
  return (
    <aside
      className="fixed inset-y-0 left-0 z-30 flex w-[var(--sidebar-width)] flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-surface)]"
      style={{
        boxShadow: "6px 0 18px rgba(0,0,0,0.28)",
      }}
    >
      <div className="border-b border-[var(--border-subtle)] px-5 py-5">
        <div className="neu-recessed-sm flex items-center gap-3 px-3 py-2.5">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-[10px] neu-raised-sm"
            aria-hidden
          >
            <span className="text-[0.7rem] font-semibold tracking-[0.12em] text-[var(--text-secondary)]">
              AC
            </span>
          </div>
          <div>
            <p className="text-[0.82rem] font-semibold tracking-[0.08em] text-[var(--text-primary)]">
              AERO CONNECT
            </p>
            <p className="label-caps mt-0.5">Ops console</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1.5 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const isActive = item.id === active;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={`flex w-full items-center rounded-[12px] px-3.5 py-2.5 text-left text-[0.82rem] transition-shadow ${
                isActive
                  ? "neu-recessed-sm font-medium text-[var(--text-primary)]"
                  : "text-[var(--text-muted)] hover:bg-[rgba(255,255,255,0.02)] hover:text-[var(--text-secondary)]"
              }`}
            >
              <span
                className="mr-3 h-1 w-1 rounded-full"
                style={{
                  background: isActive
                    ? "var(--text-secondary)"
                    : "var(--text-faint)",
                }}
                aria-hidden
              />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="border-t border-[var(--border-subtle)] px-4 py-4">
        <div className="neu-recessed-sm px-3 py-2.5">
          <p className="label-caps">Aero Connect</p>
          <p className="mt-1 text-[0.72rem] text-[var(--text-secondary)]">
            Operational POC · hardware integrated
          </p>
        </div>
      </div>
    </aside>
  );
}
