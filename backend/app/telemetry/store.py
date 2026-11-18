"""In-memory latest-value store for Raspberry Pi telemetry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.telemetry.models import (
    BackhaulTelemetry,
    LiveClient,
    PiTelemetry,
    RfTelemetry,
    PixhawkTelemetry,
)


class LiveClientsStore:
    """Keeps the latest Pi client scan while it remains fresh."""

    def __init__(self, freshness_seconds: int = 15) -> None:
        self.freshness = timedelta(seconds=freshness_seconds)
        self.latest: list[LiveClient] = []
        self.received_at: datetime | None = None

    def record(
        self,
        clients: list[LiveClient],
        received_at: datetime | None = None,
    ) -> datetime:
        self.latest = clients
        self.received_at = received_at or datetime.now(timezone.utc)
        return self.received_at

    def fresh_clients(self, now: datetime | None = None) -> list[LiveClient] | None:
        if self.received_at is None:
            return None
        if (now or datetime.now(timezone.utc)) - self.received_at > self.freshness:
            return None
        return self.latest

    def clear(self) -> None:
        self.latest = []
        self.received_at = None


class PiTelemetryStore:
    """Keeps only the most recently accepted Pi report and its receive time."""

    def __init__(self, freshness_seconds: int = 15) -> None:
        self.freshness = timedelta(seconds=freshness_seconds)
        self.latest: PiTelemetry | None = None
        self.received_at: datetime | None = None

    def record(self, telemetry: PiTelemetry, received_at: datetime | None = None) -> datetime:
        self.latest = telemetry
        self.received_at = received_at or datetime.now(timezone.utc)
        return self.received_at

    def fresh_telemetry(self, now: datetime | None = None) -> PiTelemetry | None:
        if self.latest is None or self.received_at is None:
            return None
        current_time = now or datetime.now(timezone.utc)
        if current_time - self.received_at > self.freshness:
            return None
        return self.latest

    def clear(self) -> None:
        self.latest = None
        self.received_at = None


class RfTelemetryStore:
    """Keeps only the most recently accepted RTL-SDR scan summary."""

    def __init__(self, freshness_seconds: int = 15) -> None:
        self.freshness = timedelta(seconds=freshness_seconds)
        self.latest: RfTelemetry | None = None
        self.received_at: datetime | None = None

    def record(self, telemetry: RfTelemetry, received_at: datetime | None = None) -> datetime:
        self.latest = telemetry
        self.received_at = received_at or datetime.now(timezone.utc)
        return self.received_at

    def fresh_telemetry(self, now: datetime | None = None) -> RfTelemetry | None:
        if self.latest is None or self.received_at is None:
            return None
        if (now or datetime.now(timezone.utc)) - self.received_at > self.freshness:
            return None
        return self.latest

    def clear(self) -> None:
        self.latest = None
        self.received_at = None


class BackhaulTelemetryStore:
    """Keeps only the most recent Pi-to-backend backhaul probe."""

    def __init__(self, freshness_seconds: int = 15) -> None:
        self.freshness = timedelta(seconds=freshness_seconds)
        self.latest: BackhaulTelemetry | None = None
        self.received_at: datetime | None = None

    def record(
        self,
        telemetry: BackhaulTelemetry,
        received_at: datetime | None = None,
    ) -> datetime:
        self.latest = telemetry
        self.received_at = received_at or datetime.now(timezone.utc)
        return self.received_at

    def fresh_telemetry(
        self,
        now: datetime | None = None,
    ) -> BackhaulTelemetry | None:
        if self.latest is None or self.received_at is None:
            return None
        if (now or datetime.now(timezone.utc)) - self.received_at > self.freshness:
            return None
        return self.latest

    def clear(self) -> None:
        self.latest = None
        self.received_at = None


class PixhawkTelemetryStore:
    """Keeps only the most recently accepted Pixhawk telemetry report."""

    def __init__(self, freshness_seconds: int = 15) -> None:
        self.freshness = timedelta(seconds=freshness_seconds)
        self.latest: PixhawkTelemetry | None = None
        self.received_at: datetime | None = None

    def record(
        self,
        telemetry: PixhawkTelemetry,
        received_at: datetime | None = None,
    ) -> datetime:
        self.latest = telemetry
        self.received_at = received_at or datetime.now(timezone.utc)
        return self.received_at

    def fresh_telemetry(
        self,
        now: datetime | None = None,
    ) -> PixhawkTelemetry | None:
        if self.latest is None or self.received_at is None:
            return None

        current_time = now or datetime.now(timezone.utc)

        if current_time - self.received_at > self.freshness:
            return None

        return self.latest

    def clear(self) -> None:
        self.latest = None
        self.received_at = None
