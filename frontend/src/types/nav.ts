export type NavId =
  | "dashboard"
  | "uav"
  | "network"
  | "users"
  | "disaster"
  | "camera"
  | "rf"
  | "system"
  | "events";

export interface NavItemDef {
  id: NavId;
  label: string;
}

export const NAV_ITEMS: NavItemDef[] = [
  { id: "dashboard", label: "Dashboard" },
  { id: "uav", label: "UAV & Flight" },
  { id: "network", label: "Network" },
  { id: "users", label: "Users" },
  { id: "disaster", label: "Disaster Zone" },
  { id: "camera", label: "Camera" },
  { id: "rf", label: "RF Spectrum" },
  { id: "system", label: "System" },
  { id: "events", label: "Events" },
];

export const PAGE_META: Record<NavId, { title: string; description: string }> = {
  dashboard: {
    title: "Operations Dashboard",
    description: "Disaster-response communications overview",
  },
  uav: {
    title: "UAV & Flight",
    description: "Airframe status and mission track",
  },
  network: {
    title: "Network",
    description: "Backhaul and access-link performance",
  },
  users: {
    title: "Users",
    description: "Ground devices within coverage",
  },
  disaster: {
    title: "Disaster Zone",
    description: "Incident boundary and zone posture",
  },
  camera: {
    title: "Camera",
    description: "Pi camera feed and detection overlay",
  },
  rf: {
    title: "RF Spectrum",
    description: "RTL-SDR activity overview",
  },
  system: {
    title: "System",
    description: "Raspberry Pi and ground-station health",
  },
  events: {
    title: "Events",
    description: "Operational event log",
  },
};
