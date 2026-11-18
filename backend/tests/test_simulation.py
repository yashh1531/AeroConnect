from fastapi.testclient import TestClient

from app.main import app, simulation
from app.simulation.engine import SimulationEngine
from app.simulation.models import DeploymentState


def test_initial_state_is_standby_and_coherent() -> None:
    state = SimulationEngine().snapshot()
    assert state.uav.deployment_state == DeploymentState.STANDBY
    assert state.network.connected_users == 0
    assert state.network.total_users == len(state.users)


def test_deploy_progresses_smoothly_and_connects_users() -> None:
    engine = SimulationEngine()
    start = engine.snapshot().uav.model_copy(deep=True)
    engine.deploy_uav()
    engine.advance()
    assert engine.snapshot().uav.latitude != start.latitude
    for _ in range(120):
        engine.advance()
    state = engine.snapshot()
    assert state.uav.deployment_state == DeploymentState.DEPLOYED
    assert state.network.connected_users > 0
    assert state.network.throughput > 0
    assert state.network.latency > 0


def test_return_and_reset() -> None:
    engine = SimulationEngine()
    engine.deploy_uav()
    for _ in range(120): engine.advance()
    engine.return_uav()
    for _ in range(120): engine.advance()
    assert engine.snapshot().uav.deployment_state == DeploymentState.LANDED
    assert engine.reset().uav.deployment_state == DeploymentState.STANDBY


def test_metrics_are_deterministic_for_equivalent_engines() -> None:
    first, second = SimulationEngine(), SimulationEngine()
    first.deploy_uav(); second.deploy_uav()
    for _ in range(12): first.advance(); second.advance()
    assert first.snapshot().network.model_dump() == second.snapshot().network.model_dump()
    assert first.snapshot().rf.model_dump() == second.snapshot().rf.model_dump()


def test_api_controls_and_state() -> None:
    simulation.reset()
    with TestClient(app) as client:
        assert client.get("/api/state").status_code == 200
        assert client.post("/api/simulation/deploy").json()["uav"]["deployment_state"] == "DEPLOYING"
        assert client.post("/api/simulation/return").status_code == 200
        assert client.post("/api/simulation/reset").json()["uav"]["deployment_state"] == "STANDBY"
