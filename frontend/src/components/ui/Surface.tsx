import type { ReactNode } from "react";

interface SurfaceProps {
  children: ReactNode;
  className?: string;
}

export function RaisedSurface({ children, className = "" }: SurfaceProps) {
  return <div className={`neu-raised ${className}`}>{children}</div>;
}

export function RecessedSurface({ children, className = "" }: SurfaceProps) {
  return <div className={`neu-recessed ${className}`}>{children}</div>;
}
