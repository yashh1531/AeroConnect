"""Default disaster-response scenario (deterministic layout)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.state import ConnectionStatus, DataSource
from app.simulation.models import (
    BaseStation,
    CameraState,
    DeploymentState,
    DisasterZone,
    EventSeverity,
    EventType,
    GroundUser,
    NetworkMetrics,
    RfState,
    SimEvent,
    SimulationState,
    SystemState,
    UavState,
    UavStatus,
)

# Ground station / home pad (matches existing map scaffold area)
BASE_LAT = 12.9688
BASE_LON = 77.5905

# Active incident center — east-northeast of base
ZONE_LAT = 12.9755
ZONE_LON = 77.6010
ZONE_RADIUS_M = 550.0

UAV_COVERAGE_RADIUS_M = 750.0
UAV_CRUISE_ALT_M = 120.0
UAV_CRUISE_SPEED_MPS = 18.0

# Fixed offsets (metres approx via deg) for 20 users around the zone.
# ~1 deg lat ≈ 111_320 m; lon scale ≈ cos(lat)*111_320
_USER_OFFSETS_M: list[tuple[float, float]] = [
    (-180, -90),
    (-140, 40),
    (-100, 160),
    (-60, -200),
    (-20, 220),
    (20, -40),
    (60, 120),
    (100, -160),
    (140, 60),
    (180, -120),
    (-220, 100),
    (220, -80),
    (-80, -280),
    (80, 280),
    (-250, -40),
    (250, 40),
    (0, 0),
    (-40, 320),
    (160, 200),
    (-160, -240),
]


def _offset_to_latlon(lat: float, lon: float, north_m: float, east_m: float) -> tuple[float, float]:
    dlat = north_m / 111_320.0
    dlon = east_m / (111_320.0 * max(0.2, abs(__import__("math").cos(__import__("math").radians(lat)))))
    return lat + dlat, lon + dlon


def create_initial_state() -> SimulationState:
    """Build the default scenario: 20 users, standby UAV at base, active zone."""
    now = datetime.now(timezone.utc)
    users: list[GroundUser] = []
    for i, (north, east) in enumerate(_USER_OFFSETS_M, start=1):
        lat, lon = _offset_to_latlon(ZONE_LAT, ZONE_LON, north, east)
        users.append(
            GroundUser(
                id=f"user-{i:02d}",
                device_type=("responder radio" if i % 3 == 0 else "field tablet" if i % 3 == 1 else "mobile phone"),
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                connected=False,
                signal_quality=0.0,
                latency=0.0,
                packet_loss=100.0,
                throughput=0.0,
                last_seen=None,
                distance_to_node_m=0.0,
            )
        )

    uav = UavState(
        id="uav-01",
        latitude=BASE_LAT,
        longitude=BASE_LON,
        altitude=0.0,
        speed=0.0,
        battery=100.0,
        status=UavStatus.GROUNDED,
        deployment_state=DeploymentState.STANDBY,
        coverage_radius=UAV_COVERAGE_RADIUS_M,
        heading=45.0,
        target_latitude=None,
        target_longitude=None,
    )

    events = [
        SimEvent(
            id="evt-boot-1",
            timestamp=now,
            type=EventType.SYSTEM,
            severity=EventSeverity.INFO,
            message="Simulation scenario loaded — UAV STANDBY at base.",
        ),
        SimEvent(
            id="evt-boot-2",
            timestamp=now,
            type=EventType.DISASTER,
            severity=EventSeverity.WARNING,
            message="Disaster zone active — communications degraded in AOI.",
        ),
    ]

    return SimulationState(
        tick=0,
        sim_time=0.0,
        status=ConnectionStatus.IDLE,
        message="Simulation ready. UAV on standby.",
        data_source=DataSource.SIMULATED,
        server_time=now,
        uav=uav,
        users=users,
        disaster_zone=DisasterZone(
            center_latitude=ZONE_LAT,
            center_longitude=ZONE_LON,
            radius_m=ZONE_RADIUS_M,
            severity="high",
            active=True,
        ),
        base_station=BaseStation(
            id="gs-01",
            latitude=BASE_LAT,
            longitude=BASE_LON,
            status="online",
            backhaul_status="up",
        ),
        network=NetworkMetrics(
            connected_users=0,
            total_users=len(users),
            throughput=0.0,
            latency=0.0,
            packet_loss=0.0,
            link_quality=0.0,
            signal_strength=-105.0,
            coverage_percentage=0.0,
            status="offline",
            backhaul_status="up",
        ),
        rf=RfState(
            active_bands=["2.4 GHz", "5.8 GHz"],
            spectrum_activity=[0.05] * 28,
            peak_frequency=2437.0,
            activity_level=5.0,
            noise_floor=-100.0,
            detected_signals=1,
        ),
        camera=CameraState(
            online=False,
            human_detection_count=0,
            last_detection=None,
            stream_status="offline",
            fps=0,
            resolution="1280×720",
        ),
        system=SystemState(
            cpu_usage=8.0,
            memory_usage=22.0,
            temperature=42.0,
            uptime=0,
            storage_usage=31.0,
            network_interface_status="up",
            data_source=DataSource.SIMULATED,
        ),
        events=events,
        active_alerts=1,
        throughput_history=[],
        latency_history=[],
    )
