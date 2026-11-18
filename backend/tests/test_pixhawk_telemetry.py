from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app, compose_current_state, pixhawk_telemetry, simulation
from app.telemetry.models import PixhawkTelemetry


VALID_GPS_PAYLOAD = {
    "armed": True,
    "gps_valid": True,
    "gps_fix": 3,
    "satellites": 12,
    "latitude": 12.9755,
    "longitude": 77.601,
    "altitude": 121.5,
    "ground_speed": 17.2,
    "heading": 92.0,
    "battery_remaining": 78.0,
}


@pytest.fixture(autouse=True)
def reset_telemetry_store() -> None:
    simulation.reset()
    pixhawk_telemetry.clear()
    yield
    pixhawk_telemetry.clear()


def test_fresh_pixhawk_with_valid_gps_overrides_uav_position() -> None:
    pixhawk_telemetry.record(PixhawkTelemetry.model_validate(VALID_GPS_PAYLOAD))

    state = compose_current_state()

    assert state.data_source == "hardware"
    assert state.uav.gps_valid is True
    assert state.uav.gps_fix == 3
    assert state.uav.satellites == 12
    assert state.uav.latitude == VALID_GPS_PAYLOAD["latitude"]
    assert state.uav.longitude == VALID_GPS_PAYLOAD["longitude"]


def test_fresh_pixhawk_without_gps_fix_keeps_simulated_position_unmarked() -> None:
    simulated = simulation.snapshot().uav
    payload = {**VALID_GPS_PAYLOAD, "gps_valid": False, "gps_fix": 0, "satellites": 0, "latitude": None, "longitude": None}
    pixhawk_telemetry.record(PixhawkTelemetry.model_validate(payload))

    state = compose_current_state()

    assert state.data_source == "hardware"
    assert state.uav.gps_valid is False
    assert state.uav.gps_fix == 0
    assert state.uav.satellites == 0
    assert state.uav.latitude == simulated.latitude
    assert state.uav.longitude == simulated.longitude


def test_zero_coordinates_are_not_exposed_as_valid_hardware_gps() -> None:
    payload = {**VALID_GPS_PAYLOAD, "latitude": 0, "longitude": 0}
    pixhawk_telemetry.record(PixhawkTelemetry.model_validate(payload))

    state = compose_current_state()

    assert state.uav.gps_valid is False


def test_stale_pixhawk_telemetry_falls_back_to_simulated_gps_state() -> None:
    pixhawk_telemetry.record(
        PixhawkTelemetry.model_validate(VALID_GPS_PAYLOAD),
        received_at=datetime.now(timezone.utc) - timedelta(seconds=16),
    )

    state = compose_current_state()

    assert state.data_source == "simulated"
    assert state.uav.gps_valid is False
    assert state.uav.gps_fix is None
    assert state.uav.satellites is None


def test_pixhawk_state_endpoint_exposes_gps_provenance() -> None:
    with TestClient(app) as client:
        response = client.post("/api/telemetry/pixhawk", json=VALID_GPS_PAYLOAD)
        state = client.get("/api/state").json()

    assert response.status_code == 200
    assert state["uav"]["gps_valid"] is True
    assert state["uav"]["gps_fix"] == 3
    assert state["uav"]["satellites"] == 12
