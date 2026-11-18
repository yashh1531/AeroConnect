"""Geographic helpers for the communication simulation (not flight physics)."""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2, degrees [0, 360)."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(rlat2)
    y = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(rlat2) * math.cos(
        dlon
    )
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def move_towards(
    lat: float,
    lon: float,
    target_lat: float,
    target_lon: float,
    step_m: float,
) -> tuple[float, float, float, bool]:
    """
    Move from (lat, lon) toward target by at most step_m metres.

    Returns (new_lat, new_lon, heading_deg, arrived).
    """
    distance = haversine_m(lat, lon, target_lat, target_lon)
    heading = bearing_deg(lat, lon, target_lat, target_lon)
    if distance <= step_m or distance < 1.0:
        return target_lat, target_lon, heading, True

    fraction = step_m / distance
    new_lat = lat + (target_lat - lat) * fraction
    new_lon = lon + (target_lon - lon) * fraction
    return new_lat, new_lon, heading, False


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
