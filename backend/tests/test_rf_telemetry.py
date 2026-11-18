from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app, compose_current_state, pi_telemetry, rf_telemetry, simulation
from app.telemetry.models import RfTelemetry


PAYLOAD = {
    "scan_start_mhz": 88.0,
    "scan_end_mhz": 108.0,
    "noise_floor_db": -24.3,
    "threshold_db": -18.3,
    "peak_frequency_mhz": 104.836,
    "peak_power_db": -13.86,
    "activity_percent": 1.56,
    "occupied_bins": 4,
    "total_bins": 257,
    "occupied_bands": [
        {
            "start_mhz": 104.758,
            "end_mhz": 104.836,
            "peak_mhz": 104.836,
            "peak_power_db": -15.29,
            "bins": 2,
        }
    ],
}


@pytest.fixture(autouse=True)
def reset_telemetry_stores() -> None:
    simulation.reset()
    pi_telemetry.clear()
    rf_telemetry.clear()
    yield
    pi_telemetry.clear()
    rf_telemetry.clear()


def test_valid_rf_telemetry_is_accepted() -> None:
    with TestClient(app) as client:
        response = client.post("/api/telemetry/rf", json=PAYLOAD)
    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert "received_at" in response.json()


@pytest.mark.parametrize(
    "payload",
    [
        {**PAYLOAD, "activity_percent": 101},
        {**PAYLOAD, "occupied_bins": 258},
        {**PAYLOAD, "scan_end_mhz": 80.0},
    ],
)
def test_invalid_rf_payload_is_rejected(payload: dict[str, object]) -> None:
    with TestClient(app) as client:
        assert client.post("/api/telemetry/rf", json=payload).status_code == 422


def test_fresh_rf_telemetry_appears_in_state() -> None:
    with TestClient(app) as client:
        client.post("/api/telemetry/rf", json=PAYLOAD)
        state = client.get("/api/state").json()
    assert state["rf"]["data_source"] == "hardware"
    assert state["rf"]["peak_frequency"] == PAYLOAD["peak_frequency_mhz"]
    assert state["rf"]["occupied_bands"] == PAYLOAD["occupied_bands"]
    assert state["rf"]["scan_start_mhz"] == PAYLOAD["scan_start_mhz"]


def test_stale_rf_telemetry_falls_back_to_simulation() -> None:
    rf_telemetry.record(
        RfTelemetry.model_validate(PAYLOAD),
        received_at=datetime.now(timezone.utc) - timedelta(seconds=16),
    )
    state = compose_current_state()
    assert state.rf.data_source == "simulated"
    assert state.rf.scan_start_mhz is None
