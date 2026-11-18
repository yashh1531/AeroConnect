import type { ButtonHTMLAttributes, ReactNode } from "react";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  active?: boolean;
}

export function IconButton({
  children,
  active = false,
  className = "",
  ...rest
}: IconButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex h-9 w-9 items-center justify-center rounded-[10px] text-[var(--text-secondary)] transition-shadow ${
        active
          ? "neu-recessed-sm text-[var(--text-primary)]"
          : "neu-raised-sm hover:text-[var(--text-primary)]"
      } ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
