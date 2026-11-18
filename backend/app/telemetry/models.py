"""Pydantic models for telemetry reported by the Raspberry Pi edge node."""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, IPvAnyAddress, field_validator, model_validator


class PiTelemetry(BaseModel):
    cpu_usage: float = Field(ge=0, le=100)
    memory_usage: float = Field(ge=0, le=100)
    temperature: float
    uptime: int = Field(ge=0, description="Seconds")
    storage_usage: float = Field(ge=0, le=100)
    network_interface_status: Literal["up", "degraded", "down"]
    ip_address: IPvAnyAddress


class RfOccupiedBand(BaseModel):
    start_mhz: float
    end_mhz: float
    peak_mhz: float
    peak_power_db: float
    bins: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_frequency_range(self) -> "RfOccupiedBand":
        if self.end_mhz < self.start_mhz:
            raise ValueError("end_mhz must be greater than or equal to start_mhz")
        if not self.start_mhz <= self.peak_mhz <= self.end_mhz:
            raise ValueError("peak_mhz must be within the occupied band")
        return self


class RfTelemetry(BaseModel):
    scan_start_mhz: float
    scan_end_mhz: float
    noise_floor_db: float
    threshold_db: float
    peak_frequency_mhz: float
    peak_power_db: float
    activity_percent: float = Field(ge=0, le=100)
    occupied_bins: int = Field(ge=0)
    total_bins: int = Field(gt=0)
    occupied_bands: list[RfOccupiedBand]

    @model_validator(mode="after")
    def validate_scan(self) -> "RfTelemetry":
        if self.scan_end_mhz <= self.scan_start_mhz:
            raise ValueError("scan_end_mhz must be greater than scan_start_mhz")
        if not self.scan_start_mhz <= self.peak_frequency_mhz <= self.scan_end_mhz:
            raise ValueError("peak_frequency_mhz must be inside the scan range")
        if self.occupied_bins > self.total_bins:
            raise ValueError("occupied_bins cannot exceed total_bins")
        return self


class BackhaulTelemetry(BaseModel):
    """End-to-end Pi-to-backend reachability probe result."""

    reachable: bool
    latency_ms: float | None = Field(default=None, ge=0)
    packet_loss_percent: float | None = Field(default=None, ge=0, le=100)
    target: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_unreachable_probe(self) -> "BackhaulTelemetry":
        if not self.reachable and self.latency_ms is not None:
            raise ValueError("latency_ms must be null when the target is unreachable")
        return self


class PixhawkTelemetry(BaseModel):
    armed: bool | None = None
    flight_mode: str | None = None

    gps_fix: int | None = Field(default=None, ge=0)
    satellites: int | None = Field(default=None, ge=0)
    latitude: float | None = None
    longitude: float | None = None
    gps_altitude: float | None = None
    gps_valid: bool = False

    altitude: float | None = None
    relative_altitude: float | None = None
    ground_speed: float | None = Field(default=None, ge=0)
    heading: float | None = Field(default=None, ge=0, le=360)

    roll: float | None = None
    pitch: float | None = None
    yaw: float | None = None

    airspeed: float | None = Field(default=None, ge=0)
    throttle: float | None = Field(default=None, ge=0, le=100)

    battery_voltage: float | None = Field(default=None, ge=0)
    battery_current: float | None = None
    battery_remaining: float | None = Field(default=None, ge=0, le=100)


MAC_ADDRESS_PATTERN = re.compile(r"^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$", re.IGNORECASE)


class LiveClient(BaseModel):
    """One device observed on the Pi's client-facing network."""

    ip: IPvAnyAddress
    mac: str = Field(min_length=17, max_length=17)
    hostname: str | None = Field(default=None, max_length=255)
    status: Literal["CONNECTED", "STALE", "DISCONNECTED"]
    interface: str = Field(min_length=1, max_length=64)
    last_seen: datetime | None = None

    @field_validator("mac")
    @classmethod
    def validate_mac(cls, value: str) -> str:
        if not MAC_ADDRESS_PATTERN.fullmatch(value):
            raise ValueError("mac must be a colon-separated hardware address")
        return value.lower()

    @field_validator("hostname", mode="before")
    @classmethod
    def normalize_hostname(cls, value: str | None) -> str | None:
        if value is None:
            return None
        hostname = value.strip()
        return hostname or None


class LiveClientsPayload(BaseModel):
    """Latest client scan submitted by the Pi discovery agent."""

    clients: list[LiveClient] = Field(default_factory=list)
