from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app, compose_current_state, pi_telemetry, simulation
from app.telemetry.models import PiTelemetry


PAYLOAD = {
    "cpu_usage": 31.7,
    "memory_usage": 48.2,
    "temperature": 53.4,
    "uptime": 123456,
    "storage_usage": 36.1,
    "network_interface_status": "up",
    "ip_address": "192.168.1.23",
}


@pytest.fixture(autouse=True)
def reset_telemetry_store() -> None:
    simulation.reset()
    pi_telemetry.clear()
    yield
    pi_telemetry.clear()


def test_valid_pi_telemetry_is_accepted() -> None:
    with TestClient(app) as client:
        response = client.post("/api/telemetry/pi", json=PAYLOAD)
    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert "received_at" in response.json()


@pytest.mark.parametrize(
    ("field", "value"),
    [("cpu_usage", 101), ("memory_usage", -1), ("storage_usage", 100.1)],
)
def test_invalid_utilization_is_rejected(field: str, value: float) -> None:
    payload = {**PAYLOAD, field: value}
    with TestClient(app) as client:
        assert client.post("/api/telemetry/pi", json=payload).status_code == 422


def test_invalid_ip_is_rejected() -> None:
    with TestClient(app) as client:
        assert client.post("/api/telemetry/pi", json={**PAYLOAD, "ip_address": "not-an-ip"}).status_code == 422


def test_fresh_telemetry_overrides_only_system_state() -> None:
    simulated = simulation.snapshot().model_copy(deep=True)
    pi_telemetry.record(PiTelemetry.model_validate(PAYLOAD))
    composed = compose_current_state()
    assert composed.system.cpu_usage == PAYLOAD["cpu_usage"]
    assert composed.system.data_source == "hardware"
    assert composed.uav == simulated.uav
    assert composed.network == simulated.network
    assert composed.rf == simulated.rf


def test_stale_telemetry_falls_back_to_simulation() -> None:
    pi_telemetry.record(
        PiTelemetry.model_validate(PAYLOAD),
        received_at=datetime.now(timezone.utc) - timedelta(seconds=16),
    )
    assert compose_current_state().system.data_source == "simulated"


def test_state_endpoint_returns_hardware_system_when_fresh() -> None:
    with TestClient(app) as client:
        client.post("/api/telemetry/pi", json=PAYLOAD)
        state = client.get("/api/state").json()
    assert state["system"]["cpu_usage"] == PAYLOAD["cpu_usage"]
    assert state["system"]["data_source"] == "hardware"
    assert state["data_source"] == "simulated"


def test_websocket_initial_state_uses_composed_state() -> None:
    with TestClient(app) as client:
        client.post("/api/telemetry/pi", json=PAYLOAD)
        with client.websocket_connect("/ws") as websocket:
            state = websocket.receive_json()
    assert state["system"]["memory_usage"] == PAYLOAD["memory_usage"]
    assert state["system"]["data_source"] == "hardware"
