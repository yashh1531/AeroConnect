import { Panel } from "../ui/Panel";
import type { AppState } from "../../types/state";
export function CameraFeed({ state }: { state: AppState | null }) {
  const camera = state?.camera;
  const isOnline = Boolean(camera?.online);

  return <Panel title="Camera Feed" subtitle="UAV camera telemetry" className="h-full">
    <div className="neu-recessed flex aspect-video flex-col items-center justify-center px-4 text-center">
      <p className="text-[0.78rem] font-medium tracking-[0.15em] text-[var(--text-secondary)]">
        {isOnline ? "CAMERA ONLINE" : "CAMERA OFFLINE"}
      </p>
      <p className="mt-2 text-[0.72rem] text-[var(--text-faint)]">
        {isOnline ? `${camera?.fps ?? "—"} FPS · ${camera?.resolution ?? "—"}` : "Camera telemetry unavailable."}
      </p>
    </div>
    <div className="mt-3 flex items-center justify-between gap-3 text-[0.68rem] text-[var(--text-faint)]">
      <span>Stream: <span className="metric-value">{camera?.stream_status?.toUpperCase() ?? "—"}</span></span>
      <span>Detections: <span className="metric-value">{camera?.human_detection_count ?? "—"}</span></span>
    </div>
  </Panel>;
}
