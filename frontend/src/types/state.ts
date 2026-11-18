/** Mirrors backend/app/simulation/models.py. */
export type DataSource = "simulated" | "hardware";
export type ConnectionStatus = "idle" | "live" | "degraded";
export type DeploymentState = "STANDBY" | "DEPLOYING" | "DEPLOYED" | "RETURNING" | "LANDED";
export interface UserState { id: string; device_type: string; connected: boolean; signal_quality: number; latency: number; packet_loss: number; throughput: number; distance_to_node_m: number; latitude: number; longitude: number; last_seen: string | null; }
/** A real device reported by the Raspberry Pi client-network scan. */
export interface LiveClient { ip: string; mac: string; hostname: string | null; status: "CONNECTED" | "STALE" | "DISCONNECTED"; interface: string; last_seen: string | null; }
export interface SimulationEvent { id: string; timestamp: string; type: string; severity: "info" | "warning" | "critical"; message: string; }
/** UAV readings composed by the backend from simulation and, when fresh, Pixhawk telemetry. */
export interface UavState {
  id: string;
  latitude: number | null;
  longitude: number | null;
  altitude: number | null;
  speed: number | null;
  battery: number | null;
  status: string | null;
  deployment_state: DeploymentState | null;
  coverage_radius: number | null;
  heading: number | null;
  gps_valid: boolean;
  satellites: number | null;
  gps_fix: number | null;
}
export interface RfOccupiedBand { start_mhz: number; end_mhz: number; peak_mhz: number; peak_power_db: number; bins: number; }
export interface AppState {
  tick: number; sim_time: number; status: ConnectionStatus; message: string; data_source: DataSource; server_time: string;
  uav: UavState;
  users: UserState[];
  live_clients: LiveClient[];
  disaster_zone: { center_latitude: number; center_longitude: number; radius_m: number; severity: string; active: boolean; };
  base_station: { id: string; latitude: number; longitude: number; status: string; backhaul_status: string; };
  network: { connected_users: number; total_users: number; throughput: number; latency: number; packet_loss: number; link_quality: number; signal_strength: number; coverage_percentage: number; status: string; backhaul_status: string; backhaul: { status: "up" | "degraded" | "down"; latency_ms: number | null; packet_loss_percent: number | null; target: string | null; data_source: DataSource; }; };
  rf: { active_bands: string[]; spectrum_activity: number[]; peak_frequency: number; activity_level: number; noise_floor: number; detected_signals: number; data_source: DataSource; scan_start_mhz: number | null; scan_end_mhz: number | null; threshold_db: number | null; peak_power_db: number | null; occupied_bins: number | null; total_bins: number | null; occupied_bands: RfOccupiedBand[]; };
  camera: { online: boolean; stream_status: string; fps: number; resolution: string; human_detection_count: number; last_detection: string | null; };
  system: { cpu_usage: number; memory_usage: number; temperature: number; uptime: number; storage_usage: number; network_interface_status: string; data_source: DataSource; };
  events: SimulationEvent[]; active_alerts: number; throughput_history: number[]; latency_history: number[];
}
export function isAppState(value: unknown): value is AppState {
  const state = value as Partial<AppState> | null;
  return Boolean(state && typeof state.tick === "number" && state.uav && state.network && Array.isArray(state.users) && Array.isArray(state.events));
}
