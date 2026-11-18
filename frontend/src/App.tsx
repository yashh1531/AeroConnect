import { useState } from "react";
import { useLiveState } from "./hooks/useLiveState";
import { useLocalClock } from "./hooks/useLocalClock";
import { AppShell } from "./components/layout/AppShell";
import { Dashboard } from "./components/dashboard/Dashboard";
import { OperationsView } from "./components/views/OperationsView";
import type { NavId } from "./types/nav";

export default function App() {
  const { state, wsStatus, lastError } = useLiveState();
  const clock = useLocalClock();
  const [page, setPage] = useState<NavId>("dashboard");

  return (
    <AppShell
      page={page}
      onNavigate={setPage}
      clock={clock}
      wsStatus={wsStatus}
      state={state}
    >
      {page === "dashboard" ? <Dashboard state={state} wsStatus={wsStatus} lastError={lastError} /> : <OperationsView page={page} state={state} wsStatus={wsStatus} />}
    </AppShell>
  );
}
