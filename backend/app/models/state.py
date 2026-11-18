"""
Core application state model.

Task 1 keeps this minimal. Later milestones will extend this with UAV,
network, RF, camera, and incident fields — all driven by simulation or
hardware sources, never by fake UI-only numbers.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class DataSource(str, Enum):
    """Where a value comes from. Always surfaced to the UI."""

    SIMULATED = "simulated"
    HARDWARE = "hardware"


class ConnectionStatus(str, Enum):
    IDLE = "idle"
    LIVE = "live"
    DEGRADED = "degraded"


class AppState(BaseModel):
    """Minimal live state shared over WebSocket."""

    tick: int = 0
    status: ConnectionStatus = ConnectionStatus.IDLE
    message: str = "Backend online. Waiting for clients."
    data_source: DataSource = DataSource.SIMULATED
    server_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def advance(self) -> "AppState":
        """Produce the next tick of live state (deterministic, server-owned)."""
        self.tick += 1
        self.status = ConnectionStatus.LIVE
        self.message = f"Live state tick #{self.tick}"
        self.server_time = datetime.now(timezone.utc)
        return self
