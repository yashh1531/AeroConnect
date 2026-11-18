"""Deterministic, stateful disaster-response simulation engine."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from app.models.state import ConnectionStatus
from app.simulation.geo import clamp, haversine_m, move_towards
from app.simulation.models import (
    DeploymentState,
    EventSeverity,
    EventType,
    SimEvent,
    SimulationState,
    UavStatus,
)
from app.simulation.scenario import (
    BASE_LAT,
    BASE_LON,
    UAV_CRUISE_ALT_M,
    UAV_CRUISE_SPEED_MPS,
    ZONE_LAT,
    ZONE_LON,
    create_initial_state,
)


class SimulationCommandError(ValueError):
    """Raised when a command does not apply to the current flight state."""


class SimulationEngine:
    """Owns and evolves one scenario. No random generator is used."""

    HISTORY_LIMIT = 40
    EVENT_LIMIT = 60

    def __init__(self) -> None:
        self.state = create_initial_state()

    def snapshot(self) -> SimulationState:
        return self.state

    def deploy_uav(self) -> SimulationState:
        if self.state.uav.deployment_state not in {
            DeploymentState.STANDBY,
            DeploymentState.LANDED,
        }:
            raise SimulationCommandError("UAV is already deployed or transitioning.")
        uav = self.state.uav
        uav.deployment_state = DeploymentState.DEPLOYING
        uav.status = UavStatus.IN_FLIGHT
        uav.target_latitude, uav.target_longitude = ZONE_LAT, ZONE_LON
        self.state.status = ConnectionStatus.LIVE
        self.state.message = "UAV deploying to disaster zone."
        self._event(EventType.UAV, EventSeverity.INFO, "UAV deployed to disaster zone.")
        return self.state

    def return_uav(self) -> SimulationState:
        if self.state.uav.deployment_state not in {
            DeploymentState.DEPLOYING,
            DeploymentState.DEPLOYED,
        }:
            raise SimulationCommandError("UAV is not airborne and cannot return.")
        uav = self.state.uav
        uav.deployment_state = DeploymentState.RETURNING
        uav.status = UavStatus.LANDING
        uav.target_latitude, uav.target_longitude = BASE_LAT, BASE_LON
        self.state.message = "UAV returning to base."
        self._event(EventType.UAV, EventSeverity.WARNING, "UAV return-to-base initiated.")
        return self.state

    def reset(self) -> SimulationState:
        self.state = create_initial_state()
        self._event(EventType.SYSTEM, EventSeverity.INFO, "Simulation reset to baseline scenario.")
        return self.state

    def advance(self, seconds: float = 1.0) -> SimulationState:
        """Advance a fixed simulation timestep and derive all dependent metrics."""
        if seconds <= 0:
            raise ValueError("seconds must be positive")
        state = self.state
        state.tick += 1
        state.sim_time += seconds
        state.server_time = datetime.now(timezone.utc)
        state.status = ConnectionStatus.LIVE
        self._advance_uav(seconds)
        self._derive_users_and_network()
        self._derive_rf_camera_system()
        state.message = self._message_for_state()
        return state

    def _advance_uav(self, seconds: float) -> None:
        uav = self.state.uav
        if uav.deployment_state in {DeploymentState.DEPLOYING, DeploymentState.RETURNING}:
            target_lat, target_lon = uav.target_latitude, uav.target_longitude
            assert target_lat is not None and target_lon is not None
            uav.speed = UAV_CRUISE_SPEED_MPS
            uav.latitude, uav.longitude, uav.heading, arrived = move_towards(
                uav.latitude, uav.longitude, target_lat, target_lon, uav.speed * seconds
            )
            if uav.deployment_state == DeploymentState.DEPLOYING:
                uav.altitude = min(UAV_CRUISE_ALT_M, uav.altitude + 12 * seconds)
            else:
                remaining = haversine_m(uav.latitude, uav.longitude, BASE_LAT, BASE_LON)
                uav.altitude = min(UAV_CRUISE_ALT_M, max(0, remaining / 6))
            uav.battery = clamp(uav.battery - 0.035 * seconds, 0, 100)
            if arrived:
                if uav.deployment_state == DeploymentState.DEPLOYING:
                    uav.deployment_state, uav.status = DeploymentState.DEPLOYED, UavStatus.ON_STATION
                    uav.speed, uav.altitude = 0.0, UAV_CRUISE_ALT_M
                    self._event(EventType.UAV, EventSeverity.INFO, "UAV established coverage over disaster zone.")
                else:
                    uav.deployment_state, uav.status = DeploymentState.LANDED, UavStatus.GROUNDED
                    uav.speed, uav.altitude = 0.0, 0.0
                    self._event(EventType.UAV, EventSeverity.INFO, "UAV landed at base.")
        elif uav.deployment_state == DeploymentState.DEPLOYED:
            # A gentle station-keeping orbit avoids a static, artificial-looking node.
            angle = self.state.sim_time / 75
            uav.latitude = ZONE_LAT + math.sin(angle) * 0.00022
            uav.longitude = ZONE_LON + math.cos(angle) * 0.00022
            uav.heading = (math.degrees(angle) + 90) % 360
            uav.altitude, uav.speed = UAV_CRUISE_ALT_M, 4.0
            uav.battery = clamp(uav.battery - 0.025 * seconds, 0, 100)

    def _derive_users_and_network(self) -> None:
        state, uav = self.state, self.state.uav
        connected = []
        for index, user in enumerate(state.users):
            distance = haversine_m(uav.latitude, uav.longitude, user.latitude, user.longitude)
            user.distance_to_node_m = round(distance, 1)
            if uav.deployment_state in {DeploymentState.DEPLOYING, DeploymentState.DEPLOYED, DeploymentState.RETURNING}:
                quality = clamp(100 - (distance / uav.coverage_radius) * 78 - (index % 4) * 2, 0, 100)
            else:
                quality = 0.0
            was_connected = user.connected
            user.connected = quality >= 28
            user.signal_quality = round(quality, 1)
            user.latency = round(12 + (100 - quality) * 0.72, 1) if user.connected else 0.0
            user.packet_loss = round(clamp((38 - quality) * 0.12, 0, 8), 2) if user.connected else 100.0
            user.throughput = round(max(0, quality - 22) * 0.065, 2) if user.connected else 0.0
            user.last_seen = state.server_time if user.connected else None
            if was_connected != user.connected:
                verb = "connected" if user.connected else "disconnected"
                self._event(EventType.NETWORK, EventSeverity.INFO if user.connected else EventSeverity.WARNING, f"{user.id} {verb} to UAV coverage.")
            if user.connected:
                connected.append(user)
        count = len(connected)
        avg_quality = sum(u.signal_quality for u in connected) / count if count else 0
        load_factor = count / max(1, len(state.users))
        throughput = sum(u.throughput for u in connected) * (1 - 0.18 * load_factor)
        latency = sum(u.latency for u in connected) / count if count else 0
        loss = sum(u.packet_loss for u in connected) / count if count else 0
        status = "offline" if count == 0 else "degraded" if avg_quality < 45 else "online"
        state.network.connected_users = count
        state.network.throughput = round(throughput, 2)
        state.network.latency = round(latency, 1)
        state.network.packet_loss = round(loss, 2)
        state.network.link_quality = round(avg_quality, 1)
        state.network.signal_strength = round(-92 + avg_quality * 0.48, 1) if count else -105.0
        state.network.coverage_percentage = round(count / len(state.users) * 100, 1)
        state.network.status = status
        state.network.backhaul_status = "up" if status == "online" else "degraded" if count else "up"
        state.network.backhaul.status = state.network.backhaul_status
        state.base_station.backhaul_status = state.network.backhaul_status
        state.throughput_history = (state.throughput_history + [state.network.throughput])[-self.HISTORY_LIMIT :]
        state.latency_history = (state.latency_history + [state.network.latency])[-self.HISTORY_LIMIT :]

    def _derive_rf_camera_system(self) -> None:
        state, t = self.state, self.state.sim_time
        activity = 8 + state.network.connected_users * 2.7 + 7 * (1 + math.sin(t / 9))
        state.rf.activity_level = round(clamp(activity, 0, 100), 1)
        state.rf.noise_floor = round(-101 + state.rf.activity_level * 0.18, 1)
        state.rf.peak_frequency = 2437.0 if int(t / 18) % 2 == 0 else 5805.0
        state.rf.detected_signals = 1 + int(state.rf.activity_level // 18)
        state.rf.active_bands = ["2.4 GHz", "5.8 GHz"] if state.network.connected_users else ["2.4 GHz"]
        state.rf.spectrum_activity = [round(clamp(0.08 + 0.62 * max(0, math.sin((i + 1) * 0.43 + t / 10)) ** 3 + state.rf.activity_level / 260, 0, 1), 2) for i in range(28)]
        camera_active = self.state.uav.deployment_state == DeploymentState.DEPLOYED
        state.camera.online = camera_active
        state.camera.stream_status = "live" if camera_active else "idle"
        state.camera.fps = 24 if camera_active else 0
        state.camera.resolution = "1280×720"
        detections = int(t // 22) if camera_active else 0
        if detections > state.camera.human_detection_count:
            state.camera.human_detection_count = detections
            state.camera.last_detection = state.server_time
            self._event(EventType.CAMERA, EventSeverity.WARNING, "Camera detected a person in the incident area.")
        workload = state.network.connected_users * 1.55 + state.rf.activity_level * 0.18
        state.system.cpu_usage = round(clamp(13 + workload + 4 * math.sin(t / 12), 0, 100), 1)
        state.system.memory_usage = round(clamp(24 + state.network.connected_users * 1.2, 0, 100), 1)
        state.system.temperature = round(40 + state.system.cpu_usage * 0.32, 1)
        state.system.uptime = int(state.sim_time)
        state.system.storage_usage = 31.0
        state.system.network_interface_status = "up" if state.network.status != "offline" else "degraded"
        state.active_alerts = sum(1 for event in state.events if event.severity != EventSeverity.INFO and (state.server_time - event.timestamp).total_seconds() < 180)

    def _message_for_state(self) -> str:
        deployment = self.state.uav.deployment_state.value.lower()
        return f"Simulation live · UAV {deployment} · {self.state.network.connected_users} users connected."

    def _event(self, event_type: EventType, severity: EventSeverity, message: str) -> None:
        state = self.state
        event = SimEvent(id=f"evt-{state.tick}-{len(state.events)}", timestamp=state.server_time, type=event_type, severity=severity, message=message)
        state.events = [event, *state.events][: self.EVENT_LIMIT]
