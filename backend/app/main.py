"""
AERO CONNECT — FastAPI backend (Task 1).

Provides:
  GET  /health          — liveness check
  GET  /api/state       — current AppState snapshot
  WS   /ws              — live AppState stream (1 Hz)

All values are server-owned. UI must not invent metrics.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.models.state import DataSource
from app.simulation.engine import SimulationCommandError, SimulationEngine
from app.simulation.models import (
    BackhaulState,
    LiveClient,
    RfState,
    SimulationState,
    SystemState,
    UavStatus,
)
from app.telemetry.models import (
    BackhaulTelemetry,
    LiveClientsPayload,
    PiTelemetry,
    RfTelemetry,
    PixhawkTelemetry,
)
from app.telemetry.store import (
    BackhaulTelemetryStore,
    LiveClientsStore,
    PiTelemetryStore,
    RfTelemetryStore,
    PixhawkTelemetryStore,
)
from app.websocket import ConnectionManager


manager = ConnectionManager()
simulation = SimulationEngine()

pi_telemetry = PiTelemetryStore(freshness_seconds=15)
rf_telemetry = RfTelemetryStore(freshness_seconds=15)
backhaul_telemetry = BackhaulTelemetryStore(freshness_seconds=15)
pixhawk_telemetry = PixhawkTelemetryStore(freshness_seconds=15)
live_clients = LiveClientsStore(freshness_seconds=15)

broadcast_task: asyncio.Task | None = None


def compose_current_state() -> SimulationState:
    """Overlay fresh real hardware telemetry onto the simulation state."""

    state = simulation.snapshot().model_copy(deep=True)

    # The client scan is independent of the simulation users. Expire it rather
    # than continuing to display devices which the Pi has stopped reporting.
    discovered_clients = live_clients.fresh_clients()
    state.live_clients = (
        [LiveClient.model_validate(client.model_dump(mode="json")) for client in discovered_clients]
        if discovered_clients is not None
        else []
    )

    # ---------------------------------------------------------
    # Raspberry Pi system telemetry
    # ---------------------------------------------------------
    telemetry = pi_telemetry.fresh_telemetry()

    if telemetry is not None:
        state.system = SystemState(
            cpu_usage=telemetry.cpu_usage,
            memory_usage=telemetry.memory_usage,
            temperature=telemetry.temperature,
            uptime=telemetry.uptime,
            storage_usage=telemetry.storage_usage,
            network_interface_status=telemetry.network_interface_status,
            data_source=DataSource.HARDWARE,
        )

    # ---------------------------------------------------------
    # RTL-SDR RF telemetry
    # ---------------------------------------------------------
    rf_report = rf_telemetry.fresh_telemetry()

    if rf_report is not None:
        state.rf = RfState(
            active_bands=[
                f"{band.start_mhz:.3f}-{band.end_mhz:.3f} MHz"
                for band in rf_report.occupied_bands
            ],
            spectrum_activity=[],
            peak_frequency=rf_report.peak_frequency_mhz,
            activity_level=rf_report.activity_percent,
            noise_floor=rf_report.noise_floor_db,
            detected_signals=len(rf_report.occupied_bands),
            data_source=DataSource.HARDWARE,
            scan_start_mhz=rf_report.scan_start_mhz,
            scan_end_mhz=rf_report.scan_end_mhz,
            threshold_db=rf_report.threshold_db,
            peak_power_db=rf_report.peak_power_db,
            occupied_bins=rf_report.occupied_bins,
            total_bins=rf_report.total_bins,
            occupied_bands=[
                band.model_dump()
                for band in rf_report.occupied_bands
            ],
        )

    # ---------------------------------------------------------
    # Pixhawk telemetry
    # ---------------------------------------------------------
    pixhawk = pixhawk_telemetry.fresh_telemetry()

    if pixhawk is not None:
        has_hardware_gps = (
            pixhawk.gps_valid
            and pixhawk.latitude is not None
            and pixhawk.longitude is not None
            and not (pixhawk.latitude == 0 and pixhawk.longitude == 0)
        )
        state.uav.gps_valid = has_hardware_gps
        state.uav.satellites = pixhawk.satellites
        state.uav.gps_fix = pixhawk.gps_fix

        # Only use GPS coordinates when the GPS position is valid.
        # This prevents invalid 0,0 coordinates indoors.
        if has_hardware_gps:
            state.uav.latitude = pixhawk.latitude
            state.uav.longitude = pixhawk.longitude

        # Real Pixhawk flight telemetry
        if pixhawk.altitude is not None:
            state.uav.altitude = pixhawk.altitude

        if pixhawk.ground_speed is not None:
            state.uav.speed = pixhawk.ground_speed

        if pixhawk.heading is not None:
            state.uav.heading = pixhawk.heading

        # Use battery percentage only when Pixhawk provides it.
        if pixhawk.battery_remaining is not None:
            state.uav.battery = pixhawk.battery_remaining

        # Map Pixhawk armed state to the dashboard UAV status.
        if pixhawk.armed is True:
            state.uav.status = UavStatus.IN_FLIGHT
        elif pixhawk.armed is False:
            state.uav.status = UavStatus.GROUNDED

        # Mark the overall state as hardware-backed.
        state.data_source = DataSource.HARDWARE

    # ---------------------------------------------------------
    # Pi-to-backend NanoStation backhaul probe
    # ---------------------------------------------------------
    backhaul = backhaul_telemetry.fresh_telemetry()

    if backhaul is not None:
        backhaul_status = _backhaul_status(backhaul)
        state.network.backhaul = BackhaulState(
            status=backhaul_status,
            latency_ms=backhaul.latency_ms,
            packet_loss_percent=backhaul.packet_loss_percent,
            target=backhaul.target,
            data_source=DataSource.HARDWARE,
        )
        state.network.backhaul_status = backhaul_status
        state.base_station.backhaul_status = backhaul_status

    return state


async def _broadcast_loop() -> None:
    """Advance and broadcast state once per second while clients are connected."""

    while True:
        await asyncio.sleep(1.0)
        simulation.advance()

        if manager.active_connections:
            await manager.broadcast_text(
                compose_current_state().model_dump_json()
            )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global broadcast_task

    broadcast_task = asyncio.create_task(_broadcast_loop())

    yield

    if broadcast_task is not None:
        broadcast_task.cancel()

        try:
            await broadcast_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="AERO CONNECT API",
    description="Disaster-response communication dashboard backend (simulation-first).",
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "aero-connect",
    }


@app.get("/api/state")
async def get_state() -> SimulationState:
    return compose_current_state()


@app.post("/api/telemetry/pi")
async def ingest_pi_telemetry(
    telemetry: PiTelemetry,
) -> dict[str, object]:
    received_at = pi_telemetry.record(telemetry)

    return {
        "accepted": True,
        "received_at": received_at,
    }


@app.post("/api/telemetry/rf")
async def ingest_rf_telemetry(
    telemetry: RfTelemetry,
) -> dict[str, object]:
    received_at = rf_telemetry.record(telemetry)

    return {
        "accepted": True,
        "received_at": received_at,
    }


@app.post("/api/telemetry/backhaul")
async def ingest_backhaul_telemetry(
    telemetry: BackhaulTelemetry,
) -> dict[str, object]:
    received_at = backhaul_telemetry.record(telemetry)

    return {
        "accepted": True,
        "received_at": received_at,
    }


@app.post("/api/telemetry/pixhawk")
async def ingest_pixhawk_telemetry(
    telemetry: PixhawkTelemetry,
) -> dict[str, object]:
    received_at = pixhawk_telemetry.record(telemetry)

    return {
        "accepted": True,
        "received_at": received_at,
    }


@app.post("/api/clients")
async def ingest_live_clients(payload: LiveClientsPayload) -> dict[str, object]:
    """Accept the latest real-device scan from the Raspberry Pi."""

    received_at = live_clients.record(payload.clients)
    return {
        "accepted": True,
        "received_at": received_at,
        "client_count": len(payload.clients),
    }


def _command_error(error: SimulationCommandError) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail=str(error),
    )


def _backhaul_status(telemetry: BackhaulTelemetry) -> str:
    if not telemetry.reachable:
        return "down"
    if (
        (telemetry.packet_loss_percent is not None and telemetry.packet_loss_percent >= 5)
        or (telemetry.latency_ms is not None and telemetry.latency_ms >= 100)
    ):
        return "degraded"
    return "up"


@app.post(
    "/api/simulation/deploy",
    response_model=SimulationState,
)
async def deploy_uav() -> SimulationState:
    try:
        return simulation.deploy_uav()
    except SimulationCommandError as error:
        raise _command_error(error) from error


@app.post(
    "/api/simulation/return",
    response_model=SimulationState,
)
async def return_uav() -> SimulationState:
    try:
        return simulation.return_uav()
    except SimulationCommandError as error:
        raise _command_error(error) from error


@app.post(
    "/api/simulation/reset",
    response_model=SimulationState,
)
async def reset_simulation() -> SimulationState:
    return simulation.reset()


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
) -> None:
    await manager.connect(websocket)

    # Send current snapshot immediately so the UI is not blank
    # until the next tick.
    await websocket.send_text(
        compose_current_state().model_dump_json()
    )

    try:
        while True:
            # Keep the socket open; clients may send pings
            # or control messages later.
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)
