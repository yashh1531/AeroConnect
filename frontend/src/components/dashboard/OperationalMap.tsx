import { MapContainer, TileLayer, Circle, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Panel } from "../ui/Panel";
import { StatusIndicator } from "../ui/StatusIndicator";
import type { WsStatus } from "../../hooks/useLiveState";
import type { AppState } from "../../types/state";

const CENTER: [number, number] = [12.9716, 77.5946];
const BASE: [number, number] = [12.9688, 77.5905];

export function OperationalMap({ wsStatus, state }: { wsStatus: WsStatus; state: AppState | null }) {
  const base: [number, number] = state ? [state.base_station.latitude, state.base_station.longitude] : BASE;
  const zone: [number, number] = state ? [state.disaster_zone.center_latitude, state.disaster_zone.center_longitude] : CENTER;
  const uavPosition = state && canUseUavPosition(state)
    ? [state.uav.latitude, state.uav.longitude] as [number, number]
    : null;
  const gpsUnavailable = Boolean(state && !state.uav.gps_valid);
  return <Panel title="Operational Map" subtitle="Incident AOI · dark basemap" className="min-h-[420px] lg:min-h-0 lg:h-full" bodyClassName="flex flex-col gap-3 !pt-3" action={<StatusIndicator label={wsStatus === "connected" ? "Feed live" : "Feed offline"} tone={wsStatus === "connected" ? "success" : "danger"} />}>
    <div className="neu-recessed relative min-h-[320px] flex-1 overflow-hidden lg:min-h-[360px]"><MapContainer center={zone} zoom={14} className="h-full min-h-[320px] w-full lg:min-h-[360px]" zoomControl attributionControl>
      <TileLayer attribution="Tiles © Esri" url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}" />
      <Circle center={base} radius={state?.uav.coverage_radius ?? 900} pathOptions={{ color: "#4a4e52", weight: 1, fillColor: "#3a3d40", fillOpacity: 0.12 }} />
      <Circle center={zone} radius={state?.disaster_zone.radius_m ?? 450} pathOptions={{ color: "#5a5550", weight: 1, dashArray: "4 6", fillColor: "#4a4540", fillOpacity: 0.08 }} />
      <CircleMarker center={base} radius={6} pathOptions={{ color: "#7a7e82", fillColor: "#5a5e62", fillOpacity: 0.9 }}><Popup>Ground station · {state?.base_station.backhaul_status ?? "waiting"}</Popup></CircleMarker>
      {state ? <>{uavPosition ? <CircleMarker center={uavPosition} radius={8} pathOptions={{ color: "#8a7a5c", fillColor: "#8a7a5c", fillOpacity: 0.9 }}><Popup>UAV · {state.uav.deployment_state ?? "unknown"} · {state.data_source}</Popup></CircleMarker> : null}{state.users.filter((user) => user.connected).map((user) => <CircleMarker key={user.id} center={[user.latitude, user.longitude]} radius={3} pathOptions={{ color: "#6d7a6f", fillColor: "#6d7a6f", fillOpacity: 0.8 }}><Popup>{user.id} · {user.device_type}</Popup></CircleMarker>)}</> : null}
    </MapContainer><div className="pointer-events-none absolute inset-x-3 top-3 z-[500] flex justify-center"><div className="neu-raised-sm px-3 py-1.5 text-[0.65rem] tracking-[0.08em] text-[var(--text-muted)]">{gpsUnavailable ? "UAV POSITION UNAVAILABLE · NO GPS FIX" : state ? `LIVE · ${state.data_source.toUpperCase()} · UAV · ${state.network.connected_users} USERS · ZONE` : "AWAITING STATE"}</div></div></div>
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-6">{[["UAV", state?.uav.deployment_state ?? "pending"], ["GPS", state?.uav.gps_valid ? "fix" : "no fix"], ["Users", state ? `${state.network.connected_users}/${state.network.total_users}` : "pending"], ["Disaster zone", state?.disaster_zone.severity ?? "scaffold"], ["Coverage", state ? `${state.network.coverage_percentage.toFixed(0)}%` : "scaffold"], ["Base station", state?.base_station.backhaul_status ?? "scaffold"]].map(([name, detail]) => <div key={name} className="neu-recessed-sm px-2.5 py-2"><p className="label-caps">{name}</p><p className="mt-1 text-[0.68rem] text-[var(--text-faint)]">{detail}</p></div>)}</div>
  </Panel>;
}

function hasValidPosition(latitude: number | null, longitude: number | null): boolean {
  return typeof latitude === "number" && typeof longitude === "number" && Number.isFinite(latitude) && Number.isFinite(longitude) && latitude >= -90 && latitude <= 90 && longitude >= -180 && longitude <= 180 && !(latitude === 0 && longitude === 0);
}

function canUseUavPosition(state: AppState): boolean {
  return state.uav.gps_valid && hasValidPosition(state.uav.latitude, state.uav.longitude);
}
