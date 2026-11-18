#!/usr/bin/env python3
"""Forward Pixhawk MAVLink telemetry to the Aero Connect backend."""

from __future__ import annotations

import argparse
import json
import math
import signal
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.request import Request, urlopen

from pymavlink import mavutil


DEFAULT_DEVICE = "/dev/ttyACM0"
DEFAULT_BAUD = 115200
DEFAULT_ENDPOINT = "http://192.168.1.10:8000/api/telemetry/pixhawk"
GPS_STALE_SECONDS = 5.0
HEARTBEAT_TIMEOUT_SECONDS = 10.0


@dataclass
class Telemetry:
    """Fields accepted by backend/app/telemetry/models.py::PixhawkTelemetry."""

    armed: bool | None = None
    flight_mode: str | None = None
    gps_fix: int | None = None
    satellites: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    gps_altitude: float | None = None
    gps_valid: bool = False
    altitude: float | None = None
    relative_altitude: float | None = None
    ground_speed: float | None = None
    heading: float | None = None
    roll: float | None = None
    pitch: float | None = None
    yaw: float | None = None
    airspeed: float | None = None
    throttle: float | None = None
    battery_voltage: float | None = None
    battery_current: float | None = None
    battery_remaining: float | None = None
    last_gps_at: float | None = field(default=None, repr=False)

    def payload(self, now: float) -> dict[str, Any]:
        payload = self.__dict__.copy()
        payload.pop("last_gps_at")
        if self.last_gps_at is None or now - self.last_gps_at > GPS_STALE_SECONDS:
            payload["gps_valid"] = False
            payload["latitude"] = None
            payload["longitude"] = None
            payload["gps_altitude"] = None
        return payload


def valid_coordinates(latitude: float, longitude: float) -> bool:
    return (
        -90 <= latitude <= 90
        and -180 <= longitude <= 180
        and not (latitude == 0 and longitude == 0)
    )


def set_message_intervals(connection: Any) -> None:
    """Request the MAVLink messages used by the backend telemetry schema."""

    message_ids = (
        mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT,
        mavutil.mavlink.MAVLINK_MSG_ID_GPS_RAW_INT,
        mavutil.mavlink.MAVLINK_MSG_ID_ATTITUDE,
        mavutil.mavlink.MAVLINK_MSG_ID_VFR_HUD,
        mavutil.mavlink.MAVLINK_MSG_ID_SYS_STATUS,
        mavutil.mavlink.MAVLINK_MSG_ID_HEARTBEAT,
    )
    for message_id in message_ids:
        connection.mav.command_long_send(
            connection.target_system,
            connection.target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
            0,
            message_id,
            1_000_000,  # One message per second is sufficient for a two-second POST cadence.
            0,
            0,
            0,
            0,
            0,
        )


def update_telemetry(telemetry: Telemetry, message: Any, now: float) -> bool:
    """Apply one MAVLink message and return whether it was a heartbeat."""

    message_type = message.get_type()
    if message_type == "HEARTBEAT":
        telemetry.armed = bool(message.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        telemetry.flight_mode = mavutil.mode_string_v10(message)
        return True

    if message_type == "GPS_RAW_INT":
        telemetry.gps_fix = message.fix_type
        telemetry.satellites = message.satellites_visible
        latitude = message.lat / 10_000_000
        longitude = message.lon / 10_000_000
        telemetry.last_gps_at = now
        telemetry.gps_valid = message.fix_type >= 3 and valid_coordinates(latitude, longitude)
        if telemetry.gps_valid:
            telemetry.latitude = latitude
            telemetry.longitude = longitude
            telemetry.gps_altitude = message.alt / 1_000
        else:
            # Never keep an earlier GPS position after the flight controller reports no fix.
            telemetry.latitude = None
            telemetry.longitude = None
            telemetry.gps_altitude = None
        return False

    if message_type == "GLOBAL_POSITION_INT":
        telemetry.altitude = message.alt / 1_000
        telemetry.relative_altitude = message.relative_alt / 1_000
        telemetry.ground_speed = math.hypot(message.vx, message.vy) / 100
        if message.hdg != 65535:
            telemetry.heading = message.hdg / 100
        return False

    if message_type == "ATTITUDE":
        telemetry.roll = message.roll
        telemetry.pitch = message.pitch
        telemetry.yaw = message.yaw
        return False

    if message_type == "VFR_HUD":
        telemetry.airspeed = message.airspeed
        telemetry.ground_speed = message.groundspeed
        telemetry.heading = message.heading if message.heading >= 0 else None
        telemetry.throttle = message.throttle if message.throttle >= 0 else None
        return False

    if message_type == "SYS_STATUS":
        telemetry.battery_voltage = message.voltage_battery / 1_000 if message.voltage_battery != 65535 else None
        telemetry.battery_current = message.current_battery / 100 if message.current_battery != -1 else None
        telemetry.battery_remaining = message.battery_remaining if message.battery_remaining != -1 else None
    return False


def post(endpoint: str, payload: dict[str, Any]) -> None:
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        response.read()


def connect(device: str, baud: int, stop_event: threading.Event) -> Any:
    print(f"connecting to Pixhawk at {device} ({baud} baud)", flush=True)
    connection = mavutil.mavlink_connection(device, baud=baud)
    while not stop_event.is_set():
        heartbeat = connection.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
        if heartbeat is not None:
            print("Pixhawk heartbeat received; requesting telemetry intervals", flush=True)
            set_message_intervals(connection)
            return connection
    connection.close()
    raise InterruptedError("shutdown requested")


def run(device: str, baud: int, endpoint: str, interval: float, stop_event: threading.Event) -> None:
    retry_delay = 1.0
    while not stop_event.is_set():
        connection = None
        try:
            connection = connect(device, baud, stop_event)
            telemetry = Telemetry()
            last_heartbeat_at = time.monotonic()
            next_post_at = last_heartbeat_at
            retry_delay = 1.0
            print("Pixhawk telemetry forwarding active", flush=True)

            while not stop_event.is_set():
                now = time.monotonic()
                message = connection.recv_match(blocking=False)
                if message is not None and update_telemetry(telemetry, message, now):
                    last_heartbeat_at = now

                if now - last_heartbeat_at > HEARTBEAT_TIMEOUT_SECONDS:
                    raise ConnectionError("MAVLink heartbeat timed out")

                if now >= next_post_at:
                    payload = telemetry.payload(now)
                    try:
                        post(endpoint, payload)
                        print(
                            "telemetry sent "
                            f"armed={payload['armed']} gps_valid={payload['gps_valid']} "
                            f"speed={payload['ground_speed']}",
                            flush=True,
                        )
                    except Exception as error:
                        # Backend outages do not discard the serial connection or stop future reports.
                        print(f"telemetry POST failed: {error}", flush=True)
                    next_post_at = now + interval

                if message is None:
                    stop_event.wait(0.05)
        except InterruptedError:
            break
        except Exception as error:
            print(f"Pixhawk connection lost: {error}; retrying in {retry_delay:.0f}s", flush=True)
            stop_event.wait(retry_delay)
            retry_delay = min(retry_delay * 2, 15.0)
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
    print("Pixhawk telemetry agent stopped", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be greater than 0")

    stop_event = threading.Event()

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    run(args.device, args.baud, args.endpoint, args.interval, stop_event)


if __name__ == "__main__":
    main()
