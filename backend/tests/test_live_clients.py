from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app, compose_current_state, live_clients, simulation
from app.telemetry.models import LiveClient


PAYLOAD = {
    "clients": [
        {
            "ip": "10.42.0.142",
            "mac": "2a:49:59:2d:36:0a",
            "hostname": "phone",
            "status": "CONNECTED",
            "interface": "wlan0",
            "last_seen": "2026-09-15T12:00:00Z",
        }
    ]
}


@pytest.fixture(autouse=True)
def reset_live_client_store() -> None:
    simulation.reset()
    live_clients.clear()
    yield
    live_clients.clear()


def test_fresh_live_clients_are_separate_from_simulated_users() -> None:
    simulated_users = [user.model_copy(deep=True) for user in simulation.snapshot().users]
    live_clients.record([LiveClient.model_validate(PAYLOAD["clients"][0])])

    state = compose_current_state()

    assert state.users == simulated_users
    assert len(state.live_clients) == 1
    assert state.live_clients[0].mac == "2a:49:59:2d:36:0a"


def test_stale_live_client_scan_is_not_returned() -> None:
    live_clients.record(
        [LiveClient.model_validate(PAYLOAD["clients"][0])],
        received_at=datetime.now(timezone.utc) - timedelta(seconds=16),
    )

    assert compose_current_state().live_clients == []


def test_clients_endpoint_validates_and_exposes_latest_scan() -> None:
    with TestClient(app) as client:
        response = client.post("/api/clients", json=PAYLOAD)
        state = client.get("/api/state").json()

    assert response.status_code == 200
    assert response.json()["client_count"] == 1
    assert state["live_clients"][0]["ip"] == PAYLOAD["clients"][0]["ip"]
    assert state["live_clients"][0]["mac"] == PAYLOAD["clients"][0]["mac"]
    assert state["live_clients"][0]["hostname"] == PAYLOAD["clients"][0]["hostname"]
    assert state["live_clients"][0]["status"] == PAYLOAD["clients"][0]["status"]
    assert state["live_clients"][0]["interface"] == PAYLOAD["clients"][0]["interface"]


def test_clients_endpoint_rejects_invalid_mac() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/clients",
            json={"clients": [{**PAYLOAD["clients"][0], "mac": "not-a-mac"}]},
        )

    assert response.status_code == 422


def test_websocket_initial_state_contains_live_clients() -> None:
    with TestClient(app) as client:
        assert client.post("/api/clients", json=PAYLOAD).status_code == 200
        with client.websocket_connect("/ws") as websocket:
            state = websocket.receive_json()

    assert state["live_clients"][0]["ip"] == "10.42.0.142"
