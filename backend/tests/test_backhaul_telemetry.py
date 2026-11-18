from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app, backhaul_telemetry, compose_current_state, simulation
from app.telemetry.models import BackhaulTelemetry


HEALTHY_PAYLOAD = {
    "reachable": True,
    "latency_ms": 2.4,
    "packet_loss_percent": 0,
    "target": "192.168.1.10",
}


@pytest.fixture(autouse=True)
def reset_telemetry_store() -> None:
    simulation.reset()
    backhaul_telemetry.clear()
    yield
    backhaul_telemetry.clear()


def test_fresh_hardware_backhaul_report_overrides_only_backhaul_state() -> None:
    simulated = simulation.snapshot().network.model_copy(deep=True)
    backhaul_telemetry.record(BackhaulTelemetry.model_validate(HEALTHY_PAYLOAD))

    state = compose_current_state()

    assert state.network.backhaul.status == "up"
    assert state.network.backhaul.data_source == "hardware"
    assert state.network.backhaul.latency_ms == 2.4
    assert state.network.backhaul.packet_loss_percent == 0
    assert state.network.throughput == simulated.throughput
    assert state.network.latency == simulated.latency
    assert state.network.link_quality == simulated.link_quality


def test_unreachable_hardware_backhaul_is_down() -> None:
    payload = {**HEALTHY_PAYLOAD, "reachable": False, "latency_ms": None, "packet_loss_percent": 100}
    backhaul_telemetry.record(BackhaulTelemetry.model_validate(payload))

    state = compose_current_state()

    assert state.network.backhaul.status == "down"
    assert state.base_station.backhaul_status == "down"


def test_high_packet_loss_hardware_backhaul_is_degraded() -> None:
    payload = {**HEALTHY_PAYLOAD, "packet_loss_percent": 20}
    backhaul_telemetry.record(BackhaulTelemetry.model_validate(payload))

    state = compose_current_state()

    assert state.network.backhaul.status == "degraded"
    assert state.base_station.backhaul_status == "degraded"


def test_stale_backhaul_report_falls_back_to_simulated_backhaul() -> None:
    backhaul_telemetry.record(
        BackhaulTelemetry.model_validate(HEALTHY_PAYLOAD),
        received_at=datetime.now(timezone.utc) - timedelta(seconds=16),
    )

    state = compose_current_state()

    assert state.network.backhaul.data_source == "simulated"
    assert state.network.backhaul.latency_ms is None


def test_state_endpoint_exposes_hardware_backhaul() -> None:
    with TestClient(app) as client:
        response = client.post("/api/telemetry/backhaul", json=HEALTHY_PAYLOAD)
        state = client.get("/api/state").json()

    assert response.status_code == 200
    assert state["network"]["backhaul"] == {
        "status": "up",
        "latency_ms": 2.4,
        "packet_loss_percent": 0.0,
        "target": "192.168.1.10",
        "data_source": "hardware",
    }
