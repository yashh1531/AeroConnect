import type { AppState } from "../types/state";

export async function simulationCommand(command: "deploy" | "return" | "reset"): Promise<AppState> {
  const response = await fetch(`/api/simulation/${command}`, { method: "POST" });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Simulation ${command} failed`);
  }
  return response.json() as Promise<AppState>;
}
