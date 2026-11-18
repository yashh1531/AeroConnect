"""Simulation entity models — source of truth for live Aero Connect state."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.models.state import ConnectionStatus, DataSource


class DeploymentState(str, Enum):
    STANDBY = "STANDBY"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    RETURNING = "RETURNING"
    LANDED = "LANDED"


class UavStatus(str, Enum):
    IDLE = "idle"
    IN_FLIGHT = "in_flight"
    ON_STATION = "on_station"
    LANDING = "landing"
    GROUNDED = "grounded"


class EventSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class EventType(str, Enum):
    SYSTEM = "system"
    UAV = "uav"
    NETWORK = "network"
    DISASTER = "disaster"
    CAMERA = "camera"
    RF = "rf"
    ALERT = "alert"


class UavState(BaseModel):
    id: str
    latitude: float
    longitude: float
    altitude: float
    speed: float
    battery: float
    status: UavStatus
    deployment_state: DeploymentState
    coverage_radius: float
    heading: float
    # GPS provenance is false for simulation and set from fresh Pixhawk telemetry.
    gps_valid: bool = False
    satellites: int | None = None
    gps_fix: int | None = None
    target_latitude: float | None = None
    target_longitude: float | None = None


class GroundUser(BaseModel):
    id: str
    device_type: str
    latitude: float
    longitude: float
    connected: bool
    signal_quality: float
    latency: float
    packet_loss: float
    throughput: float
    last_seen: datetime | None = None
    distance_to_node_m: float = 0.0


class LiveClient(BaseModel):
    """A real device observed by the Raspberry Pi client-discovery agent."""

    ip: str
    mac: str
    hostname: str | None = None
    status: Literal["CONNECTED", "STALE", "DISCONNECTED"]
    interface: str
    last_seen: datetime | None = None


class DisasterZone(BaseModel):
    center_latitude: float
    center_longitude: float
    radius_m: float
    severity: Literal["low", "moderate", "high", "critical"]
    active: bool


class BaseStation(BaseModel):
    id: str
    latitude: float
    longitude: float
    status: Literal["online", "degraded", "offline"]
    backhaul_status: Literal["up", "degraded", "down"]


class BackhaulState(BaseModel):
    """Backhaul health, independently sourced from aggregate access metrics."""

    status: Literal["up", "degraded", "down"] = "up"
    latency_ms: float | None = None
    packet_loss_percent: float | None = None
    target: str | None = None
    data_source: DataSource = DataSource.SIMULATED


class NetworkMetrics(BaseModel):
    connected_users: int
    total_users: int
    throughput: float  # Mbps aggregate
    latency: float  # ms average (connected)
    packet_loss: float  # % average (connected)
    link_quality: float  # 0-100
    signal_strength: float  # dBm, aggregate
    coverage_percentage: float  # % of users inside coverage radius
    status: Literal["online", "degraded", "offline"]
    backhaul_status: Literal["up", "degraded", "down"]
    backhaul: BackhaulState = Field(default_factory=BackhaulState)


class RfState(BaseModel):
    active_bands: list[str]
    spectrum_activity: list[float]  # normalized 0-1 bins
    peak_frequency: float  # MHz
    activity_level: float  # 0-100
    noise_floor: float  # dBm
    detected_signals: int
    data_source: DataSource = DataSource.SIMULATED
    scan_start_mhz: float | None = None
    scan_end_mhz: float | None = None
    threshold_db: float | None = None
    peak_power_db: float | None = None
    occupied_bins: int | None = None
    total_bins: int | None = None
    occupied_bands: list[dict[str, float | int]] = Field(default_factory=list)


class CameraState(BaseModel):
    online: bool
    human_detection_count: int
    last_detection: datetime | None = None
    stream_status: Literal["live", "idle", "offline"]
    fps: int
    resolution: str


class SystemState(BaseModel):
    cpu_usage: float
    memory_usage: float
    temperature: float
    uptime: int  # seconds
    storage_usage: float
    network_interface_status: Literal["up", "degraded", "down"]
    data_source: DataSource = DataSource.SIMULATED


class SimEvent(BaseModel):
    id: str
    timestamp: datetime
    type: EventType
    severity: EventSeverity
    message: str


class SimulationState(BaseModel):
    """Complete live state broadcast over WebSocket."""

    tick: int = 0
    sim_time: float = 0.0
    status: ConnectionStatus = ConnectionStatus.IDLE
    message: str = "Simulation ready."
    data_source: DataSource = DataSource.SIMULATED
    server_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    uav: UavState
    users: list[GroundUser]
    live_clients: list[LiveClient] = Field(default_factory=list)
    disaster_zone: DisasterZone
    base_station: BaseStation
    network: NetworkMetrics
    rf: RfState
    camera: CameraState
    system: SystemState
    events: list[SimEvent] = Field(default_factory=list)
    active_alerts: int = 0
    throughput_history: list[float] = Field(default_factory=list)
    latency_history: list[float] = Field(default_factory=list)
